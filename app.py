"""ReadyRelief M1 entry point. Run: python -m streamlit run app.py."""
import streamlit as st
from ui.state import initialize
from ui.components import frame, footer, apply_style
from ui.shell import toolbar, render_dock, full_chat
from ui import pages

st.set_page_config(page_title='ReadyRelief · Your next step', page_icon='🌿', layout='wide', initial_sidebar_state='auto')
initialize(st.session_state)
toolbar()
apply_style()
pages.sidebar()
frame()
render_dock()
from ui.tour import render_tour
render_tour()
notice = st.session_state.pop('assistant_result_notice', None)
if notice:
    st.success(notice)
page = st.session_state['page']
if page == 'Assistant':
    full_chat()
elif page == 'Recover':
    from ui.recovery_page import render
    with st.container(key='recovery_workspace'):
        render()
else:
    with st.container(key='household_form_target' if page=='Household' else 'page_workspace'):
        {'Home': pages.home, 'Protect': pages.protect, 'Respond': pages.respond,
         'Household': pages.household, 'Evidence': pages.evidence}.get(page, pages.home)()
footer()
