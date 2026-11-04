"""Synthetic pending-danger events must beat every integrated Recovery write."""
import sqlite3
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from recovery.database import SQLiteRecoveryRepository
from recovery.extraction_consumer import prepare_review
from recovery.models import TaskStatus
from test_extraction_consumer import NEW, RETURNING, wire
from test_recovery_records import saved, inventory


def button(app, label):
    return next(w for w in app.button if w.label == label)


def ordinary_state(path, repo, case):
    with sqlite3.connect(path) as connection:
        history = connection.execute('SELECT * FROM recovery_reassessments ORDER BY plan_id').fetchall()
        counts = tuple(connection.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                       for table in ['recovery_cases', 'recovery_plans', 'recovery_records'])
    return (repo.get_recovery_records(case.case_id), repo.get_active_plan(case.case_id),
            repo.list_approved_plans(case.case_id), history, counts)


def app_for(path, case, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    return app


def review_ready(saved, monkeypatch):
    path, repo, case = saved
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    records = repo.get_recovery_records(case.case_id)
    message = NEW+' '+RETURNING
    result = wire(case, records, changes={'reported_county': ('Miami-Dade', 'Miami-Dade'),
        'electricity': ('Available', 'Electricity came back')},
        damage=[('refrigerator', 'our refrigerator is damaged')])
    review = prepare_review(result, message, case=case, records=records,
                            plan=repo.get_active_plan(case.case_id))
    app = app_for(path, case, monkeypatch)
    app.session_state['rr_extraction_review'] = review.model_dump_json()
    app.run()
    button(app, 'Review selected changes').click().run()
    next(w for w in app.selectbox if w.label == 'Safety assessment for selected changes').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label == 'I confirm the selected changes shown above').check()
    return app, review


def assert_emergency(app):
    assert not app.exception
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I can't call 911" in [w.label for w in app.button]
    assert 'Confirm selected changes' not in [w.label for w in app.button]
    assert 'Save progress' not in [w.label for w in app.button]
    assert any('not contacted or dispatched' in w.value for w in app.error)
    assert not app.success


def test_pending_danger_precedes_valid_confirmation_and_preserves_all_progress(saved, monkeypatch):
    path, repo, case = saved
    app, _ = review_ready(saved, monkeypatch)
    before = ordinary_state(path, repo, case)
    calls = []
    original = SQLiteRecoveryRepository.report_immediate_danger
    def report(repository, case_id):
        calls.append('danger')
        return original(repository, case_id)
    monkeypatch.setattr(SQLiteRecoveryRepository, 'report_immediate_danger', report)
    def forbidden(*args, **kwargs):
        pytest.fail('Ordinary confirmation ran before pending danger')
    from ui import recovery_page
    monkeypatch.setattr(recovery_page, 'accept_review', forbidden)
    app.session_state['rr_pending_danger'] = [str(case.case_id)]
    button(app, 'Confirm selected changes').click().run()
    assert_emergency(app)
    assert calls == ['danger']
    assert ordinary_state(path, repo, case) == before
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    assert app.session_state['rr_pending_danger'] == []
    assert 'rr_extraction_review' not in app.session_state
    assert 'rr_extraction_ready' not in app.session_state


def test_failed_danger_persistence_blocks_reruns_and_retry_stale_confirmation(saved, monkeypatch):
    path, repo, case = saved
    app, review = review_ready(saved, monkeypatch)
    stale_ready = dict(app.session_state['rr_extraction_ready'])
    before = ordinary_state(path, repo, case)
    original = SQLiteRecoveryRepository.report_immediate_danger
    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError('synthetic unavailable storage')
    monkeypatch.setattr(SQLiteRecoveryRepository, 'report_immediate_danger', unavailable)
    app.session_state['rr_pending_danger'] = [str(case.case_id)]
    button(app, 'Confirm selected changes').click().run()
    assert_emergency(app)
    assert app.session_state['rr_pending_danger'] == [str(case.case_id)]
    assert ordinary_state(path, repo, case) == before
    assert repo.get_case(case.case_id).intake.immediate_danger is False
    assert any('could not be saved' in w.value for w in app.warning)
    button(app, "I can't call 911").click().run()
    assert_emergency(app)
    assert any('not guaranteed' in w.value for w in app.info)
    button(app, 'Return to app — this does not confirm safety').click().run()
    app.session_state['page'] = 'Recover'
    # An old event/proposal cannot bypass the retry on a subsequent rerun.
    app.session_state['rr_extraction_review'] = review.model_dump_json()
    app.session_state['rr_extraction_ready'] = stale_ready
    app.run()
    assert_emergency(app)
    assert app.session_state['rr_pending_danger'] == [str(case.case_id)]
    assert ordinary_state(path, repo, case) == before
    assert 'rr_extraction_ready' not in app.session_state
    monkeypatch.setattr(SQLiteRecoveryRepository, 'report_immediate_danger', original)
    app.run()
    assert_emergency(app)
    assert app.session_state['rr_pending_danger'] == []
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    assert ordinary_state(path, repo, case) == before
    button(app, 'Return to app — this does not confirm safety').click().run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_extraction_review'] = review.model_dump_json()
    app.session_state['rr_extraction_ready'] = stale_ready
    app.run()
    assert not app.exception
    assert 'Confirm selected changes' not in [w.label for w in app.button]
    assert 'Save progress' not in [w.label for w in app.button]
    assert ordinary_state(path, repo, case) == before


@pytest.mark.parametrize('action', ['extraction', 'household', 'damage', 'progress', 'revision', 'initial_plan', 'new_case'])
def test_last_moment_pending_danger_blocks_each_write_handler(saved, monkeypatch, action):
    path, repo, case = saved
    if action == 'extraction':
        app, _ = review_ready(saved, monkeypatch)
        label = 'Confirm selected changes'
    else:
        if action == 'initial_plan':
            from uuid import uuid4
            case = case.model_copy(update={'case_id': uuid4()})
            repo.create_case(case)
        app = app_for(path, case, monkeypatch).run()
        if action in ('household', 'damage'):
            button(app, 'Document damage').click().run()
            if action == 'household':
                next(w for w in app.text_input if w.label == 'Number of children (if known)').input('7')
                next(w for w in app.checkbox if w.label == 'I confirm these household details').check()
                label = 'Save confirmed household details'
            else:
                next(w for w in app.text_input if w.label == 'Item or area description').input('Refrigerator')
                next(w for w in app.text_area if w.label == 'User-reported damage description').input('Reported damaged')
                next(w for w in app.checkbox if w.label == 'I confirm this damage record').check()
                label = 'Save confirmed damage record'
        elif action == 'progress':
            next(w for w in app.selectbox if w.label.startswith('Status ·')).select(TaskStatus.IN_PROGRESS)
            label = 'Save progress'
        elif action == 'revision':
            next(w for w in app.selectbox if w.label == 'Updated immediate danger assessment').select('No immediate danger reported').run()
            next(w for w in app.selectbox if w.label == 'Electricity availability').select('Available')
            button(app, 'Preview proposed changes').click().run()
            label = 'Approve this revision'
        elif action == 'initial_plan':
            next(w for w in app.checkbox if w.label == 'I reviewed these tasks and want to accept this plan').check()
            label = 'Approve my recovery plan'
        else:
            button(app, 'Open a different case').click().run()
            next(w for w in app.selectbox if w.label == 'Immediate danger assessment').select('No immediate danger reported')
            label = 'Create draft plan'
    before = ordinary_state(path, repo, case)
    events = []
    # Inject after all render-time guards have passed, at the actual submit event.
    name = 'button' if action in ('extraction', 'revision', 'initial_plan') else 'form_submit_button'
    original_widget = getattr(st, name)
    def late_pending(*args, **kwargs):
        result = original_widget(*args, **kwargs)
        if result and (args[0] if args else kwargs.get('label')) == label:
            app.session_state['rr_pending_danger'] = [str(case.case_id)]
            events.append('pending')
        return result
    monkeypatch.setattr(st, name, late_pending)
    button(app, label).click().run()
    assert events == ['pending']
    assert_emergency(app)
    assert ordinary_state(path, repo, case) == before
    if action == 'new_case':
        assert app.session_state['rr_pending_danger'] == [str(case.case_id)]
    else:
        assert repo.get_case(case.case_id).intake.immediate_danger is True


def test_delivery_rejects_pending_danger_without_staging_a_proposal(saved):
    from ui.recovery_page import stage_extraction_result
    _, repo, case = saved
    state = {'rr_case_id': str(case.case_id), 'rr_pending_danger': [str(case.case_id)]}
    with pytest.raises(ValueError, match='paused'):
        stage_extraction_result(state, repo, {}, NEW)
    assert 'rr_extraction_review' not in state
