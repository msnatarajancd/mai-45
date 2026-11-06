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


def navigate(page):
    """Widget callback: update navigation before Streamlit's single render."""
    from ui.capabilities import resolve_page
    st.session_state['page'] = resolve_page(page)


def navigate_destination(page, focus=None):
    """Open an existing Recovery destination without consuming staged work."""
    from ui.capabilities import navigation_target
    item = navigation_target(page)
    if item:
        page, focus = item.page, focus if focus is not None else item.focus
    navigate(page)
    if focus is not None and st.session_state['page'] == 'Recover':
        st.session_state['rr_focus'] = focus


def go(page):
    navigate(page)
    st.rerun()


def heading(kicker, title, description=''):
    st.markdown(f'<div class="rr-eyebrow">{escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    if description:
        st.write(description)


def emergency_controls():
    from ui.emergency_page import render_access_controls
    render_access_controls()


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
