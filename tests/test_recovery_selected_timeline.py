"""Selected CAP contributions from 8227671; no replay or optional household model changes."""
import sqlite3
from datetime import datetime,timedelta,timezone
import pytest
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import RecoveryCase,RecoveryIntake,RecoveryRecords,TaskStatus

def case_fixture():
    return RecoveryCase(intake=RecoveryIntake(disaster_type='Synthetic flood',
        housing_condition='Reported water damage', utility_availability={'electricity': False},
        temporary_accommodation_status='No lodging arranged', immediate_danger=False,
        household_recovery_needs=['Damage documentation']))


def test_events_use_clock_and_noops_proposals_reads_do_not_add_events(tmp_path):
    now = datetime(2026, 11, 1, 23, 0, tzinfo=timezone(timedelta(hours=-5)))
    repo = SQLiteRecoveryRepository(tmp_path / 'journey.db', clock=lambda: now)
    case = case_fixture()
    repo.create_case(case)
    assert case.created_at == datetime(2026, 11, 2, 4, tzinfo=timezone.utc)
    records = repo.get_recovery_records(case.case_id)
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    assert repo.get_recovery_records(case.case_id).version == 1
    records = repo.get_recovery_records(case.case_id)
    draft = create_demo_draft_plan(case)
    repo.save_draft_plan(draft)
    assert [e['kind'] for e in repo.list_journey_events(case.case_id)] == ['case_created']
    plan = repo.approve_plan(draft.plan_id)
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    task = plan.proposed_tasks[0]
    repo.update_task_status(plan.plan_id, task.task_id, TaskStatus.IN_PROGRESS)
    repo.update_task_status(plan.plan_id, task.task_id, TaskStatus.IN_PROGRESS)
    assert repo.get_active_plan(case.case_id).progress_version == 1
    records.household.adults = 2
    repo.save_recovery_records(records, expected_version=1, explicitly_confirmed=True)
    repo.report_immediate_danger(case.case_id)
    repo.report_immediate_danger(case.case_id)
    events = repo.list_journey_events(case.case_id)
    assert [e['kind'] for e in events] == ['case_created', 'plan_approved', 'task_status_changed', 'records_confirmed', 'danger_reported']
    assert events[2]['occurred_at'] == '2026-11-03T12:00:00+00:00'
    assert 'Adults: 2' in events[3]['detail']
    assert repo.list_task_history(case.case_id)[0]['changed_at'] == events[2]['occurred_at']
    assert len(set(e['event_id'] for e in events)) == 5


def test_event_failure_rolls_back_case_and_records_atomically(tmp_path):
    path = tmp_path / 'rollback.db'
    repo = SQLiteRecoveryRepository(path)
    case = case_fixture()
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_journey BEFORE INSERT ON recovery_journey_events BEGIN SELECT RAISE(ABORT, 'synthetic event failure'); END")
    with pytest.raises(sqlite3.Error):
        repo.create_case(case)
    assert repo.get_case(case.case_id) is None
    with sqlite3.connect(path) as connection:
        connection.execute('DROP TRIGGER fail_journey')
    repo.create_case(case)
    records = repo.get_recovery_records(case.case_id)
    records.household.adults = 2
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_journey BEFORE INSERT ON recovery_journey_events BEGIN SELECT RAISE(ABORT, 'synthetic event failure'); END")
    with pytest.raises(sqlite3.Error):
        repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    assert repo.get_recovery_records(case.case_id).version == 0
    assert len(repo.list_journey_events(case.case_id)) == 1


def test_stale_records_do_not_append_event(tmp_path):
    repo = SQLiteRecoveryRepository(tmp_path / 'stale.db')
    case = case_fixture()
    repo.create_case(case)
    records = repo.get_recovery_records(case.case_id)
    records.household.adults = 2
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    with pytest.raises(ValueError, match='stale'):
        repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    assert len(repo.list_journey_events(case.case_id)) == 2


def test_legacy_database_has_no_invented_events(tmp_path):
    path = tmp_path / 'legacy.db'
    case = case_fixture()
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE recovery_cases (case_id TEXT PRIMARY KEY, case_json TEXT NOT NULL)')
        connection.execute('INSERT INTO recovery_cases VALUES (?,?)', (str(case.case_id), case.model_dump_json()))
    repo = SQLiteRecoveryRepository(path)
    assert repo.get_case(case.case_id) == case
    assert repo.list_journey_events(case.case_id) == []


def test_naive_repository_clock_is_rejected_before_case_write(tmp_path):
    repo = SQLiteRecoveryRepository(tmp_path / 'naive.db', clock=lambda: datetime(2026, 11, 1))
    case = case_fixture()
    with pytest.raises(ValueError, match='timezone-aware'):
        repo.create_case(case)
    assert repo.get_case(case.case_id) is None


def test_approved_revision_keeps_completion_and_records_clocked_accepted_change(tmp_path):
    from recovery.reassessment import preview_reassessment
    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    repo = SQLiteRecoveryRepository(tmp_path / 'revision.db', clock=lambda: now)
    case = case_fixture()
    repo.create_case(case)
    plan = create_demo_draft_plan(case)
    repo.save_draft_plan(plan)
    repo.approve_plan(plan.plan_id)
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED)
    plan = repo.get_active_plan(case.case_id)
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    updated = case.intake.model_copy(update={'temporary_accommodation_status': 'Staying with family'})
    preview = preview_reassessment(case, plan, updated)
    before_events = repo.list_journey_events(case.case_id)
    assert len(before_events) == 3
    approved = repo.approve_reassessment(preview, explicitly_approved=True)
    events = repo.list_journey_events(case.case_id)
    assert events[-1]['kind'] == 'revision_approved'
    assert events[-1]['occurred_at'] == '2026-11-03T12:00:00+00:00'
    assert 'Staying with family' in events[-1]['detail']
    assert repo.get_case(case.case_id).updated_at == now
    assert approved.proposed_tasks[0].status is TaskStatus.COMPLETED
    with pytest.raises(ValueError, match='stale'):
        repo.approve_reassessment(preview, explicitly_approved=True)
    assert repo.list_journey_events(case.case_id) == events


@pytest.mark.parametrize('action', ['approve', 'progress', 'revision', 'danger'])
def test_event_insert_failure_rolls_back_every_accepted_operation(tmp_path, action):
    from recovery.reassessment import preview_reassessment
    path = tmp_path / f'{action}.db'
    repo = SQLiteRecoveryRepository(path)
    case = case_fixture()
    repo.create_case(case)
    plan = create_demo_draft_plan(case)
    repo.save_draft_plan(plan)
    if action != 'approve':
        plan = repo.approve_plan(plan.plan_id)
    preview = preview_reassessment(case, plan, case.intake.model_copy(update={'temporary_accommodation_status': 'Staying with family'})) if action == 'revision' else None
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_journey BEFORE INSERT ON recovery_journey_events BEGIN SELECT RAISE(ABORT, 'synthetic event failure'); END")
        before = list(connection.iterdump())
    with pytest.raises(sqlite3.Error):
        if action == 'approve':
            repo.approve_plan(plan.plan_id)
        elif action == 'progress':
            repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED)
        elif action == 'revision':
            repo.approve_reassessment(preview, explicitly_approved=True)
        else:
            repo.report_immediate_danger(case.case_id)
    with sqlite3.connect(path) as connection:
        assert list(connection.iterdump()) == before
