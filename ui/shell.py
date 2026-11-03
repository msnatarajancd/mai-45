"""Compact top toolbar and a shared floating/full-screen assistant."""
import streamlit as st
from ui.capabilities import search_pages


def toolbar():
    with st.container(key='top_toolbar'):
        search, theme = st.columns([4,1.35],vertical_alignment='center')
        search.text_input('Search menu',placeholder='Search screens · tasks, weather, family…',help='Press Enter to filter the menu. Clear to show all screens.',key='nav_search',label_visibility='collapsed')
        theme.radio('Appearance',['Bright','Dark'],horizontal=True,key='appearance',label_visibility='collapsed')
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
            if st.button('Ask ReadyRelief',icon=':material/chat:',type='primary'):
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
