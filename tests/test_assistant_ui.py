from pathlib import Path
from streamlit.testing.v1 import AppTest
import pytest

@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH',str(tmp_path/'chat.sqlite3'))
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()


def button(app,name): return next(b for b in app.button if b.label==name)


def test_navigation_search_and_empty_state(app):
    next(t for t in app.text_input if t.label=='Search menu').input('tasks').run()
    assert 'Recover' in [b.label for b in app.button]
    assert 'Protect' in [b.label for b in app.button]  # Primary navigation stays available.
    assert 'Open Recover' in [b.label for b in app.button]
    assert 'Open Protect' not in [b.label for b in app.button]
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    next(t for t in app.text_input if t.label=='Search menu').input('zzzzz').run()
    assert any('No matching' in x.value for x in app.caption)


def test_tour_navigation_and_exit(app):
    button(app,'Show me around').click().run()
    button(app,'Start exploring').click().run()
    assert app.session_state['tour_step']==0
    button(app,'Next step').click().run()
    assert app.session_state['page']=='Household'
    assert app.session_state['tour_step']==1
    button(app,'Previous step').click().run()
    assert app.session_state['page']=='Home'
    button(app,'End tour').click().run()
    assert 'tour_step' not in app.session_state


@pytest.mark.parametrize('entry', ['Start guided demo', 'Meet the demo household'])
def test_demo_opens_visible_guide_and_can_restart(app, entry):
    button(app, entry).click().run()
    assert any('Meet the Rivera household.' in item.value for item in app.title)
    button(app, 'Start demo tour').click().run()
    for index, page in enumerate(('Protect', 'Respond', 'Recover')):
        assert app.session_state['page'] == page
        assert any(f'STEP {index + 1} OF 3' in item.value for item in app.caption)
        assert not app.exception
        button(app, 'Finish tour' if index == 2 else 'Next step').click().run()
    assert 'tour_step' not in app.session_state
    button(app, 'Start guided demo').click().run()
    assert app.session_state['tour_welcome']
    assert app.session_state['page'] == 'Protect'
    button(app, 'End tour').click().run()
    button(app, 'Show me around').click().run()
    button(app, 'Start exploring').click().run()
    assert app.session_state['page'] == 'Home'
    assert any('STEP 1 OF 6' in item.value for item in app.caption)


def test_demo_restart_preserves_recovery_and_emergency_state():
    from ui.state import initialize, load_demo
    state = {'rr_case_id': 'existing-case', 'rr_emergency': True, 'rr_pending_danger': ['existing-case']}
    initialize(state)
    load_demo(state)
    first_run = state['tour_run']
    load_demo(state)
    assert state['tour_run'] != first_run
    assert state['rr_case_id'] == 'existing-case'
    assert state['rr_pending_danger'] == ['existing-case']
    assert state['rr_emergency'] is True


@pytest.mark.parametrize('mode', ['Local guide · no AI', 'Nebius AI'])
@pytest.mark.parametrize('destination', ['Recover', 'Recovery Progress'])
def test_chat_navigation_is_immediate(app, monkeypatch, mode, destination):
    import ui.assistant_page as screen
    if destination == 'Recovery Progress':
        import sys
        from types import SimpleNamespace
        import streamlit as st
        monkeypatch.setitem(sys.modules, 'ui.recovery_progress_page', SimpleNamespace(render=lambda: st.title('Recovery Progress route')))
    monkeypatch.setattr(screen, 'local_proposal', lambda *args, **kwargs: pytest.fail('Navigation must not call the planner'))
    monkeypatch.setattr(screen, 'propose', lambda *args, **kwargs: pytest.fail('Navigation must not call the model'))
    app.session_state['page']='Assistant'; app.run()
    next(r for r in app.radio if r.label=='Assistant mode').set_value(mode).run()
    app.chat_input[0].set_value('open ' + destination).run()
    assert app.session_state['page']==destination
    assert 'assistant_pending' not in app.session_state
    assert not app.exception


def test_chat_question_stays_in_chat_and_uses_assistant(app, monkeypatch):
    import ui.assistant_page as screen
    from services.assistant import Proposal
    calls = []
    def answer(text, *args, **kwargs):
        calls.append(text)
        return Proposal(answer='Use the recovery screen to review a proposed plan.')
    monkeypatch.setattr(screen, 'propose', answer)
    monkeypatch.setenv('NEBIUS_API_KEY', 'test-key-not-used')
    app.session_state['page'] = 'Assistant'
    app.session_state['assistant_mode_preference'] = 'Nebius AI'
    app.run()
    app.chat_input[0].set_value('How does recovery work?').run()
    assert calls == ['How does recovery work?']
    assert app.session_state['page'] == 'Assistant'
    assert 'assistant_pending' not in app.session_state


def test_chat_ambiguous_route_asks_instead_of_guessing(app, monkeypatch):
    import ui.assistant_page as screen
    monkeypatch.setattr(screen, 'propose', lambda *a, **kw: pytest.fail('No AI needed'))
    monkeypatch.setattr(screen, 'local_proposal', lambda *a, **kw: pytest.fail('No AI needed'))
    app.session_state['page'] = 'Assistant'; app.run()
    app.chat_input[0].set_value('open re').run()
    assert app.session_state['page'] == 'Assistant'
    assert len(app.session_state['assistant_routes']) > 1
    button(app, 'Open Recover').click().run()
    assert app.session_state['page'] == 'Recover'


def test_chat_danger_still_interrupts_before_navigation(app):
    app.session_state['page'] = 'Assistant'; app.run()
    next(r for r in app.radio if r.label == 'Assistant mode').set_value('Local guide · no AI').run()
    app.chat_input[0].set_value('Open Recover, we are trapped').run()
    assert app.session_state['rr_emergency'] is True


@pytest.mark.parametrize('destination,focus', [('Insurance & Documents', 'Prepare for insurance'), ('My Recovery Plan', 'Continue my recovery')])
def test_chat_opens_explicit_recovery_focus(app, monkeypatch, destination, focus):
    import ui.assistant_page as screen
    monkeypatch.setattr(screen, 'propose', lambda *a, **kw: pytest.fail('No model needed for navigation'))
    monkeypatch.setattr(screen, 'local_proposal', lambda *a, **kw: pytest.fail('No planner needed for navigation'))
    app.session_state['rr_focus'] = 'Document damage'
    app.session_state['page'] = 'Assistant'
    app.run()
    app.chat_input[0].set_value('open ' + destination).run()
    assert app.session_state['page'] == 'Recover'
    assert app.session_state['rr_focus'] == focus
    assert not app.exception


def test_ai_profile_action_preview_then_confirm(app,monkeypatch):
    import ui.assistant_page as screen
    from services.assistant import propose
    from tests.test_assistant import Client
    monkeypatch.setenv('NEBIUS_API_KEY','test-key-not-used')
    monkeypatch.setattr(screen,'propose',lambda text,state,repo,history=(): propose(text,state,repo,Client({'answer':'Review your preferences.','action':{'kind':'update_household','members':4,'has_vehicle':False}})))
    app.session_state['page']='Assistant'; app.run()
    app.chat_input[0].set_value('We have four people and no car').run()
    assert app.session_state['household'].members==1
    button(app,'Confirm action').click().run()
    assert app.session_state['household'].members==4
    assert not app.session_state['household'].has_vehicle
    assert 'assistant_pending' not in app.session_state
    assert not app.exception
