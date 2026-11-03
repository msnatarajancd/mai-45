"""Conversational UI with separately reviewed, app-validated operations."""
import os
import streamlit as st
from services.assistant import Proposal,propose,local_proposal,execute,capture
from recovery.models import RecoveryPlan
from ui.components import heading


def get_repo():
    from ui.recovery_page import repository
    try: return repository()
    except Exception: return None


def append_message(role,text,provider=''):
    messages=st.session_state.get('assistant_messages',[])
    st.session_state['assistant_messages']=(messages+[dict(role=role,content=text,provider=provider)])[-30:]


def preview_action(proposal):
    a=proposal.action
    st.caption('PROPOSED ACTION · NOT EXECUTED')
    names={'navigate':'Open a screen','start_tour':'Start the product walkthrough','start_demo':'Load the fictional demo household','set_context':'Change area and alert mode','update_household':'Update household preferences','check_alerts':'Check alerts in the selected mode','show_plan':'Read your saved plan','resume_case':'Open a saved fictional case','draft_plan':'Create a fictional case and unapproved draft','reassess':'Prepare a revision for review','approve_plan':'Approve the displayed draft','update_task':'Save task progress'}
    st.subheader(names[a.kind])
    if a.kind=='navigate': st.write('Destination: **'+a.page+'**')
    elif a.kind=='set_context': st.write(f'Area: **{a.location_id}** · Mode: **{a.mode.value}**')
    elif a.kind=='update_household':
        labels={'members':'People','mobility_support':'Mobility support','has_vehicle':'Vehicle available','pets':'Pets'}
        for name,value in a.model_dump(exclude_none=True,exclude={'kind'}).items(): st.write(f'**{labels[name]}:** {value}')
        st.caption('Session preferences only; accepted recovery cases are unchanged.')
    elif a.kind=='update_task':
        import json
        old=json.loads(proposal.snapshot)
        tasks=(old.get('plan') or {}).get('proposed_tasks',[])
        target=next((t for t in tasks if t['task_id']==str(a.task_id)),None)
        st.write('Task: **'+(target['title'] if target else 'Not found in current plan')+'**')
        if target: st.write(f'From {target["status"]} to **{a.status.value}**')
    elif a.kind=='resume_case': st.code(str(a.case_id),language=None)
    elif a.kind in {'draft_plan','reassess'}:
        for name,value in a.intake.model_dump().items(): st.write('**'+name.replace('_',' ').capitalize()+':**',value)
        st.caption('This prepares a deterministic organization plan, not source-grounded emergency guidance. Reassessment does not approve a revision.')
    elif a.kind=='start_demo': st.caption('Changes session preferences and alert mode to the fictional Rivera scenario. Existing recovery cases are kept.')
    elif a.kind=='check_alerts': st.caption('The simulated mode uses a labeled fixture. Live mode requests official county-wide NWS alerts; failures remain unavailable and no alerts is not proof of safety.')


def show_draft(draft_json):
    plan=RecoveryPlan.model_validate_json(draft_json)
    for i,t in enumerate(plan.proposed_tasks,1):
        st.write(f'**{i}. {t.title}** · {t.priority.value}')
        st.write(t.description)
        st.caption('Why: '+t.reason_for_recommendation)
        st.caption('Source: '+(t.source_reference or 'No verified official source attached'))
    if plan.planning_disclosure: st.warning(plan.planning_disclosure)


def pending_action(repo):
    raw=st.session_state.get('assistant_pending')
    if not raw: return
    proposal=Proposal.model_validate_json(raw)
    with st.container(border=True,key='assistant_action'):
        preview_action(proposal)
        danger_confirmed=False
        reviewed=True
        if proposal.action.kind in {'draft_plan','reassess'}:
            danger_confirmed=st.checkbox('I confirm no immediate danger is reported in this fictional scenario',key='danger_confirm_'+proposal.proposal_id)
        if proposal.action.kind=='approve_plan':
            draft=st.session_state.get('rr_draft')
            if draft: show_draft(draft)
            reviewed=st.checkbox('I reviewed every displayed task and approve saving this plan',key='plan_confirm_'+proposal.proposal_id)
        cols=st.columns(2)
        if cols[0].button('Confirm action',type='primary',width='stretch'):
            try:
                if not reviewed: raise ValueError('Review the displayed draft and check the approval box first.')
                result=execute(proposal,st.session_state,repo,confirmed=True,danger_confirmed=danger_confirmed)
                append_message('assistant',result,'Application result · not AI')
                st.session_state.pop('assistant_pending',None)
                st.session_state['assistant_result_notice']=result
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error('The action could not be completed. No successful save is claimed. Check the current case before retrying.')
        if cols[1].button('Cancel action',width='stretch'):
            st.session_state.pop('assistant_pending',None)
            append_message('assistant','Proposed action cancelled.','Application result · not AI')
            st.rerun()


def render(compact=False):
    if not compact: heading('Your conversational copilot','A little guidance. A simpler way to act.','Ask how something works, or tell ReadyRelief what you want to do. Review proposed changes before they happen.')
    repo=get_repo()
    with st.expander('Assistant settings', expanded=False):
        modes=['Nebius AI','Local guide · no AI']
        preferred=st.session_state.get('assistant_mode_preference', 'Nebius AI' if os.getenv('NEBIUS_API_KEY') else 'Local guide · no AI')
        mode=st.radio('Assistant mode',modes,index=modes.index(preferred),horizontal=True,key='assistant_mode')
        st.session_state['assistant_mode_preference']=mode
        st.caption('Nebius AI sends your message, recent chat and current fictional household/recovery context to Nebius. Use fictional data only. Chat history lasts for this browser session; no automatic AI calls.')
        if mode=='Nebius AI' and not os.getenv('NEBIUS_API_KEY'):
            st.info('Configure NEBIUS_API_KEY in the server environment to enable AI. Local guide and walkthrough remain available.')
        if not compact:
            cols=st.columns(3)
            examples=['Show me around','How do I save my progress?','Show my plan']
            for col,text in zip(cols,examples):
                if col.button(text,key='example_'+text,width='stretch'):
                    st.session_state['assistant_queued']=text
        if st.button('Clear conversation'):
            st.session_state.pop('assistant_messages',None)
            st.session_state.pop('assistant_pending',None)
            st.session_state.pop('assistant_queued',None)
            st.rerun()
    if repo is None: st.warning('Recovery storage is unavailable. Product help and navigation remain available.')
    with st.container(height=300 if compact else 430, key='chat_transcript'):
        if not st.session_state.get('assistant_messages'):
            st.write('Hello! Ask me how to use ReadyRelief, or tell me what you would like to do.')
            st.caption('For example: “Show my plan” or “We have 4 people and no vehicle”. Changes need your confirmation.')
        for message in st.session_state.get('assistant_messages',[]):
            with st.chat_message(message['role']):
                if message['provider']: st.caption(message['provider'])
                st.write(message['content'])
        pending_action(repo)
        if st.session_state.get('rr_draft'):
            with st.expander('Current unapproved draft · review the tasks'):
                show_draft(st.session_state['rr_draft'])
            st.caption('Ask “approve this draft” to prepare an approval card, or open Recover to review it there.')
    prompt=st.chat_input('Ask for help or an action… e.g. “We have 4 people and no vehicle”',max_chars=2500,key='shared_chat_input')
    prompt=prompt or st.session_state.pop('assistant_queued',None)
    if prompt:
        st.session_state.pop('assistant_pending',None)
        history=[dict(role=m['role'],content=m['content']) for m in st.session_state.get('assistant_messages',[])][-6:]
        append_message('user',prompt)
        try:
            with st.spinner('Understanding your request…'):
                proposal=(propose(prompt,st.session_state,repo,history=history) if mode=='Nebius AI' else local_proposal(prompt,st.session_state,repo))
            append_message('assistant',proposal.answer,proposal.provider)
            if proposal.action: st.session_state['assistant_pending']=proposal.model_dump_json()
        except Exception:
            append_message('assistant','The assistant is unavailable or returned an invalid response. No action was taken. Try again, use the local guide, or use the regular screens.','Application notice · not AI')
        st.rerun()
