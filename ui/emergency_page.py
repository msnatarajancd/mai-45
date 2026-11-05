"""CAP-04 presentation: immediate human contact, then optional local routing.

Render the shared action strip exactly once, before optional adapters. Directory
errors, pending reviews, and persistence failures never remove that strip.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import streamlit as st

from domain.contracts import AppMode
from emergency.content import (ALTERNATIVES_NOTICE, AREA_OPTIONS, COMMUNICATION_OPTIONS,
                               DESKTOP_FALLBACK, MIAMI_DADE, NO_CONNECTION,
                               NO_DISPATCH, TYPE_LABELS)


def _open_alternatives():
    st.session_state['rr_alternative'] = True
    st.session_state['page'] = 'Respond'
    st.session_state['chat_open'] = False
    st.session_state.pop('tour_step', None)
    st.session_state.pop('tour_explanation', None)


def _report_danger(entrypoint='respond'):
    from emergency.models import SituationInput
    from emergency.service import evaluate_situation
    from emergency.workflow import begin_emergency
    decision = evaluate_situation(SituationInput(immediate_danger=True, entrypoint=entrypoint))
    begin_emergency(st.session_state, decision, entrypoint=entrypoint, event_id=str(uuid4()))


def _current_county():
    return MIAMI_DADE if st.session_state.get('rr_incident_area') == AREA_OPTIONS[1] else None


def _area_changed():
    st.session_state['rr_incident_county'] = _current_county()
    st.session_state.pop('resources', None)


def _county_selector():
    st.selectbox('Where is help needed?', AREA_OPTIONS, key='rr_incident_area', on_change=_area_changed)
    st.caption('Choose the current incident area. Your saved or monitored area does not establish where you are now.')


def render_access_controls():
    """No optional service import or I/O before the two emergency actions."""
    with st.container(key='emergency_bar'):
        cols = st.columns([1.2, 1, 1.3, 1])
        cols[0].markdown('<div class="rr-emergency-label">Need urgent help?</div>', unsafe_allow_html=True)
        cols[1].link_button('Call 911', 'tel:911', width='stretch')
        cols[2].button("I Can't Call 911", key='rr_cannot_call', width='stretch', on_click=_open_alternatives)
        entry = {'Protect': 'guardian', 'Recover': 'recovery', 'Assistant': 'assistant'}.get(
            st.session_state.get('page'), 'respond')
        cols[3].button('Immediate danger', key='rr_report_danger', width='stretch',
                       on_click=_report_danger, args=(entry,))
        st.caption(DESKTOP_FALLBACK)

    if st.session_state.get('rr_demo_active'):
        st.caption('FICTIONAL RECOVERY REPLAY · Leaving this story preserves its saved history, including any danger report.')
        if st.button('Leave fictional recovery scenario', key='rr_leave_recovery_demo'):
            from recovery.demo_session import leave_demo
            leave_demo(st.session_state)
            st.rerun()

    if st.session_state.get('rr_emergency'):
        # Compatibility with older callers/restored state. A naked legacy True
        # represented an explicit danger report; new entries carry a decision.
        if not st.session_state.get('rr_emergency_decision'):
            _report_danger(entry)
        st.session_state.pop('tour_step', None)
        st.session_state.pop('tour_explanation', None)
        render_workspace(interrupted=True)
        st.stop()


def _save_pending_danger():
    case_id = st.session_state.get('rr_case_id')
    pending = set(st.session_state.get('rr_pending_danger', []))
    if not case_id or case_id not in pending:
        return
    try:
        from ui.recovery_page import repository
        repository().report_immediate_danger(UUID(case_id))
        pending.discard(case_id)
        st.session_state['rr_pending_danger'] = sorted(pending)
    except Exception:
        st.warning('The danger report could not be saved. Emergency contact controls remain available.')


def _return_to_app():
    st.session_state['rr_emergency'] = False
    st.session_state['page'] = 'Respond'
    st.session_state.pop('rr_route_result', None)
    # Keep persisted danger/pending writes. Leaving the view is not a safety report.


def _render_alternatives():
    st.subheader("If you can't call 911")
    st.info(ALTERNATIVES_NOTICE)
    reason = st.radio('What makes calling difficult? (optional)', COMMUNICATION_OPTIONS,
                      index=None, key='rr_communication_constraint')
    if reason == 'No usable connection':
        st.warning(NO_CONNECTION)
    elif reason == 'This device cannot call':
        st.write(DESKTOP_FALLBACK)
    elif reason == 'Hearing or speech access needs':
        st.write('Read the official accessibility and text-to-911 information below. Supported options depend on your location and device.')
    if _current_county() == MIAMI_DADE:
        st.link_button('Miami-Dade Text-to-911 information', 'https://www.mdso.com/text-911', width='stretch')
        st.caption('Official county information. This link does not verify your connection, message delivery, or a response.')
    else:
        st.caption('Local texting availability has not been established for your current location. Select Miami-Dade only if it applies to this incident.')
    st.link_button('National 911 calling and texting information', 'https://www.911.gov/calling-911/frequently-asked-questions/')
    st.link_button('FCC accessibility and Text-to-911 information',
                   'https://www.fcc.gov/consumers/guides/what-you-need-know-about-text-911')


def _assess():
    from emergency.models import SituationInput
    from emergency.workflow import begin_emergency
    from services.emergency import assess_situation
    text = st.session_state.get('rr_situation_description', '')
    category = TYPE_LABELS.get(st.session_state.get('rr_situation_type'))
    st.session_state.pop('rr_demo_label', None)
    try:
        decision = assess_situation(SituationInput(text=text, category=category,
                                   incident_county=_current_county(), entrypoint='respond'))
        st.session_state['rr_route_result'] = decision.model_dump(mode='json')
        if decision.interrupt_routine:
            begin_emergency(st.session_state, decision, entrypoint='respond', event_id=str(uuid4()))
    except Exception:
        # Access is independent even if the local adapter has a deployment error.
        st.session_state['rr_assessment_error'] = True


def _category_changed():
    st.session_state.pop('rr_route_result', None)
    if st.session_state.get('rr_situation_type') in {'Trapped / cannot get out', 'Medical concern', 'Utility hazard', 'Flooding', 'Not sure'}:
        _assess()


def _render_resource_result(raw):
    from services import resources
    from domain.resources import ResourceQuery
    types = raw.get('incident_types', [])
    future = raw.get('urgency') == 'ordinary'
    event = st.selectbox('Event context (optional)', ['Not specified', 'Hurricane', 'Flood', 'Wildfire'],
                         key='rr_assistance_hazard')
    categories = raw.get('resource_categories', []) or types
    # The directory accepts one canonical need, not a concatenated search query.
    need = 'transportation' if 'transportation' in categories else (categories[0] if categories else 'unknown')
    # Topic types also include historical/negated mentions. Only an explicit
    # event selection establishes directory hazard context.
    query = ResourceQuery(needs=need,
                          county=_current_county(), phase='prepare' if future else 'respond',
                          purpose='planning' if future else 'urgent_assistance',
                          hazard=event.lower() if event != 'Not specified' else None)
    try:
        result = resources.lookup_resources(query, now=datetime.now(timezone.utc))
    except Exception:
        st.warning('The reviewed assistance directory is unavailable. Use official entry links to check information directly.')
        result = None
    if result:
        if result.status != 'matches':
            st.info('No reviewed assistance match is available for this request. Current availability is not verified.')
        for limitation in result.limitations:
            st.caption(limitation)
        for record in result.records:
            with st.container(border=True):
                st.subheader(record.official_name)
                st.write(record.description)
                st.caption(record.provider + ' · ' + record.service_area)
                for condition in record.prerequisites:
                    st.write('• ' + condition)
                if record.enrollment_timing:
                    st.write(record.enrollment_timing)
                if record.official_contact:
                    st.write('Official contact: ' + record.official_contact)
                st.caption('Current availability not verified. Reviewed: ' + record.reviewed_at.isoformat())
                for limitation in record.limitations:
                    st.caption(limitation)
                st.link_button('View official resource', record.official_url)
    if _current_county() == MIAMI_DADE:
        st.subheader('Official places to check')
        if 'evacuation_support' in types or 'transport' in query.needs.lower():
            st.write('EEAP evacuation assistance')
            if not result or result.status != 'matches':
                st.caption('Official entry links — directory review pending or no matching reviewed scope. Read registration timing and eligibility directly with the county. No pickup, enrollment, or response is guaranteed.')
            else:
                st.caption('Read current registration timing and eligibility directly with the county. No pickup, enrollment, or response is guaranteed.')
            st.link_button('Read EEAP program information',
                           'https://www.miamidade.gov/global/service.page?Mduid_service=ser1470238193996672')
            st.link_button('Check EEAP registration timing',
                           'https://www.miamidade.gov/global/faq.page?Mduid_faq=faq1598023863344518')
        st.link_button('Miami-Dade official emergency updates',
                       'https://www.miamidade.gov/global/emergency/activation/home.page')
        st.caption('Official information links do not establish current orders, shelter openings, or transport capacity.')
    else:
        st.info('Local assistance starts with Miami-Dade. Confirm the incident area above to see county entry links. No local service match is assumed.')


def _load_demo(scenario_id=None):
    from emergency.demo import load_scenario
    from emergency.workflow import begin_emergency
    from services.emergency import assess_situation
    if st.session_state.get('mode') != AppMode.DEMO:
        return
    scenario = load_scenario(scenario_id or st.session_state['rr_demo_scenario'], mode='demo')
    st.session_state['rr_demo_label'] = scenario.display_label
    st.session_state['rr_situation_description'] = scenario.input.text
    st.session_state['rr_situation_type'] = None
    st.session_state['rr_incident_area'] = AREA_OPTIONS[1] if scenario.input.incident_county == MIAMI_DADE else AREA_OPTIONS[0]
    st.session_state['rr_incident_county'] = scenario.input.incident_county
    communication = scenario.input.communication
    flags = (communication.cannot_speak_safely, communication.hearing_or_speech_access,
             communication.device_cannot_call, communication.no_usable_connection) if communication else ()
    st.session_state['rr_alternative'] = any(flags)
    st.session_state['rr_communication_constraint'] = next(
        (label for flag, label in zip(flags, COMMUNICATION_OPTIONS) if flag), None)
    decision = assess_situation(scenario.input)
    st.session_state['rr_route_result'] = decision.model_dump(mode='json')
    if decision.interrupt_routine:
        begin_emergency(st.session_state, decision, entrypoint=scenario.input.entrypoint, event_id=str(uuid4()))


def render_workspace(*, interrupted=False):
    if st.session_state.get('rr_demo_label'):
        st.caption('SIMULATED DEMO · ' + st.session_state['rr_demo_label'])
    if interrupted:
        st.error('Emergency access comes first. ReadyRelief has not contacted or dispatched anyone. Routine recovery actions are paused.')
        st.write('If you are in immediate danger, call 911. Follow instructions from emergency services and local authorities.')
        raw = st.session_state.get('rr_emergency_decision', {})
        if raw.get('message'):
            st.write(raw['message'])
        _county_selector()
        if st.session_state.get('rr_alternative'):
            _render_alternatives()
        _save_pending_danger()
        st.button('Return to app — this does not confirm safety', key='rr_leave_emergency', on_click=_return_to_app)
        st.caption('Online-only course prototype. Returning does not clear a saved danger report or confirm safety.')
        return

    from ui.components import heading
    heading('02 / Respond', 'I Need Help Now', 'Emergency contact options come first. The questions below are optional.')
    st.caption(NO_DISPATCH)
    _county_selector()
    if st.session_state.get('rr_alternative'):
        _render_alternatives()
    with st.container(border=True, key='assistance_controls'):
        st.subheader('Find the next appropriate option')
        st.radio('Situation type (optional)', list(TYPE_LABELS), index=None, key='rr_situation_type',
                 on_change=_category_changed)
        st.text_area('Describe the situation (optional)', max_chars=2500, key='rr_situation_description',
                     placeholder='For example: We may need accessible evacuation transport next week.')
        st.button('Show assistance options', type='primary', key='rr_assess', on_click=_assess)
        st.caption('You can skip these questions and use the emergency actions above at any time.')
    if st.session_state.pop('rr_assessment_error', False):
        st.warning('Situation guidance is unavailable. Emergency contact options remain above.')
    raw = st.session_state.get('rr_route_result')
    if raw:
        st.write(raw['message'])
        if raw['route'] == 'resources':
            _render_resource_result(raw)
    if st.session_state.get('mode') == AppMode.DEMO:
        with st.expander('Try a fictional scenario'):
            from emergency.demo import load_scenarios
            scenarios = load_scenarios(mode='demo')
            labels = {s.id: s.display_label for s in scenarios}
            st.caption('SIMULATED DEMO · No scenario describes a real incident. Never place a real emergency call during a demonstration.')
            st.selectbox('Fictional scenario', list(labels), format_func=labels.get, key='rr_demo_scenario')
            st.button('Load fictional scenario', key='rr_load_scenario', on_click=_load_demo)
            st.button('Simulate rising water / trapped', key='rr_simulate_danger',
                       on_click=_load_demo, args=('demo-rising-water',))
    from ui.guidance import render as grounded_guidance
    grounded_guidance('respond')
    st.button('Next · Review recovery needs', key='rr_next_recovery',
              on_click=lambda: st.session_state.update(page='Recover'))
