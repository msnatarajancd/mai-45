"""Client-side suggestions for the native search widget; navigation only."""
from pathlib import Path
import streamlit as st
from streamlit.components.v2 import component
from ui.capabilities import navigation_search_data
from ui.components import navigate_destination

_suggestions=component('readyrelief_search_suggestions',
    js=Path(__file__).with_name('search_assets').joinpath('search.js').read_text(encoding='utf-8'))

def render_suggestions():
    data = navigation_search_data()
    result=_suggestions(key='search_suggestions',data=data,
        on_destination_change=lambda:None)
    destination=result.destination
    if isinstance(destination,str) and destination in {item['page'] for item in data['pages']}:
        navigate_destination(destination)
        st.session_state['_clear_nav_search']=True
        st.rerun()
