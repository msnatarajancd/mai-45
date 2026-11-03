"""Offline integration using isolated, clearly SYNTHETIC approved fixtures."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from domain.contracts import Household
from knowledge.models import CandidateStatus, DisasterPhase as Phase, Hazard, ReviewStatus, SourceBundle
from knowledge.review import PublicationError, mark_stale, review_candidate, review_source
from knowledge.candidates import candidate_context_hash, make_candidate
from knowledge.service import FoundationKnowledgeService
from knowledge.store import SourceStore, context_hash, replace_record
from services.knowledge import retrieve_guidance
from test_knowledge_retrieval import reviewed_store, request, decision

ROOT = Path(__file__).resolve().parents[1]


def adapt(fixture, query='electrical wires', phase='recover', **changes):
    kwargs = dict(hazard='flood', jurisdiction='US-FL-MIAMI-DADE',
                  service=FoundationKnowledgeService(fixture[0]))
    return retrieve_guidance(query, phase, Household(), **(kwargs | changes))


def export(fixture, req=None, chunk_id=None):
    store, bundle, candidates = fixture
    return FoundationKnowledgeService(store).export_to_m5(bundle.source.source_id,
        chunk_id or candidates[0].chunk_id, req or request())


def test_approved_candidate_exports_complete_context_and_m5_shape(reviewed_store):
    from recovery.ai_planner import RecoveryEvidence
    _, bundle, candidates = reviewed_store
    payload = export(reviewed_store)
    assert RecoveryEvidence.model_validate(payload).source_id == candidates[0].chunk_id
    assert payload['verified'] is True and payload['reviewed'] is True
    assert bundle.source.source_id in payload['guidance_text']
    assert candidates[0].original_passage in payload['guidance_text']
    assert all(c in payload['guidance_text'] for c in candidates[0].safety_caveats)
    assert all(c in payload['guidance_text'] for c in bundle.source.limitations)
    assert 'Do not touch electrical wires.' in payload['guidance_text']


def test_parent_section_id_never_bypasses_candidate_gate(reviewed_store):
    with pytest.raises(PublicationError, match='parent-section IDs'):
        export(reviewed_store, chunk_id=reviewed_store[1].chunks[0].chunk_id)


def test_partial_passage_export_retains_parent_negative_instruction(reviewed_store):
    store, bundle, _ = reviewed_store
    candidate = make_candidate(bundle, bundle.chunks[0], end=25, phases=[Phase.RECOVER])
    assert 'Do not touch' not in candidate.original_passage
    with store.admin_lock():
        store.save_candidate_locked(candidate)
    review_candidate(store, candidate.source_id, candidate.chunk_id,
        decision(candidate.original_content_hash, candidate_context_hash(candidate)))
    payload = export(reviewed_store, chunk_id=candidate.chunk_id)
    assert 'Do not touch electrical wires.' in payload['guidance_text']


def test_oversized_complete_context_is_rejected_without_truncation(reviewed_store):
    store, bundle, _ = reviewed_store
    candidate = make_candidate(bundle, bundle.chunks[0], phases=[Phase.RECOVER],
        caveats=[str(i) + ' SYNTHETIC TEST ' + 'x' * 900 for i in range(8)])
    with store.admin_lock():
        store.save_candidate_locked(candidate)
    review_candidate(store, candidate.source_id, candidate.chunk_id,
        decision(candidate.original_content_hash, candidate_context_hash(candidate)))
    with pytest.raises(PublicationError, match='text limit'):
        export(reviewed_store, chunk_id=candidate.chunk_id)


def test_reacquisition_invalidates_old_candidate_export(reviewed_store):
    from datetime import datetime, timezone
    store, bundle, _ = reviewed_store
    fresh = SourceBundle(source=replace_record(bundle.source, retrieved_at=datetime.now(timezone.utc),
        reviewer=None, reviewed_at=None, review_status=ReviewStatus.REVIEW_REQUIRED),
        chunks=[replace_record(c, review_status=ReviewStatus.REVIEW_REQUIRED) for c in bundle.chunks])
    with store.admin_lock():
        store.save_locked(fresh)
    review_source(store, fresh.source.source_id,
        decision(fresh.source.original_content_hash, context_hash(fresh)))
    with pytest.raises(PublicationError, match='predates'):
        export(reviewed_store)


def test_pending_candidate_cannot_export_or_display(reviewed_store):
    store, _, candidates = reviewed_store
    pending = replace_record(candidates[0], review_status=CandidateStatus.PENDING, review=None)
    with store.admin_lock():
        store.save_candidate_locked(pending)
    with pytest.raises(PublicationError, match='approved candidate'):
        export(reviewed_store)
    assert not adapt(reviewed_store).citations


@pytest.mark.parametrize('state', [ReviewStatus.REVIEW_REQUIRED, ReviewStatus.STALE])
def test_nonapproved_source_blocks_approved_candidate(reviewed_store, state):
    store, bundle, _ = reviewed_store
    unreviewed = SourceBundle(source=replace_record(bundle.source, review_status=state,
        reviewer=None, reviewed_at=None),
        chunks=[replace_record(c, review_status=state) for c in bundle.chunks])
    with store.admin_lock():
        store.save_locked(unreviewed)
    with pytest.raises(PublicationError):
        export(reviewed_store)
    assert not adapt(reviewed_store).citations


@pytest.mark.parametrize('changes', [dict(jurisdiction='US-GA'),
    dict(hazard=Hazard.WILDFIRE), dict(disaster_phase=Phase.PREPARE)])
def test_wrong_scope_export_fails_and_adapter_abstains(reviewed_store, changes):
    with pytest.raises(PublicationError, match='not applicable'):
        export(reviewed_store, request(**changes))
    kwargs = {('phase' if k == 'disaster_phase' else k): v for k, v in changes.items()}
    result = adapt(reviewed_store, **kwargs)
    assert not result.citations and result.insufficient_evidence


@pytest.mark.parametrize('target', ['original', 'source-context', 'candidate-context', 'candidate-hash'])
def test_modified_hashes_or_context_fail_closed(reviewed_store, target):
    store, bundle, candidates = reviewed_store
    if target == 'original':
        path = store.root / 'originals' / (bundle.source.original_content_hash + '.bin')
        path.write_bytes(path.read_bytes() + b' changed')
    elif target == 'source-context':
        changed = replace_record(bundle, source=replace_record(bundle.source, limitations=['Changed']))
        with store.admin_lock():
            store.save_locked(changed)
    else:
        c = candidates[0]
        path = store.root / 'candidates' / c.source_id / (c.chunk_id + '.json')
        data = json.loads(path.read_bytes())
        if target == 'candidate-context':
            data['safety_caveats'] = ['Changed after approval']
        else:
            data['original_content_hash'] = '0' * 64
        path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(PublicationError):
        export(reviewed_store)
    result = adapt(reviewed_store)
    assert not result.citations and result.insufficient_evidence


def test_m1_preserves_exact_passage_and_all_citation_provenance(reviewed_store):
    _, bundle, candidates = reviewed_store
    result = adapt(reviewed_store)
    citation = result.citations[0]
    assert citation.passage == candidates[0].original_passage
    assert citation.citation_id == result.sources[0].citation_id == candidates[0].chunk_id
    assert citation.source_id == bundle.source.source_id
    assert citation.original_content_hash == bundle.source.original_content_hash
    assert citation.official_url == bundle.source.official_url
    assert citation.candidate_review == candidates[0].review.model_dump(mode='json')
    assert citation.source_review == bundle.review.model_dump(mode='json')
    assert citation.surrounding_context == [c.model_dump(mode='json') for c in candidates[0].surrounding_context]
    assert citation.safety_caveats == candidates[0].safety_caveats
    assert citation.phases == ['recover'] and citation.jurisdiction == 'US-FL'
    assert result.insufficient_evidence and result.retrieval_status == 'INSUFFICIENT_EVIDENCE'


def test_m1_citations_are_stable_unique_and_success_is_preserved(reviewed_store):
    first = adapt(reviewed_store, 'synthetic test')
    assert first == adapt(reviewed_store, 'synthetic test')
    assert len({c.citation_id for c in first.citations}) == len(first.citations) == 3
    assert not first.insufficient_evidence and first.retrieval_status == 'SUCCESS'


@pytest.mark.parametrize('phase,expected', [('protect', 'prepare'), ('respond', 'respond'), ('recover', 'recover')])
def test_phase_translation_is_explicit(phase, expected):
    from knowledge.models import GuidanceResult, RetrievalStatus
    class Service:
        def retrieve_guidance(self, req):
            assert req.disaster_phase.value == expected
            return GuidanceResult(matching_context=req, evidence_records=[], source_metadata=[],
                limitations=[], missing_information=[], retrieval_status=RetrievalStatus.UNAVAILABLE)
    result = retrieve_guidance('electrical hazards', phase, hazard='flood',
        jurisdiction='US-FL', service=Service())
    assert not result.citations


@pytest.mark.parametrize('changes', [dict(hazard=None), dict(jurisdiction=None),
    dict(phase='guardian'), dict(hazard='earthquake')])
def test_missing_or_unsupported_context_abstains(reviewed_store, changes):
    result = adapt(reviewed_store, **changes)
    assert result.insufficient_evidence and not result.citations


def test_adapter_sanitizes_store_failure():
    class Broken:
        def retrieve_guidance(self, request):
            raise OSError('private path and secret')
    result = retrieve_guidance('electrical hazards', 'recover', hazard='flood',
        jurisdiction='US-FL', service=Broken())
    assert result.retrieval_status == 'UNAVAILABLE'
    assert not result.citations and 'secret' not in result.model_dump_json()


def test_real_pending_store_produces_zero_m1_citations():
    result = retrieve_guidance('electrical hazards', 'recover', hazard='flood', jurisdiction='US-FL-MIAMI-DADE')
    assert result.retrieval_status == 'UNAVAILABLE'
    assert not result.citations and not result.sources
    store = SourceStore(ROOT / 'data/official_sources')
    candidates = [c for b in store.list_bundles() for c in store.list_candidates(b.source.source_id)]
    assert len(candidates) == 16 and all(c.review_status is CandidateStatus.PENDING for c in candidates)


def button(app, label):
    return next(b for b in app.button if b.label == label)


@pytest.mark.parametrize('reviewed_store', [Phase.PREPARE], indirect=True)
def test_protect_displays_exact_excerpts_without_model_call(reviewed_store, monkeypatch, tmp_path):
    from services import knowledge
    from recovery.llm_client import NebiusClient
    original = knowledge.retrieve_guidance
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'ui.sqlite3'))
    monkeypatch.setattr(knowledge, 'retrieve_guidance', lambda *args, **kwargs:
        original(*args, **kwargs, service=FoundationKnowledgeService(reviewed_store[0])))
    def forbidden(*args, **kwargs):
        raise AssertionError('No model or network call for excerpt display')
    monkeypatch.setattr(NebiusClient, 'complete', forbidden)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Protect'
    app.run()
    next(s for s in app.selectbox if s.label == 'Guidance hazard').select('flood')
    next(s for s in app.selectbox if s.label == 'General preparedness topic').select('Electrical hazards')
    button(app, 'Explain with verified sources').click().run()
    assert not app.exception
    assert any(reviewed_store[2][0].original_passage == t.value for t in app.text)
    assert any(reviewed_store[2][0].chunk_id in c.value for c in app.caption)
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert "I can't call 911" in [b.label for b in app.button]
    # A later source revocation must remove the previously displayed excerpt.
    mark_stale(reviewed_store[0], reviewed_store[1].source.source_id)
    app.run()
    assert not any(reviewed_store[2][0].original_passage == t.value for t in app.text)
    # Changing scope/topic must clear the previously displayed evidence.
    next(s for s in app.selectbox if s.label == 'Guidance hazard').select('hurricane').run()
    assert not any(reviewed_store[2][0].original_passage == t.value for t in app.text)


def test_m3_failure_keeps_both_emergency_controls(monkeypatch, tmp_path):
    from services import knowledge
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'ui.sqlite3'))
    def broken(*args, **kwargs):
        raise OSError('retrieval unavailable')
    monkeypatch.setattr(knowledge, 'retrieve_guidance', broken)
    app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Protect'
    app.run()
    button(app, 'Explain with verified sources').click().run()
    assert not app.exception
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    button(app, "I can't call 911").click().run()
    assert any('cannot send a text or contact responders' in i.value for i in app.info)
