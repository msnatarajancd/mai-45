"""Directory publication against isolated official captures; approvals are test-only."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from knowledge.candidates import candidate_context_hash, make_candidate
from knowledge.models import DisasterPhase, ResourceRecord, ReviewDecision, ReviewStatus, SourceBundle
from knowledge.review import PublicationError, mark_stale, review_candidate, review_source
from knowledge.store import SourceStore, context_hash, replace_record

ROOT = Path(__file__).resolve().parents[1]


def api():
    import knowledge.resources as directory
    from domain.resources import ResourceQuery
    return directory, ResourceQuery


@pytest.fixture
def directory_store(tmp_path):
    # Exact real bytes, new isolated review state. No production review is changed.
    real = SourceStore(ROOT / 'data/official_sources')
    store = SourceStore(tmp_path / 'official')
    original = real.load('miami-dade-eeap')
    source = replace_record(original.source, review_status=ReviewStatus.REVIEW_REQUIRED,
                            reviewer=None, reviewed_at=None)
    bundle = SourceBundle(source=source, chunks=[replace_record(c, review_status=ReviewStatus.REVIEW_REQUIRED)
                                               for c in original.chunks])
    with store.admin_lock():
        store.write_original(real.original(source.original_content_hash))
        store.save_locked(bundle)
    review_source(store, source.source_id, ReviewDecision(reviewer='TEST ONLY source reviewer',
        expected_content_hash=source.original_content_hash, expected_context_hash=context_hash(bundle),
        provenance_checked=True, content_checked=True, geographic_scope_checked=True,
        applicability_checked=True, caveats_preserved=True))
    candidate = make_candidate(bundle, bundle.chunks[0], phases=[DisasterPhase.PREPARE],
                               context=bundle.chunks, caveats=['Current availability is not verified.'])
    with store.admin_lock():
        store.save_candidate_locked(candidate)
    review_candidate(store, source.source_id, candidate.chunk_id, ReviewDecision(reviewer='TEST ONLY passage reviewer',
        expected_content_hash=source.original_content_hash, expected_context_hash=candidate_context_hash(candidate),
        provenance_checked=True, content_checked=True, geographic_scope_checked=True,
        applicability_checked=True, caveats_preserved=True, standalone_passage_checked=True))
    return store, candidate


def pending_listing(store, candidate, **changes):
    directory, _ = api()
    resource = ResourceRecord(resource_id='eeap-test', source_id='miami-dade-eeap',
        official_name='Emergency & Evacuation Assistance Program (EEAP)',
        service_category='evacuation', service_area='US-FL-MIAMI-DADE',
        official_url=candidate.official_url, prerequisites=[],
        limitations=['Current availability not verified.'])
    fields = {name: [candidate.chunk_id] for name in ('official_name', 'service_category', 'description')}
    data = dict(resource=resource, provider='Miami-Dade County', description='free evacuation',
        enrollment_timing=None, matching_tags=['transportation', 'evacuation_support'],
        counties=['US-FL-MIAMI-DADE'], phases=[DisasterPhase.PREPARE], purposes=['planning'],
        hazards=candidate.hazards, hazard_independent=False, supporting_candidate_ids=[candidate.chunk_id],
        field_evidence=fields, source_content_hash=candidate.original_content_hash,
        review=directory.DirectoryReview(review_due_at=datetime.now(timezone.utc)+timedelta(days=29)))
    data.update(changes)
    listing = directory.ResourceListing(**data)
    directory.save_listing(store, listing)
    return listing


def approved_listing(store, candidate, **changes):
    directory, _ = api()
    listing = pending_listing(store, candidate, **changes)
    inspection = directory.inspect_listing(store, listing.resource.resource_id)
    return directory.approve_listing(store, listing.resource.resource_id, reviewer='TEST ONLY directory reviewer',
                                     expected_fingerprint=inspection['fingerprint'])


def lookup(store, **changes):
    directory, Query = api()
    args = dict(needs='transportation', county='Miami-Dade', hazard='hurricane', phase='prepare', purpose='planning')
    args.update(changes)
    return directory.lookup_resources(store, Query(**args), datetime.now(timezone.utc))


def test_directory_module_is_implemented():
    import importlib.util
    assert importlib.util.find_spec('knowledge.resources') is not None


def test_approved_matching_uses_real_publication_gate_and_unknown_availability(directory_store):
    store, candidate = directory_store
    approved_listing(store, candidate)
    result = lookup(store)
    assert result.status == 'matches'
    assert len(result.records) == 1
    record = result.records[0]
    assert record.official_name == 'Emergency & Evacuation Assistance Program (EEAP)'
    assert record.availability_status == 'UNKNOWN'
    assert record.retrieved_at == store.load('miami-dade-eeap').source.retrieved_at
    assert record.source_reviewed_at == store.load('miami-dade-eeap').source.reviewed_at


@pytest.mark.parametrize('query', [dict(county=None), dict(county='Broward'), dict(phase='respond'),
                                   dict(purpose='urgent_assistance'), dict(needs='medical'), dict(hazard=None)])
def test_query_cannot_expand_reviewed_applicability(directory_store, query):
    store, candidate = directory_store
    approved_listing(store, candidate)
    assert lookup(store, **query).records == []


def test_unknown_hazard_requires_explicit_listing_review(directory_store):
    store, candidate = directory_store
    approved_listing(store, candidate, hazard_independent=True)
    assert lookup(store, hazard=None).status == 'matches'


def test_source_approval_does_not_approve_listing(directory_store):
    store, candidate = directory_store
    pending_listing(store, candidate)
    result = lookup(store)
    assert result.status == 'review_required' and result.records == []


@pytest.mark.parametrize('change', ['description', 'matching_tags', 'review_due_at', 'reviewed_at', 'field_evidence', 'source_content_hash'])
def test_listing_changes_invalidate_fingerprint(directory_store, change):
    store, candidate = directory_store
    approved_listing(store, candidate)
    path = store.root / 'resources/eeap-test.json'
    data = json.loads(path.read_text())
    if change == 'review_due_at': data['review']['review_due_at'] = (datetime.now(timezone.utc)+timedelta(days=28)).isoformat()
    elif change == 'reviewed_at': data['review']['reviewed_at'] = (datetime.fromisoformat(data['review']['reviewed_at'])-timedelta(seconds=1)).isoformat()
    elif change == 'description': data[change] = 'evacuation'
    elif change == 'field_evidence': data[change]['description'] = []
    elif change == 'source_content_hash': data[change] = '0'*64
    else: data[change] += ['medical']
    path.write_text(json.dumps(data))
    assert lookup(store).records == []


def test_deadline_can_be_future_but_actual_review_cannot(directory_store):
    directory, _ = api()
    now = datetime.now(timezone.utc)
    directory.DirectoryReview(review_due_at=now+timedelta(days=29))
    with pytest.raises(ValidationError):
        directory.DirectoryReview(status='APPROVED', reviewer='TEST', reviewed_at=now+timedelta(days=1),
            review_due_at=now+timedelta(days=29), fingerprint='0'*64)
    with pytest.raises(ValidationError):
        directory.DirectoryReview(review_due_at=now.replace(tzinfo=None))
    store, candidate = directory_store
    listing = approved_listing(store, candidate)
    from domain.resources import ResourceQuery
    result = directory.lookup_resources(store, ResourceQuery(needs='transportation', county='Miami-Dade',
        phase='prepare', hazard='hurricane', purpose='planning'), listing.review.review_due_at+timedelta(seconds=1))
    assert result.records == []


def test_contact_needs_field_specific_approved_support(directory_store):
    directory, _ = api()
    store, candidate = directory_store
    listing = pending_listing(store, candidate)
    bad = replace_record(listing.resource, official_contact='555-0100', contact_evidence_chunk_id=candidate.chunk_id)
    listing = replace_record(listing, resource=bad,
        field_evidence={**listing.field_evidence, 'official_contact': [candidate.chunk_id]})
    directory.save_listing(store, listing)
    with pytest.raises(PublicationError):
        directory.approve_listing(store, 'eeap-test', reviewer='TEST ONLY',
                                 expected_fingerprint=directory.inspect_listing(store, 'eeap-test')['fingerprint'])


def test_candidate_revoked_or_missing_removes_next_lookup(directory_store):
    store, candidate = directory_store
    approved_listing(store, candidate)
    assert lookup(store).records
    (store.root / 'candidates' / candidate.source_id / (candidate.chunk_id+'.json')).unlink()
    assert lookup(store).records == []


def test_source_revoked_removes_next_lookup(directory_store):
    store, candidate = directory_store
    approved_listing(store, candidate)
    mark_stale(store, 'miami-dade-eeap')
    assert lookup(store).records == []


def test_revoke_records_identity_and_stops_publication(directory_store):
    directory, _ = api()
    store, candidate = directory_store
    approved_listing(store, candidate)
    directory.revoke_listing(store, 'eeap-test', reviewer='TEST ONLY', reason='Test revocation')
    assert lookup(store).records == []
    assert directory.load_listing(store, 'eeap-test').review.status == 'REVOKED'


def test_stale_inspection_cannot_approve(directory_store):
    directory, _ = api()
    store, candidate = directory_store
    listing = pending_listing(store, candidate)
    fingerprint = directory.inspect_listing(store, 'eeap-test')['fingerprint']
    directory.save_listing(store, replace_record(listing, matching_tags=['transportation', 'medical']))
    with pytest.raises(PublicationError):
        directory.approve_listing(store, 'eeap-test', reviewer='TEST ONLY', expected_fingerprint=fingerprint)


def test_directory_uses_one_lock_and_storage_failure_differs_from_no_match(directory_store):
    store, candidate = directory_store
    approved_listing(store, candidate)
    # SourceStore lock is non-reentrant; a nested acquisition would make matching fail.
    assert lookup(store).status == 'matches'
    with store.admin_lock():
        assert lookup(store).status == 'unavailable'
    assert lookup(store, needs='unrelated').status == 'no_match'


def test_official_links_import_and_remain_available_when_store_absent(tmp_path):
    from services.resources import OFFICIAL_LINKS, lookup_resources
    from domain.resources import ResourceQuery
    assert OFFICIAL_LINKS and all(item.url.startswith('https://') for item in OFFICIAL_LINKS)
    result = lookup_resources(ResourceQuery(needs='transportation'), store=SourceStore(tmp_path/'missing'))
    assert result.status == 'unavailable' and result.records == []


def test_prepare_candidate_cannot_publish_under_respond_listing(directory_store):
    directory, _ = api()
    store, candidate = directory_store
    listing = pending_listing(store, candidate, phases=[DisasterPhase.RESPOND], purposes=['urgent_assistance'])
    with pytest.raises(PublicationError):
        directory.approve_listing(store, 'eeap-test', reviewer='TEST ONLY',
                                 expected_fingerprint=directory.inspect_listing(store, 'eeap-test')['fingerprint'])


@pytest.mark.parametrize('source_id,url', [
    ('miami-dade-text-911', 'https://www.mdso.com/text-911'),
    ('miami-dade-weather-contacts', 'https://www.miamidade.gov/initiative/weather-ready/contact.page'),
    ('fcc-text-911', 'https://www.fcc.gov/consumers/guides/what-you-need-know-about-text-911'),
])
def test_new_directory_sources_start_without_review(source_id, url):
    from knowledge.sources import get_source
    source = get_source(source_id).source
    assert source.official_url == url
    assert source.review_status is ReviewStatus.LINK_ONLY
    assert source.reviewed_at is None and source.reviewer is None


@pytest.mark.parametrize('source_id,phrase', [
    ('miami-dade-text-911', 'Communication over text message is only available in English at this time'),
    ('miami-dade-weather-contacts', 'Miami-Dade County Contact Center'),
])
def test_directory_captures_extract_only_main_content_and_verified_title(source_id, phrase):
    from knowledge.extraction import extract_sections, ExtractionError
    store = SourceStore(ROOT/'data/official_sources')
    source = store.load(source_id).source
    raw = store.original(source.original_content_hash)
    chunks = extract_sections(raw, source)
    text = '\n'.join(c.guidance_text for c in chunks)
    assert phrase in text
    assert 'Sheriff Rosie Socials' not in text
    with pytest.raises(ExtractionError):
        extract_sections(raw.replace(b'<h1', b'<h4').replace(b'</h1', b'</h4'), source)


def test_legacy_directory_boundary_returns_only_approved_records(directory_store):
    from knowledge.service import FoundationKnowledgeService
    from knowledge.models import KnowledgeRequest, Hazard
    store, candidate = directory_store
    approved_listing(store, candidate)
    result = FoundationKnowledgeService(store).find_resources(KnowledgeRequest(hazard=Hazard.HURRICANE,
        disaster_phase=DisasterPhase.PREPARE, jurisdiction='US-FL-MIAMI-DADE', household_needs=['transportation']))
    assert result.retrieval_status.value == 'SUCCESS'
    assert len(result.resources) == 1
    assert result.source_metadata[0].source_id == 'miami-dade-eeap'


def test_hazard_independent_listing_still_checks_known_hazard_evidence(directory_store):
    store, candidate = directory_store
    approved_listing(store, candidate, hazard_independent=True, hazards=[])
    assert lookup(store, hazard='hurricane').status == 'matches'
    assert lookup(store, hazard='wildfire').records == []


def test_shipped_packets_remain_pending_and_evidence_linked(tmp_path):
    """Seven captured packets can be reviewed; failed FCC capture cannot publish."""
    import shutil
    directory, _ = api()
    real = SourceStore(ROOT/'data/official_sources')
    store = SourceStore(tmp_path/'copy')
    source_ids = ('miami-dade-eeap', 'miami-dade-text-911', 'miami-dade-weather-contacts')
    with store.admin_lock():
        for source_id in source_ids:
            bundle = real.load(source_id)
            assert bundle.source.review_status != ReviewStatus.REVIEWED
            store.write_original(real.original(bundle.source.original_content_hash))
            store.save_locked(bundle)
            for c in real.list_candidates(source_id):
                assert c.review_status.value == 'PENDING'
                store.save_candidate_locked(c)
    shutil.copytree(real.root/'resources', store.root/'resources')
    captured = []
    for path in (store.root/'resources').glob('*.json'):
        listing = directory.load_listing(store,path.stem)
        assert listing.review.status == 'PENDING' and listing.review.reviewer is None
        if listing.source_content_hash: captured.append(listing)
    assert 5 <= len(captured) <= 8
    for source_id in source_ids:
        b = store.load(source_id)
        review_source(store,source_id,ReviewDecision(reviewer='TEST ONLY source reviewer',
            expected_content_hash=b.source.original_content_hash,expected_context_hash=context_hash(b),
            provenance_checked=True,content_checked=True,geographic_scope_checked=True,
            applicability_checked=True,caveats_preserved=True))
        for c in store.list_candidates(source_id):
            review_candidate(store,source_id,c.chunk_id,ReviewDecision(reviewer='TEST ONLY passage reviewer',
                expected_content_hash=c.original_content_hash,expected_context_hash=candidate_context_hash(c),
                provenance_checked=True,content_checked=True,geographic_scope_checked=True,
                applicability_checked=True,caveats_preserved=True,standalone_passage_checked=True))
    for listing in captured:
        inspection=directory.inspect_listing(store,listing.resource.resource_id)
        assert inspection['publication_blockers'] == []
        directory.approve_listing(store,listing.resource.resource_id,reviewer='TEST ONLY directory reviewer',
                                  expected_fingerprint=inspection['fingerprint'])
    assert lookup(store, needs='communication_access', phase='respond', purpose='communication_access', hazard=None).records
    assert lookup(real, needs='communication_access', phase='respond', purpose='communication_access', hazard=None).records == []
