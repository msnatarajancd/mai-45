import streamlit as st

from recovery.ui import render_recovery_copilot


st.set_page_config(page_title="ReadyRelief Recovery Copilot", layout="centered")
render_recovery_copilot()