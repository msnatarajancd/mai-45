"""CAP-07/08/09 acceptance with fictional facts and fake Qwen transport only."""
import sqlite3
from uuid import UUID

import pytest
from recovery.database import SQLiteRecoveryRepository
from recovery.models import RecoveryCase, RecoveryIntake, RecoveryRecords, DamageRecord, TaskStatus
from recovery.demo_planner import create_demo_draft_plan
from recovery.reassessment import preview_reassessment
from test_recovery_records import dump
from test_recovery_landing import app, button
from test_recovery_qwen_integration import install, submit, confirm
from test_recovery_extraction import proposed

NEW='Our house flooded. Electricity is out, we need somewhere to stay, and our furniture is damaged.'
RETURN='We found temporary accommodation and electricity is back, but our refrigerator is damaged.'


def case_and_records(repo):
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood',housing_condition='Flooded',
        utility_availability={'electricity':False,'water':True},temporary_accommodation_status='Needed',
        immediate_danger=False,household_recovery_needs=['Temporary housing']))
    repo.create_case(case)
    records=repo.get_recovery_records(case.case_id)
    records.damage_records=[DamageRecord(case_id=case.case_id,item_description='Furniture',damage_description='Fictional flood damage')]
    return case,repo.save_recovery_records(records,expected_version=0,explicitly_confirmed=True)


def test_personalized_plan_priorities_dependencies_and_no_approval_writes(tmp_path):
    repo=SQLiteRecoveryRepository(tmp_path/'cap.sqlite3');case,records=case_and_records(repo)
    before=dump(tmp_path/'cap.sqlite3')
    plan=create_demo_draft_plan(case,records)
    assert 4 <= len(plan.proposed_tasks) <= 7
    assert dump(tmp_path/'cap.sqlite3')==before
    assert repo.get_active_plan(case.case_id) is None
    assert {t.planning_key for t in plan.proposed_tasks} >= {'housing','utilities','damage','insurance'}
    assert any('Furniture' in t.description for t in plan.proposed_tasks)
    assert all(t.reason_for_recommendation for t in plan.proposed_tasks)
    assert any(t.dependencies for t in plan.proposed_tasks)
    assert any(t.resource_categories == ['Housing'] for t in plan.proposed_tasks)
    with pytest.raises(ValueError,match='explicit'):
        repo.approve_plan(plan.plan_id,new_draft=plan)
    assert dump(tmp_path/'cap.sqlite3')==before
    repo.approve_plan(plan.plan_id,new_draft=plan,explicitly_approved=True)
    assert repo.get_active_plan(case.case_id).plan_id == plan.plan_id


def test_stale_initial_plan_rejected_atomically(tmp_path):
    path=tmp_path/'cap.sqlite3';repo=SQLiteRecoveryRepository(path);case,records=case_and_records(repo)
    plan=create_demo_draft_plan(case,records)
    repo.save_recovery_records(records,expected_version=records.version,explicitly_confirmed=True)
    before=dump(path)
    with pytest.raises(ValueError,match='stale draft'):
        repo.approve_plan(plan.plan_id,new_draft=plan,explicitly_approved=True)
    assert dump(path)==before and repo.get_plan(plan.plan_id) is None


def test_status_event_and_plan_write_roll_back_together(tmp_path):
    path=tmp_path/'cap.sqlite3';repo=SQLiteRecoveryRepository(path);case,records=case_and_records(repo)
    plan=create_demo_draft_plan(case,records);repo.approve_plan(plan.plan_id,new_draft=plan,explicitly_approved=True)
    with sqlite3.connect(path) as c:
        c.execute("CREATE TRIGGER fail_progress BEFORE UPDATE ON recovery_plans BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    before=dump(path)
    with pytest.raises(sqlite3.IntegrityError):
        repo.update_task_status(plan.plan_id,plan.proposed_tasks[0].task_id,TaskStatus.IN_PROGRESS,expected_progress_version=0)
    assert dump(path)==before
    assert repo.list_task_history(case.case_id)==[]


def test_review_metadata_cannot_be_forged(tmp_path):
    path=tmp_path/'cap.sqlite3';repo=SQLiteRecoveryRepository(path);case,records=case_and_records(repo)
    draft=create_demo_draft_plan(case,records);plan=repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
    updated=case.intake.model_copy(deep=True);updated.utility_availability['electricity']=True
    preview=preview_reassessment(case,plan,updated,previous_records=records,updated_records=records)
    key=next(str(t.task_id) for t in plan.proposed_tasks if t.planning_key=='utilities')
    assert not preview.proposed_revision.task_reviews[key].applicable
    preview.proposed_revision.task_reviews[key].applicable=True
    before=dump(path)
    with pytest.raises(ValueError,match='evidence differs'):
        repo.approve_reassessment(preview,explicitly_approved=True)
    assert dump(path)==before


def test_full_personalized_plan_progress_and_confirmed_reassessment(app,monkeypatch):
    path=__import__('os').environ['READYRELIEF_DB_PATH'];repo=SQLiteRecoveryRepository(path)
    install(monkeypatch,{'fields':{
        'disaster_type':proposed('Flood','Our house flooded'),
        'housing_condition':proposed('Flooded','Our house flooded'),
        'electricity':proposed('Unavailable','Electricity is out'),
        'temporary_accommodation':proposed('Needed','we need somewhere to stay'),
        'household_recovery_needs':proposed(['Temporary housing'],'we need somewhere to stay')},
        'new_damage':[proposed('furniture','our furniture is damaged')]})
    before=dump(path);submit(app,NEW);assert dump(path)==before
    confirm(app);case_id=UUID(app.session_state['rr_case_id'])
    assert repo.get_active_plan(case_id) is None
    with sqlite3.connect(path) as c:assert c.execute('SELECT COUNT(*) FROM recovery_plans').fetchone()[0]==0
    assert any(w.label.startswith('Official pathway:') for w in app.get('link_button'))
    next(w for w in app.checkbox if w.label=='I reviewed these tasks and want to accept this plan').check()
    button(app,'Approve my recovery plan').click().run();assert not app.exception
    plan=repo.get_active_plan(case_id)
    targets={'damage':TaskStatus.COMPLETED,'insurance':TaskStatus.IN_PROGRESS,'housing':TaskStatus.BLOCKED}
    for key,status in targets.items():
        task=next(t for t in plan.proposed_tasks if t.planning_key==key)
        next(w for w in app.selectbox if w.label.startswith('Status ') and w.label.endswith(task.title)).select(status)
        # Each status form contains its own submit button, in task order.
        task_index=next(i for i,t in enumerate(plan.proposed_tasks) if t.task_id==task.task_id)
        [w for w in app.button if w.label=='Save progress'][task_index].click().run()
        assert not app.exception
    old_plan=repo.get_active_plan(case_id);history=repo.list_task_history(case_id)
    assert len(history)==3
    reopened=SQLiteRecoveryRepository(path)
    assert reopened.get_active_plan(case_id)==old_plan
    assert {t.status for t in old_plan.proposed_tasks} >= set(targets.values())
    app.session_state['page']='Home';app.run();app.session_state['page']='Recover';app.run()
    assert any('furniture' in w.value.lower() for w in app.markdown)
    install(monkeypatch,{'fields':{
        'temporary_accommodation':proposed('Temporary lodging','We found temporary accommodation'),
        'electricity':proposed('Available','electricity is back')},
        'new_damage':[proposed('refrigerator','our refrigerator is damaged')]})
    before=dump(path);submit(app,RETURN);assert dump(path)==before
    button(app,'Review selected changes').click().run()
    assert any('No longer current after approval:' in w.value for w in app.text)
    assert dump(path)==before
    next(w for w in app.selectbox if w.label=='Safety assessment for selected changes').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label=='I confirm the selected changes shown above').check()
    if any(w.label == 'I approve the proposed plan revision' for w in app.checkbox):
        next(w for w in app.checkbox if w.label == 'I approve the proposed plan revision').check()
    button(app,'Confirm Details & Continue').click().run();assert not app.exception
    current=repo.get_active_plan(case_id);records=repo.get_recovery_records(case_id)
    assert [t.status for t in current.proposed_tasks[:len(old_plan.proposed_tasks)]]==[t.status for t in old_plan.proposed_tasks]
    assert old_plan in repo.list_approved_plans(case_id)
    assert repo.list_task_history(case_id)==history
    assert {d.item_description for d in records.damage_records}=={'furniture','refrigerator'}
    assert 'Temporary housing' not in repo.get_case(case_id).intake.household_recovery_needs
    for task in old_plan.proposed_tasks:
        if task.planning_key in {'housing','utilities'}:
            assert not current.task_reviews[str(task.task_id)].applicable
    assert any('refrigerator' in t.title for t in current.proposed_tasks[len(old_plan.proposed_tasks):])
    assert any(w.label.startswith('No longer applicable:') for w in app.expander)
    assert next(w for w in app.metric if w.label=='Needs attention').value=='0'
    button(app,'Prepare for insurance').click().run()
    assert any('furniture' in w.value.lower() and 'refrigerator' in w.value.lower() for w in app.text)
    assert SQLiteRecoveryRepository(path).get_active_plan(case_id)==current
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]


def test_resolved_applicability_survives_later_updates_without_reset(tmp_path):
    path=tmp_path/'cap.sqlite3';repo=SQLiteRecoveryRepository(path);case,records=case_and_records(repo)
    draft=create_demo_draft_plan(case,records);plan=repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
    housing=next(t for t in plan.proposed_tasks if t.planning_key=='housing')
    repo.update_task_status(plan.plan_id,housing.task_id,TaskStatus.BLOCKED,expected_progress_version=0)
    plan=repo.get_active_plan(case.case_id)
    updated=case.intake.model_copy(deep=True);updated.temporary_accommodation_status='Temporary lodging';updated.utility_availability['electricity']=True
    preview=preview_reassessment(case,plan,updated,previous_records=records,updated_records=records)
    accepted=repo.approve_reassessment(preview,explicitly_approved=True)
    assert accepted.proposed_tasks[0].status==TaskStatus.BLOCKED
    before=dump(path)
    with pytest.raises(ValueError,match='no longer applicable'):
        repo.update_task_status(accepted.plan_id,housing.task_id,TaskStatus.COMPLETED)
    assert dump(path)==before
    next_case=repo.get_case(case.case_id)
    again=preview_reassessment(next_case,accepted,next_case.intake,previous_records=records,updated_records=records)
    assert not again.new_tasks
    assert not again.proposed_revision.task_reviews[str(housing.task_id)].applicable
    assert repo.list_task_history(case.case_id)[0]['new_status']=='BLOCKED'


def test_old_json_defaults_are_additive_and_completed_tasks_remain_completed():
    from recovery.models import RecoveryTask,RecoveryPlan,TaskPriority
    old=RecoveryTask(title='Legacy task',description='Existing reported action',priority=TaskPriority.MEDIUM,
        reason_for_recommendation='Existing report',status=TaskStatus.COMPLETED)
    raw=old.model_dump(exclude={'planning_key','dependencies','resource_categories'})
    restored=RecoveryTask.model_validate(raw)
    assert restored.status==TaskStatus.COMPLETED and restored.dependencies==[]
    plan=RecoveryPlan(case_id=__import__('uuid').uuid4(),proposed_tasks=[restored])
    legacy=plan.model_dump(exclude={'planning_basis','records_version','task_reviews','confirmed_damage_ids'})
    assert RecoveryPlan.model_validate(legacy).task_reviews=={}


def test_initial_approval_transaction_rolls_back_on_failure(tmp_path):
    path=tmp_path/'cap.sqlite3';repo=SQLiteRecoveryRepository(path);case,records=case_and_records(repo)
    draft=create_demo_draft_plan(case,records)
    with sqlite3.connect(path) as c:
        c.execute("CREATE TRIGGER fail_approval BEFORE UPDATE OF active_plan_id ON recovery_cases BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    before=dump(path)
    with pytest.raises(sqlite3.IntegrityError):
        repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
    assert dump(path)==before and repo.get_plan(draft.plan_id) is None


def test_recurring_gap_gets_a_new_followup_without_reopening_completed_work(tmp_path):
    path=tmp_path/'cap.sqlite3';repo=SQLiteRecoveryRepository(path);case,records=case_and_records(repo)
    draft=create_demo_draft_plan(case,records);plan=repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
    utility=next(t for t in plan.proposed_tasks if t.planning_key=='utilities')
    repo.update_task_status(plan.plan_id,utility.task_id,TaskStatus.COMPLETED)
    def revise(available):
        c=repo.get_case(case.case_id);p=repo.get_active_plan(case.case_id)
        i=c.intake.model_copy(deep=True);i.utility_availability['electricity']=available
        return repo.approve_reassessment(preview_reassessment(c,p,i),explicitly_approved=True)
    revise(True);plan=revise(False)
    gap=next(t for t in plan.proposed_tasks if t.title=='Review electricity availability gap')
    repo.update_task_status(plan.plan_id,gap.task_id,TaskStatus.COMPLETED)
    revise(True);plan=revise(False)
    followup=next(t for t in plan.proposed_tasks if t.title=='Review electricity availability gap (new report 2)')
    assert followup.status==TaskStatus.NOT_STARTED and followup.task_id != gap.task_id
    assert next(t for t in plan.proposed_tasks if t.task_id==gap.task_id).status==TaskStatus.COMPLETED
    assert next(t for t in plan.proposed_tasks if t.task_id==utility.task_id).status==TaskStatus.COMPLETED


def test_task_cards_render_official_pathways_rationale_and_dependencies(tmp_path):
    from streamlit.testing.v1 import AppTest
    from services.assistance_pathways import PATHWAYS
    repo=SQLiteRecoveryRepository(tmp_path/'cards.sqlite3');case,records=case_and_records(repo)
    plan=create_demo_draft_plan(case,records)
    def cards(raw):
        from ui.assistant_page import show_draft
        show_draft(raw)
    view=AppTest.from_function(cards,args=(plan.model_dump_json(),)).run()
    assert not view.exception
    links={w.url for w in view.get('link_button')}
    assert {r.url for r in PATHWAYS if r.category in {'Housing','Electricity','Disaster assistance'} and r.geography!='Miami-Dade'} <= links
    captions=' '.join(w.value for w in view.caption)
    assert 'Why this step:' in captions and 'Before this step:' in captions
    assert 'not M3-reviewed' in captions and 'USAGov' in captions
    assert 'No open shelter' in captions and 'determines no eligibility' in captions
    assert all(t.source_reference is None for t in plan.proposed_tasks)


def test_secondary_plan_views_respect_historical_applicability(tmp_path):
    from streamlit.testing.v1 import AppTest
    repo=SQLiteRecoveryRepository(tmp_path/'views.sqlite3');case,records=case_and_records(repo)
    draft=create_demo_draft_plan(case,records);plan=repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
    updated=case.intake.model_copy(deep=True)
    updated.temporary_accommodation_status='Temporary lodging';updated.utility_availability['electricity']=True
    accepted=repo.approve_reassessment(preview_reassessment(case,plan,updated,previous_records=records,updated_records=records),explicitly_approved=True)
    def assistant_view(raw):
        from ui.assistant_page import show_draft
        show_draft(raw)
    view=AppTest.from_function(assistant_view,args=(accepted.model_dump_json(),)).run()
    assert not view.exception
    assert sum('Historical / no longer applicable:' in w.value for w in view.caption)==2
    def dashboard(path,case_id):
        import streamlit as st
        from recovery.database import SQLiteRecoveryRepository
        from recovery.ui import _render_dashboard
        st.session_state['case_id']=case_id
        _render_dashboard(SQLiteRecoveryRepository(path))
    view=AppTest.from_function(dashboard,args=(str(tmp_path/'views.sqlite3'),str(case.case_id))).run()
    assert not view.exception
    assert sum(w.label.startswith('No longer applicable:') for w in view.expander)==2
    assert len([w for w in view.selectbox if w.label=='Task status'])==len(accepted.proposed_tasks)-2
    assert not any('Planner: AI-assisted' in w.value for w in view.caption)


def test_legacy_saved_case_reopens_without_rewriting_progress(app):
    import json,os
    path=os.environ['READYRELIEF_DB_PATH'];repo=SQLiteRecoveryRepository(path)
    case,records=case_and_records(repo)
    draft=create_demo_draft_plan(case,records);plan=repo.approve_plan(draft.plan_id,new_draft=draft,explicitly_approved=True)
    repo.update_task_status(plan.plan_id,plan.proposed_tasks[0].task_id,TaskStatus.COMPLETED,expected_progress_version=0)
    # Synthetic pre-CAP JSON: additive fields absent, IDs and accepted statuses intact.
    with sqlite3.connect(path) as connection:
        raw=json.loads(connection.execute('SELECT plan_json FROM recovery_plans WHERE plan_id=?',(str(plan.plan_id),)).fetchone()[0])
        for name in ('planning_basis','records_version','task_reviews','confirmed_damage_ids'):raw.pop(name,None)
        for task in raw['proposed_tasks']:
            for name in ('planning_key','dependencies','resource_categories'):task.pop(name,None)
        connection.execute('UPDATE recovery_plans SET plan_json=? WHERE plan_id=?',(json.dumps(raw),str(plan.plan_id)))
    before=dump(path)
    app.session_state['rr_case_id']=str(case.case_id);app.session_state['rr_focus']='Continue my recovery';app.run()
    assert not app.exception
    assert repo.get_active_plan(case.case_id).proposed_tasks[0].status==TaskStatus.COMPLETED
    assert dump(path)==before
    assert any(w.value=='1' for w in app.metric if w.label=='Steps completed')
