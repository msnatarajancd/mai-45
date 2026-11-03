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


def main():
    parser = argparse.ArgumentParser(description='Inspect acquired public content or record an explicit human review.')
    parser.add_argument('action', choices=['inspect', 'approve', 'stale'])
    parser.add_argument('--root', type=Path, default=Path('data/official_sources'))
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--reviewer')
    parser.add_argument('--expected-content-hash')
    parser.add_argument('--expected-context-hash')
    for flag in ('provenance-checked', 'content-checked', 'geographic-scope-checked',
                 'applicability-checked', 'caveats-preserved'):
        parser.add_argument('--' + flag, action='store_true')
    args = parser.parse_args()
    store = SourceStore(args.root)
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
