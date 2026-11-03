from html import escape
import streamlit as st
from domain.contracts import AppMode, Household, LOCATIONS
from services import nws_alerts, knowledge, emergency, resources
from ui.components import ROOT, go, navigate, heading, icon
from ui.state import change_context, load_demo
from ui.capabilities import PAGES, search_pages


def sidebar():
    with st.sidebar:
        from ui.navigation_component import render_toggle
        render_toggle('sidebar_toggle')
        st.markdown('<div class="rr-brand"><span class="rr-brand-mark">'+icon('shield')+'</span><div>ReadyRelief<small>A clearer next step.</small></div></div>',unsafe_allow_html=True)
        st.caption('WORKSPACE')
        matches=PAGES  # Search suggestions must never remove primary navigation.
        for name in matches:
            if name=='Household': st.caption('YOUR TOOLS')
            st.button(name,icon=':material/'+PAGES[name][0]+':',key='nav_'+name,
                type='primary' if st.session_state['page']==name else 'secondary',width='stretch',on_click=navigate,args=(name,))
        with st.container(key='sidebar_guide'):
            st.markdown('<div class="rr-sidebar-kicker">A little help getting started</div>',unsafe_allow_html=True)
            from ui.tour import start_tour
            st.button('Show me around',icon=':material/explore:',width='stretch',on_click=start_tour)
        with st.container(key='sidebar_demo'):
            st.markdown('<div class="rr-sidebar-kicker">TRY THE DEMONSTRATION</div><p class="rr-sidebar-copy">Meet the Rivera household.<br>One journey, from ready to recovery.</p>',unsafe_allow_html=True)
            st.button('Start guided demo',icon=':material/play_circle:',width='stretch',on_click=load_demo,args=(st.session_state,))
            if st.session_state.get('demo_started'):
                st.caption('FICTIONAL HOUSEHOLD · 3 PEOPLE')
                for label,page in [('1 · Prepare together','Protect'),('2 · Find immediate help','Respond'),('3 · Build a recovery plan','Recover')]:
                    st.button(label,key='demo_'+page,width='stretch',on_click=navigate,args=(page,))
        st.caption('DEMO DAY 2026 · TEAM MAI-45')


def home():
    with st.container(key='home_hero'):
        left,right=st.columns([1.25,1],gap='large',vertical_alignment='center')
        with left:
            st.markdown('<div class="rr-hero"><div class="rr-eyebrow">PREPARE WITH CONFIDENCE</div><h1>A little more ready.<br><em>A lot less alone.</em></h1><p>From preparing your household to finding your next step after a storm. Clear information. Help you can understand. Progress you control.</p></div>',unsafe_allow_html=True)
            a,b=st.columns(2)
            a.button('Explore your next step',icon=':material/arrow_forward:',type='primary',width='stretch',on_click=navigate,args=('Protect',))
            if b.button('Meet the demo household',icon=':material/play_circle:',width='stretch'):
                load_demo(st.session_state)
                st.rerun()
            st.markdown('<div class="rr-trustline"><span>✓ No account needed</span><span>◎ Miami-Dade, Florida</span></div>',unsafe_allow_html=True)
        with right:
            st.markdown('<div class="rr-journey-visual"><div class="rr-orbit rr-orbit-one"></div><div class="rr-orbit rr-orbit-two"></div><div class="rr-visual-heading"><span class="rr-live-dot"></span> BUILT AROUND YOUR HOUSEHOLD</div><div class="rr-shield-hero">'+icon('shield')+'</div><div class="rr-journey-title">Your next step,<br>made clearer.</div><div class="rr-journey-flow"><div><b>01</b><span>Protect</span><small>Prepare together</small></div><i>›</i><div><b>02</b><span>Respond</span><small>Find the right help</small></div><i>›</i><div><b>03</b><span>Recover</span><small>Move forward</small></div></div><div class="rr-visual-foot">Official sources. Thoughtful guidance. Your decisions.</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="rr-section-head"><div><span class="rr-eyebrow">ONE STEP AT A TIME</span><h2>What do you need today?</h2></div><p>Choose where you are in your journey.</p></div>',unsafe_allow_html=True)
    cards=[('01','shield','Protect','Feel more prepared.','Check official weather alerts and plan around your household.','Prepare my household'),('02','help','Respond','Find your connection.','Reach emergency options or explore official assistance.','Find help now'),('03','home','Recover','Make progress, together.','Review your plan and save each small step toward recovery.','Start my recovery')]
    with st.container(key='home_actions'):
        for col,(number,symbol,page,title,copy,action) in zip(st.columns(3,gap='medium'),cards):
            with col,st.container(border=True,key='home_card_'+page):
                st.markdown(f'<div class="rr-card-top">{icon(symbol)}<span>{number} / {page.upper()}</span></div><h3>{title}</h3><p class="rr-card-copy">{copy}</p>',unsafe_allow_html=True)
                st.button(action,icon=':material/arrow_forward:',key='home_'+page,width='stretch',on_click=navigate,args=(page,))
    st.markdown('<div class="rr-note"><b>You stay in control.</b> Review every proposed change. See the source behind guidance. Know what is live, simulated or unavailable.</div>',unsafe_allow_html=True)


def household():
    heading('Your context · Optional', 'Ready starts with your household.', 'Use fictional details only. These preferences stay in this browser session and help organize the demonstration.')
    current = st.session_state['household']
    with st.form('household_form'):
        a, b = st.columns(2)
        label = a.text_input('Fictional household label', current.label, max_chars=60)
        members = b.number_input('People in the household', 1, 12, current.members)
        location = st.selectbox('Supported area', list(LOCATIONS), index=list(LOCATIONS).index(st.session_state['location_id']), format_func=LOCATIONS.get)
        mobility = st.checkbox('Someone needs mobility support', current.mobility_support)
        vehicle = st.checkbox('A vehicle is available', current.has_vehicle)
        pets = st.checkbox('Pets are part of the household', current.pets)
        st.caption('No exact address, medical history, phone number, or real identity is needed. Saving these details does not register you for assistance.')
        if st.form_submit_button('Save household preferences', type='primary'):
            st.session_state['household'] = Household(label=label.strip() or 'Your fictional household', members=members, mobility_support=mobility, has_vehicle=vehicle, pets=pets)
            change_context(st.session_state, location, st.session_state['mode'])
            st.session_state.pop('guidance', None)
            st.success('Preferences saved for this session. Accepted recovery cases are unchanged; use reassessment to update their needs.')
    if st.button('Continue to Protect', type='primary'):
        go('Protect')


def update_alert_context():
    change_context(st.session_state, st.session_state['alert_location_picker'], st.session_state['alert_mode_picker'])


def protect():
    heading('01 / Protect', 'A clearer picture. A better next step.', 'Start with official alert information, then consider what your household needs.')
    with st.container(border=True,key='alert_controls'):
        a, b = st.columns(2)
        mode = a.radio('Alert mode', list(AppMode), index=list(AppMode).index(st.session_state['mode']), format_func=lambda m:m.value, horizontal=True, key='alert_mode_picker', on_change=update_alert_context)
        location = b.selectbox('Check an area', list(LOCATIONS), index=list(LOCATIONS).index(st.session_state['location_id']), format_func=LOCATIONS.get, key='alert_location_picker', on_change=update_alert_context)
        if st.button('Show simulated alert' if mode == AppMode.DEMO else 'Check official alerts', type='primary'):
            try:
                result = nws_alerts.get_alerts(location, mode)
                # Reject an adapter that crosses the live/demo boundary.
                if mode == AppMode.LIVE and result.simulated:
                    raise ValueError('simulation returned for live request')
                st.session_state['alerts'] = result
            except Exception:
                from domain.contracts import AlertResult
                st.session_state['alerts'] = AlertResult(status='unavailable', message='The alert service could not be reached. Current conditions are unknown; check NWS directly.')
    result = st.session_state.get('alerts')
    if result:
        if result.status == 'alerts':
            for alert in result.alerts:
                st.markdown(f'<div class="rr-warning"><div class="rr-eyebrow">{"SIMULATED SCENARIO · NOT CURRENT CONDITIONS" if result.simulated else "OFFICIAL ALERT RESULT"}</div><h3>{escape(alert.headline)}</h3><p>{escape(alert.description)}</p><span class="rr-badge">{escape(alert.severity)}</span></div>', unsafe_allow_html=True)
                if alert.sent_at:
                    st.caption('Issued: ' + alert.sent_at + ' · Effective: ' + (alert.effective_at or 'Not supplied'))
                if alert.expires_at:
                    st.caption('Expires: ' + alert.expires_at)
                st.caption('Area: ' + (alert.area or 'Not supplied') + ' · Sender: ' + (alert.sender or 'NWS'))
                if alert.instruction:
                    with st.expander('Official alert instructions'):
                        st.text(alert.instruction)
                if alert.source_url and not result.simulated:
                    st.link_button('Original official alert', alert.source_url)
        elif result.status == 'none':
            st.info('No active alerts returned for this area. This does not mean the area or your household is safe.')
        else:
            st.warning(result.message)
        st.caption(result.message)
        if result.simulated:
            st.caption('Fixture loaded for the walkthrough. No official issue time or live check is claimed.')
        elif result.checked_at:
            st.caption('Lookup started: ' + result.checked_at + ' · On-demand only; not continuous monitoring.')
        st.link_button('Open National Weather Service', 'https://www.weather.gov/mfl/')
    else:
        st.info('No alert check has been made. Choose a mode above to begin.')
    a, b = st.columns([1.2, 1], gap='large')
    h = st.session_state['household']
    with a, st.container(border=True):
        st.subheader('What matters for your household')
        st.write(f'**{h.label}** · {h.members} people')
        if h.mobility_support:
            st.write('• Mobility support is part of your planning context.')
        if not h.has_vehicle:
            st.write('• Transportation is a reported need. Review assistance requirements early.')
        if h.pets:
            st.write('• Include pets when reviewing household arrangements.')
        st.caption('Preferences are not a safety assessment or an assistance registration.')
        if st.button('Edit household preferences'):
            go('Household')
    with b, st.container(border=True):
        st.subheader('Understand the information')
        st.write('General source excerpts are separate from the alert details above. They do not establish current conditions, orders, or household safety.')
        hazard = st.selectbox('Guidance hazard', ['Select a hazard', 'flood', 'hurricane'], key='guidance_hazard')
        topic = st.selectbox('General preparedness topic',
            ['Flood preparedness', 'Electrical hazards', 'Evacuation assistance program'], key='guidance_topic')
        # These supported named areas are explicitly within Miami-Dade. Do not
        # geocode, infer a county from household text, or use an unknown location.
        jurisdiction = 'US-FL-MIAMI-DADE' if location in LOCATIONS else None
        st.caption('Guidance scope: Miami-Dade County; preparedness phase. No live alert explanation is generated.')
        binding = (hazard, topic, jurisdiction, 'protect')
        if st.session_state.get('guidance_binding') != binding:
            st.session_state.pop('guidance', None)
        if st.button('Explain with verified sources'):
            st.session_state['guidance_binding'] = binding
        # Revalidate a requested display on every rerender: revocation or changed
        # source bytes must not leave a previously verified session result visible.
        if st.session_state.get('guidance_binding') == binding:
            try:
                st.session_state['guidance'] = knowledge.retrieve_guidance(topic, 'protect', h,
                    hazard=None if hazard == 'Select a hazard' else hazard, jurisdiction=jurisdiction)
            except Exception:
                st.session_state.pop('guidance', None)
                st.warning('The knowledge service is unavailable. Check official guidance directly.')
        result = st.session_state.get('guidance')
        if result:
            if result.insufficient_evidence:
                st.warning(result.answer)
            else:
                st.info(result.answer)
            for citation in result.citations:
                st.subheader(citation.section_heading)
                st.text(citation.passage)
                st.caption('Citation: ' + citation.citation_id + ' | Parent source: ' + citation.source_id)
                st.caption('Geography: ' + citation.jurisdiction + ' | Phase: ' + ', '.join(citation.phases))
                st.link_button(citation.title, citation.official_url)
                for caveat in citation.safety_caveats:
                    st.caption(caveat)
                with st.expander('Citation review provenance: ' + citation.citation_id):
                    for limitation in citation.source_limitations:
                        st.caption(limitation)
                    st.caption('Original SHA-256: ' + citation.original_content_hash)
                    st.json({'source_review': citation.source_review, 'candidate_review': citation.candidate_review})
            for limitation in result.limitations:
                st.caption(limitation)
            for missing in result.missing_information:
                st.caption(missing)
        st.caption('Deterministic excerpt display; no AI call or current safety determination.')
    from ui.guidance import render as grounded_guidance
    grounded_guidance('protect')
    if st.button('Next · Explore assistance', type='primary'):
        go('Respond')


def respond():
    heading('02 / Respond', 'Help starts with the right connection.', 'Emergency calling options stay above every screen. This app does not contact or dispatch responders.')
    left, right = st.columns([1.15, 1], gap='large')
    with left, st.container(border=True,key='assistance_controls'):
        st.subheader('What kind of help do you need?')
        need = st.radio('Choose an assistance category', ['Transportation', 'Temporary housing', 'Supplies', 'Immediate danger / not sure'])
        if st.button('Show assistance options', type='primary'):
            try:
                route = emergency.route_situation(need)
                if route.route == 'emergency':
                    st.session_state['rr_emergency'] = True
                    st.rerun()
                st.session_state['resource_need'] = need
            except Exception:
                st.warning('Situation guidance is unavailable. Emergency contact options remain above.')
        if st.session_state.get('resource_need'):
            try:
                records = resources.find_resources(st.session_state['resource_need'])
            except Exception:
                records = []
            if not records:
                st.info('No verified resource match is connected yet. Use the official county links to check options and requirements. Availability is unknown.')
            for record in records:
                st.write(record.title)
                st.caption(record.caveat)
                st.caption('Last checked: ' + (record.last_checked or 'Not verified'))
                st.link_button('View official resource', record.url)
        st.divider()
        st.write('**Try the fictional escalation**')
        st.caption('The demo household reports: “Water is rising; we’re trapped.”')
        if st.button('Simulate rising water / trapped'):
            st.session_state['rr_emergency'] = True
            st.rerun()
    with right:
        st.subheader('Official places to start')
        for record in resources.OFFICIAL_LINKS[1:3]:
            with st.container(border=True):
                st.write('**' + record.title + '**')
                st.caption(record.caveat)
                st.link_button('Open official information', record.url, width='stretch')
        st.caption('These are information links, not confirmed service matches. No live shelter capacity or pickup availability is shown.')
    from ui.guidance import render as grounded_guidance
    grounded_guidance('respond')
    if st.button('Next · Review recovery needs', type='primary'):
        go('Recover')


def evidence():
    heading('Trust through transparency', 'Know what’s behind the next step.', 'A clear view of connected capabilities, sources, and the boundaries of this prototype.')
    a, b, c = st.columns(3)
    a.metric('Shared application', 'Connected')
    b.metric('Recovery persistence', 'Local SQLite')
    c.metric('Reviewed retrieval', 'Connected')
    st.subheader('Integration readiness')
    integrations = [
        {'Owner': 'M1', 'Capability': 'Application, searchable menu, tour and conversational actions', 'State': 'Implemented'},
        {'Owner': 'M2', 'Capability': 'NWS Guardian alert retrieval', 'State': 'Integrated · live checks are on demand'},
        {'Owner': 'M3', 'Capability': 'Reviewed CDC retrieval and M1 Qwen explanations', 'State': 'Integrated · limited recovery evidence; resource directory pending'},
        {'Owner': 'M4', 'Capability': 'Reviewed emergency rules and safety evaluation', 'State': 'TODO · conservative access fallback'},
        {'Owner': 'M5', 'Capability': 'Intake, plan approval, saved tasks and reassessment', 'State': 'Integrated from PR #1'},
    ]
    for row in integrations:
        with st.container(border=True):
            left, right = st.columns([2, 1])
            left.write("**" + row["Owner"] + " · " + row["Capability"] + "**")
            right.caption(row["State"])
    st.subheader('Sources and provenance')
    st.write('The links below point to official publishers. Reviewed CDC recovery passages are available through the guidance panels. These general directory links do not themselves establish reviewed evidence. Resource availability must be checked with the provider.')
    for record in resources.OFFICIAL_LINKS:
        with st.expander(record.title):
            st.write(record.caveat)
            st.caption('Provenance: official entry point · directory verification pending M3/M4')
            st.link_button('Visit official source', record.url)
    with st.expander('What the demo can honestly show', expanded=True):
        st.write('A fictional household journey; explicitly simulated warning; immediate emergency links; a reviewable deterministic recovery draft; local saved progress; changes proposed before approval.')
        st.write('The Assistant and tour explanations use Nebius only when requested and configured; proposed actions are validated and require confirmation. The reviewed-guidance panels retrieve M3 evidence before Qwen generation and preserve limitations. The application uses deterministic organization drafts for task planning; source explanations never silently create or update tasks. No hidden AI calls are made by the application shell.')
    with st.expander('Storage, privacy and deployment limits'):
        st.write('No login. Household preferences last for the session. Fictional recovery cases persist on this local machine and can be resumed with their case ID. Case IDs are not authentication. This is a local single-user demo, not a private multi-user service. Streamlit hosted disk may be reset on restart or redeploy.')
        st.write('No offline guarantee, dispatch, monitoring, live shelter inventory, insurance submission, FEMA eligibility decision, or validation for real emergencies.')
