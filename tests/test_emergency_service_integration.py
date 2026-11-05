"""Service boundary tests for interrupted provider work and stale writes."""
import json

import pytest

from domain.contracts import AppMode, Household
from emergency.models import SituationInput
from emergency.service import evaluate_situation
from emergency.workflow import begin_emergency
from services import assistant, generation
from test_grounded_generation import evidence, FakeClient


def session():
    return dict(page='Protect', household=Household(), location_id='miami', mode=AppMode.DEMO, rr_emergency=False)


class NeverCalled:
    def complete(self, messages):
        pytest.fail('A current-danger report must bypass every provider call')


@pytest.mark.parametrize('text', ['My child is not breathing', 'The house is on fire', 'gas smell', 'I need an ambulance'])
def test_current_danger_uses_shared_workflow_before_model_or_repository(text):
    class NoRepositoryRead:
        def __getattr__(self, name):
            pytest.fail('A current-danger report must not wait for persistence')
    state = session() | {'rr_case_id': 'case-1'}
    proposal = assistant.propose(text, state, NoRepositoryRead(), NeverCalled())
    assert proposal.action is None and state['rr_emergency_epoch'] == 1
    assert state['rr_pending_danger'] == ['case-1']


def test_proposal_arriving_after_danger_is_discarded():
    state = session()
    class Interrupted:
        def complete(self, messages):
            begin_emergency(state, evaluate_situation(SituationInput(immediate_danger=True)),
                            entrypoint='respond', event_id='during-model')
            return json.dumps({'answer': 'Stale routine answer', 'action': {'kind': 'navigate', 'page': 'Recover'}})
    result = assistant.propose('open recovery', state, None, Interrupted())
    assert result.action is None and 'Stale routine answer' not in result.answer
    assert state['rr_emergency']


def test_same_context_after_emergency_cannot_reuse_old_proposal():
    state = session()
    proposal = assistant.local_proposal('open Recover', state, None)
    begin_emergency(state, evaluate_situation(SituationInput()), entrypoint='respond', event_id='help')
    state['rr_emergency'] = False
    with pytest.raises(ValueError, match='changed'):
        assistant.execute(proposal, state, None, confirmed=True)
    assert state['page'] == 'Protect'


def test_active_emergency_never_starts_routine_model():
    state = session() | {'rr_emergency': True}
    result = assistant.propose('open recovery', state, None, NeverCalled())
    assert result.action is None


def test_guidance_interrupts_before_retrieval(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('Danger must be screened before retrieval')
    monkeypatch.setattr(generation.knowledge, 'retrieve_guidance', forbidden)
    state = session()
    result = generation.explain('My child is not breathing', 'recover', hazard=None,
                                jurisdiction=None, client=NeverCalled(), state=state)
    assert result.generation_status == 'emergency' and not result.claims
    assert state['rr_emergency_epoch'] == 1


def test_guidance_generated_before_interruption_cannot_survive_return(monkeypatch, evidence):
    monkeypatch.setattr(generation.knowledge, 'retrieve_guidance', lambda *a, **k: evidence)
    state = session()
    result = generation.explain('electrical hazards', 'recover', hazard='flood',
                                jurisdiction=None, client=FakeClient(), state=state)
    assert result.claims
    begin_emergency(state, evaluate_situation(SituationInput()), entrypoint='respond', event_id='help')
    state['rr_emergency'] = False
    result = generation.revalidate(result, state=state)
    assert not result.claims and result.generation_status == 'emergency'


def test_guidance_provider_completion_after_interruption_never_becomes_answer(monkeypatch, evidence):
    monkeypatch.setattr(generation.knowledge, 'retrieve_guidance', lambda *a, **k: evidence)
    state = session()
    class Interrupted(FakeClient):
        def complete(self, messages):
            output = super().complete(messages)
            begin_emergency(state, evaluate_situation(SituationInput(immediate_danger=True)),
                            entrypoint='respond', event_id='during-guidance')
            return output
    client = Interrupted()
    result = generation.explain('electrical hazards', 'recover', hazard='flood',
                                jurisdiction=None, client=client, state=state)
    assert not result.claims and result.generation_status == 'emergency'
    assert len(client.calls) == 1  # No second verification model request after interruption.
