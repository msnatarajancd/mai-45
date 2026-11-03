"""SYNTHETIC REVIEW FIXTURES ONLY: isolated stores and test-scoped allowlist.

OFFICIAL_SOURCE below exercises the real publication gate, not a claim of official
authorship. Reserved .test URLs are registered only by pytest's monkeypatch.
No fixture or reviewer signoff is installed in the production store.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from knowledge.candidates import candidate_context_hash, make_candidate
from knowledge.extraction import extract_sections
from knowledge.models import (CandidateStatus, Classification, DisasterPhase as Phase,
    Hazard, KnowledgeRequest, ReviewDecision, ReviewStatus, RetrievalStatus, SourceBundle,
    SourceRecord)
from knowledge.review import PublicationError, reject_candidate, review_candidate, review_source
from knowledge.service import FoundationKnowledgeService
from knowledge.sources import SourceSpec
from knowledge.store import SourceStore, context_hash, replace_record

RAW = b'''<main><h1>SYNTHETIC TEST FIXTURE, NOT OFFICIAL GUIDANCE</h1>
<h2>Electrical hazards</h2><p>SYNTHETIC TEST: Avoid electrical equipment in floodwater. Do not touch electrical wires.</p>
<h2>Floodwater precautions</h2><p>SYNTHETIC TEST: Avoid floodwater contact. Do not assume floodwater is clean.</p>
<h2>Program limitations</h2><p>SYNTHETIC TEST: Registration does not guarantee transportation or assistance.</p></main>'''
ROOT = Path(__file__).resolve().parents[1]


def request(topic='electrical wires', **changes):
    values = dict(hazard=Hazard.FLOOD, disaster_phase=Phase.RECOVER,
        jurisdiction='US-FL-MIAMI-DADE', safety_topic=topic, requested_evidence_count=1)
    return KnowledgeRequest(**(values | changes))


def decision(content_hash, fingerprint):
    return ReviewDecision(reviewer='SYNTHETIC TEST REVIEWER; not a human production signoff',
        expected_content_hash=content_hash, expected_context_hash=fingerprint,
        provenance_checked=True, content_checked=True, geographic_scope_checked=True,
        applicability_checked=True, caveats_preserved=True)


@pytest.fixture
def reviewed_store(tmp_path, monkeypatch, request):
    url = 'https://synthetic-knowledge.test/static-fixture'
    source = SourceRecord(source_id='synthetic-test-only', publisher='SYNTHETIC TEST ONLY',
        title='SYNTHETIC TEST ONLY, NOT OFFICIAL GUIDANCE', official_url=url,
        source_type='synthetic_test_fixture', jurisdiction='US-FL', hazards=[Hazard.FLOOD],
        disaster_phases=[getattr(request, 'param', Phase.RECOVER)], classification=Classification.OFFICIAL_SOURCE,
        limitations=['SYNTHETIC TEST ONLY; never production evidence.'])
    monkeypatch.setattr('knowledge.sources.CURATED_SOURCES',
        (SourceSpec(source, (url,), ('synthetic',)),))
    store = SourceStore(tmp_path / 'synthetic-store')
    digest = hashlib.sha256(RAW).hexdigest()
    source = replace_record(source, original_content_hash=digest, retrieved_at=datetime.now(timezone.utc),
        final_url=url, content_type='text/html', charset='utf-8', byte_count=len(RAW),
        http_status=200, review_status=ReviewStatus.DOWNLOADED_UNREVIEWED)
    bundle = SourceBundle(source=source, chunks=extract_sections(RAW, source))
    with store.admin_lock():
        store.write_original(RAW)
        store.save_locked(bundle)
    bundle = review_source(store, source.source_id, decision(digest, context_hash(bundle)))
    candidates = []
    for parent in bundle.chunks:
        candidate = make_candidate(bundle, parent, phases=source.disaster_phases,
            caveats=['SYNTHETIC TEST ONLY; no live availability or personal safety determination.'])
        with store.admin_lock():
            store.save_candidate_locked(candidate)
        candidates.append(review_candidate(store, source.source_id, candidate.chunk_id,
            decision(digest, candidate_context_hash(candidate))))
    return store, bundle, candidates


def retrieve(fixture, req=None):
    return FoundationKnowledgeService(fixture[0]).retrieve_guidance(req or request())


def test_relevant_query_returns_exact_evidence_and_traceable_citation(reviewed_store):
    store, bundle, candidates = reviewed_store
    result = retrieve(reviewed_store)
    assert result.retrieval_status is RetrievalStatus.SUCCESS
    assert len(result.evidence_records) == len(result.evidence_metadata) == 1
    evidence, proof = result.evidence_records[0], result.evidence_metadata[0]
    assert evidence.chunk_id == proof.chunk_id == candidates[0].chunk_id
    assert evidence.guidance_text == candidates[0].original_passage
    assert 'Do not touch electrical wires.' in evidence.guidance_text
    assert proof.official_url == bundle.source.official_url
    assert proof.original_content_hash == hashlib.sha256(store.original(proof.original_content_hash)).hexdigest()
    assert proof.source_review == bundle.review
    assert proof.candidate_review == candidates[0].review
    parent = next(c for c in proof.surrounding_context if c.chunk_id == proof.parent_chunk_id)
    assert parent.guidance_text[proof.passage_start:proof.passage_end] == evidence.guidance_text
    assert proof.safety_caveats == candidates[0].safety_caveats


def test_irrelevant_query_abstains(reviewed_store):
    result = retrieve(reviewed_store, request('pizza insurance astronomy'))
    assert result.retrieval_status is RetrievalStatus.NO_RELEVANT_EVIDENCE
    assert not result.evidence_records


@pytest.mark.parametrize('changes', [dict(jurisdiction='US-GA'), dict(jurisdiction='US'),
    dict(jurisdiction='US-FLORIDA'), dict(hazard=Hazard.WILDFIRE), dict(disaster_phase=Phase.RESPOND)])
def test_wrong_source_scope_is_excluded(reviewed_store, changes):
    result = retrieve(reviewed_store, request(**changes))
    assert result.retrieval_status is RetrievalStatus.NO_RELEVANT_EVIDENCE
    assert not result.evidence_records


@pytest.mark.parametrize('changes', [dict(jurisdiction='US-FL-OTHER'),
    dict(hazards=[Hazard.HURRICANE]), dict(phases=[Phase.PREPARE])])
def test_candidate_scope_is_checked_independently(reviewed_store, changes):
    store, bundle, candidates = reviewed_store
    old = candidates[0]
    candidate = make_candidate(bundle, bundle.chunks[0], phases=changes.get('phases', old.phases),
        hazards=changes.get('hazards', old.hazards))
    if 'jurisdiction' in changes:
        candidate = replace_record(candidate, jurisdiction=changes['jurisdiction'])
    path = store.root / 'candidates' / old.source_id / (old.chunk_id + '.json')
    path.unlink()
    with store.admin_lock():
        store.save_candidate_locked(candidate)
    if 'jurisdiction' in changes:
        with pytest.raises(PublicationError):
            review_candidate(store, candidate.source_id, candidate.chunk_id,
                decision(candidate.original_content_hash, candidate_context_hash(candidate)))
    else:
        review_candidate(store, candidate.source_id, candidate.chunk_id,
            decision(candidate.original_content_hash, candidate_context_hash(candidate)))
    assert not retrieve(reviewed_store).evidence_records


@pytest.mark.parametrize('state', ['pending', 'rejected'])
def test_unreviewed_or_rejected_candidate_is_excluded(reviewed_store, state):
    store, _, candidates = reviewed_store
    old = candidates[0]
    pending = replace_record(old, review_status=CandidateStatus.PENDING, review=None)
    with store.admin_lock():
        store.save_candidate_locked(pending)
    if state == 'rejected':
        reject_candidate(store, old.source_id, old.chunk_id, reviewer='SYNTHETIC TEST REVIEWER',
            reason='SYNTHETIC rejection', expected_content_hash=old.original_content_hash,
            expected_context_hash=candidate_context_hash(old))
    assert not retrieve(reviewed_store).evidence_records


@pytest.mark.parametrize('state', [ReviewStatus.REVIEW_REQUIRED, ReviewStatus.STALE])
def test_unreviewed_or_stale_parent_excludes_approved_candidates(reviewed_store, state):
    store, bundle, _ = reviewed_store
    unreviewed = SourceBundle(source=replace_record(bundle.source, review_status=state,
        reviewer=None, reviewed_at=None),
        chunks=[replace_record(c, review_status=state) for c in bundle.chunks])
    with store.admin_lock():
        store.save_locked(unreviewed)
    result = retrieve(reviewed_store)
    assert result.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert not result.evidence_records


@pytest.mark.parametrize('corruption', ['raw', 'candidate', 'source', 'context', 'missing-original'])
def test_hash_and_provenance_corruption_fail_closed(reviewed_store, corruption):
    store, bundle, candidates = reviewed_store
    original = store.root / 'originals' / (bundle.source.original_content_hash + '.bin')
    if corruption == 'raw':
        original.write_bytes(RAW + b' changed')
    elif corruption == 'missing-original':
        original.unlink()
    elif corruption == 'source':
        altered = replace_record(bundle, source=replace_record(bundle.source, jurisdiction='US'))
        with store.admin_lock():
            store.save_locked(altered)
    else:
        candidate = candidates[0]
        path = store.root / 'candidates' / candidate.source_id / (candidate.chunk_id + '.json')
        data = json.loads(path.read_bytes())
        if corruption == 'candidate':
            data['original_passage'] += ' fabricated'
        else:
            data['safety_caveats'] = ['Modified after review']
        path.write_text(json.dumps(data), encoding='utf-8')
    result = retrieve(reviewed_store)
    assert not result.evidence_records and not result.evidence_metadata
    assert result.retrieval_status is RetrievalStatus.UNAVAILABLE


def test_deterministic_ranking_unique_ids_and_insufficient_count(reviewed_store):
    first = retrieve(reviewed_store, request('floodwater', requested_evidence_count=3))
    second = retrieve(reviewed_store, request('floodwater', requested_evidence_count=3))
    assert first == second
    assert first.retrieval_status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    ids = [c.chunk_id for c in first.evidence_records]
    assert len(ids) == len(set(ids)) == 2
    assert len(first.source_metadata) == 1
    assert len(first.evidence_metadata) == 2


def test_lexical_ranking_prefers_more_matching_content(reviewed_store):
    result = retrieve(reviewed_store, request('electrical floodwater', requested_evidence_count=2))
    assert result.retrieval_status is RetrievalStatus.SUCCESS
    assert result.evidence_records[0].chunk_id == reviewed_store[2][0].chunk_id


def test_empty_topic_requires_clarification(reviewed_store):
    result = retrieve(reviewed_store, request('flood hurricane'))
    assert result.retrieval_status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert not result.evidence_records


@pytest.mark.parametrize('topic', ['Are there current flood alerts?', 'Is there an evacuation order?',
    'Does the shelter have capacity?', 'Is transportation available?', 'Am I eligible for assistance?',
    'Is my flooded home safe?', 'Can I reenter my house?', 'Will EEAP transport me?',
    'Is the shelter open?', 'Is electrical equipment safe to use?', 'Latest floodwater information',
    'Should I evacuate?', 'My flooded home is safe, correct?', 'Is this shelter accepting people?'])
def test_operational_questions_abstain_even_with_lexical_matches(reviewed_store, topic):
    result = retrieve(reviewed_store, request(topic))
    assert result.retrieval_status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert not result.evidence_records and not result.source_metadata


def test_household_operational_need_blocks_static_topic(reviewed_store):
    result = retrieve(reviewed_store, request('electrical wires', household_needs=['Need transportation now']))
    assert result.retrieval_status is RetrievalStatus.INSUFFICIENT_EVIDENCE
    assert not result.evidence_records


@pytest.mark.parametrize('failure', [OSError('private path'), ValueError('corrupt JSON')])
def test_store_failure_discards_partial_results(reviewed_store, monkeypatch, failure):
    store, _, _ = reviewed_store
    def broken(*args):
        raise failure
    monkeypatch.setattr(store, 'list_candidates', broken)
    result = retrieve(reviewed_store)
    assert result.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert not result.evidence_records
    assert 'private path' not in result.model_dump_json()


def test_busy_store_fails_closed(reviewed_store):
    with reviewed_store[0].admin_lock():
        assert retrieve(reviewed_store).retrieval_status is RetrievalStatus.UNAVAILABLE


def test_reacquisition_invalidates_older_candidate_signoffs(reviewed_store):
    store, bundle, _ = reviewed_store
    source = replace_record(bundle.source, retrieved_at=datetime.now(timezone.utc),
        reviewed_at=None, reviewer=None, review_status=ReviewStatus.REVIEW_REQUIRED)
    fresh = SourceBundle(source=source,
        chunks=[replace_record(c, review_status=ReviewStatus.REVIEW_REQUIRED) for c in bundle.chunks])
    with store.admin_lock():
        store.save_locked(fresh)
    review_source(store, source.source_id, decision(source.original_content_hash, context_hash(fresh)))
    result = retrieve(reviewed_store)
    assert result.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert not result.evidence_records


def test_retrieval_never_approves_or_changes_reviewed_artifacts(reviewed_store, monkeypatch):
    store, _, _ = reviewed_store
    before = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    def forbidden(*args, **kwargs):
        raise AssertionError('Retrieval must not record a human review or use the network')
    monkeypatch.setattr('knowledge.review.review_source', forbidden)
    monkeypatch.setattr('knowledge.review.review_candidate', forbidden)
    monkeypatch.setattr('knowledge.ingestion.OfficialHTTPTransport.fetch', forbidden)
    assert retrieve(reviewed_store).retrieval_status is RetrievalStatus.SUCCESS
    after = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    assert before == after


def test_missing_store_is_not_created(tmp_path):
    path = tmp_path / 'absent'
    result = FoundationKnowledgeService(SourceStore(path)).retrieve_guidance(request())
    assert result.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert not path.exists()


def test_real_unreviewed_store_returns_zero_without_any_artifact_changes():
    store = SourceStore(ROOT / 'data/official_sources')
    before = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    result = FoundationKnowledgeService(store).retrieve_guidance(request('electrical hazards'))
    assert result.retrieval_status is RetrievalStatus.UNAVAILABLE
    assert not result.evidence_records and not result.source_metadata and not result.evidence_metadata
    candidates = [c for b in store.list_bundles() for c in store.list_candidates(b.source.source_id)]
    assert len(candidates) == 16
    assert all(c.review_status is CandidateStatus.PENDING and c.review is None for c in candidates)
    after = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    assert before == after


def test_test_only_allowlist_does_not_exist_in_production():
    from knowledge.sources import get_source
    with pytest.raises(ValueError):
        get_source('synthetic-test-only')
