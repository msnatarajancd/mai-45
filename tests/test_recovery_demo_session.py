"""Replay labels and clocks must never follow an unrelated selected case."""
import os
from uuid import UUID

import pytest

from domain.contracts import AppMode, Household
from recovery.database import SQLiteRecoveryRepository
from recovery.demo import load_checkpoint
from recovery.demo_session import enter_demo
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import TaskStatus
from services.assistant import Proposal, capture, execute
from test_recovery_capabilities import case_and_records
from test_recovery_landing import app, button


def test_leaving_demo_danger_does_not_report_danger_on_original_case(app):
    primary = SQLiteRecoveryRepository(os.environ['READYRELIEF_DB_PATH'])
    original, records = case_and_records(primary)
    draft = create_demo_draft_plan(original, records)
    primary.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True)
    app.session_state['rr_case_id'] = str(original.case_id)
    app.session_state['rr_focus'] = 'Continue my recovery'
    app.run()
    button(app, 'Load fictional checkpoint').click().run()
    demo_path = app.session_state['rr_demo_database_path']
    demo_id = UUID(app.session_state['rr_case_id'])
    next(w for w in app.selectbox if w.label == 'Updated immediate danger assessment').select('Immediate danger reported').run()
    assert app.session_state['rr_emergency']
    button(app, 'Leave fictional recovery scenario').click().run()
    assert not app.exception
    assert app.session_state['rr_case_id'] == str(original.case_id)
    assert primary.get_case(original.case_id).intake.immediate_danger is False
    assert not app.session_state['rr_emergency']
    assert SQLiteRecoveryRepository(demo_path).get_case(demo_id).intake.immediate_danger is True


def test_open_different_case_leaves_replay_and_preserves_its_progress(app):
    primary = SQLiteRecoveryRepository(os.environ['READYRELIEF_DB_PATH'])
    original, _ = case_and_records(primary)
    next(w for w in app.selectbox if w.label == 'Fictional household').select('rivera')
    app.run()
    button(app, 'Load fictional checkpoint').click().run()
    demo_path = app.session_state['rr_demo_database_path']
    demo_id = UUID(app.session_state['rr_case_id'])
    demo_repo = SQLiteRecoveryRepository(demo_path)
    plan = demo_repo.get_active_plan(demo_id)
    task = plan.proposed_tasks[0]
    demo_repo.update_task_status(plan.plan_id, task.task_id, TaskStatus.COMPLETED)
    button(app, 'Open a different case').click().run()
    assert not app.exception
    assert not app.session_state.get('rr_demo_active', False)
    next(w for w in app.text_input if w.label == 'Saved fictional case ID').input(str(original.case_id))
    button(app, 'Resume saved case').click().run()
    assert not app.exception
    assert app.session_state['rr_case_id'] == str(original.case_id)
    assert not any('Story as of' in w.value for w in app.caption)
    assert demo_repo.get_active_plan(demo_id).proposed_tasks[0].status is TaskStatus.COMPLETED


def test_assistant_cannot_resume_another_case_under_replay_metadata(tmp_path):
    path = tmp_path / 'stories-demo.sqlite3'
    rivera = load_checkpoint(path, 'rivera', 1)
    chen = load_checkpoint(path, 'chen', 30)
    state = dict(page='Recover', household=Household(), location_id='miami', mode=AppMode.DEMO)
    enter_demo(state, chen, path)
    repo = SQLiteRecoveryRepository(path)
    proposal = Proposal(answer='Review', action={'kind': 'resume_case', 'case_id': rivera.case_id},
                        snapshot=capture(state, repo))
    with pytest.raises(ValueError, match='Leave.*fictional'):
        execute(proposal, state, repo, confirmed=True)
    assert state['rr_case_id'] == str(chen.case_id)
    assert state['rr_demo_selection']['case_id'] == str(chen.case_id)


def test_repository_rejects_case_that_does_not_match_replay_clock(tmp_path, monkeypatch):
    from ui import recovery_page
    path = tmp_path / 'stories-demo.sqlite3'
    rivera = load_checkpoint(path, 'rivera', 1)
    chen = load_checkpoint(path, 'chen', 30)
    state = {}
    enter_demo(state, chen, path)
    state['rr_case_id'] = str(rivera.case_id)
    monkeypatch.setattr(recovery_page.st, 'session_state', state)
    with pytest.raises(ValueError, match='replay.*case'):
        recovery_page.repository()


def test_dashboard_rejects_metadata_for_another_case(tmp_path, monkeypatch):
    from recovery import dashboard_ui
    path = tmp_path / 'stories-demo.sqlite3'
    rivera = load_checkpoint(path, 'rivera', 1)
    chen = load_checkpoint(path, 'chen', 30)
    state = {}
    enter_demo(state, chen, path)
    repo = SQLiteRecoveryRepository(path)
    monkeypatch.setattr(dashboard_ui.st, 'session_state', state)
    with pytest.raises(ValueError, match='replay.*case'):
        dashboard_ui.render_overview(repo, repo.get_case(rivera.case_id), repo.get_active_plan(rivera.case_id))
