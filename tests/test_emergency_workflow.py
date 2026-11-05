from emergency.models import SituationInput
from emergency.service import evaluate_situation
from emergency.workflow import begin_emergency


def test_new_report_invalidates_pending_work_but_preserves_saved_case_and_tasks():
    state = {'rr_case_id': 'case-1', 'assistant_pending': 'old proposal',
             'assistant_result_notice': 'old success', 'tour_step': 3, 'tour_run': 'old',
             'tour_explanation': 'old', 'protect_generated_guidance': 'old',
             'rr_draft': 'old draft', 'rr_revision': 'old revision',
             'rr_progress_task1': 'COMPLETED', 'saved_tasks': ['completed']}
    decision = evaluate_situation(SituationInput(text='My child is not breathing'))
    begin_emergency(state, decision, entrypoint='assistant', event_id='event-1')
    assert state['rr_emergency'] and state['rr_emergency_epoch'] == 1
    assert state['rr_pending_danger'] == ['case-1']
    assert state['rr_emergency_decision']['persist_danger']
    assert state['rr_case_id'] == 'case-1' and state['saved_tasks'] == ['completed']
    assert state['rr_progress_task1'] == 'COMPLETED'
    assert state['rr_draft'] == 'old draft'
    for key in ('assistant_pending', 'assistant_result_notice', 'tour_step', 'tour_run',
                'tour_explanation', 'protect_generated_guidance', 'rr_revision'):
        assert key not in state


def test_event_retry_is_noop_and_new_event_advances_epoch():
    state = {'rr_case_id': 'case-1'}
    decision = evaluate_situation(SituationInput(immediate_danger=True))
    begin_emergency(state, decision, entrypoint='respond', event_id='event-1')
    state['rr_pending_danger'] = []  # Existing M5 save succeeded.
    begin_emergency(state, decision, entrypoint='respond', event_id='event-1')
    assert state['rr_emergency_epoch'] == 1 and state['rr_pending_danger'] == []
    begin_emergency(state, decision, entrypoint='respond', event_id='event-2')
    assert state['rr_emergency_epoch'] == 2 and state['rr_pending_danger'] == ['case-1']
    begin_emergency(state, decision, entrypoint='respond', event_id='event-1')
    assert state['rr_emergency_epoch'] == 2


def test_unclear_help_pauses_without_creating_a_persisted_danger_report():
    state = {'rr_case_id': 'case-1', 'rr_pending_danger': ['other-case']}
    begin_emergency(state, evaluate_situation(SituationInput()), entrypoint='respond', event_id='help-1')
    assert state['rr_emergency'] and state['rr_pending_danger'] == ['other-case']


def test_ordinary_decision_does_not_start_an_emergency():
    state = {'rr_case_id': 'case-1'}
    begin_emergency(state, evaluate_situation(SituationInput(text='transport next week')), entrypoint='respond', event_id='future-1')
    assert not state.get('rr_emergency') and not state.get('rr_pending_danger')
