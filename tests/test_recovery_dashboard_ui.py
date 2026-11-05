from uuid import UUID
from datetime import date

from test_recovery_landing import app, button
from recovery.database import SQLiteRecoveryRepository
from test_recovery_capabilities import case_and_records
from recovery.demo_planner import create_demo_draft_plan


def test_returning_dashboard_shows_changes_and_review_cursor_without_writes(app):
    import os
    repo = SQLiteRecoveryRepository(os.environ['READYRELIEF_DB_PATH'])
    case, records = case_and_records(repo)
    draft = create_demo_draft_plan(case, records)
    repo.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True)
    before = repo.list_journey_events(case.case_id)
    app.session_state['rr_case_id'] = str(case.case_id)
    app.session_state['rr_focus'] = 'Continue my recovery'
    app.run()
    assert not app.exception
    assert any('What changed' in w.value for w in app.subheader)
    button(app, 'Mark updates reviewed').click().run()
    assert any('No new updates' in w.value for w in app.info)
    assert repo.list_journey_events(case.case_id) == before
    assert any(w.label == 'Report a change' for w in app.expander)


def test_manual_assessment_preview_does_not_save_until_confirmed(app):
    import os, sqlite3
    path = os.environ['READYRELIEF_DB_PATH']
    next(w for w in app.selectbox if w.label == 'Immediate danger assessment').select('No immediate danger reported')
    next(w for w in app.selectbox if w.label == 'Housing type (optional)').select('Apartment')
    button(app, 'Create draft plan').click().run()
    assert not app.exception
    assert 'rr_case_id' not in app.session_state
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM recovery_cases').fetchone()[0] == 0
    assert any('Your situation to review' in w.value for w in app.subheader)
    button(app, 'Confirm situation and create draft').click().run()
    assert not app.exception
    records = SQLiteRecoveryRepository(path).get_recovery_records(UUID(app.session_state['rr_case_id']))
    assert records.household.housing_type == 'Apartment'
    assert records.household.insurer_contact_status == 'Unknown'


def test_synthetic_checkpoint_is_explicit_and_separate_from_main_database(app):
    import os, sqlite3
    path = os.environ['READYRELIEF_DB_PATH']
    assert not app.session_state.get('rr_demo_active', False)
    next(w for w in app.selectbox if w.label == 'Fictional household').select('chen')
    app.run()
    next(w for w in app.selectbox if w.label == 'Story checkpoint').select(30)
    button(app, 'Load fictional checkpoint').click().run()
    assert not app.exception
    assert app.session_state['rr_demo_active']
    assert app.session_state['rr_demo_selection']['day'] == 30
    assert any('What changed' in w.value for w in app.subheader)
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM recovery_cases').fetchone()[0] == 0
    button(app, 'Leave fictional recovery scenario').click().run()
    assert not app.exception
    assert not app.session_state.get('rr_demo_active', False)


def test_demo_danger_interrupts_and_leaving_keeps_its_saved_report(app):
    next(w for w in app.selectbox if w.label == 'Fictional household').select('lewis')
    app.run()
    next(w for w in app.selectbox if w.label == 'Story checkpoint').select(30)
    button(app, 'Load fictional checkpoint').click().run()
    assert not app.exception
    selection = app.session_state['rr_demo_selection']
    demo_path = app.session_state['rr_demo_database_path']
    assert app.session_state['rr_emergency']
    assert any(w.label == 'Call 911' for w in app.get('link_button'))
    button(app, 'Leave fictional recovery scenario').click().run()
    assert not app.exception
    assert not app.session_state['rr_emergency']
    assert SQLiteRecoveryRepository(demo_path).get_case(UUID(selection['case_id'])).intake.immediate_danger is True


def test_demo_pending_revision_requires_safety_recheck_and_approval(app):
    next(w for w in app.selectbox if w.label == 'Fictional household').select('bennett')
    app.run()
    next(w for w in app.selectbox if w.label == 'Story checkpoint').select(7)
    button(app, 'Load fictional checkpoint').click().run()
    assert not app.exception
    assert 'rr_revision' in app.session_state
    assert not any(w.label == 'Approve this revision' for w in app.button)
    case_id = UUID(app.session_state['rr_case_id'])
    repo = SQLiteRecoveryRepository(app.session_state['rr_demo_database_path'])
    before = repo.list_journey_events(case_id)
    next(w for w in app.selectbox if w.label == 'Updated immediate danger assessment').select('No immediate danger reported').run()
    assert repo.list_journey_events(case_id) == before
    assert 'rr_revision' in app.session_state
    button(app, 'Approve this revision').click().run()
    assert not app.exception
    assert 'rr_revision' not in app.session_state
    assert len(repo.list_journey_events(case_id)) > len(before)
    assert not any('Fictional update awaiting' in w.value for w in app.warning)


def test_saved_replay_resumes_after_new_browser_session_with_progress(app):
    from streamlit.testing.v1 import AppTest
    from recovery.models import TaskStatus
    button(app, 'Load fictional checkpoint').click().run()
    case_id = UUID(app.session_state['rr_case_id'])
    repo = SQLiteRecoveryRepository(app.session_state['rr_demo_database_path'])
    plan = repo.get_active_plan(case_id)
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED,
                            expected_progress_version=plan.progress_version)
    before = repo.list_journey_events(case_id)
    from pathlib import Path
    fresh = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    fresh.session_state['page'] = 'Recover'
    fresh.run()
    next(w for w in fresh.text_input if w.label == 'Replay case ID').input(str(case_id))
    button(fresh, 'Resume fictional replay').click().run()
    assert not fresh.exception
    assert fresh.session_state['rr_case_id'] == str(case_id)
    assert fresh.session_state['rr_demo_selection']['scenario_id'] == 'rivera'
    assert repo.get_active_plan(case_id).proposed_tasks[0].status == TaskStatus.COMPLETED
    assert repo.list_journey_events(case_id) == before
