"""Trusted admin review and exact-ID publication checks; no automatic signoff."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .extraction import ExtractionError, extract_sections
from .ingestion import validate_target
from .models import (Classification, ReviewDecision, ReviewRecord, ReviewStatus,
                     SourceBundle)
from .sources import get_source
from .store import SourceStore, context_hash, replace_record


class PublicationError(ValueError):
    pass


def verify_original(store: SourceStore, bundle: SourceBundle):
    source = bundle.source
    if source.classification is not Classification.OFFICIAL_SOURCE:
        raise PublicationError('SIMULATED_DEMO cannot be published as official reviewed evidence')
    if not source.original_content_hash or source.http_status != 200 or not bundle.chunks or source.failure_category:
        raise PublicationError('complete acquired provenance and actual excerpts are required')
    try:
        spec = get_source(source.source_id)
        if source.official_url != spec.source.official_url:
            raise ValueError('original URL changed')
        validate_target(spec, source.final_url)
        raw = store.original(source.original_content_hash)
        if hashlib.sha256(raw).hexdigest() != source.original_content_hash:
            raise ValueError('original hash mismatch')
        extracted = extract_sections(raw, source, charset=source.charset)
        current = [c.model_dump(exclude={'review_status'}) for c in bundle.chunks]
        expected = [c.model_dump(exclude={'review_status'}) for c in extracted]
        if current != expected:
            raise ValueError('excerpt differs from acquired document')
    except (OSError, ValueError, TypeError):
        raise PublicationError('original provenance or exact extracted content could not be verified') from None


def verify_publication(store: SourceStore, bundle: SourceBundle):
    if (bundle.source.review_status is not ReviewStatus.REVIEWED or bundle.review is None
            or any(c.review_status is not ReviewStatus.REVIEWED for c in bundle.chunks)):
        raise PublicationError('only human-reviewed sources and chunks may be published')
    verify_original(store, bundle)
    review = bundle.review
    if (review.context_hash != context_hash(bundle)
            or review.decision.expected_context_hash != review.context_hash
            or review.decision.expected_content_hash != review.content_hash):
        raise PublicationError('content or applicability changed after human review')


def review_source(store: SourceStore, source_id: str, decision: ReviewDecision) -> SourceBundle:
    """Admin-only: reviewer must inspect raw content, extracted sections and metadata.

    Timestamps are generated here, not accepted from a model/user request. All
    checks and expected hashes are mandatory and are recorded with the signoff.
    """
    decision = ReviewDecision.model_validate_json(decision.model_dump_json())
    with store.admin_lock():
        bundle = store.load(source_id)
        if bundle is None:
            raise PublicationError('source has not been acquired')
        if bundle.source.review_status not in (ReviewStatus.DOWNLOADED_UNREVIEWED, ReviewStatus.REVIEW_REQUIRED):
            raise PublicationError('source is not in a publishable review-queue state')
        verify_original(store, bundle)
        fingerprint = context_hash(bundle)
        if decision.expected_content_hash != bundle.source.original_content_hash or decision.expected_context_hash != fingerprint:
            raise PublicationError('source changed since inspection; inspect it again')
        timestamp = datetime.now(timezone.utc)
        source = replace_record(bundle.source, review_status=ReviewStatus.REVIEWED,
                                reviewer=decision.reviewer, reviewed_at=timestamp)
        chunks = [replace_record(c, review_status=ReviewStatus.REVIEWED) for c in bundle.chunks]
        reviewed = SourceBundle(source=source, chunks=chunks,
            review=ReviewRecord(reviewer=decision.reviewer, reviewed_at=timestamp,
                content_hash=source.original_content_hash, context_hash=fingerprint, decision=decision))
        verify_publication(store, reviewed)
        store.save_locked(reviewed)
        return reviewed


def mark_stale(store: SourceStore, source_id: str) -> SourceBundle:
    with store.admin_lock():
        bundle = store.load(source_id)
        if bundle is None:
            raise PublicationError('source does not exist')
        stale = SourceBundle(source=replace_record(bundle.source, review_status=ReviewStatus.STALE),
            chunks=[replace_record(c, review_status=ReviewStatus.STALE) for c in bundle.chunks])
        store.save_locked(stale)
        return stale


def review_candidate(store: SourceStore, source_id: str, chunk_id: str,
                     decision: ReviewDecision):
    """Explicit per-excerpt decision; never approves the parent source/publication."""
    from .candidates import candidate_context_hash, verify_candidate_trace
    from .models import CandidateStatus
    decision = ReviewDecision.model_validate_json(decision.model_dump_json())
    if not decision.standalone_passage_checked:
        raise PublicationError('review the standalone passage and safety caveats without publishing surrounding context')
    with store.admin_lock():
        candidate = store.load_candidate(source_id, chunk_id)
        if candidate is None or candidate.review_status is not CandidateStatus.PENDING:
            raise PublicationError('candidate is missing or already decided')
        verify_candidate_trace(store, candidate)
        fingerprint = candidate_context_hash(candidate)
        if (decision.expected_content_hash != candidate.original_content_hash
                or decision.expected_context_hash != fingerprint):
            raise PublicationError('candidate changed since inspection')
        reviewed = replace_record(candidate, review_status=CandidateStatus.APPROVED,
            review=ReviewRecord(reviewer=decision.reviewer, reviewed_at=datetime.now(timezone.utc),
                content_hash=candidate.original_content_hash, context_hash=fingerprint, decision=decision))
        store.save_candidate_locked(reviewed)
        return reviewed


def reject_candidate(store: SourceStore, source_id: str, chunk_id: str, *, reviewer: str,
                     reason: str, expected_content_hash: str, expected_context_hash: str):
    from .candidates import candidate_context_hash
    from .models import CandidateRejection, CandidateStatus
    with store.admin_lock():
        candidate = store.load_candidate(source_id, chunk_id)
        if candidate is None or candidate.review_status is not CandidateStatus.PENDING:
            raise PublicationError('candidate is missing or already decided')
        fingerprint = candidate_context_hash(candidate)
        if expected_content_hash != candidate.original_content_hash or expected_context_hash != fingerprint:
            raise PublicationError('candidate changed since inspection')
        rejected = replace_record(candidate, review_status=CandidateStatus.REJECTED,
            rejection=CandidateRejection(reviewer=reviewer, rejected_at=datetime.now(timezone.utc),
                reason=reason, content_hash=candidate.original_content_hash, context_hash=fingerprint))
        store.save_candidate_locked(rejected)
        return rejected


def main():
    parser = argparse.ArgumentParser(description='Inspect acquired public content or record an explicit human review.')
    parser.add_argument('action', choices=['inspect', 'approve', 'reject', 'stale'])
    parser.add_argument('--root', type=Path, default=Path('data/official_sources'))
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--chunk-id', help='Review one prepared candidate instead of the entire source.')
    parser.add_argument('--reason', help='Required explanation for rejecting a candidate.')
    parser.add_argument('--reviewer')
    parser.add_argument('--expected-content-hash')
    parser.add_argument('--expected-context-hash')
    for flag in ('provenance-checked', 'content-checked', 'geographic-scope-checked',
                 'applicability-checked', 'caveats-preserved', 'standalone-passage-checked'):
        parser.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    store = SourceStore(args.root)
    if args.chunk_id is not None:
        from .candidates import candidate_context_hash
        if args.action == 'inspect':
            candidate = store.load_candidate(args.source_id, args.chunk_id)
            if candidate is None:
                parser.error('candidate does not exist')
            print(json.dumps({'candidate': candidate.model_dump(mode='json'),
                              'expected_context_hash': candidate_context_hash(candidate)}, indent=2))
        elif args.action == 'approve':
            decision = ReviewDecision(reviewer=args.reviewer,
                expected_content_hash=args.expected_content_hash, expected_context_hash=args.expected_context_hash,
                provenance_checked=args.provenance_checked, content_checked=args.content_checked,
                geographic_scope_checked=args.geographic_scope_checked,
                applicability_checked=args.applicability_checked, caveats_preserved=args.caveats_preserved,
                standalone_passage_checked=args.standalone_passage_checked)
            print(review_candidate(store, args.source_id, args.chunk_id, decision).model_dump_json(indent=2))
        elif args.action == 'reject':
            print(reject_candidate(store, args.source_id, args.chunk_id, reviewer=args.reviewer,
                reason=args.reason, expected_content_hash=args.expected_content_hash,
                expected_context_hash=args.expected_context_hash).model_dump_json(indent=2))
        else:
            parser.error('stale is a source-level action; use reject for a pending candidate')
        return
    if args.action == 'reject':
        parser.error('reject requires --chunk-id; stale remains the source-level revocation action')
    if args.action == 'inspect':
        bundle = store.load(args.source_id)
        if bundle is None:
            parser.error('source has not been acquired')
        print(json.dumps({'bundle': bundle.model_dump(mode='json'),
                          'expected_context_hash': context_hash(bundle)}, indent=2))
    elif args.action == 'stale':
        print(mark_stale(store, args.source_id).model_dump_json(indent=2))
    else:
        decision = ReviewDecision(reviewer=args.reviewer,
            expected_content_hash=args.expected_content_hash, expected_context_hash=args.expected_context_hash,
            provenance_checked=args.provenance_checked, content_checked=args.content_checked,
            geographic_scope_checked=args.geographic_scope_checked,
            applicability_checked=args.applicability_checked, caveats_preserved=args.caveats_preserved)
        print(review_source(store, args.source_id, decision).model_dump_json(indent=2))


if __name__ == '__main__':
    main()
