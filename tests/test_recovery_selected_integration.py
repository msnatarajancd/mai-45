"""Selected projection and concurrency regressions attributed to 8227671."""
import pytest
from domain.contracts import AppMode,Household
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import DamageRecord,RecoveryCase,RecoveryIntake,RecoveryPlan,TaskPriority,TaskReview
from recovery.reassessment import preview_reassessment
from services.assistant import Proposal,capture,execute
from test_recovery_landing import app
from test_insurance_workspace import insurance
from test_recovery_records import saved

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


def test_assistant_records_change_invalidates_proposed_progress(tmp_path):
    repo, case, records, plan, state = setup_case(tmp_path)
    proposal = Proposal(answer='Review', action={'kind':'update_task', 'task_id':plan.proposed_tasks[0].task_id,
        'status':'COMPLETED'}, snapshot=capture(state, repo))
    records.household.children = 2
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    with pytest.raises(ValueError, match='changed'):
        execute(proposal, state, repo, confirmed=True)
    assert repo.get_active_plan(case.case_id).progress_version == 0


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
    from recovery.task_view import current_task_views
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
    views = current_task_views(accepted)
    historical = [v for v in views if not v.applicable]
    assert len(historical) == 1 and historical[0].task.status is TaskStatus.COMPLETED
    assert accepted.task_reviews[str(housing.task_id)].applicable is False
    assert next(t for t in accepted.proposed_tasks if t.task_id == housing.task_id).status is TaskStatus.COMPLETED
    assert repo.get_plan(plan.plan_id).model_dump_json() == original



def test_guided_flow_timeline_reopen_and_insurance_remain_connected(app, monkeypatch):
    from test_recovery_capabilities import test_full_personalized_plan_progress_and_confirmed_reassessment
    from test_recovery_landing import button
    from uuid import UUID
    import os
    test_full_personalized_plan_progress_and_confirmed_reassessment(app, monkeypatch)
    repo=SQLiteRecoveryRepository(os.environ['READYRELIEF_DB_PATH'])
    case_id=UUID(app.session_state['rr_case_id'])
    events=repo.list_journey_events(case_id)
    assert [e['kind'] for e in events].count('task_status_changed')==3
    assert [e['kind'] for e in events].count('revision_approved')==1
    button(app,'Continue my recovery').click().run()
    assert not app.exception
    assert any(w.label=='Recovery timeline' for w in app.expander)
    assert any('Recovery plan approved' in w.value for w in app.text)
    assert any('User-reported task progress' in w.value for w in app.text)
    assert not any('fictional recovery scenario' in w.label.lower() for w in app.button)


def test_saved_photo_insurance_exports_do_not_change_progress_or_journey(insurance):
    from test_insurance_workspace import photo,save,dump
    from recovery.insurance_exports import build_preparation_package
    from recovery.insurance_models import InsuranceProfile
    path,repo,case=insurance
    snapshot=repo.get_insurance_snapshot(case.case_id)
    workspace=snapshot.workspace.model_copy(deep=True)
    workspace.profile=InsuranceProfile(insurer_name='Synthetic Combined Insurer')
    original=photo(snapshot)
    plan=repo.get_active_plan(case.case_id)
    events=repo.list_journey_events(case.case_id)
    save(repo,snapshot,workspace,additions=[original])
    reopened=SQLiteRecoveryRepository(path)
    current=reopened.get_insurance_snapshot(case.case_id)
    assert current.workspace.profile.insurer_name=='Synthetic Combined Insurer'
    assert current.attachments[0].content==original.content
    assert current.attachments[0].metadata.damage_id==current.records.damage_records[0].damage_id
    before=dump(path)
    pdf,csv,archive=build_preparation_package(reopened,case.case_id)
    assert pdf.startswith(b'%PDF') and b'Refrigerator' in csv and archive.startswith(b'PK')
    assert dump(path)==before
    assert reopened.get_active_plan(case.case_id)==plan
    assert reopened.list_journey_events(case.case_id)==events


@pytest.mark.parametrize('screen', ['guided', 'legacy'])
def test_guided_task_submit_rejects_records_changed_since_display(insurance, monkeypatch, screen):
    from test_insurance_ui import launch
    from test_recovery_landing import button
    from recovery.models import TaskStatus
    path,repo,case=insurance
    if screen == 'guided':
        app=launch(path,case,monkeypatch)
        button(app,'Continue my recovery').click().run()
    else:
        from streamlit.testing.v1 import AppTest
        def render_legacy(path, case_id):
            import streamlit as st
            from recovery.database import SQLiteRecoveryRepository
            from recovery.ui import _render_dashboard
            st.session_state['case_id']=case_id
            _render_dashboard(SQLiteRecoveryRepository(path))
        app=AppTest.from_function(render_legacy,args=(str(path),str(case.case_id))).run()
    plan=repo.get_active_plan(case.case_id)
    task=next(t for t in plan.proposed_tasks if t.status is TaskStatus.NOT_STARTED)
    records=repo.get_recovery_records(case.case_id)
    records.household.children=2
    repo.save_recovery_records(records,expected_version=records.version,explicitly_confirmed=True)
    events=repo.list_journey_events(case.case_id)
    history=repo.list_task_history(case.case_id)
    from recovery.task_view import current_task_views
    displayed=[v for v in current_task_views(plan) if v.applicable]
    index=next(i for i,v in enumerate(displayed) if v.task.task_id==task.task_id)
    if screen == 'guided':
        control=next(w for w in app.selectbox if w.label.startswith('Status ') and w.label.endswith(task.title))
        submit_label='Save progress'
    else:
        control=[w for w in app.selectbox if w.label=='Task status'][index]
        submit_label='Save task status'
    control.select(TaskStatus.IN_PROGRESS)
    [w for w in app.button if w.label==submit_label][index].click().run()
    assert not app.exception
    assert repo.get_active_plan(case.case_id)==plan
    assert repo.list_task_history(case.case_id)==history
    assert repo.list_journey_events(case.case_id)==events
    assert any('stale' in w.value.lower() for w in app.error)
