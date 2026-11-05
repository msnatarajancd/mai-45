"""Offline regression coverage for accepted journey events and honest projections."""
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import HouseholdRecoveryDetails, RecoveryCase, RecoveryIntake, RecoveryRecords, TaskStatus


def case_fixture():
    return RecoveryCase(intake=RecoveryIntake(disaster_type='Synthetic flood',
        housing_condition='Reported water damage', utility_availability={'electricity': False},
        temporary_accommodation_status='No lodging arranged', immediate_danger=False,
        household_recovery_needs=['Damage documentation']))


def test_additive_records_validate_old_payload_and_new_explicit_facts():
    case = case_fixture()
    old = RecoveryRecords.model_validate({'case_id': str(case.case_id)})
    assert old.incident_date is None and old.next_check_in_date is None
    assert old.household.insurer_contact_status == 'Unknown'
    assert old.household.accessibility_needs == []
    records = old.model_copy(update={'incident_date': date(2026, 11, 1)})
    records.household = HouseholdRecoveryDetails(housing_type='Rented apartment',
        accessibility_needs=['Step-free entrance'], insurer_contact_status='Contacted')
    assert RecoveryRecords.model_validate_json(records.model_dump_json()) == records
    with pytest.raises(ValidationError):
        HouseholdRecoveryDetails(insurer_contact_status='Claim approved')


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
    records.household.insurer_contact_status = 'Contacted'
    repo.save_recovery_records(records, expected_version=1, explicitly_confirmed=True)
    repo.report_immediate_danger(case.case_id)
    repo.report_immediate_danger(case.case_id)
    events = repo.list_journey_events(case.case_id)
    assert [e['kind'] for e in events] == ['case_created', 'plan_approved', 'task_status_changed', 'records_confirmed', 'danger_reported']
    assert events[2]['occurred_at'] == '2026-11-03T12:00:00+00:00'
    assert 'Contacted' in events[3]['detail']
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


@pytest.mark.parametrize('incident,as_of,state,elapsed,target', [
    (None, date(2026, 11, 5), 'unknown', None, 2),
    (date(2026, 11, 8), date(2026, 11, 5), 'future', None, 2),
    (date(2026, 11, 1), date(2026, 11, 5), 'known', 4, 2),
    (date(2026, 11, 1), date(2026, 11, 8), 'known', 7, -1),
])
def test_dashboard_dates_are_reported_elapsed_days_and_separate_targets(incident, as_of, state, elapsed, target):
    from recovery.dashboard import build_dashboard
    case = case_fixture()
    records = RecoveryRecords(case_id=case.case_id, incident_date=incident, next_check_in_date=date(2026, 11, 7))
    view = build_dashboard(case, records, None, [], as_of=as_of)
    assert (view.incident_date_state, view.elapsed_days, view.target_days) == (state, elapsed, target)
    assert view.timeline == () and view.next_task is None
    assert view.first_visit and view.latest_event_id is None


def test_dashboard_effective_counts_exclude_historical_and_draft_tasks():
    from recovery.dashboard import build_dashboard
    from recovery.models import PlanStatus, TaskReview, TaskPriority
    case = case_fixture()
    records = RecoveryRecords(case_id=case.case_id)
    draft = create_demo_draft_plan(case)
    assert build_dashboard(case, records, draft, []).counts.total == 0
    plan = draft.model_copy(deep=True, update={'approval_status': PlanStatus.APPROVED})
    historical, completed, blocked, next_task = plan.proposed_tasks[:4]
    historical.status = completed.status = TaskStatus.COMPLETED
    blocked.status = TaskStatus.BLOCKED
    plan.task_reviews[str(historical.task_id)] = TaskReview(applicable=False, description='Historical', explanation='Need changed')
    plan.task_reviews[str(next_task.task_id)] = TaskReview(priority=TaskPriority.URGENT, description='Current step', explanation='Reviewed urgency')
    view = build_dashboard(case, records, plan, [])
    assert view.counts.total == len(plan.proposed_tasks)
    assert view.counts.current == len(plan.proposed_tasks) - 1
    assert view.counts.completed == 1 and view.counts.completed_historical == 1
    assert view.counts.historical == 1 and view.counts.blocked == 1
    assert view.next_task.task.task_id == next_task.task_id
    case.intake.immediate_danger = True
    interrupted = build_dashboard(case, records, plan, [])
    assert interrupted.emergency and interrupted.next_task is None
    case.intake.immediate_danger = None
    assert build_dashboard(case, records, plan, []).next_task is None


def test_dashboard_cursor_and_timezone_do_not_invent_events_or_mutate_inputs():
    from recovery.dashboard import build_dashboard
    case = case_fixture()
    records = RecoveryRecords(case_id=case.case_id, incident_date=date(2026, 11, 1))
    events = [dict(event_id=1, kind='case_created', title='Situation saved', detail='Reported', occurred_at='2026-11-02T04:00:00+00:00'),
              dict(event_id=2, kind='plan_approved', title='Plan approved', detail='Accepted', occurred_at='2026-11-02T05:00:00+00:00')]
    local_as_of = datetime(2026, 11, 1, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
    view = build_dashboard(case, records, None, events, as_of=local_as_of, since_event_id=1)
    assert view.as_of == date(2026, 11, 1) and view.elapsed_days == 0
    assert [event.event_id for event in view.timeline] == [1]
    assert view.changes == () and not view.first_visit and view.latest_event_id == 1
    assert events[0]['title'] == 'Situation saved'
    with pytest.raises((AttributeError, TypeError)):
        view.elapsed_days = 200
    with pytest.raises(ValueError, match='timezone-aware'):
        build_dashboard(case, records, None, events, as_of=datetime(2026, 11, 1))
    with pytest.raises(ValueError, match='belong'):
        build_dashboard(case_fixture(), records, None, [])


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


def test_dashboard_next_task_snapshot_cannot_modify_source_plan():
    from recovery.dashboard import build_dashboard
    from recovery.models import PlanStatus
    case = case_fixture()
    plan = create_demo_draft_plan(case).model_copy(update={'approval_status': PlanStatus.APPROVED})
    original_title = plan.proposed_tasks[0].title
    view = build_dashboard(case, RecoveryRecords(case_id=case.case_id), plan, [])
    view.next_task.task.title = 'Modified detached display copy'
    assert plan.proposed_tasks[0].title == original_title


def test_events_name_the_confirmed_contact_and_accommodation_change(tmp_path):
    from recovery.reassessment import preview_reassessment
    repo = SQLiteRecoveryRepository(tmp_path / 'labels.db')
    case = case_fixture()
    repo.create_case(case)
    records = repo.get_recovery_records(case.case_id)
    records.household.insurer_contact_status = 'Follow-up requested'
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    assert 'follow-up' in repo.list_journey_events(case.case_id)[-1]['title'].casefold()
    plan = create_demo_draft_plan(case)
    repo.save_draft_plan(plan)
    plan = repo.approve_plan(plan.plan_id)
    preview = preview_reassessment(case, plan, case.intake.model_copy(update={'temporary_accommodation_status': 'Staying with others'}))
    repo.approve_reassessment(preview, explicitly_approved=True)
    assert 'accommodation' in repo.list_journey_events(case.case_id)[-1]['title'].casefold()
