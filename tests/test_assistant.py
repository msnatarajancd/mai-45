import json
import pytest
from services.assistant import Action, Reply, propose, execute, capture, is_danger
from ui.capabilities import search_pages
from domain.contracts import Household, AppMode


def state():
    return dict(page='Home', household=Household(), location_id='miami', mode=AppMode.DEMO, rr_emergency=False)


class Client:
    def __init__(self, output): self.output=output; self.calls=0
    def complete(self, messages): self.calls+=1; return json.dumps(self.output)


def test_search_synonyms():
    assert 'Recover' in search_pages('tasks')
    assert 'Household' in search_pages('mobility')
    assert search_pages('zzzzzz') == []
    assert 'Assistant' in search_pages('chat')


def test_unknown_action_rejected():
    with pytest.raises(ValueError):
        Reply.model_validate({'answer':'ok', 'action':{'kind':'run_sql','sql':'DELETE'}})


def test_progress_navigation_schema_local_proposal_and_disabled_fallback(monkeypatch):
    from services.assistant import local_proposal
    monkeypatch.setenv('READYRELIEF_PROGRESS_PREVIEW', '1')
    s = state()
    reply = Reply.model_validate({'answer': 'Open progress.', 'action': {'kind': 'navigate', 'page': 'Recovery Progress'}})
    assert reply.action.page == 'Recovery Progress'
    proposal = local_proposal('open recovery progress', s, None)
    assert proposal.action.page == 'Recovery Progress'
    execute(proposal, s, None, confirmed=True)
    assert s['page'] == 'Recovery Progress'
    s = state()
    proposal = local_proposal('open recovery progress', s, None)
    monkeypatch.setenv('READYRELIEF_PROGRESS_PREVIEW', 'off')
    execute(proposal, s, None, confirmed=True)
    assert s['page'] == 'Recover'


@pytest.mark.parametrize('destination,focus', [('Insurance & Documents', 'Prepare for insurance'), ('My Recovery Plan', 'Continue my recovery')])
def test_local_proposal_retains_explicit_recovery_focus(destination, focus):
    from services.assistant import local_proposal
    s = state()
    s['rr_focus'] = 'Document damage'
    proposal = local_proposal('open ' + destination, s, None)
    assert proposal.action.page == 'Recover'
    assert proposal.action.focus == focus
    execute(proposal, s, None, confirmed=True)
    assert s['page'] == 'Recover'
    assert s['rr_focus'] == focus


def test_proposal_does_not_mutate_state():
    s=state(); client=Client({'answer':'Open recovery.', 'action':{'kind':'navigate','page':'Recover'}})
    p=propose('open recovery',s,None,client)
    assert s['page']=='Home'
    execute(p,s,None,confirmed=True)
    assert s['page']=='Recover'
    with pytest.raises(ValueError): execute(p,s,None,confirmed=True)


def test_action_requires_confirmation():
    s=state(); p=propose('open recovery',s,None,Client({'answer':'Ready.', 'action':{'kind':'navigate','page':'Recover'}}))
    with pytest.raises(ValueError): execute(p,s,None,confirmed=False)
    assert s['page']=='Home'


@pytest.mark.parametrize('text',['we are trapped','water is rising','cannot breathe','I smell gas','there is a fire'])
def test_danger_bypasses_provider(text):
    s=state(); c=Client({})
    reply=propose(text,s,None,c)
    assert c.calls==0 and s['rr_emergency']
    assert reply.action is None


@pytest.mark.parametrize('text,expected', [
    ("I'm in danger", True), ('We are in danger', True),
    ('We are in immediate danger', True), ("I’m in danger", True),
    ("We're in danger", True), ('I am in danger', True),
    ("I'm not in danger", False), ("I'm not in immediate danger", False),
    ("What should I do if I'm in danger?", False),
    ("What should I do if I'm in immediate danger?", False),
    ("What should I do? I'm in danger.", True),
    ("If I'm in danger, I will call. We are in danger now.", True),
])
def test_explicit_current_danger_reports(text, expected):
    assert is_danger(text) is expected


def test_context_changes_invalidate_pending_action():
    s=state(); p=propose('change area',s,None,Client({'answer':'Ready', 'action':{'kind':'set_context','location_id':'homestead','mode':'SIMULATED DEMO'}}))
    s['location_id']='miami-beach'
    with pytest.raises(ValueError,match='changed'): execute(p,s,None,confirmed=True)


def test_bad_json_does_not_change_state():
    class Bad:
        def complete(self,messages): return 'not json'
    s=state()
    with pytest.raises(ValueError): propose('hello',s,None,Bad())
    assert s['page']=='Home'


def saved_plan(tmp_path):
    from recovery.database import SQLiteRecoveryRepository
    from recovery.assessment import start_recovery_case
    from recovery.demo_planner import create_demo_draft_plan
    from recovery.models import RecoveryIntake
    repo=SQLiteRecoveryRepository(tmp_path/'cases.sqlite3')
    case=start_recovery_case(RecoveryIntake(disaster_type='Flood',housing_condition='Minor damage',utility_availability={'water':None,'electricity':None},temporary_accommodation_status='Staying with others',immediate_danger=False,household_recovery_needs=['Temporary housing']),repo)
    draft=create_demo_draft_plan(case)
    repo.save_draft_plan(draft); repo.approve_plan(draft.plan_id)
    s=state(); s['rr_case_id']=str(case.case_id)
    return s,repo,case,draft


def test_task_update_requires_current_plan_and_preserves_other_tasks(tmp_path):
    s,r,c,plan=saved_plan(tmp_path)
    p=propose('mark housing completed',s,r,Client({'answer':'Review update','action':{'kind':'update_task','task_id':str(plan.proposed_tasks[0].task_id),'status':'COMPLETED'}}))
    assert r.get_active_plan(c.case_id).proposed_tasks[0].status.value=='NOT_STARTED'
    execute(p,s,r,confirmed=True)
    result=r.get_active_plan(c.case_id)
    assert result.proposed_tasks[0].status.value=='COMPLETED'
    assert result.proposed_tasks[1:]==plan.proposed_tasks[1:]


def test_changed_progress_blocks_chat_proposal(tmp_path):
    from recovery.models import TaskStatus
    s,r,c,plan=saved_plan(tmp_path)
    p=propose('mark housing completed',s,r,Client({'answer':'Review update','action':{'kind':'update_task','task_id':str(plan.proposed_tasks[0].task_id),'status':'COMPLETED'}}))
    r.update_task_status(plan.plan_id,plan.proposed_tasks[0].task_id,TaskStatus.BLOCKED,expected_progress_version=0)
    with pytest.raises(ValueError,match='changed'): execute(p,s,r,confirmed=True)
    assert r.get_active_plan(c.case_id).proposed_tasks[0].status==TaskStatus.BLOCKED


def test_pending_danger_blocks_chat_writes(tmp_path):
    s,r,c,plan=saved_plan(tmp_path); s['rr_pending_danger']=[str(c.case_id)]
    p=propose('mark housing completed',s,r,Client({'answer':'Review update','action':{'kind':'update_task','task_id':str(plan.proposed_tasks[0].task_id),'status':'COMPLETED'}}))
    with pytest.raises(ValueError,match='danger'): execute(p,s,r,confirmed=True)


def test_draft_requires_human_danger_confirmation(tmp_path):
    from recovery.database import SQLiteRecoveryRepository
    s=state(); r=SQLiteRecoveryRepository(tmp_path/'new.sqlite3')
    p=propose('create plan',s,r,Client({'answer':'Review','action':{'kind':'draft_plan','intake':{'disaster_type':'Flood','housing_condition':'Minor damage','utility_availability':{'water':None},'temporary_accommodation_status':'Staying with others','household_recovery_needs':['Temporary housing']}}}))
    with pytest.raises(ValueError,match='confirm'): execute(p,s,r,confirmed=True)
    assert 'rr_case_id' not in s
    execute(p,s,r,confirmed=True,danger_confirmed=True)
    from uuid import UUID
    assert r.get_active_plan(UUID(s['rr_case_id'])) is None
    assert 'rr_draft' in s
    approved=propose('approve',s,r,Client({'answer':'Review','action':{'kind':'approve_plan'}}))
    execute(approved,s,r,confirmed=True)
    assert r.get_active_plan(UUID(s['rr_case_id'])) is not None


def test_profile_updates_only_requested_fields():
    s=state()
    p=propose('4 people',s,None,Client({'answer':'Review','action':{'kind':'update_household','members':4}}))
    execute(p,s,None,confirmed=True)
    assert s['household'].members==4 and s['household'].has_vehicle


def test_how_to_question_cannot_propose_a_write():
    s=state()
    result=propose('How do I change my household?',s,None,Client({'answer':'Use Household.','action':{'kind':'update_household','members':9}}))
    assert result.action is None


def test_help_about_danger_button_is_not_a_danger_report():
    assert not is_danger('How does the immediate danger button work?')
    assert not is_danger('No immediate danger is reported')
    assert is_danger("I'm in immediate danger")


def test_concurrent_update_between_snapshot_check_and_write_is_rejected(tmp_path):
    from recovery.models import TaskStatus
    s,r,c,plan=saved_plan(tmp_path)
    p=propose('mark housing in progress',s,r,Client({'answer':'Review','action':{'kind':'update_task','task_id':str(plan.proposed_tasks[0].task_id),'status':'IN_PROGRESS'}}))
    class RacingRepository:
        calls=0
        def __getattr__(self,name): return getattr(r,name)
        def get_active_plan(self,case_id):
            result=r.get_active_plan(case_id)
            self.calls+=1
            if self.calls==1:
                r.update_task_status(plan.plan_id,plan.proposed_tasks[0].task_id,TaskStatus.COMPLETED,expected_progress_version=0)
            return result
    with pytest.raises(ValueError,match='stale'):
        execute(p,s,RacingRepository(),confirmed=True)
    assert r.get_active_plan(c.case_id).proposed_tasks[0].status==TaskStatus.COMPLETED


def test_chat_started_tour_gets_fresh_muted_narration_session():
    from services.assistant import local_proposal
    s=state(); s['tour_run']='previously-spoken'; s['tour_explanation']=(0,'old help')
    proposal=local_proposal('start tour',s,None)
    execute(proposal,s,None,confirmed=True)
    assert s['tour_run']!='previously-spoken'
    assert s['tour_step']==0 and s['page']=='Home'
    assert 'tour_explanation' not in s
