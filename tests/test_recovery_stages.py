"""Stage-based UI acceptance; provider responses are synthetic and never persisted implicitly."""
from test_recovery_landing import app, button
from test_recovery_qwen_integration import install, new_reply, submit, NEW
from test_recovery_records import dump


def test_describe_primary_resume_and_optional_intake(app):
    assert any(w.label == 'Continue to Review' for w in app.button)
    assert any(w.label == 'Resume My Recovery' for w in app.button)
    button(app, 'Resume My Recovery').click().run()
    assert any(w.label == 'Recovery case ID' for w in app.text_input)
    assert any(w.label == 'Open saved recovery' for w in app.button)
    assert any(w.label == 'Use structured intake or resume a saved case' for w in app.expander)
    assert 'rr_case_id' not in app.session_state


def test_clarification_has_answer_control_and_requires_new_review(app, monkeypatch):
    reply = new_reply()
    reply['clarification_fields'] = ['adults', 'children']
    clients = install(monkeypatch, reply)
    path = __import__('os').environ['READYRELIEF_DB_PATH']
    before = dump(path)
    submit(app, NEW)
    assert any(w.label == 'Your clarification (optional)' for w in app.text_area)
    assert not any(w.label == 'Resume My Recovery' for w in app.button)
    assert any('Unknown (not inferred)' in w.value and 'adults' in w.value for w in app.caption)
    old_review = app.session_state['rr_extraction_review']
    next(w for w in app.text_area if w.label == 'Your clarification (optional)').input('I do not know the individual counts.')
    button(app, 'Review my clarification').click().run()
    assert not app.exception
    assert len(clients) == 2
    assert app.session_state['rr_extraction_review'] != old_review
    assert 'rr_extraction_ready' not in app.session_state
    assert dump(path) == before


def test_optional_clarification_can_stay_unknown(app, monkeypatch):
    reply = new_reply(); reply['clarification_fields'] = ['adults']
    clients = install(monkeypatch, reply)
    submit(app, NEW)
    button(app, 'Review my clarification').click().run()
    assert len(clients) == 1
    assert not app.exception
    assert 'rr_case_id' not in app.session_state


def test_danger_in_clarification_interrupts_without_second_model_call(app, monkeypatch):
    reply = new_reply(); reply['clarification_fields'] = ['adults']
    clients = install(monkeypatch, reply)
    submit(app, NEW)
    next(w for w in app.text_area if w.label == 'Your clarification (optional)').input('We are trapped in rising floodwater.')
    button(app, 'Review my clarification').click().run()
    assert not app.exception
    assert len(clients) == 1
    assert app.session_state['rr_emergency']
    assert 'rr_extraction_review' not in app.session_state
    assert any(w.label == 'Call 911' for w in app.get('link_button'))
    assert any(w.label == "I Can't Call 911" for w in app.button)


def test_plan_cards_keep_sequential_reading_order_and_remain_unapproved(tmp_path):
    from streamlit.testing.v1 import AppTest
    from recovery.database import SQLiteRecoveryRepository
    from recovery.models import RecoveryPlan
    from test_recovery_capabilities import case_and_records
    path = tmp_path / 'plan-order.sqlite3'
    repo = SQLiteRecoveryRepository(path)
    case, _ = case_and_records(repo)
    before = dump(path)

    def show_plan(path, case_id):
        from uuid import UUID
        from recovery.database import SQLiteRecoveryRepository
        from ui.recovery_page import planning
        repo = SQLiteRecoveryRepository(path)
        planning(repo, repo.get_case(UUID(case_id)))

    view = AppTest.from_function(show_plan, args=(str(path), str(case.case_id))).run()
    assert not view.exception
    draft = RecoveryPlan.model_validate_json(view.session_state['rr_draft'])
    assert [heading.value for heading in view.subheader][1:] == [task.title for task in draft.proposed_tasks]
    assert dump(path) == before
    assert repo.get_active_plan(case.case_id) is None
