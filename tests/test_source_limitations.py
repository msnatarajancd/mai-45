"""SYNTHETIC .test documents only; never modify real human approvals."""
import json

import pytest

from knowledge.candidates import candidate_context_hash, make_candidate, public_source_limitations
from knowledge.models import ReviewStatus
from knowledge.review import PublicationError, review_source, review_candidate
from knowledge.service import FoundationKnowledgeService
from knowledge.store import context_hash, replace_record
from services.knowledge import retrieve_guidance
from test_knowledge_retrieval import _synthetic_store, decision, request

LEGACY = 'Candidate source; human review required before publication.'
STATIC = 'Static guidance is not live availability or a current evacuation order.'
HTML = 'HTML-only extraction may omit images, embedded documents, or dynamic content.'
HOLD = 'SYNTHETIC HOLD: Unapproved parent instruction.'
PASSAGE = 'SYNTHETIC TEST: Avoid electrical wires. Do not touch electrical equipment in water.'


@pytest.fixture
def legacy_store(tmp_path, monkeypatch):
    raw = ('<main><h1>SYNTHETIC TEST ONLY</h1><p>'+HOLD+'</p><p>'+PASSAGE+'</p></main>').encode()
    monkeypatch.setattr('test_knowledge_retrieval.RAW',raw)
    store, bundle, _ = _synthetic_store(tmp_path,monkeypatch,approve=False,
        limitations=[LEGACY, STATIC, HTML, 'SYNTHETIC TEST ONLY.'])
    return store, bundle


def approve_fixture(store, bundle):
    bundle = review_source(store,bundle.source.source_id,
        decision(bundle.source.original_content_hash,context_hash(bundle)))
    parent=bundle.chunks[0]; start=parent.guidance_text.index(PASSAGE)
    candidate=make_candidate(bundle,parent,start=start,end=start+len(PASSAGE),
        phases=parent.applicable_phases)
    with store.admin_lock(): store.save_candidate_locked(candidate)
    candidate=review_candidate(store,candidate.source_id,candidate.chunk_id,
        decision(candidate.original_content_hash,candidate_context_hash(candidate)))
    return bundle,candidate


def test_source_projection_all_outputs_prompts_and_immutable_records(legacy_store):
    from recovery.ai_planner import create_ai_draft_plan
    from recovery.models import RecoveryCase,RecoveryIntake
    from test_ai_planner import Fake
    store,bundle=legacy_store
    bundle,candidate=approve_fixture(store,bundle)
    def snapshot():
        return {str(p.relative_to(store.root)):p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    before=snapshot(); service=FoundationKnowledgeService(store)
    result=service.retrieve_guidance(request('electrical wires'))
    adapted=retrieve_guidance('electrical wires','recover',hazard='flood',
        jurisdiction='US-FL-MIAMI-DADE',service=service)
    payload=service.export_to_m5(candidate.source_id,candidate.chunk_id,request())
    case=RecoveryCase(intake=RecoveryIntake(disaster_type='SYNTHETIC flood',housing_condition='SYNTHETIC damage',
        utility_availability={'water':None},temporary_accommodation_status='SYNTHETIC stay',
        immediate_danger=False,household_recovery_needs=[]))
    fake=Fake(); create_ai_draft_plan(case,[payload],fake)
    for output in (result.model_dump_json(),adapted.model_dump_json(),json.dumps(payload,default=str),json.dumps(fake.calls)):
        assert LEGACY not in output
        assert STATIC in output and HTML in output
        assert HOLD not in output
        assert PASSAGE in output and candidate.chunk_id in output
    assert result.source_metadata[0].limitations == public_source_limitations(bundle.source)
    assert result.evidence_metadata[0].source_review == bundle.review
    assert store.load(bundle.source.source_id)==bundle
    assert store.load_candidate(candidate.source_id,candidate.chunk_id)==candidate
    assert store.load(bundle.source.source_id).source.limitations[0]==LEGACY
    assert snapshot()==before


def test_unreviewed_source_cannot_be_projected_or_publish(legacy_store):
    store,bundle=legacy_store
    with pytest.raises(PublicationError,match='reviewed'):
        public_source_limitations(bundle.source)
    service=FoundationKnowledgeService(store)
    assert not service.retrieve_guidance(request()).evidence_records
    pending=store.list_candidates(bundle.source.source_id)[0]
    with pytest.raises(PublicationError):
        service.export_to_m5(pending.source_id,pending.chunk_id,request())


@pytest.mark.parametrize('annotation', ['PENDING source review.', 'Candidate source; review needed.',
    'Human review required before sharing.', 'Awaiting formal human review.'])
def test_unknown_source_review_annotations_fail_closed(legacy_store,annotation):
    store,bundle=legacy_store
    altered=replace_record(bundle,source=replace_record(bundle.source,limitations=[annotation,STATIC,HTML]))
    with store.admin_lock(): store.save_locked(altered)
    reviewed,candidate=approve_fixture(store,altered)
    with pytest.raises(PublicationError,match='unresolved review-state'):
        public_source_limitations(reviewed.source)
    service=FoundationKnowledgeService(store)
    assert not service.retrieve_guidance(request('electrical wires')).evidence_records
    with pytest.raises(PublicationError,match='unresolved review-state'):
        service.export_to_m5(candidate.source_id,candidate.chunk_id,request())


def test_m1_projects_legacy_source_metadata_from_trusted_service(legacy_store):
    store,bundle=legacy_store; bundle,_=approve_fixture(store,bundle)
    service=FoundationKnowledgeService(store)
    class LegacyMetadata:
        def retrieve_guidance(self, req):
            result=service.retrieve_guidance(req)
            return replace_record(result,source_metadata=[bundle.source])
    adapted=retrieve_guidance('electrical wires','recover',hazard='flood',
        jurisdiction='US-FL-MIAMI-DADE',service=LegacyMetadata())
    assert adapted.citations
    assert LEGACY not in adapted.model_dump_json()
    assert STATIC in adapted.citations[0].source_limitations
