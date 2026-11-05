"""Real M1 service and integrated UI, synthetic provider responses only."""
import json
from uuid import UUID

import pytest
import streamlit as st
from services import assistant
from recovery.database import SQLiteRecoveryRepository
from recovery.models import TaskStatus
from test_recovery_extraction import FakeClient, proposed
from test_recovery_landing import app, button
from test_recovery_records import saved, inventory, dump
from test_pending_danger import app_for, ordinary_state, assert_emergency

NEW = 'We are five people at home, including an elderly family member. Our house flooded, the electricity is out, and we need somewhere to stay.'
RETURNING = 'Electricity is back, but our refrigerator is damaged.'


def new_reply():
    return {'fields': {'disaster_type': proposed('Flood', 'Our house flooded'),
        'housing_condition': proposed('Flooded', 'Our house flooded'),
        'electricity': proposed('Unavailable', 'the electricity is out'),
        'temporary_accommodation': proposed('Needed', 'we need somewhere to stay'),
        'household_recovery_needs': proposed(['Temporary housing'], 'we need somewhere to stay')}}


def install(monkeypatch, reply, *, error=None, callback=None):
    clients = []
    class Provider(FakeClient):
        def complete(self, messages):
            if not self.calls and callback:
                callback()
            return super().complete(messages)
    def factory(**kwargs):
        client = Provider(reply, error=error)
        clients.append(client)
        return client
    monkeypatch.setattr(assistant, 'NebiusClient', factory)
    return clients


def submit(app, message):
    next(w for w in app.checkbox if w.label == 'Use Qwen to propose details for my review').check()
    next(w for w in app.text_area if w.label == "Describe what's happening or what you need help with.").input(message)
    button(app, 'Help me get started').click().run()
    assert not app.exception


def confirm(app):
    button(app, 'Review selected changes').click().run()
    next(w for w in app.selectbox if w.label == 'Safety assessment for selected changes').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label == 'I confirm the selected changes shown above').check()
    button(app, 'Confirm selected changes').click().run()
    assert not app.exception


def test_new_household_real_service_review_then_explicit_save(app, monkeypatch):
    clients = install(monkeypatch, new_reply())
    path = __import__('os').environ['READYRELIEF_DB_PATH']
    before = dump(path)
    submit(app, NEW)
    assert len(clients) == 1 and len(clients[0].calls) == 2
    assert dump(path) == before
    assert any(w.value == "Here's what I understood. Please review." for w in app.subheader)
    assert any('Supporting quote: Our house flooded' == w.value for w in app.text)
    from recovery.extraction_consumer import ExtractionReview
    review = ExtractionReview.model_validate_json(app.session_state['rr_extraction_review'])
    assert review.result['fields']['adults']['state'] == review.result['fields']['children']['state'] == 'UNKNOWN'
    assert review.proposed['household_recovery_needs'] == ['Temporary housing']
    button(app, 'Review selected changes').click().run()
    button(app, 'Confirm selected changes').click().run()
    assert dump(path) == before  # Missing approval/safety cannot create a case.
    next(w for w in app.selectbox if w.label == 'Safety assessment for selected changes').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label == 'I confirm the selected changes shown above').check()
    button(app, 'Confirm selected changes').click().run()
    assert not app.exception
    repo = SQLiteRecoveryRepository(path)
    case_id = UUID(app.session_state['rr_case_id'])
    assert repo.get_case(case_id).intake.utility_availability['electricity'] is False
    assert repo.get_recovery_records(case_id).household.adults is None
    assert repo.get_recovery_records(case_id).household.children is None
    assert repo.get_active_plan(case_id) is None
    app.run()
    assert len(clients) == 1  # Rerenders never regenerate.
    button(app, 'Find Help Now').click().run()
    assert any('Official assistance pathways' == w.value for w in app.subheader)


def test_returning_atomic_revision_preserves_damage_progress_and_insurance(saved, monkeypatch):
    path, repo, case = saved
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    original = repo.get_active_plan(case.case_id)
    clients = install(monkeypatch, {'fields': {'electricity': proposed('Available', 'Electricity is back')},
        'new_damage': [proposed('refrigerator', 'our refrigerator is damaged')]})
    app = app_for(path, case, monkeypatch).run()
    before = dump(path)
    submit(app, RETURNING)
    assert dump(path) == before
    payload = json.loads(clients[0].calls[0][1]['content'])['confirmed_context']
    assert payload['reported_damage'] == ['Furniture'] and payload['electricity'] == 'Unavailable'
    confirm(app)
    records = SQLiteRecoveryRepository(path).get_recovery_records(case.case_id)
    assert [d.item_description for d in records.damage_records] == ['Furniture', 'refrigerator']
    assert records.household.children == 2 and records.household.adults is None
    assert repo.get_case(case.case_id).intake.utility_availability['electricity'] is True
    assert repo.get_active_plan(case.case_id).proposed_tasks[:len(original.proposed_tasks)] == original.proposed_tasks
    assert original in repo.list_approved_plans(case.case_id)
    button(app, 'Prepare for insurance').click().run()
    assert any('Item / area: refrigerator' in w.value for w in app.text)
    # Reporting the same item again must not duplicate the approved inventory.
    submit(app, RETURNING)
    assert len(repo.get_recovery_records(case.case_id).damage_records) == 2
    assert 'damage:0' not in __import__('recovery.extraction_consumer', fromlist=['ExtractionReview']).ExtractionReview.model_validate_json(app.session_state['rr_extraction_review']).proposed


@pytest.mark.parametrize('message,danger', [("I'm in danger", True), ('We are in danger', True),
    ("I'm not in danger", False), ("What should I do if I'm in danger?", False)])
def test_danger_precheck_before_qwen_and_hypotheticals(app, monkeypatch, message, danger):
    clients = install(monkeypatch, {'fields': {}})
    submit(app, message)
    if danger:
        assert not clients
        assert_emergency(app)
    else:
        assert len(clients) == 1
        assert not app.session_state['rr_emergency']
        assert 'rr_extraction_review' in app.session_state


@pytest.mark.parametrize('failure', ['missing_key', 'timeout', 'invalid', 'clarification'])
def test_model_failures_and_clarification_leave_structured_input(app, monkeypatch, failure):
    from recovery.llm_client import PlanningClientError
    reply = 'invalid json' if failure == 'invalid' else {'fields': {}}
    error = PlanningClientError('private error', code=failure) if failure in {'missing_key', 'timeout'} else None
    install(monkeypatch, reply, error=error)
    path = __import__('os').environ['READYRELIEF_DB_PATH'];before = dump(path)
    submit(app, 'Please help with recovery')
    assert dump(path) == before
    assert any(w.label == 'Create draft plan' for w in app.button)
    if failure == 'clarification':
        assert any('What household conditions' in w.value for w in app.text)
    else:
        assert any('unavailable or invalid' in w.value for w in app.warning)
    assert not any('private error' in w.value for w in app.warning)
    assert 'Call 911' in [w.label for w in app.get('link_button')]


def test_cancel_discards_proposal_without_writes(app, monkeypatch):
    clients = install(monkeypatch, new_reply())
    path = __import__('os').environ['READYRELIEF_DB_PATH'];before = dump(path)
    submit(app, NEW)
    button(app, 'Reject proposal and use structured input').click().run()
    assert 'rr_extraction_review' not in app.session_state
    assert dump(path) == before and len(clients) == 1


def test_pending_danger_during_generation_overrides_result(saved, monkeypatch):
    path, repo, case = saved
    before = ordinary_state(path, repo, case)
    def interrupt():
        st.session_state['rr_pending_danger'] = [str(case.case_id)]
    install(monkeypatch, {'fields': {}}, callback=interrupt)
    app = app_for(path, case, monkeypatch).run()
    submit(app, RETURNING)
    assert_emergency(app)
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    assert ordinary_state(path, repo, case) == before


def test_persisted_danger_never_calls_model(saved, monkeypatch):
    path, repo, case = saved
    repo.report_immediate_danger(case.case_id)
    clients = install(monkeypatch, {'fields': {}})
    app = app_for(path, case, monkeypatch).run()
    submit(app, RETURNING)
    assert not clients
    assert_emergency(app)


@pytest.mark.parametrize('changed', ['records', 'plan'])
def test_changes_during_model_request_reject_original_snapshot(saved, monkeypatch, changed):
    path, repo, case = saved
    def concurrent():
        if changed == 'records':
            r = repo.get_recovery_records(case.case_id)
            repo.save_recovery_records(r, expected_version=r.version, explicitly_confirmed=True)
        else:
            p = repo.get_active_plan(case.case_id)
            repo.update_task_status(p.plan_id, p.proposed_tasks[1].task_id, TaskStatus.COMPLETED)
    install(monkeypatch, {'fields': {}}, callback=concurrent)
    app = app_for(path, case, monkeypatch).run()
    submit(app, RETURNING)
    assert 'rr_extraction_review' not in app.session_state
    assert any('changed' in w.value for w in app.error)
    assert not repo.get_recovery_records(case.case_id).damage_records


def test_storage_failure_does_not_replay_a_deferred_model_request(app, monkeypatch):
    from ui import recovery_page
    original = recovery_page.repository
    clients = install(monkeypatch, new_reply())
    monkeypatch.setattr(recovery_page, 'repository', lambda: (_ for _ in ()).throw(OSError('synthetic outage')))
    submit(app, NEW)
    assert not clients
    assert 'rr_extraction_message' not in app.session_state
    monkeypatch.setattr(recovery_page, 'repository', original)
    app.run()
    assert not clients
    assert 'rr_case_id' not in app.session_state


def test_recorded_live_rejection_keeps_saved_progress_and_structured_fallback(saved, monkeypatch):
    from pathlib import Path
    path, repo, case = saved
    raw = (Path(__file__).parent / 'fixtures' / 'synthetic_qwen_household_total_rejected.json').read_text(encoding='utf-8')
    clients = install(monkeypatch, raw)
    before = dump(path)
    app = app_for(path, case, monkeypatch).run()
    submit(app, NEW)
    assert len(clients) == 1 and len(clients[0].calls) == 1
    assert dump(path) == before
    assert any('unavailable or invalid' in w.value for w in app.warning)
    button(app, 'Document damage').click().run()
    assert any(w.label == 'Item or area description' for w in app.text_input)
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I can't call 911" in [w.label for w in app.button]
    assert not app.success
