"""Offline regressions for structured danger and confirmed-record approval guards."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from domain.contracts import AppMode, Household
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import DamageRecord, RecoveryCase, RecoveryIntake, RecoveryPlan, TaskPriority, TaskReview
from recovery.reassessment import ReassessmentPreview, preview_reassessment
from services.assistant import Proposal, capture, execute


def setup_case(tmp_path, *, approved=True):
    repo = SQLiteRecoveryRepository(tmp_path / 'integration.sqlite3')
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Minor reported damage',
        utility_availability={'water': True}, temporary_accommodation_status='Staying with others',
        household_recovery_needs=[], immediate_danger=False))
    repo.create_case(case)
    records = repo.get_recovery_records(case.case_id)
    draft = create_demo_draft_plan(case, records)
    plan = repo.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True) if approved else draft
    state = dict(page='Recover', household=Household(), location_id='miami', mode=AppMode.DEMO,
                 rr_case_id=str(case.case_id), rr_emergency=False)
    if not approved:
        state['rr_draft'] = draft.model_dump_json()
    return repo, case, records, plan, state


@pytest.mark.parametrize('label,kind,submit,confirmation', [
    ('Reported property damage', 'text_area', 'Save confirmed household details', 'I confirm these household details'),
    ('Item or area description', 'text_input', 'Save confirmed damage record', 'I confirm this damage record'),
    ('User-reported damage description', 'text_area', 'Save confirmed damage record', 'I confirm this damage record'),
    ('Optional notes', 'text_area', 'Save confirmed damage record', 'I confirm this damage record'),
])
def test_current_danger_in_structured_narrative_interrupts_before_records_save(tmp_path, monkeypatch, label, kind, submit, confirmation):
    repo, case, records, _, _ = setup_case(tmp_path)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'integration.sqlite3'))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    app.run()
    next(w for w in app.button if w.label == 'Document damage').click().run()
    next(w for w in app.text_input if w.label == 'Item or area description').input('Furniture')
    next(w for w in app.text_area if w.label == 'User-reported damage description').input('Wet upholstery')
    next(w for w in getattr(app, kind) if w.label == label).input('I smell gas right now')
    next(w for w in app.checkbox if w.label == confirmation).check()
    next(w for w in app.button if w.label == submit).click().run()
    assert not app.exception
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    assert repo.get_recovery_records(case.case_id) == records
    assert app.session_state['rr_emergency'] is True


def test_assistant_records_change_invalidates_proposed_progress(tmp_path):
    repo, case, records, plan, state = setup_case(tmp_path)
    proposal = Proposal(answer='Review', action={'kind':'update_task', 'task_id':plan.proposed_tasks[0].task_id,
        'status':'COMPLETED'}, snapshot=capture(state, repo))
    records.household.children = 2
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    with pytest.raises(ValueError, match='changed'):
        execute(proposal, state, repo, confirmed=True)
    assert repo.get_active_plan(case.case_id).progress_version == 0


def test_assistant_reassessment_includes_confirmed_damage_snapshots(tmp_path):
    repo, case, records, _, state = setup_case(tmp_path)
    records.damage_records.append(DamageRecord(case_id=case.case_id, item_description='Sofa', damage_description='Wet'))
    records = repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    proposal = Proposal(answer='Review', action={'kind':'reassess', 'intake':case.intake.model_dump(exclude={'immediate_danger'})}, snapshot=capture(state, repo))
    execute(proposal, state, repo, confirmed=True, danger_confirmed=True)
    preview = ReassessmentPreview.model_validate_json(state['rr_revision'])
    assert preview.previous_records == records == preview.updated_records
    assert any('Sofa' in r.task.title for r in preview.new_tasks)


def test_failed_assistant_approval_leaves_no_persisted_draft(tmp_path):
    repo, case, records, draft, state = setup_case(tmp_path, approved=False)
    records.household.children = 2
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    proposal = Proposal(answer='Review', action={'kind':'approve_plan'}, snapshot=capture(state, repo))
    with pytest.raises(ValueError, match='stale'):
        execute(proposal, state, repo, confirmed=True)
    assert repo.get_plan(draft.plan_id) is None
    assert repo.get_active_plan(case.case_id) is None


def test_assistant_new_draft_binds_empty_confirmed_records(tmp_path):
    repo = SQLiteRecoveryRepository(tmp_path / 'new.sqlite3')
    state = dict(page='Recover', household=Household(), location_id='miami', mode=AppMode.DEMO, rr_emergency=False)
    intake = dict(disaster_type='Flood', housing_condition='Minor reported damage', utility_availability={'water':True},
                  temporary_accommodation_status='Staying with others', household_recovery_needs=[])
    proposal = Proposal(answer='Review', action={'kind':'draft_plan','intake':intake}, snapshot=capture(state,repo))
    execute(proposal, state, repo, confirmed=True, danger_confirmed=True)
    draft = RecoveryPlan.model_validate_json(state['rr_draft'])
    assert draft.records_version == 0


def test_revised_tasks_keep_relevant_pathways_and_prerequisites(tmp_path):
    repo, case, records, plan, _ = setup_case(tmp_path)
    update = case.intake.model_copy(deep=True)
    update.temporary_accommodation_status = 'No lodging arranged'
    update.utility_availability['water'] = False
    records.damage_records.append(DamageRecord(case_id=case.case_id,item_description='Sofa',damage_description='Wet'))
    preview = preview_reassessment(case,plan,update,previous_records=repo.get_recovery_records(case.case_id),updated_records=records)
    tasks = {r.task.title:r.task for r in preview.new_tasks}
    assert tasks['Review changed housing arrangements'].resource_categories == ['Housing']
    assert tasks['Review water availability gap'].resource_categories == ['Water']
    assert 'provider' in ' '.join(tasks['Review water availability gap'].dependencies).lower()
    assert 'safe' in ' '.join(tasks['Document newly reported damage: Sofa'].dependencies).lower()


def test_effective_task_view_orders_reviewed_priorities_without_mutating_history(tmp_path):
    from recovery.task_view import current_task_views
    repo, case, records, plan, state = setup_case(tmp_path)
    first, second = plan.proposed_tasks[:2]
    plan.task_reviews[str(first.task_id)] = TaskReview(priority=TaskPriority.LOW,applicable=False,
        description='Historical description',explanation='Resolved reported need')
    plan.task_reviews[str(second.task_id)] = TaskReview(priority=TaskPriority.URGENT,applicable=True,
        description='Updated description',explanation='Current reported need')
    before = plan.model_dump_json()
    views = current_task_views(plan)
    assert views[0].task.task_id == second.task_id
    assert views[0].priority is TaskPriority.URGENT
    assert views[0].description == 'Updated description'
    assert next(v for v in views if v.task.task_id == first.task_id).applicable is False
    assert plan.model_dump_json() == before
    # Chat must use the same effective priority order as task cards/exports.
    with repo._connection() as connection:
        connection.execute('UPDATE recovery_plans SET plan_json=? WHERE plan_id=?',(plan.model_dump_json(),str(plan.plan_id)))
    proposal = Proposal(answer='Review',action={'kind':'show_plan'},snapshot=capture(state,repo))
    result = execute(proposal,state,repo,confirmed=True)
    assert result.index(second.title) < result.index(first.title)


@pytest.mark.parametrize('field', ['housing_condition', 'temporary_accommodation_status', 'household_recovery_needs'])
def test_assistant_structured_intake_danger_interrupts_before_case_creation(tmp_path, field):
    repo = SQLiteRecoveryRepository(tmp_path / 'new.sqlite3')
    state = dict(page='Recover', household=Household(), location_id='miami', mode=AppMode.DEMO, rr_emergency=False)
    intake = dict(disaster_type='Flood', housing_condition='Minor reported damage', utility_availability={'water':True},
                  temporary_accommodation_status='Staying with others', household_recovery_needs=[])
    intake[field] = ['I smell gas right now'] if field == 'household_recovery_needs' else 'I smell gas right now'
    proposal = Proposal(answer='Review',action={'kind':'draft_plan','intake':intake},snapshot=capture(state,repo))
    execute(proposal,state,repo,confirmed=True,danger_confirmed=True)
    assert state['rr_emergency'] is True
    assert 'rr_case_id' not in state


def test_assistant_records_race_at_task_write_rejects_stale_update(tmp_path):
    from recovery.models import TaskStatus
    repo, case, records, plan, state = setup_case(tmp_path)
    proposal = Proposal(answer='Review', action={'kind':'update_task', 'task_id':plan.proposed_tasks[0].task_id,
        'status':'COMPLETED'}, snapshot=capture(state, repo))

    class ConcurrentRecords:
        def __getattr__(self, name):
            return getattr(repo, name)

        def update_task_status(self, *args, **kwargs):
            records.household.children = 2
            repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
            return repo.update_task_status(*args, **kwargs)

    with pytest.raises(ValueError, match='stale.*records'):
        execute(proposal, state, ConcurrentRecords(), confirmed=True)
    assert repo.get_active_plan(case.case_id).proposed_tasks[0].status is TaskStatus.NOT_STARTED
    assert repo.list_task_history(case.case_id) == []
    assert not any(e['kind'] == 'task_status_changed' for e in repo.list_journey_events(case.case_id))
    assert repo.get_recovery_records(case.case_id).household.children == 2


def test_completed_resolved_tasks_become_historical_without_losing_completion(tmp_path):
    from recovery.dashboard import build_dashboard
    from recovery.models import TaskStatus
    repo, case, records, _, _ = setup_case(tmp_path, approved=False)
    case.intake.temporary_accommodation_status = 'No lodging arranged'
    # This report is a separate persisted case so the initial plan reflects housing need.
    case = RecoveryCase(intake=case.intake)
    repo.create_case(case)
    records = repo.get_recovery_records(case.case_id)
    draft = create_demo_draft_plan(case, records)
    plan = repo.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True)
    housing = next(t for t in plan.proposed_tasks if t.planning_key == 'housing')
    repo.update_task_status(plan.plan_id, housing.task_id, TaskStatus.COMPLETED)
    plan = repo.get_active_plan(case.case_id)
    original = plan.model_dump_json()
    updated = case.intake.model_copy(deep=True)
    updated.temporary_accommodation_status = 'Staying with others'
    preview = preview_reassessment(case, plan, updated, previous_records=records, updated_records=records)
    accepted = repo.approve_reassessment(preview, explicitly_approved=True)
    view = build_dashboard(repo.get_case(case.case_id), records, accepted, repo.list_journey_events(case.case_id))
    assert view.counts.completed_historical == 1
    assert view.counts.completed == 0
    assert view.counts.historical == 1
    assert view.counts.current == len(accepted.proposed_tasks) - 1
    assert accepted.task_reviews[str(housing.task_id)].applicable is False
    assert next(t for t in accepted.proposed_tasks if t.task_id == housing.task_id).status is TaskStatus.COMPLETED
    assert repo.get_plan(plan.plan_id).model_dump_json() == original
