"""ReadyRelief M1 entry point. Run: python -m streamlit run app.py."""
import streamlit as st
from ui.state import initialize
from ui.components import frame, footer
from ui import pages

st.set_page_config(page_title='ReadyRelief · Your next step', page_icon='🌿', layout='wide', initial_sidebar_state='auto')
initialize(st.session_state)
pages.sidebar()
frame()
from ui.tour import render_tour
render_tour()
if st.session_state['page'] != 'Assistant':
    if st.button('Ask ReadyRelief', icon=':material/chat:', key='open_assistant'):
        st.session_state['page'] = 'Assistant'
        st.rerun()
notice = st.session_state.pop('assistant_result_notice', None)
if notice:
    st.success(notice)
page = st.session_state['page']
if page == 'Assistant':
    from ui.assistant_page import render
    render()
elif page == 'Recover':
    from ui.recovery_page import render
    render()
else:
    {'Home': pages.home, 'Protect': pages.protect, 'Respond': pages.respond,
     'Household': pages.household, 'Evidence': pages.evidence}.get(page, pages.home)()
footer()
