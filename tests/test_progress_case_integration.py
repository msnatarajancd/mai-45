"""Profile review and saved-case projection through real local storage."""
from datetime import datetime, timezone
from pathlib import Path
from streamlit.testing.v1 import AppTest
from recovery.models import TaskStatus, TaskReview
from recovery.progress.case_reader import load_saved_input, current_progress_revision
from test_recovery_records import saved, dump


def launch(path, case, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    code = '''from ui.recovery_page import repository
from ui.recovery_progress_profile import render_progress_profile
from uuid import UUID
import streamlit as st
repo=repository()
render_progress_profile(repo,repo.get_case(UUID(st.session_state['case_id'])))
'''
    app = AppTest.from_string(code, default_timeout=20)
    app.session_state['case_id'] = str(case.case_id)
    return app.run()


def widget(app, group, label):
    return next(item for item in getattr(app, group) if item.label == label)


def test_profile_form_reviews_confirms_and_never_saves_silent_defaults(saved, monkeypatch):
    path, repo, case = saved
    app = launch(path, case, monkeypatch)
    before = dump(path)
    assert not app.exception
    assert widget(app, 'number_input', 'Confirmed household total (optional)').value is None
    assert widget(app, 'number_input', 'Nightly housing budget in USD (optional)').value is None
    widget(app, 'number_input', 'Confirmed household total (optional)').set_value(4)
    widget(app, 'text_input', 'Fictional ZIP code (optional)').input('33101')
    widget(app, 'button', 'Review household details').click().run()
    assert dump(path) == before
    widget(app, 'button', 'Confirm and save household details').click().run()
    assert dump(path) == before and app.warning
    widget(app, 'checkbox', 'I confirm the household details shown above').check()
    widget(app, 'button', 'Confirm and save household details').click().run()
    assert not app.exception
    profile = repo.get_progress_profile(case.case_id)
    assert profile.total == 4 and profile.zip_code == '33101'
    assert profile.housing_budget is None and profile.gas_applicable is None
    assert repo.get_case(case.case_id) == case
    reopened = launch(path, case, monkeypatch)
    assert widget(reopened, 'number_input', 'Confirmed household total (optional)').value == 4


def test_profile_pending_danger_blocks_review_and_save(saved, monkeypatch):
    path, repo, case = saved
    app = launch(path, case, monkeypatch)
    widget(app, 'button', 'Review household details').click().run()
    before = dump(path)
    app.session_state['rr_pending_danger'] = True
    app.run()
    assert dump(path) == before
    assert not any(item.label == 'Confirm and save household details' for item in app.button)


def test_cheap_revision_reads_no_original_bytes_and_detects_changes(saved):
    _, repo, case = saved
    revision = current_progress_revision(repo, case.case_id)
    statements = []
    from contextlib import contextmanager
    original = repo._connection
    @contextmanager
    def traced():
        with original() as connection:
            connection.set_trace_callback(statements.append)
            yield connection
    repo._connection = traced
    assert current_progress_revision(repo, case.case_id) == revision
    assert not any('content' in sql.lower() for sql in statements)
    profile = repo.get_progress_profile(case.case_id)
    profile.pets = False
    repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    assert current_progress_revision(repo, case.case_id) != revision


def test_task_status_and_review_applicability_are_preserved(saved):
    _, repo, case = saved
    plan = repo.get_active_plan(case.case_id)
    assert plan
    plan.proposed_tasks[0].status = TaskStatus.COMPLETED
    other = plan.proposed_tasks[-1]
    plan.task_reviews[str(other.task_id)] = TaskReview(applicable=False, description='Preserved history', explanation='No longer current')
    with repo._connection() as connection:
        connection.execute('UPDATE recovery_plans SET plan_json=? WHERE plan_id=?', (plan.model_dump_json(), str(plan.plan_id)))
    result = load_saved_input(repo, case.case_id)
    mapped = {task.task_id: task for task in result.reviewed_tasks}
    assert mapped[str(plan.proposed_tasks[0].task_id)].completed
    assert not mapped[str(other.task_id)].applicable
    assert repo.get_active_plan(case.case_id) == plan


def test_profile_review_cannot_overwrite_a_newer_saved_profile(saved, monkeypatch):
    path, repo, case = saved
    app = launch(path, case, monkeypatch)
    widget(app, 'number_input', 'Confirmed household total (optional)').set_value(4)
    widget(app, 'button', 'Review household details').click().run()
    profile = repo.get_progress_profile(case.case_id).model_copy(update={'total': 2})
    repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    app.run()
    assert not app.exception
    assert repo.get_progress_profile(case.case_id).total == 2
    assert not any(item.label == 'Confirm and save household details' for item in app.button)


def test_count_sum_is_a_suggestion_until_user_enters_confirmed_total(saved, monkeypatch):
    path, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    records.household.adults, records.household.children = 2, 1
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    app = launch(path, case, monkeypatch)
    assert widget(app, 'number_input', 'Confirmed household total (optional)').value is None
    assert any('suggest 3 people' in item.value for item in app.caption)
    assert repo.get_progress_profile(case.case_id).total is None


def test_saved_profile_offers_existing_needs_review_without_mutating_plan(saved, monkeypatch):
    path, repo, case = saved
    profile = repo.get_progress_profile(case.case_id)
    repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    plan = repo.get_active_plan(case.case_id)
    app = launch(path, case, monkeypatch)
    widget(app, 'button', 'Review changed recovery needs').click().run()
    assert app.session_state['rr_focus'] == 'Continue my recovery'
    assert app.session_state['rr_update_mode'] is True
    assert repo.get_active_plan(case.case_id) == plan


import pytest


@pytest.mark.parametrize('band', ['Unknown', 'Not sure', 'Prefer not to say', 'None available'])
def test_profile_ui_preserves_contribution_uncertainty_and_decline(saved, monkeypatch, band):
    path, repo, case = saved
    app = launch(path, case, monkeypatch)
    widget(app, 'selectbox', 'Broad repair contribution band (optional)').select(band)
    widget(app, 'button', 'Review household details').click().run()
    widget(app, 'checkbox', 'I confirm the household details shown above').check()
    widget(app, 'button', 'Confirm and save household details').click().run()
    assert not app.exception
    profile = repo.get_progress_profile(case.case_id)
    assert profile.contribution_band == (None if band == 'Unknown' else band)
    assert profile.housing_budget is None
