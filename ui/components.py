from html import escape
from pathlib import Path
import streamlit as st
from domain.contracts import AppMode, LOCATIONS

ROOT = Path(__file__).resolve().parents[1]
ICONS = {
    'shield': '<path d="M12 3 20 6v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    'help': '<circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 3v1"/>',
    'home': '<path d="m3 11 9-8 9 8M5 9v12h14V9M9 21v-8h6v8"/>',
}


def icon(name):
    return f'<div class="rr-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg></div>'


def go(page):
    st.session_state['page'] = page
    st.rerun()


def heading(kicker, title, description=''):
    st.markdown(f'<div class="rr-eyebrow">{escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    if description:
        st.write(description)


def emergency_controls():
    with st.container(key='emergency_bar'):
        cols = st.columns([1.2, 1, 1.25, 1])
        cols[0].markdown('<div class="rr-emergency-label">Need urgent help?</div>', unsafe_allow_html=True)
        cols[1].link_button('Call 911', 'tel:911', width='stretch')
        if cols[2].button("I can't call 911", width='stretch'):
            st.session_state['rr_alternative'] = not st.session_state.get('rr_alternative', False)
        if cols[3].button('Immediate danger', width='stretch'):
            st.session_state['rr_emergency'] = True
            st.rerun()
    if st.session_state.get('rr_alternative'):
        st.info('If you cannot call, text-to-911 may be an option. Local network and device availability vary; delivery is not guaranteed. This app cannot send a text or contact responders. If possible, ask someone nearby to call for you.')
        st.link_button('Read county Text-to-911 information', 'https://www.miamidade.gov/global/release.page?Mduid_release=rel1748353190014356')
    if st.session_state['rr_emergency']:
        st.error('Emergency access comes first. ReadyRelief has not contacted or dispatched anyone. Routine recovery actions are paused.')
        st.write('If you are in immediate danger, call 911. Follow instructions from emergency services and local authorities.')
        # Persist interruption for the active M5 case when possible, without gating controls.
        if st.session_state.get('rr_case_id'):
            pending = set(st.session_state.get('rr_pending_danger', []))
            pending.add(st.session_state['rr_case_id'])
            st.session_state['rr_pending_danger'] = list(pending)
            try:
                from ui.recovery_page import repository
                from uuid import UUID
                repository().report_immediate_danger(UUID(st.session_state['rr_case_id']))
                pending.discard(st.session_state['rr_case_id'])
                st.session_state['rr_pending_danger'] = list(pending)
            except Exception:
                st.warning('The danger report could not be saved. Emergency contact controls remain available.')
        if st.button('Return to app — this does not confirm safety'):
            st.session_state['rr_emergency'] = False
            st.session_state['page'] = 'Respond'
            st.rerun()
        st.stop()


def apply_style():
    from ui.theme import theme_variables
    st.markdown('<style>' + theme_variables(st.session_state.get('appearance', 'Bright')) + (ROOT / 'ui/styles.css').read_text(encoding='utf-8-sig') + '</style>', unsafe_allow_html=True)


def frame():
    mode = st.session_state['mode']
    label = LOCATIONS[st.session_state['location_id']]
    st.markdown(f'<div class="rr-topline"><span>MIAMI-DADE, FLORIDA &nbsp; / &nbsp; {escape(label)}</span><span class="rr-badge">{escape(mode.value)} · COURSE PROTOTYPE</span></div>', unsafe_allow_html=True)
    emergency_controls()


def footer():
    st.markdown('<div class="rr-footer">ReadyRelief · Protect. Respond. Recover.<br>Educational prototype · Online only · No dispatch or safety verification · Use fictional household information only.</div>', unsafe_allow_html=True)
