from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH',str(tmp_path/'dock.sqlite3'))
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()

def button(a,label): return next(b for b in a.button if b.label==label)

def test_dock_expand_minimize_preserves_conversation(app):
    button(app,'Ask ReadyRelief').click().run()
    assert app.session_state['chat_open']
    assert app.session_state['page']=='Home'
    next(r for r in app.radio if r.label=='Assistant mode').set_value('Local guide · no AI').run()
    app.chat_input[0].set_value('open Recover').run()
    assert app.session_state['page']=='Recover'
    assert 'assistant_pending' not in app.session_state
    assert not app.session_state['chat_open']
    messages=[message.copy() for message in app.session_state['assistant_messages']]
    assert [(message['role'],message['content']) for message in messages]==[
        ('user','open Recover'),('assistant','Opened Recover.')]
    button(app,'Ask ReadyRelief').click().run()
    assert app.session_state['assistant_messages']==messages
    button(app,'Expand chat').click().run()
    assert app.session_state['page']=='Assistant'
    assert app.session_state['assistant_messages']==messages
    assert 'assistant_pending' not in app.session_state
    button(app,'Minimize chat').click().run()
    assert app.session_state['page']=='Recover'
    assert app.session_state['chat_open']
    assert app.session_state['assistant_messages']==messages
    assert 'assistant_pending' not in app.session_state
    button(app,'Close chat').click().run()
    assert not app.session_state['chat_open']
    assert app.session_state['assistant_messages']==messages
    button(app,'Ask ReadyRelief').click().run()
    assert next(r for r in app.radio if r.label=='Assistant mode').value=='Local guide · no AI'
    assert not app.exception
    assert app.session_state['assistant_messages']==messages
    assert 'assistant_pending' not in app.session_state

def test_dark_theme_preserves_household_and_emergency_access(app):
    button(app,'Switch to dark mode').click().run()
    assert app.session_state['appearance']=='Dark'
    assert app.session_state['household'].members==1
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert not app.exception

def test_search_is_in_main_toolbar(app):
    assert not any(t.label=='Search menu' for t in app.sidebar.text_input)
    next(t for t in app.text_input if t.label=='Search menu').input('tasks').run()
    assert 'Recover' in [b.label for b in app.button]
    assert not app.exception


def test_top_walkthrough_and_mobile_menu_keep_navigation_available(app):
    button(app,'Start walkthrough').click().run()
    assert app.session_state['tour_step']==0
    button(app,'Immediate danger').click().run()
    assert 'tour_step' not in app.session_state
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert not app.exception
