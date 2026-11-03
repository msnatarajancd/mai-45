"""Client-side suggestions for the native search widget; navigation only."""
from pathlib import Path
import streamlit as st
from streamlit.components.v2 import component
from ui.capabilities import PAGES

_suggestions=component('readyrelief_search_suggestions',
    js=Path(__file__).with_name('search_assets').joinpath('search.js').read_text(encoding='utf-8'))

def render_suggestions():
    result=_suggestions(key='search_suggestions',data=[{'page':page,'keywords':words} for page,(_,words) in PAGES.items()],
        on_destination_change=lambda:None)
    destination=result.destination
    if isinstance(destination,str) and destination in PAGES:
        st.session_state['page']=destination
        st.session_state['_clear_nav_search']=True
        st.rerun()
