"""Contextual native walkthrough, anchored to the app's actual controls."""
from uuid import uuid4
import streamlit as st
from ui.tour_component import render_spotlight
from ui.capabilities import TOUR


def start_tour():
    from ui.state import start_walkthrough
    start_walkthrough(st.session_state)


def tour_steps():
    return TOUR[2:5] if st.session_state.get('tour_demo') else TOUR


def begin_exploring():
    st.session_state['tour_welcome']=False


def move_step(index):
    steps = tour_steps()
    st.session_state.pop('tour_explanation', None)
    if index >= len(steps) or index < 0:
        st.session_state.pop('tour_step', None)
        st.session_state.pop('tour_welcome', None)
        st.session_state.pop('tour_demo', None)
    else:
        st.session_state['tour_step'] = index
        st.session_state['page'] = steps[index][0]


def render_tour():
    if st.session_state.get('rr_emergency'):
        st.session_state.pop('tour_step',None)
        st.session_state.pop('tour_explanation',None)
    if 'tour_step' not in st.session_state: return
    steps = tour_steps()
    demo = st.session_state.get('tour_demo', False)
    if st.session_state.get('tour_welcome'):
        with st.container(key='tour_welcome', border=True):
            st.caption('SIMULATED DEMO · THREE GUIDED STEPS' if demo else 'WELCOME · YOUR GUIDED TOUR')
            st.title('Meet the Rivera household.' if demo else "Let's find your next step.")
            if demo:
                st.write('Three people, mobility support, no vehicle, and pets. Their fictional preferences are loaded.')
                st.info('First, try “Show simulated alert” in Protect. Then follow the guide through Respond and Recover.')
                st.caption('No live requests or recovery changes made. Review and approve any plan before saving.')
            else:
                st.write('Explore ReadyRelief in six short steps. We will highlight each control and explain how to use it. Narration starts automatically; mute it or choose a different voice at any time.')
                st.caption('You stay in control. No changes are saved by taking the tour.')
            start, close = st.columns(2)
            start.button('Start demo tour' if demo else 'Start exploring', type='primary', width='stretch', on_click=begin_exploring)
            close.button('End tour', width='stretch', on_click=move_step, args=(-1,))
        return
    index=max(0,min(int(st.session_state['tour_step']),len(steps)-1))
    page,title,body,hint=steps[index]
    with st.container(border=True,key='guided_tour'):
        st.caption(f'STEP {index+1} OF {len(steps)} · {page.upper()}')
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
        narration = {
            'Home': "Welcome to ReadyRelief. Start here by choosing what you need: prepare your household, find help, or work on recovery. Let's take it one step at a time.",
            'Household': "Here you can describe your demo household. Add the number of people and any transport, mobility, or pet needs. Use fictional details, then save your preferences.",
            'Protect': "This is Protect. Choose an alert mode and an area, then use the button to check alerts. Simulated demo shows an example. Live check requests official information. The labels tell you which you're viewing.",
            'Respond': "This is Respond. Choose the kind of assistance you need to explore official resources. Emergency options are separate from the AI assistant. This app does not contact or dispatch responders.",
            'Recover': "This is Recover. Start with the immediate danger assessment, then describe your household's situation. Review the draft plan before accepting it. You're in control of every saved change.",
            'Assistant': "You can also ask ReadyRelief for help in chat. Ask how a feature works, or request an action. You'll review proposed changes before confirming them. You can minimize this screen to keep chatting while you explore.",
        }
        render_spotlight(
            run=st.session_state.setdefault('tour_run',uuid4().hex),
            step=index, target=targets[page],
            narration=narration[page],
            active=st.session_state['page']==page,
        )
        st.progress((index+1)/len(steps))
        if st.session_state['page']!=page:
            if st.button('Take me to this step'):
                st.session_state['page']=page
                st.rerun()
        cols=st.columns(3)
        cols[0].button('Previous step',disabled=index==0,width='stretch',on_click=move_step,args=(index-1,))
        cols[1].button('Next step' if index<len(steps)-1 else 'Finish tour',type='primary',width='stretch',on_click=move_step,args=(index+1,))
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
