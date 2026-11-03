import streamlit as st
from ui.tour import start_tour, render_tour
st.session_state.setdefault('page', 'Home')
if st.button('Start test tour'): start_tour()
render_tour()
