"""Contextual native walkthrough, anchored to the app's actual controls."""
from uuid import uuid4
import streamlit as st
from ui.tour_component import render_spotlight
from ui.capabilities import TOUR


def start_tour():
    st.session_state['tour_run']=uuid4().hex
    st.session_state['tour_step']=0
    st.session_state['page']='Home'
    st.session_state.pop('tour_explanation',None)


def move_step(index):
    st.session_state.pop('tour_explanation', None)
    if index >= len(TOUR) or index < 0:
        st.session_state.pop('tour_step', None)
    else:
        st.session_state['tour_step'] = index
        st.session_state['page'] = TOUR[index][0]


def render_tour():
    if st.session_state.get('rr_emergency'):
        st.session_state.pop('tour_step',None)
        st.session_state.pop('tour_explanation',None)
    if 'tour_step' not in st.session_state: return
    index=max(0,min(int(st.session_state['tour_step']),len(TOUR)-1))
    page,title,body,hint=TOUR[index]
    with st.container(border=True,key='guided_tour'):
        st.caption(f'STEP {index+1} OF {len(TOUR)} · {page.upper()}')
        st.subheader(title)
        st.write(hint)
        targets = {
            'Home': '.st-key-home_card_Protect',
            'Household': '.st-key-household_form_target [data-testid="stTextInput"]',
            'Protect': '.st-key-alert_controls [data-testid="stRadio"]',
            'Respond': '.st-key-assistance_controls [data-testid="stRadio"]',
            'Recover': '.st-key-recovery_workspace [role="combobox"]',
            'Assistant': '.st-key-full_chat [data-testid="stChatInput"]',
        }
        render_spotlight(
            run=st.session_state.setdefault('tour_run',uuid4().hex),
            step=index, target=targets[page],
            narration=f'Step {index+1}. {page}. {title}. {hint} {body}',
            active=st.session_state['page']==page,
        )
        st.progress((index+1)/len(TOUR))
        if st.session_state['page']!=page:
            if st.button('Take me to this step'):
                st.session_state['page']=page
                st.rerun()
        cols=st.columns(3)
        cols[0].button('Previous step',disabled=index==0,width='stretch',on_click=move_step,args=(index-1,))
        cols[1].button('Next step' if index<len(TOUR)-1 else 'Finish tour',type='primary',width='stretch',on_click=move_step,args=(index+1,))
        cols[2].button('End tour',width='stretch',on_click=move_step,args=(-1,))
        with st.expander('Details & AI help'):
            st.write(body)
            if st.button('Explain this step with AI',width='stretch'):
                from services.assistant import propose
                try:
                    # Share only the fictional household/page context for product help, not recovery records.
                    context={k:st.session_state[k] for k in ('page','mode','location_id','household')}
                    with st.spinner('Explaining this feature with Nebius…'):
                        result=propose(f'Explain how to use the {page} page for a new user. Keep it short; do not propose any action.',context,None)
                    st.session_state['tour_explanation']=(index,result.answer)
                except Exception:
                    st.warning('The AI explanation is unavailable. The product guide above still works; nothing was changed.')
            st.caption('AI explanation sends this step and fictional household preferences to Nebius. The tour itself makes no API calls.')
            explanation=st.session_state.get('tour_explanation')
            if explanation and explanation[0]==index:
                st.markdown('**Nebius AI explanation · product help**')
                st.write(explanation[1])
