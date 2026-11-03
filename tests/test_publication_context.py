"""SYNTHETIC ONLY: approved Candidate 2 beside pending/HOLD Candidate 1.

Quoted government passages are embedded in a labeled .test fixture; neither the
real source nor any real candidate receives a review or modification.
"""
import hashlib
import json
from html import escape
from pathlib import Path

import pytest
from pydantic import ValidationError
from streamlit.testing.v1 import AppTest

from knowledge.candidates import candidate_context_hash, make_candidate
from knowledge.models import CandidatePacket, CandidateStatus, EvidenceProvenance
from knowledge.review import PublicationError, review_candidate
from knowledge.service import FoundationKnowledgeService
from knowledge.store import replace_record
from services.knowledge import retrieve_guidance
from test_knowledge_retrieval import reviewed_store, request, decision

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def adjacent_candidates(monkeypatch, request):
    real_packet = CandidatePacket.model_validate_json(
        (ROOT / 'data/official_sources/candidate_packet.json').read_bytes())
    held_passage = real_packet.candidates[0].original_passage
    published_passage = real_packet.candidates[1].original_passage
    raw = ('<main><h1>SYNTHETIC TEST DOCUMENT; NOT OFFICIAL GUIDANCE</h1><p>'
           + escape(held_passage) + '</p><p>' + escape(published_passage) + '</p></main>').encode()
    monkeypatch.setattr('test_knowledge_retrieval.RAW', raw)
    store, bundle, old = request.getfixturevalue('reviewed_store')
    for candidate in old:
        (store.root / 'candidates' / candidate.source_id / (candidate.chunk_id + '.json')).unlink()
    parent = bundle.chunks[0]
    start = parent.guidance_text.index(published_passage)
    held = make_candidate(bundle, parent, end=len(held_passage), phases=parent.applicable_phases)
    selected = make_candidate(bundle, parent, start=start, end=start+len(published_passage),
        phases=parent.applicable_phases,
        caveats=['SYNTHETIC REVIEW: A building-inspector prerequisite is not household safety verification.'])
    with store.admin_lock():
        store.save_candidate_locked(held)
        store.save_candidate_locked(selected)
    selected = review_candidate(store, selected.source_id, selected.chunk_id,
        decision(selected.original_content_hash, candidate_context_hash(selected)))
    return store, bundle, held, selected


def test_candidate2_retrieval_and_serialization_never_publish_held_candidate1(adjacent_candidates):
    store, _, held, selected = adjacent_candidates
    result = FoundationKnowledgeService(store).retrieve_guidance(request('building inspector'))
    assert result.retrieval_status.value == 'SUCCESS'
    assert result.evidence_records[0].chunk_id == selected.chunk_id
    assert result.evidence_records[0].guidance_text == selected.original_passage
    serialized = result.model_dump_json()
    assert 'Cover windows with storm shutters or plywood.' not in serialized
    assert held.original_passage not in serialized
    assert result.evidence_metadata[0].surrounding_context == []
    assert store.load_candidate(held.source_id, held.chunk_id).review_status is CandidateStatus.PENDING


def test_parent_approval_does_not_publish_held_candidate(adjacent_candidates):
    store, _, held, _ = adjacent_candidates
    with pytest.raises(PublicationError, match='approved candidate'):
        FoundationKnowledgeService(store).export_to_m5(held.source_id, held.chunk_id, request())


def test_resource_validation_cannot_publish_parent_context(adjacent_candidates):
    from knowledge.models import ResourceRecord
    store, bundle, held, _ = adjacent_candidates
    resource = ResourceRecord(resource_id='synthetic-context-attempt', source_id=held.source_id,
        official_name='Cover windows with storm shutters or plywood.',
        service_category='Cover windows with storm shutters or plywood.',
        service_area=bundle.source.jurisdiction, official_url=bundle.source.official_url,
        prerequisites=[], limitations=['SYNTHETIC TEST; availability unknown.'])
    with pytest.raises(PublicationError, match='individually approved'):
        FoundationKnowledgeService(store).validate_resource(resource)


@pytest.mark.parametrize('value', ['true', 1, None])
def test_standalone_attestation_requires_a_boolean(value):
    with pytest.raises(ValidationError):
        replace_record(decision('a'*64,'b'*64), standalone_passage_checked=value)


def test_m1_result_retains_citations_but_no_context_in_any_field(adjacent_candidates):
    store, bundle, _, selected = adjacent_candidates
    result = retrieve_guidance('building inspector', 'recover', hazard='flood',
        jurisdiction='US-FL-MIAMI-DADE', service=FoundationKnowledgeService(store))
    assert result.citations[0].passage == selected.original_passage
    assert result.citations[0].citation_id == selected.chunk_id
    assert result.citations[0].source_id == bundle.source.source_id
    assert result.citations[0].original_content_hash == selected.original_content_hash
    assert result.citations[0].candidate_review == selected.review.model_dump(mode='json')
    assert 'Cover windows with storm shutters or plywood.' not in result.model_dump_json()
    assert result.citations[0].surrounding_context == []


def test_m5_payload_and_actual_planner_prompt_exclude_held_context(adjacent_candidates):
    from recovery.ai_planner import create_ai_draft_plan
    from recovery.models import RecoveryCase, RecoveryIntake
    from test_ai_planner import Fake
    store, _, _, selected = adjacent_candidates
    payload = FoundationKnowledgeService(store).export_to_m5(selected.source_id, selected.chunk_id, request())
    assert selected.original_passage in payload['guidance_text']
    assert all(note in payload['guidance_text'] for note in selected.safety_caveats)
    assert 'Cover windows with storm shutters or plywood.' not in payload['guidance_text']
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='SYNTHETIC flood',
        housing_condition='SYNTHETIC reported damage', utility_availability={'water':None},
        temporary_accommodation_status='SYNTHETIC stay', immediate_danger=False,
        household_recovery_needs=['Supplies']))
    fake = Fake()
    create_ai_draft_plan(case, [payload], fake)
    prompt = json.dumps(fake.calls)
    assert 'Cover windows with storm shutters or plywood.' not in prompt
    assert selected.original_passage in prompt


def test_human_inspection_retains_full_context_and_same_fingerprint(adjacent_candidates, monkeypatch, capsys):
    from knowledge.review import main
    store, _, held, selected = adjacent_candidates
    stored = store.load_candidate(selected.source_id, selected.chunk_id)
    assert held.original_passage in stored.surrounding_context[0].guidance_text
    assert candidate_context_hash(stored) == selected.review.context_hash
    monkeypatch.setattr('sys.argv', ['review', 'inspect', '--root', str(store.root),
        '--source-id', selected.source_id, '--chunk-id', selected.chunk_id])
    main()
    inspected = json.loads(capsys.readouterr().out)
    assert held.original_passage in inspected['candidate']['surrounding_context'][0]['guidance_text']


def test_legacy_approval_without_standalone_attestation_fails_closed(adjacent_candidates):
    store, _, _, selected = adjacent_candidates
    old_decision = replace_record(selected.review.decision, standalone_passage_checked=False)
    old_review = replace_record(selected.review, decision=old_decision)
    legacy = replace_record(selected, review=old_review)
    with store.admin_lock():
        store.save_candidate_locked(legacy)
    with pytest.raises(PublicationError, match='standalone'):
        FoundationKnowledgeService(store).export_to_m5(selected.source_id, selected.chunk_id, request())
    result = FoundationKnowledgeService(store).retrieve_guidance(request('building inspector'))
    assert not result.evidence_records


def test_public_schema_rejects_legacy_context_and_adapter_abstains(adjacent_candidates):
    store, _, _, selected = adjacent_candidates
    service = FoundationKnowledgeService(store)
    result = service.retrieve_guidance(request('building inspector'))
    proof = result.evidence_metadata[0]
    with pytest.raises(ValidationError):
        replace_record(proof, surrounding_context=selected.surrounding_context)
    # Simulate a stale service object bypassing validation. Adapter revalidation
    # must reject it, not copy raw context into any public DTO or model input.
    bad_proof = proof.model_copy(update={'surrounding_context':selected.surrounding_context})
    class Legacy:
        def retrieve_guidance(self, req):
            return result.model_copy(update={'matching_context':req, 'evidence_metadata':[bad_proof]})
    adapted = retrieve_guidance('building inspector','recover',hazard='flood',
        jurisdiction='US-FL-MIAMI-DADE',service=Legacy())
    assert adapted.retrieval_status == 'UNAVAILABLE' and not adapted.citations


def test_m1_renderer_never_shows_context_even_from_stale_dto(adjacent_candidates, monkeypatch, tmp_path):
    from services import knowledge
    store, _, _, selected = adjacent_candidates
    result = retrieve_guidance('building inspector','recover',hazard='flood',
        jurisdiction='US-FL-MIAMI-DADE',service=FoundationKnowledgeService(store))
    citation = result.citations[0].model_copy(update={'surrounding_context':[
        c.model_dump(mode='json') for c in selected.surrounding_context]})
    stale = result.model_copy(update={'citations':[citation]})
    monkeypatch.setattr(knowledge,'retrieve_guidance',lambda *args, **kwargs:stale)
    monkeypatch.setenv('READYRELIEF_DB_PATH',str(tmp_path/'ui.sqlite3'))
    app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20).run()
    app.session_state['page']='Protect'; app.run()
    next(b for b in app.button if b.label=='Explain with verified sources').click().run()
    assert not app.exception
    assert any(t.value==selected.original_passage for t in app.text)
    assert not any('Cover windows with storm shutters or plywood.' in t.value for t in app.text)
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert "I can't call 911" in [b.label for b in app.button]


def test_real_store_candidates_and_full_context_unchanged():
    root=ROOT/'data/official_sources'
    packet=CandidatePacket.model_validate_json((root/'candidate_packet.json').read_bytes())
    assert len(packet.candidates)==16
    assert all(c.review_status is CandidateStatus.PENDING for c in packet.candidates)
    assert packet.candidates[0].original_passage in packet.candidates[1].surrounding_context[0].guidance_text
    # Existing real-capture integrity tests verify all original bytes separately.
    from knowledge.store import SourceStore
    store=SourceStore(root)
    for c in packet.candidates:
        assert store.load_candidate(c.source_id,c.chunk_id)==c
        assert hashlib.sha256(store.original(c.original_content_hash)).hexdigest()==c.original_content_hash
