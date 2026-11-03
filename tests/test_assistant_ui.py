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
    assert 'Protect' not in [b.label for b in app.button]
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    next(t for t in app.text_input if t.label=='Search menu').input('zzzzz').run()
    assert any('No matching' in x.value for x in app.caption)


def test_tour_navigation_and_exit(app):
    button(app,'Show me around').click().run()
    assert app.session_state['tour_step']==0
    button(app,'Next step').click().run()
    assert app.session_state['page']=='Household'
    assert app.session_state['tour_step']==1
    button(app,'Previous step').click().run()
    assert app.session_state['page']=='Home'
    button(app,'End tour').click().run()
    assert 'tour_step' not in app.session_state


def test_local_chat_requires_action_confirmation(app):
    app.session_state['page']='Assistant'; app.run()
    next(r for r in app.radio if r.label=='Assistant mode').set_value('Local guide · no AI').run()
    app.chat_input[0].set_value('open Recover').run()
    assert app.session_state['page']=='Assistant'
    button(app,'Confirm action').click().run()
    assert app.session_state['page']=='Recover'
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
