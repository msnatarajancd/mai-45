"""ReadyRelief M1 entry point. Run: python -m streamlit run app.py."""
import streamlit as st
from ui.state import initialize
from ui.components import frame, footer
from ui import pages

st.set_page_config(page_title='ReadyRelief · Your next step', page_icon='🌿', layout='wide', initial_sidebar_state='auto')
initialize(st.session_state)
pages.sidebar()
frame()
page = st.session_state['page']
if page == 'Recover':
    from ui.recovery_page import render
    render()
else:
    {'Home': pages.home, 'Protect': pages.protect, 'Respond': pages.respond,
     'Household': pages.household, 'Evidence': pages.evidence}.get(page, pages.home)()
footer()
