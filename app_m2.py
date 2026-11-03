"""Local M2 preview; M1 can reuse render_guardian in the shared app."""
import streamlit as st
from m2_guardian.streamlit_demo import render_guardian

st.set_page_config(page_title="ReadyRelief Guardian", layout="centered")
render_guardian()
