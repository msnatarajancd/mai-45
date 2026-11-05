"""Offline provenance and nonpublication of the new real review queue."""
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from knowledge.candidates import verify_candidate_trace, verify_candidate_publication
from knowledge.extraction import extract_sections
from knowledge.models import CandidateStatus, Hazard, DisasterPhase, KnowledgeRequest, RetrievalStatus
from knowledge.review import PublicationError
from knowledge.service import FoundationKnowledgeService
from knowledge.store import SourceStore


ROOT = Path(__file__).resolve().parents[1] / 'data/official_sources'
SOURCES = ['nfip-document-flood-damage', 'usagov-disaster-housing']


@pytest.fixture
def pending_store(tmp_path):
    """Isolated historical pending snapshots; never change real human approvals."""
    root = tmp_path / 'pending-review-fixture'
    shutil.copytree(ROOT, root)
    for source_id in SOURCES:
        snapshots = sorted((ROOT / 'history' / source_id).glob('*.json'))
        pending = next(p for p in snapshots if (lambda d: d['review'] is None and
            d['source']['original_content_hash'] is not None)(json.loads(p.read_bytes())))
        shutil.copyfile(pending, root / 'records' / (source_id + '.json'))
        for candidate in SourceStore(ROOT).list_candidates(source_id):
            history = ROOT / 'candidate_history' / source_id / candidate.chunk_id
            pending = next(p for p in sorted(history.glob('*.json'))
                           if json.loads(p.read_bytes())['review_status'] == 'PENDING')
            shutil.copyfile(pending, root / 'candidates' / source_id / (candidate.chunk_id + '.json'))
    return SourceStore(root)


@pytest.mark.parametrize('source_id', SOURCES)
def test_new_capture_candidates_are_exact_pending_and_not_exportable(source_id, pending_store):
    store = pending_store
    root = store.root
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    bundle = store.load(source_id)
    raw = store.original(bundle.source.original_content_hash)
    assert hashlib.sha256(raw).hexdigest() == bundle.source.original_content_hash
    assert bundle.review is None and bundle.source.reviewed_at is None
    assert bundle.source.reviewer is None
    assert bundle.source.review_status.value in {'DOWNLOADED_UNREVIEWED', 'REVIEW_REQUIRED'}
    fresh = extract_sections(raw, bundle.source, charset=bundle.source.charset)
    assert [c.model_dump(exclude={'review_status'}) for c in fresh] == [
        c.model_dump(exclude={'review_status'}) for c in bundle.chunks]
    candidates = store.list_candidates(source_id)
    expected_count = 4 if source_id == 'nfip-document-flood-damage' else 3
    assert len(candidates) == expected_count
    assert len({c.chunk_id for c in candidates}) == expected_count
    request = KnowledgeRequest(hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER,
                               jurisdiction='US-FL-MIAMI-DADE', safety_topic='housing furniture')
    for candidate in candidates:
        assert candidate.review_status is CandidateStatus.PENDING
        assert candidate.review is None
        verify_candidate_trace(store, candidate)
        parent = next(c for c in bundle.chunks if c.chunk_id == candidate.parent_chunk_id)
        assert parent.guidance_text[candidate.passage_start:candidate.passage_end] == candidate.original_passage == candidate.proposed_chunk
        assert candidate.passage_end - candidate.passage_start == len(candidate.original_passage)
        with pytest.raises(PublicationError):
            verify_candidate_publication(store, candidate, request)
        with pytest.raises(PublicationError):
            FoundationKnowledgeService(store).export_to_m5(source_id, candidate.chunk_id, request)
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('topic', [
    'How should I document flood-damaged furniture for insurance?',
    'Where can I learn about temporary housing assistance after flooding?',
    'pictures videos furniture', 'temporary housing',
])
def test_pending_coverage_never_appears_in_retrieval(topic, pending_store):
    store = pending_store
    result = FoundationKnowledgeService(store).retrieve_guidance(KnowledgeRequest(
        hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER,
        jurisdiction='US-FL-MIAMI-DADE', safety_topic=topic, requested_evidence_count=1))
    assert not any(e.source_id in SOURCES for e in result.evidence_records)


def test_selected_nfip_warning_and_usagov_conditions_remain_in_passages():
    store = SourceStore(ROOT)
    nfip = store.list_candidates(SOURCES[0])
    photos = next(c for c in nfip if c.original_passage.startswith('Photos and videos'))
    assert 'After taking photos, immediately throw away anything that could be a health risk' in photos.original_passage
    assert all(any('safe return' in text for text in c.safety_caveats) for c in nfip)
    housing = store.list_candidates(SOURCES[1])
    assert any('you will find out if you qualify' in c.original_passage for c in housing)
    assert any('Each office sets its own criteria' in c.original_passage for c in housing)


def test_receipts_replacement_preserves_original_candidate_and_excludes_materials():
    from knowledge.candidates import candidate_context_hash
    store = SourceStore(ROOT)
    old = store.load_candidate(SOURCES[0], 'fc072448ce3bcea4ad83400947fae856e01af8c604f986fd866bcc026bb5605f')
    assert old.review_status is CandidateStatus.PENDING and old.review is None
    assert candidate_context_hash(old) == '3d461fbeedd74f638655f7dc279dba62db4b4997bbac8c0616830bacd1c0c525'
    replacement = store.load_candidate(SOURCES[0], 'b7cd7908f13feabf79bc5bb21fb9446b3b5cb7d7b013973102e038c12cc34f13')
    verify_candidate_trace(store, replacement)
    assert replacement.review_status is CandidateStatus.PENDING and replacement.review is None
    assert (replacement.passage_start, replacement.passage_end) == (152, 253)
    assert replacement.original_passage == (
        'Receipts for repairs and replacement items.\n'
        'Warranty or manufacturer details for replaced appliances.')
    assert replacement.original_passage == old.original_passage[152:253]
    assert 'Small pieces of damaged carpet' not in replacement.original_passage
    assert 'Small pieces of damaged carpet' in replacement.surrounding_context[0].guidance_text


def test_real_approved_coverage_and_held_publication_boundaries():
    store = SourceStore(ROOT)
    before = {p: p.read_bytes() for p in ROOT.rglob('*') if p.is_file()}
    request = KnowledgeRequest(hazard=Hazard.FLOOD, disaster_phase=DisasterPhase.RECOVER,
        jurisdiction='US-FL-MIAMI-DADE', safety_topic='transitional housing', requested_evidence_count=1)
    service = FoundationKnowledgeService(store)
    approved = []
    for bundle in store.list_bundles():
        for candidate in store.list_candidates(bundle.source.source_id):
            verify_candidate_trace(store, candidate)
            if candidate.review_status is CandidateStatus.APPROVED:
                verify_candidate_publication(store, candidate)
                exported = service.export_to_m5(candidate.source_id, candidate.chunk_id, request)
                assert candidate.original_passage in exported['guidance_text']
                approved.append(candidate)
            else:
                with pytest.raises(PublicationError):
                    service.export_to_m5(candidate.source_id, candidate.chunk_id, request)
    assert len(approved) == 6
    assert sum(c.source_id == 'cdc-flood-reentry' for c in approved) == 5
    housing_id = '8630330fbd12aabc3c31bff38cd811d234bc3e214e05021a322d6f082d9f2b48'
    result = service.retrieve_guidance(request)
    assert result.retrieval_status is RetrievalStatus.SUCCESS
    assert [c.chunk_id for c in result.evidence_records] == [housing_id]
    assert result.evidence_records[0].guidance_text == store.load_candidate(SOURCES[1], housing_id).original_passage
    proof = result.evidence_metadata[0]
    assert proof.official_url == 'https://www.usa.gov/disaster-housing-shelter'
    assert not proof.surrounding_context
    assert any('qualif' in caveat.lower() for caveat in proof.safety_caveats)
    for candidate in approved:
        if candidate.source_id == 'cdc-flood-reentry':
            query = {'0a': 'building inspector', '98': 'electric tool', 'a6': 'tap water',
                     'ab': 'mold sewage', 'ff': 'electrician electrical'}[candidate.chunk_id[:2]]
            response = service.retrieve_guidance(request.model_copy(update={'safety_topic': query}))
            assert response.retrieval_status is RetrievalStatus.SUCCESS
            assert [c.chunk_id for c in response.evidence_records] == [candidate.chunk_id]
    for question, status in (
        ('What does official guidance say about qualifying for transitional housing?', RetrievalStatus.NO_RELEVANT_EVIDENCE),
        ('Where can I find temporary housing after flooding?', RetrievalStatus.SUCCESS),
        ('Where can I learn about temporary housing assistance after flooding?', RetrievalStatus.INSUFFICIENT_EVIDENCE),
    ):
        response = service.retrieve_guidance(request.model_copy(update={'safety_topic': question}))
        assert response.retrieval_status is status
        assert [c.chunk_id for c in response.evidence_records] == ([housing_id] if status is RetrievalStatus.SUCCESS else [])
    assert before == {p: p.read_bytes() for p in ROOT.rglob('*') if p.is_file()}
