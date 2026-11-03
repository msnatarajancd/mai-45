import pytest
from pydantic import ValidationError

from knowledge.ingestion import acquire_source
from knowledge.models import (Classification, DisasterPhase, Hazard, KnowledgeRequest,
    ReviewDecision, ReviewStatus, RetrievalStatus, SourceBundle)
from knowledge.review import PublicationError, review_source
from knowledge.service import FoundationKnowledgeService
from knowledge.store import SourceStore, context_hash, replace_record
from test_knowledge_ingestion import DEMO_HTML, FakeTransport, demo_spec


def request(jurisdiction='US-FL-MIAMI-DADE'):
    return KnowledgeRequest(hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER,
        jurisdiction=jurisdiction, household_needs=['SIMULATED_DEMO organizational need'], requested_evidence_count=2)


def decision(bundle):
    return ReviewDecision(reviewer='SIMULATED_DEMO unit-test identity, not a real signoff',
        expected_content_hash=bundle.source.original_content_hash, expected_context_hash=context_hash(bundle),
        provenance_checked=True, content_checked=True, geographic_scope_checked=True,
        applicability_checked=True, caveats_preserved=True)


def test_unreviewed_evidence_cannot_export_verified(tmp_path, demo_spec):
    store = SourceStore(tmp_path)
    bundle = acquire_source(demo_spec.source.source_id, store, transport=FakeTransport(demo_spec))
    service = FoundationKnowledgeService(store)
    with pytest.raises(PublicationError, match='human-reviewed'):
        service.export_to_m5(bundle.source.source_id, bundle.chunks[0].chunk_id, request())


def test_simulated_content_cannot_be_reviewed_official_evidence(tmp_path, demo_spec):
    store = SourceStore(tmp_path)
    bundle = acquire_source(demo_spec.source.source_id, store, transport=FakeTransport(demo_spec))
    with pytest.raises(PublicationError, match='SIMULATED_DEMO'):
        review_source(store, bundle.source.source_id, decision(bundle))
    with pytest.raises(ValidationError):
        replace_record(bundle.source, review_status=ReviewStatus.REVIEWED)
    assert store.load(bundle.source.source_id) == bundle


def test_no_fake_signoff_or_current_order_in_service_interfaces(tmp_path):
    service = FoundationKnowledgeService(SourceStore(tmp_path))
    guidance, resources = service.retrieve_guidance(request()), service.find_resources(request())
    assert guidance.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert resources.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert not guidance.evidence_records and not guidance.source_metadata
    assert not resources.resources
    assert any('not implemented' in value for value in guidance.limitations)
    assert any('availability' in value for value in resources.limitations)


def test_wrong_geographic_scope_fails_closed_without_review(tmp_path, demo_spec):
    store = SourceStore(tmp_path)
    bundle = acquire_source(demo_spec.source.source_id, store, transport=FakeTransport(demo_spec))
    with pytest.raises(PublicationError):
        FoundationKnowledgeService(store).export_to_m5(bundle.source.source_id, bundle.chunks[0].chunk_id,
                                                       request('CA-ON'))


def test_duplicate_chunk_ids_rejected(tmp_path, demo_spec):
    bundle = acquire_source(demo_spec.source.source_id, SourceStore(tmp_path), transport=FakeTransport(demo_spec))
    with pytest.raises(ValidationError, match='duplicate'):
        SourceBundle(source=bundle.source, chunks=[bundle.chunks[0], bundle.chunks[0]])


def test_no_verification_flags_in_runtime_request():
    with pytest.raises(ValidationError):
        KnowledgeRequest.model_validate(request().model_dump() | {'verified': True, 'reviewed': True})


@pytest.fixture
def official_acquisition(tmp_path):
    """Actual acquired CDC bytes, offline. Test signoffs exist only under tmp_path.

    The checked-in acquisition manifest is NEVER reviewed by these tests.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    fixture = root / 'tests/fixtures/knowledge/cdc_floodwater_acquired.json'
    bundle = SourceBundle.model_validate_json(fixture.read_bytes())
    raw = (root / 'data/official_sources/originals' / (bundle.source.original_content_hash + '.bin')).read_bytes()
    store = SourceStore(tmp_path)
    with store.admin_lock():
        store.write_original(raw)
        store.save_locked(bundle)
    return store, bundle, raw


def test_explicit_review_and_m5_compatibility_use_real_captured_content(official_acquisition):
    from recovery.ai_planner import RecoveryEvidence
    store, bundle, raw = official_acquisition
    reviewed = review_source(store, bundle.source.source_id, decision(bundle))
    assert reviewed.source.review_status is ReviewStatus.REVIEWED
    assert reviewed.source.reviewed_at >= bundle.source.retrieved_at
    payload = FoundationKnowledgeService(store).export_to_m5(
        bundle.source.source_id, bundle.chunks[1].chunk_id, request())
    evidence = RecoveryEvidence.model_validate(payload)
    assert evidence.verified is True and evidence.reviewed is True
    assert evidence.guidance_text == bundle.chunks[1].section_heading + '\n' + bundle.chunks[1].guidance_text


@pytest.mark.parametrize('changes', [{'jurisdiction': 'CA-ON'}, {'hazard': Hazard.WILDFIRE},
                                    {'disaster_phase': DisasterPhase.PREPARE}])
def test_wrong_context_is_excluded_even_after_review(official_acquisition, changes):
    store, bundle, _ = official_acquisition
    review_source(store, bundle.source.source_id, decision(bundle))
    with pytest.raises(PublicationError, match='not applicable'):
        FoundationKnowledgeService(store).export_to_m5(bundle.source.source_id, bundle.chunks[0].chunk_id,
            KnowledgeRequest.model_validate(request().model_dump() | changes))


def test_hash_change_after_review_requires_new_human_review(official_acquisition):
    from knowledge.sources import get_source
    store, bundle, raw = official_acquisition
    reviewed = review_source(store, bundle.source.source_id, decision(bundle))
    # A byte-only synthetic mutation of a captured fixture; not new official guidance.
    changed = acquire_source(bundle.source.source_id, store,
        transport=FakeTransport(get_source(bundle.source.source_id), raw + b'\n'))
    assert changed.source.original_content_hash != reviewed.source.original_content_hash
    assert changed.source.review_status is ReviewStatus.REVIEW_REQUIRED
    assert changed.review is None
    assert changed.source.reviewer is None and changed.source.reviewed_at is None
    with pytest.raises(PublicationError):
        FoundationKnowledgeService(store).export_to_m5(changed.source.source_id, changed.chunks[0].chunk_id, request())


def test_review_protects_against_changes_since_inspection(official_acquisition):
    store, bundle, _ = official_acquisition
    stale_decision = decision(bundle)
    altered = SourceBundle(source=replace_record(bundle.source, jurisdiction='US-FL-MIAMI-DADE'),
        chunks=[replace_record(c, geographic_scope='US-FL-MIAMI-DADE') for c in bundle.chunks])
    with store.admin_lock():
        store.save_locked(altered)
    with pytest.raises(PublicationError, match='changed since inspection'):
        review_source(store, bundle.source.source_id, stale_decision)


def test_tampered_original_and_review_context_block_publication(official_acquisition):
    store, bundle, raw = official_acquisition
    reviewed = review_source(store, bundle.source.source_id, decision(bundle))
    original_path = store.root / 'originals' / (bundle.source.original_content_hash + '.bin')
    original_path.write_bytes(raw + b'\n')
    with pytest.raises(PublicationError, match='provenance'):
        FoundationKnowledgeService(store).export_to_m5(bundle.source.source_id, bundle.chunks[0].chunk_id, request())
    original_path.write_bytes(raw)
    altered = SourceBundle(source=replace_record(reviewed.source, limitations=['Changed after review']),
                           chunks=reviewed.chunks, review=reviewed.review)
    with store.admin_lock():
        store.save_locked(altered)
    with pytest.raises(PublicationError, match='changed after human review'):
        FoundationKnowledgeService(store).export_to_m5(bundle.source.source_id, bundle.chunks[0].chunk_id, request())


def test_explicit_staleness_blocks_verified_export(official_acquisition):
    from knowledge.review import mark_stale
    store, bundle, _ = official_acquisition
    review_source(store, bundle.source.source_id, decision(bundle))
    stale = mark_stale(store, bundle.source.source_id)
    assert stale.source.review_status is ReviewStatus.STALE
    with pytest.raises(PublicationError):
        FoundationKnowledgeService(store).export_to_m5(bundle.source.source_id, bundle.chunks[0].chunk_id, request())


def test_unverified_contact_cannot_be_published(official_acquisition):
    from knowledge.models import ResourceRecord
    store, bundle, _ = official_acquisition
    review_source(store, bundle.source.source_id, decision(bundle))
    resource = ResourceRecord(resource_id='unit-test-only', source_id=bundle.source.source_id,
        official_name=bundle.chunks[0].guidance_text, service_category=bundle.chunks[0].guidance_text,
        service_area='US', official_contact='invented-contact',
        contact_evidence_chunk_id=bundle.chunks[0].chunk_id, official_url=bundle.source.official_url,
        prerequisites=[], limitations=['UNIT_TEST_ONLY; never a live resource.'])
    with pytest.raises(PublicationError, match='contact information'):
        FoundationKnowledgeService(store).validate_resource(resource)


def test_admin_lock_prevents_concurrent_replacement(official_acquisition):
    from knowledge.store import StoreBusyError
    store, bundle, _ = official_acquisition
    with store.admin_lock():
        with pytest.raises(StoreBusyError):
            review_source(store, bundle.source.source_id, decision(bundle))
