from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH',str(tmp_path/'dock.sqlite3'))
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15).run()

def button(a,label): return next(b for b in a.button if b.label==label)

def test_dock_expand_minimize_preserves_conversation(app,monkeypatch):
    import ui.assistant_page as screen
    from services.assistant import Proposal, capture
    def propose_household_update(text,state,repo):
        assert text == 'We have 4 people'
        return Proposal(answer='Review the proposed household update.',
                        action={'kind':'update_household','members':4},
                        snapshot=capture(state,repo),provider='Local test proposal')
    monkeypatch.setattr(screen,'local_proposal',propose_household_update)
    button(app,'Ask ReadyRelief').click().run()
    assert app.session_state['chat_open']
    assert app.session_state['page']=='Home'
    next(r for r in app.radio if r.label=='Assistant mode').set_value('Local guide · no AI').run()
    app.chat_input[0].set_value('We have 4 people').run()
    pending=app.session_state['assistant_pending']
    assert Proposal.model_validate_json(pending).action.kind=='update_household'
    assert app.session_state['household'].members==1
    button(app,'Expand chat').click().run()
    assert app.session_state['page']=='Assistant'
    assert app.session_state['assistant_pending']==pending
    button(app,'Minimize chat').click().run()
    assert app.session_state['page']=='Home'
    assert app.session_state['assistant_pending']==pending
    button(app,'Close chat').click().run()
    assert not app.session_state['chat_open']
    button(app,'Ask ReadyRelief').click().run()
    assert next(r for r in app.radio if r.label=='Assistant mode').value=='Local guide · no AI'
    assert not app.exception
    assert app.session_state['assistant_pending']==pending

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


def test_desktop_and_mobile_share_recovery_group(app):
    for key_prefix in ('nav_', 'mobile_nav_'):
        assert any(button.key == key_prefix + 'Recovery Progress' and button.label == 'Recovery Progress · Preview' for button in app.button)
        assert any(button.key == key_prefix + 'My Recovery Plan' for button in app.button)
        assert any(button.key == key_prefix + 'Insurance & Documents' for button in app.button)


@pytest.mark.parametrize('destination,focus', [('Insurance & Documents', 'Prepare for insurance'), ('My Recovery Plan', 'Continue my recovery')])
def test_search_opens_requested_recovery_focus(app, destination, focus):
    app.session_state['rr_focus'] = 'Document damage'
    next(field for field in app.text_input if field.label == 'Search menu').input('open ' + destination).run()
    button(app, 'Open ' + destination).click().run()
    assert app.session_state['page'] == 'Recover'
    assert app.session_state['rr_focus'] == focus
    assert not app.exception


def test_top_walkthrough_and_mobile_menu_keep_navigation_available(app):
    button(app,'Start walkthrough').click().run()
    assert app.session_state['tour_step']==0
    button(app,'Immediate danger').click().run()
    assert 'tour_step' not in app.session_state
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    assert not app.exception


def test_navigation_preserves_conversation_without_pending_approval(app):
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
