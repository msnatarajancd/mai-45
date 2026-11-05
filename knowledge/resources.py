"""Human-reviewed static directory. Runtime never acquires content or signs reviews."""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from domain.resources import ResourceLookupResult, ResourceQuery, VerifiedResource
from .candidates import (candidate_context_hash, public_safety_caveats,
                         public_source_limitations, verify_candidate_publication)
from .models import (DisasterPhase, Hash, Hazard, Identifier, KnowledgeRequest,
                     ResourceRecord, StrictRecord, Text)
from .review import PublicationError
from .service import FoundationKnowledgeService
from .store import SourceStore, context_hash, replace_record

Purpose = Literal['planning', 'urgent_assistance', 'communication_access']
LIMITATIONS = ['Current availability not verified.',
               'A contact link does not confirm connection, enrollment, dispatch, rescue, or transport.']


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('timestamps must be timezone-aware')
    return value.astimezone(timezone.utc)


class DirectoryReview(BaseModel):
    """Deadlines may be future; actual events may not. Separate from StrictRecord."""
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True)
    status: Literal['PENDING', 'APPROVED', 'REVOKED'] = 'PENDING'
    reviewer: Text | None = None
    reviewed_at: datetime | None = None
    review_due_at: datetime | None = None
    fingerprint: Hash | None = None
    revoked_at: datetime | None = None
    revoked_by: Text | None = None
    revocation_reason: Text | None = None

    @field_validator('reviewed_at', 'review_due_at', 'revoked_at')
    @classmethod
    def timestamp(cls, value, info):
        if value is None:
            return None
        value = _aware(value)
        if info.field_name != 'review_due_at' and value > datetime.now(timezone.utc):
            raise ValueError('actual review events cannot be in the future')
        return value

    @field_validator('reviewer', 'revoked_by', 'revocation_reason')
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError('review identity and reason cannot be blank')
        return value

    @model_validator(mode='after')
    def state(self):
        if self.status == 'PENDING' and any((self.reviewer, self.reviewed_at, self.fingerprint)):
            raise ValueError('pending listings cannot contain approval metadata')
        if self.status == 'APPROVED' and not all((self.reviewer, self.reviewed_at, self.review_due_at, self.fingerprint)):
            raise ValueError('approved listings require identity, actual review, deadline and fingerprint')
        if self.reviewed_at and self.review_due_at:
            if not self.reviewed_at < self.review_due_at <= self.reviewed_at+timedelta(days=30):
                raise ValueError('review deadline must follow approval by at most 30 days')
        if self.status == 'REVOKED' and not all((self.revoked_at, self.revoked_by, self.revocation_reason)):
            raise ValueError('revocation requires identity, time and reason')
        if self.status != 'REVOKED' and any((self.revoked_at, self.revoked_by, self.revocation_reason)):
            raise ValueError('revocation metadata requires revoked status')
        return self


class ResourceListing(StrictRecord):
    resource: ResourceRecord
    provider: Text
    description: str = Field(min_length=1, max_length=3000)
    enrollment_timing: str | None = Field(default=None, max_length=3000)
    matching_tags: list[Text] = Field(min_length=1)
    counties: list[Text] = Field(min_length=1)
    phases: list[DisasterPhase] = Field(min_length=1)
    purposes: list[Purpose] = Field(min_length=1)
    hazards: list[Hazard] = Field(default_factory=list)
    hazard_independent: bool = False
    supporting_candidate_ids: list[Hash] = Field(default_factory=list)
    field_evidence: dict[str, list[Hash]] = Field(default_factory=dict)
    source_content_hash: Hash | None = None
    review: DirectoryReview = Field(default_factory=DirectoryReview)
    preparation_notes: list[Text] = Field(default_factory=list)

    @model_validator(mode='after')
    def applicability(self):
        if not self.hazards and not self.hazard_independent:
            raise ValueError('a listing needs explicit hazards or hazard-independent review')
        return self


def load_listing(store: SourceStore, resource_id: str) -> ResourceListing | None:
    path = store.root / 'resources' / (store._id(resource_id)+'.json')
    if not path.exists():
        return None
    listing = ResourceListing.model_validate_json(path.read_bytes())
    if listing.resource.resource_id != resource_id:
        raise ValueError('resource record identity mismatch')
    return listing


def _save_locked(store, listing):
    listing = ResourceListing.model_validate_json(listing.model_dump_json())
    store._atomic_write(store.root/'resources'/(store._id(listing.resource.resource_id)+'.json'),
                        listing.model_dump_json(indent=2).encode())


def save_listing(store, listing):
    """Save draft changes. Existing signed fingerprint will fail after any edit."""
    with store.admin_lock():
        _save_locked(store, listing)


def _fingerprint_locked(store, listing):
    data = listing.model_dump(mode='json', exclude={'review'})
    data['review_due_at'] = (listing.review.review_due_at.isoformat() if listing.review.review_due_at else None)
    data['reviewed_at'] = listing.review.reviewed_at.isoformat() if listing.review.reviewed_at else None
    data['reviewer'] = listing.review.reviewer
    bundle = store.load(listing.resource.source_id)
    data['source_context_hash'] = context_hash(bundle) if bundle else None
    data['evidence_context_hashes'] = {}
    for candidate_id in listing.supporting_candidate_ids:
        candidate = store.load_candidate(listing.resource.source_id, candidate_id)
        data['evidence_context_hashes'][candidate_id] = candidate_context_hash(candidate) if candidate else None
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _scope_covers(scope, county):
    return scope == county or county.startswith(scope+'-')


def _validate_evidence_locked(store, listing):
    """Validate every claimed phase, purpose-independent factual field, and scope."""
    resource = listing.resource
    bundle = store.load(resource.source_id)
    if bundle is None or listing.source_content_hash != bundle.source.original_content_hash:
        raise PublicationError('listing source hash is missing or has changed')
    if listing.provider != bundle.source.publisher:
        raise PublicationError('provider must match authoritative source publisher')
    if not listing.supporting_candidate_ids:
        raise PublicationError('listing has no individually approved evidence')
    FoundationKnowledgeService(store)._validate_resource_locked(resource,
        candidate_ids=listing.supporting_candidate_ids)
    candidates = {}
    for candidate_id in listing.supporting_candidate_ids:
        candidate = store.load_candidate(resource.source_id, candidate_id)
        if candidate is None:
            raise PublicationError('supporting candidate is unavailable')
        verify_candidate_publication(store, candidate)
        for county in listing.counties:
            if not _scope_covers(bundle.source.jurisdiction, county) or not _scope_covers(candidate.jurisdiction, county):
                raise PublicationError('listing county exceeds reviewed source or candidate scope')
            for phase in listing.phases:
                if phase not in bundle.source.disaster_phases or phase not in candidate.phases:
                    raise PublicationError('listing phase exceeds reviewed source or candidate scope')
                for hazard in listing.hazards:
                    verify_candidate_publication(store, candidate, KnowledgeRequest(
                        hazard=hazard, disaster_phase=phase, jurisdiction=county))
        candidates[candidate_id] = candidate
    fields = {'official_name': resource.official_name, 'service_category': resource.service_category,
              'description': listing.description}
    fields.update({f'prerequisites.{i}': text for i, text in enumerate(resource.prerequisites)})
    if listing.enrollment_timing:
        fields['enrollment_timing'] = listing.enrollment_timing
    if resource.official_contact:
        fields['official_contact'] = resource.official_contact
    if set(fields) != set(listing.field_evidence):
        raise PublicationError('every displayed factual field needs an explicit evidence mapping')
    for field, value in fields.items():
        ids = listing.field_evidence[field]
        if not ids or any(cid not in candidates for cid in ids):
            raise PublicationError('field evidence must be among the listing supporting candidates')
        if not any(value in candidates[cid].original_passage for cid in ids):
            raise PublicationError('display field is not an exact supported string: '+field)
    if resource.official_contact and resource.contact_evidence_chunk_id not in listing.field_evidence['official_contact']:
        raise PublicationError('contact evidence disagrees with field evidence')
    return bundle, candidates


def inspect_listing(store, resource_id):
    with store.admin_lock():
        listing = load_listing(store, resource_id)
        if listing is None:
            raise PublicationError('listing does not exist')
        blockers = []
        try:
            _validate_evidence_locked(store, listing)
        except (PublicationError, OSError, ValueError) as error:
            blockers.append(str(error))
        return {'listing': listing.model_dump(mode='json'),
                'fingerprint': _fingerprint_locked(store, listing), 'publication_blockers': blockers}


def approve_listing(store, resource_id, *, reviewer, expected_fingerprint):
    if not isinstance(reviewer, str) or not reviewer.strip() or '<' in reviewer or '>' in reviewer:
        raise PublicationError('an actual reviewer identity is required')
    with store.admin_lock():
        listing = load_listing(store, resource_id)
        if listing is None or listing.review.status != 'PENDING':
            raise PublicationError('only a pending listing can be approved')
        fingerprint = _fingerprint_locked(store, listing)
        if expected_fingerprint != fingerprint:
            raise PublicationError('listing or evidence changed since inspection')
        _validate_evidence_locked(store, listing)
        timestamp = datetime.now(timezone.utc)
        review = DirectoryReview(status='APPROVED', reviewer=reviewer, reviewed_at=timestamp,
                                 review_due_at=listing.review.review_due_at, fingerprint=fingerprint)
        listing = replace_record(listing, review=review)
        review = replace_record(review, fingerprint=_fingerprint_locked(store, listing))
        listing = replace_record(listing, review=review)
        _save_locked(store, listing)
        return listing


def revoke_listing(store, resource_id, *, reviewer, reason):
    with store.admin_lock():
        listing = load_listing(store, resource_id)
        if listing is None:
            raise PublicationError('listing does not exist')
        review = replace_record(listing.review, status='REVOKED', revoked_by=reviewer,
                                revoked_at=datetime.now(timezone.utc), revocation_reason=reason)
        listing = replace_record(listing, review=review)
        _save_locked(store, listing)
        return listing


def _county(value):
    # Only these explicit spellings identify the supported incident county.
    return {'Miami-Dade': 'US-FL-MIAMI-DADE', 'US-FL-MIAMI-DADE': 'US-FL-MIAMI-DADE'}.get(value)


def _matches(listing, request, county):
    return (county in listing.counties and request.phase in listing.phases
            and request.purpose in listing.purposes
            and (request.needs.casefold().strip() in {tag.casefold() for tag in listing.matching_tags})
            and ((listing.hazard_independent or request.hazard in listing.hazards)
                 if request.hazard is not None else listing.hazard_independent))


def _lookup_locked(store, request, now):
    """Return public DTO plus legacy records from the same publication snapshot."""
    path = store.root/'resources'
    if not path.is_dir():
        raise FileNotFoundError('directory records are unavailable')
    county = _county(request.county)
    if county is None:
        return (ResourceLookupResult(status='no_match', limitations=LIMITATIONS,
            missing_information=['Select the current incident county; no county is assumed.']), [], [])
    records, source_records, resource_records, blocked = [], {}, [], False
    for filename in sorted(path.glob('*.json')):
        listing = load_listing(store, filename.stem)
        if not _matches(listing, request, county):
            continue
        try:
            review = listing.review
            if (review.status != 'APPROVED' or review.reviewed_at > now
                    or review.review_due_at <= now
                    or review.fingerprint != _fingerprint_locked(store, listing)):
                raise PublicationError('listing is pending, changed, revoked, or expired')
            bundle, candidates = _validate_evidence_locked(store, listing)
            # Recheck the actual requested context, never create a guessed hazard.
            for candidate in candidates.values():
                if request.hazard is not None:
                    verify_candidate_publication(store, candidate, KnowledgeRequest(
                        hazard=Hazard(request.hazard), disaster_phase=DisasterPhase(request.phase), jurisdiction=county))
                if candidate.review.reviewed_at > now:
                    raise PublicationError('candidate review is later than lookup time')
            if bundle.source.reviewed_at > now or bundle.source.retrieved_at > now:
                raise PublicationError('source provenance is later than lookup time')
            resource = listing.resource
            source_records[bundle.source.source_id] = bundle.source
            resource_records.append(resource)
            caveats = [*resource.limitations, *public_source_limitations(bundle.source), *LIMITATIONS]
            for candidate in candidates.values():
                caveats.extend(public_safety_caveats(candidate))
            records.append(VerifiedResource(**resource.model_dump(exclude={'contact_evidence_chunk_id', 'availability_status', 'limitations'}),
                provider=listing.provider, description=listing.description, enrollment_timing=listing.enrollment_timing,
                limitations=list(dict.fromkeys(caveats)), retrieved_at=bundle.source.retrieved_at,
                source_reviewed_at=bundle.source.reviewed_at, reviewed_at=review.reviewed_at,
                review_due_at=review.review_due_at, supporting_candidate_ids=listing.supporting_candidate_ids))
        except PublicationError:
            blocked = True
    return ResourceLookupResult(status='matches' if records else 'review_required' if blocked else 'no_match',
        records=records, limitations=LIMITATIONS,
        missing_information=['Matching official listings require current source, passage, and directory review.'] if blocked else []), resource_records, list(source_records.values())


def lookup_resources(store: SourceStore, request: ResourceQuery, now: datetime | None = None) -> ResourceLookupResult:
    """Read one consistent local snapshot; distinguish storage failure from no match."""
    try:
        request = ResourceQuery.model_validate(request.model_dump())
        now = _aware(now or datetime.now(timezone.utc))
        with store.admin_lock():
            return _lookup_locked(store, request, now)[0]
    except (OSError, ValueError, TypeError):
        return ResourceLookupResult(status='unavailable', limitations=LIMITATIONS,
                                    missing_information=['The reviewed directory is unavailable. Use official entry links.'])


def find_knowledge_resources(store, request):
    """Legacy M3 DTO adapter, using exactly the same locked publication lookup."""
    from .models import ResourceResult, RetrievalStatus
    query = ResourceQuery(needs=request.safety_topic or next(iter(request.household_needs), 'unspecified'),
        county=request.jurisdiction, phase=request.disaster_phase.value, hazard=request.hazard.value,
        purpose='planning' if request.disaster_phase == DisasterPhase.PREPARE else 'urgent_assistance')
    try:
        with store.admin_lock():
            result, resources, sources = _lookup_locked(store, query, datetime.now(timezone.utc))
        status = {'matches': RetrievalStatus.SUCCESS, 'no_match': RetrievalStatus.NO_RELEVANT_EVIDENCE,
                  'review_required': RetrievalStatus.INSUFFICIENT_EVIDENCE}[result.status]
        return ResourceResult(resources=resources, source_metadata=sources, matching_context=request,
            retrieval_status=status, limitations=result.limitations, missing_information=result.missing_information)
    except (OSError, ValueError, TypeError):
        return ResourceResult(resources=[], source_metadata=[], matching_context=request,
            retrieval_status=RetrievalStatus.UNAVAILABLE, limitations=LIMITATIONS,
            missing_information=['The reviewed directory is unavailable.'])


def main():
    parser = argparse.ArgumentParser(description='Inspect, approve or revoke a curated directory listing.')
    parser.add_argument('operation', choices=['inspect', 'approve', 'revoke'])
    parser.add_argument('--root', type=Path, default=Path('data/official_sources'))
    parser.add_argument('--resource-id', required=True)
    parser.add_argument('--reviewer')
    parser.add_argument('--expected-fingerprint')
    parser.add_argument('--reason')
    args = parser.parse_args()
    store = SourceStore(args.root)
    try:
        if args.operation == 'inspect':
            result = inspect_listing(store, args.resource_id)
        elif args.operation == 'approve':
            result = approve_listing(store, args.resource_id, reviewer=args.reviewer,
                                     expected_fingerprint=args.expected_fingerprint).model_dump(mode='json')
        else:
            result = revoke_listing(store, args.resource_id, reviewer=args.reviewer, reason=args.reason).model_dump(mode='json')
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
