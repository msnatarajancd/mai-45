"""Compact top toolbar and a shared floating/full-screen assistant."""
import streamlit as st
from ui.capabilities import search_pages, PAGES
from ui.components import navigate
from ui.tour import start_tour


def toggle_theme():
    st.session_state["appearance"] = "Bright" if st.session_state["appearance"] == "Dark" else "Dark"



def toolbar():
    if st.session_state.pop('_clear_nav_search',False):
        st.session_state['nav_search']=''
    st.session_state.setdefault('appearance','Bright')
    with st.container(key='top_toolbar'):
        title, search, theme, help_control = st.columns([.65,3,.28,.28],vertical_alignment='center',gap='small')
        with title.container(key='desktop_navigation'):
            from ui.navigation_component import render_toggle
            render_toggle('toolbar_toggle', st.session_state['page'])
        with title.container(key='mobile_nav'):
            with st.popover('Navigate',icon=':material/menu:',help='Open navigation',width='stretch'):
                st.caption('YOUR WORKSPACE')
                for page in PAGES:
                    st.button(page,key='mobile_nav_'+page,width='stretch',on_click=navigate,args=(page,))

        search.text_input('Search menu',placeholder='Search anything…',help='Suggestions appear as you type. Use arrow keys and Enter, or select a screen.',key='nav_search',label_visibility='collapsed',icon=':material/search:')
        with search:
            from ui.search_component import render_suggestions
            render_suggestions()
        dark=st.session_state['appearance']=='Dark'
        theme.button('Switch to bright mode' if dark else 'Switch to dark mode',icon=':material/light_mode:' if dark else ':material/dark_mode:',key='theme_toggle',help='Switch to bright mode' if dark else 'Switch to dark mode',width='stretch',on_click=toggle_theme)
        help_control.button('Start walkthrough',icon=':material/help_outline:',key='quick_tour',help='Take a guided tour',width='stretch',on_click=start_tour)
    query=st.session_state.get('nav_search','')
    if query:
        matches=search_pages(query)
        if matches:
            with st.container(key='search_results'):
                st.caption('MATCHING SCREENS')
                cols=st.columns(min(4,len(matches)))
                for i,page in enumerate(matches):
                    if cols[i%len(cols)].button('Open '+page,key='search_result_'+page,width='stretch'):
                        st.session_state['page']=page
                        st.rerun()
        else:
            st.caption('No matching screens. Try tasks, weather, family or chat.')


def render_dock():
    if st.session_state['page']=='Assistant': return
    if st.session_state.get('chat_open',False):
        with st.container(key='chat_panel',border=True):
            title,expand,close=st.columns([1.5,1.1,1])
            title.markdown('**ReadyRelief AI**')
            if expand.button('Expand chat',icon=':material/open_in_full:',width='stretch'):
                st.session_state['chat_return_page']=st.session_state['page']
                st.session_state['page']='Assistant'
                st.rerun()
            if close.button('Close chat',icon=':material/close:',width='stretch'):
                st.session_state['chat_open']=False
                st.rerun()
            from ui.assistant_page import render
            render(compact=True)
    else:
        with st.container(key='chat_launcher'):
            if st.button('Ask ReadyRelief',icon=':material/auto_awesome:',type='primary',help='Ask ReadyRelief'):
                st.session_state['chat_open']=True
                st.rerun()


def full_chat():
    if st.button('Minimize chat',icon=':material/close_fullscreen:'):
        st.session_state['page']=st.session_state.get('chat_return_page','Home')
        st.session_state['chat_open']=True
        st.rerun()
    from ui.assistant_page import render
    with st.container(key='full_chat'):
        render()
        from ui.guidance import render as grounded_guidance
        grounded_guidance('assistant')
