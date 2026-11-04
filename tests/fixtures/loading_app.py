import time
import streamlit as st
from ui.state import initialize
from ui.components import apply_style
from ui.shell import toolbar
st.set_page_config(layout='wide')
initialize(st.session_state)
apply_style()
toolbar()
if st.button('Run loading test'):
    time.sleep(2)
    st.success('Finished test work')
