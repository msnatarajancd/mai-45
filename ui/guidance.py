"""Shared explicit-request grounded guidance view; no automatic generation."""
import streamlit as st
from domain.contracts import LOCATIONS
from services import generation


def show(result):
    if result.generation_status=='generated':
        st.caption('REAL MODEL GENERATION · '+result.provider if result.provider.startswith('Nebius /')
                   else result.provider)
    else:
        st.caption('NO GENERATED ANSWER · '+result.generation_status.upper())
    st.warning(result.notice)
    st.caption('Evidence status: '+result.retrieval.retrieval_status)
    citations={c.citation_id:c for c in result.retrieval.citations}
    for claim in result.claims:
        st.write(claim.text)
        c=citations[claim.citation_id]
        st.link_button('Source: '+c.publisher+' · '+c.section_heading,c.official_url)
        st.caption('Citation: '+c.citation_id)
    for text in dict.fromkeys(result.retrieval.limitations+result.retrieval.missing_information):
        st.caption(text)
    for c in result.retrieval.citations:
        with st.expander('Reviewed evidence · '+c.section_heading):
            st.text(c.passage)
            st.link_button(c.title,c.official_url)
            st.caption('Citation: '+c.citation_id+' · Source: '+c.source_id)
            st.caption('Original content SHA-256: '+c.original_content_hash)
            for text in dict.fromkeys(c.safety_caveats+c.source_limitations): st.caption(text)
    if result.claims:
        st.caption('AI explanations are not independently human-reviewed. Read the official passage and its limitations. No task state was changed.')


def render(phase,*,key=None):
    key=key or phase
    if st.session_state.get('rr_emergency') or st.session_state.get('rr_case_id') in st.session_state.get('rr_pending_danger',[]):
        return
    case_id=st.session_state.get('rr_case_id')
    if case_id:
        try:
            from uuid import UUID
            from ui.recovery_page import repository
            case=repository().get_case(UUID(case_id))
            if case is None or case.intake.immediate_danger is not False:
                st.info('Routine guidance is paused for this case. Emergency contact options remain above.')
                return
        except Exception:
            st.info('The active case assessment could not be checked. Routine guidance is paused; emergency options remain available.')
            return
    with st.expander('Ask Qwen about reviewed guidance',expanded=phase=='recover'):
        st.write('Retrieve reviewed passages first, then request a cited explanation. This is general guidance, separate from live alerts and saved tasks.')
        hazard=st.selectbox('Evidence hazard',['Select a hazard','flood','hurricane'],key=key+'_evidence_hazard')
        if phase=='assistant':
            phase=st.selectbox('Evidence phase',['protect','respond','recover'],index=2,key=key+'_evidence_phase')
        default={'protect':'Flood preparedness','respond':'Floodwater hazards','recover':'electrical hazards'}[phase]
        query=st.text_input('Question for reviewed guidance',value=default,max_chars=600,key=key+'_evidence_question')
        jurisdiction='US-FL-MIAMI-DADE' if st.session_state['location_id'] in LOCATIONS else None
        st.caption('Scope: Miami-Dade · '+phase+'. The reviewed CDC reentry material covers recovery. Other phases may have no publishable evidence.')
        st.caption('Only your question, selected scope, approved passages and public limitations go to Nebius. No household details, saved tasks or review notes are sent. Use fictional details only.')
        binding=(query,phase,hazard,jurisdiction)
        state_key=key+'_generated_guidance'
        prior=st.session_state.get(state_key)
        if prior and (prior.query,prior.phase,prior.hazard or 'Select a hazard',prior.jurisdiction)!=binding:
            st.session_state.pop(state_key,None)
        if st.button('Generate cited explanation',key=key+'_generate_guidance',type='primary'):
            if not query.strip(): st.info('Enter a general guidance question first.')
            else:
                from emergency.service import screen_report
                from emergency.workflow import begin_emergency
                from uuid import uuid4
                decision = screen_report(query, entrypoint='guidance')
                if decision and decision.interrupt_routine:
                    begin_emergency(st.session_state, decision, entrypoint='guidance', event_id=str(uuid4()))
                    st.rerun()
                with st.spinner('Retrieving reviewed evidence and checking the explanation…'):
                    result=generation.explain(query,phase,hazard=None if hazard=='Select a hazard' else hazard,jurisdiction=jurisdiction,state=st.session_state)
                st.session_state[state_key]=result
        result=st.session_state.get(state_key)
        if result:
            result=generation.revalidate(result,state=st.session_state)
            st.session_state[state_key]=result
            show(result)
