from html import escape
import streamlit as st
from domain.contracts import AppMode, Household, LOCATIONS
from services import nws_alerts, knowledge, emergency, resources
from ui.components import ROOT, go, heading, icon
from ui.state import change_context, load_demo


def sidebar():
    with st.sidebar:
        st.markdown('<div class="rr-brand">Ready<span>Relief</span></div>', unsafe_allow_html=True)
        st.caption('PROTECT. RESPOND. RECOVER.')
        st.divider()
        for name, symbol in [('Home', ':material/home:'), ('Protect', ':material/shield:'), ('Respond', ':material/emergency:'), ('Recover', ':material/checklist:'), ('Household', ':material/group:'), ('Evidence', ':material/fact_check:')]:
            if st.button(name, icon=symbol, key='nav_'+name, type='primary' if st.session_state['page'] == name else 'secondary', width='stretch'):
                go(name)
        st.divider()
        st.caption('YOUR DEMONSTRATION')
        st.write('One household.\n\nA clearer path forward.')
        st.caption('3 people · Mobility support · No vehicle')
        if st.button('Start guided demo', width='stretch'):
            load_demo(st.session_state)
            st.rerun()
        if st.session_state.get('demo_started'):
            steps = [('1 · Prepare together', 'Protect'), ('2 · Find immediate help', 'Respond'), ('3 · Build a recovery plan', 'Recover'), ('4 · Show the evidence', 'Evidence')]
            for label, page in steps:
                if st.button(label, key='demo_'+page, width='stretch'):
                    go(page)
            st.caption('Fictional scenario. Never place a real emergency call during rehearsal. Starting again keeps saved recovery cases.')
        st.divider()
        st.caption('TEAM MAI-45 · DEMO DAY 2026\n\nNo account needed. No real personal data.')


def home():
    left, right = st.columns([1.3, 1], gap='large')
    with left:
        st.markdown('<div class="rr-hero"><div class="rr-eyebrow">A little more ready. A little less alone.</div><h1>When life changes,<br>know your <em>next step.</em></h1><p>Prepare your household, find the right help, and move through recovery—one clear action at a time.</p></div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        if a.button('Explore your next step', type='primary', width='stretch'):
            go('Protect')
        if b.button('Meet the demo household', width='stretch'):
            load_demo(st.session_state)
            st.rerun()
        st.caption('Miami-Dade · Hurricane & flood · Guest-first')
    with right:
        st.image(str(ROOT / 'assets/journey.svg'), width='stretch')
    st.markdown('### What do you need right now?')
    cards = [('01 / BEFORE THE STORM', 'shield', 'Protect', 'Get ready, together.', 'Check alert information and organize what matters for your household.', 'Prepare my household'), ('02 / WHEN YOU NEED HELP', 'help', 'Respond', 'Find the right help.', 'Reach emergency calling options immediately, or explore official assistance.', 'Find help now'), ('03 / AFTER THE STORM', 'home', 'Recover', 'Take the next small step.', 'Review a recovery plan, save your progress, and adapt when circumstances change.', 'Start my recovery')]
    for col, (number, image, page, title, copy, action) in zip(st.columns(3, gap='medium'), cards):
        with col, st.container(border=True):
            st.markdown(f'<div class="rr-card-number">{number}</div>{icon(image)}<h3>{title}</h3><p class="rr-card-copy">{copy}</p>', unsafe_allow_html=True)
            if st.button(action, key='home_'+page, width='stretch'):
                go(page)
    st.markdown('<div class="rr-note">Built around your household. You stay in control: review a plan before accepting it, and see what is simulated, unavailable, or connected.</div>', unsafe_allow_html=True)


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


def protect():
    heading('01 / Protect', 'A clearer picture. A better next step.', 'Start with official alert information, then consider what your household needs.')
    with st.container(border=True):
        a, b = st.columns(2)
        mode = a.radio('Alert mode', list(AppMode), index=list(AppMode).index(st.session_state['mode']), format_func=lambda m:m.value, horizontal=True, key='alert_mode_picker')
        location = b.selectbox('Check an area', list(LOCATIONS), index=list(LOCATIONS).index(st.session_state['location_id']), format_func=LOCATIONS.get, key='alert_location_picker')
        if location != st.session_state['location_id'] or mode != st.session_state['mode']:
            change_context(st.session_state, location, mode)
            st.rerun()
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
                if alert.expires_at:
                    st.caption('Expires: ' + alert.expires_at)
        elif result.status == 'none':
            st.info('No active alerts returned for this area. This does not mean the area or your household is safe.')
        else:
            st.warning(result.message)
        if result.simulated:
            st.caption('Fixture loaded for the walkthrough. No official issue time or live check is claimed.')
        elif result.checked_at:
            st.caption('Last check: ' + result.checked_at + ' · On-demand only; not continuous monitoring.')
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
        st.write('A place for the Guardian’s evidence-backed explanation, personalized to your household.')
        if st.button('Explain with verified sources'):
            try:
                st.session_state['guidance'] = knowledge.retrieve_guidance('Explain this alert for my household', 'protect', h)
            except Exception:
                st.session_state.pop('guidance', None)
                st.warning('The knowledge service is unavailable. Check official guidance directly.')
        result = st.session_state.get('guidance')
        if result:
            st.info(result.answer)
            for source in result.sources:
                st.link_button(source.title, source.url)
        st.caption('Source-grounded explanations are pending the knowledge integration.')
    if st.button('Next · Explore assistance', type='primary'):
        go('Respond')


def respond():
    heading('02 / Respond', 'Help starts with the right connection.', 'Emergency calling options stay above every screen. This app does not contact or dispatch responders.')
    left, right = st.columns([1.15, 1], gap='large')
    with left, st.container(border=True):
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
    if st.button('Next · Review recovery needs', type='primary'):
        go('Recover')


def evidence():
    heading('Trust through transparency', 'Know what’s behind the next step.', 'A clear view of connected capabilities, sources, and the boundaries of this prototype.')
    a, b, c = st.columns(3)
    a.metric('Shared application', 'Connected')
    b.metric('Recovery persistence', 'Local SQLite')
    c.metric('Live alerts / RAG', 'Pending')
    st.subheader('Integration readiness')
    integrations = [
        {'Owner': 'M1', 'Capability': 'Application, household, demo and integration UI', 'State': 'Implemented'},
        {'Owner': 'M2', 'Capability': 'NWS connector and Guardian explanation', 'State': 'TODO · simulated fixture only'},
        {'Owner': 'M3', 'Capability': 'Reviewed corpus, retrieval and local directory', 'State': 'TODO · official entry links only'},
        {'Owner': 'M4', 'Capability': 'Reviewed emergency rules and safety evaluation', 'State': 'TODO · conservative access fallback'},
        {'Owner': 'M5', 'Capability': 'Intake, plan approval, saved tasks and reassessment', 'State': 'Integrated from PR #1'},
    ]
    for row in integrations:
        with st.container(border=True):
            left, right = st.columns([2, 1])
            left.write("**" + row["Owner"] + " · " + row["Capability"] + "**")
            right.caption(row["State"])
    st.subheader('Sources and provenance')
    st.write('The links below point to official publishers. They are not a downloaded corpus and have not been used to claim grounded AI answers. Resource availability must be checked with the provider.')
    for record in resources.OFFICIAL_LINKS:
        with st.expander(record.title):
            st.write(record.caveat)
            st.caption('Provenance: official entry point · directory verification pending M3/M4')
            st.link_button('Visit official source', record.url)
    with st.expander('What the demo can honestly show', expanded=True):
        st.write('A fictional household journey; explicitly simulated warning; immediate emergency links; a reviewable deterministic recovery draft; local saved progress; changes proposed before approval.')
        st.write('The optional M5 AI planner uses Nebius only when requested and configured. Without verified evidence it is experimental and ungrounded. No hidden AI calls are made by the application shell.')
    with st.expander('Storage, privacy and deployment limits'):
        st.write('No login. Household preferences last for the session. Fictional recovery cases persist on this local machine and can be resumed with their case ID. Case IDs are not authentication. This is a local single-user demo, not a private multi-user service. Streamlit hosted disk may be reset on restart or redeploy.')
        st.write('No offline guarantee, dispatch, monitoring, live shelter inventory, insurance submission, FEMA eligibility decision, or validation for real emergencies.')
