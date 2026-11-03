from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
import pytest
from streamlit.testing.v1 import AppTest
from test_grounded_generation import evidence, FakeClient
from services import generation

APP=str(Path(__file__).resolve().parents[1]/'app.py')
def button(a,label):return next(b for b in a.button if b.label==label)
@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH',str(tmp_path/'ui.sqlite3'))
    return AppTest.from_file(APP,default_timeout=20).run()

@pytest.mark.parametrize('page',['Protect','Respond','Recover','Assistant'])
def test_guidance_available_on_journey_without_automatic_calls(app,page,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('No automatic generation')
    monkeypatch.setattr(generation,'explain',forbidden)
    app.session_state['page']=page;app.run()
    assert not app.exception
    assert 'Generate cited explanation' in [b.label for b in app.button]
    assert 'Call 911' in [b.label for b in app.get('link_button')]

def test_partial_cited_generation_rerender_and_revocation(app,monkeypatch,evidence):
    monkeypatch.setattr(generation.knowledge,'retrieve_guidance',lambda *a,**k:evidence)
    original=generation.explain
    client=FakeClient()
    monkeypatch.setattr(generation,'explain',lambda *a,**k:original(*a,**k,client=client))
    app.session_state['page']='Recover';app.run()
    next(s for s in app.selectbox if s.label=='Evidence hazard').select('flood').run()
    button(app,'Generate cited explanation').click().run()
    assert not app.exception
    assert len(client.calls)==2
    assert any('Partial evidence' in w.value for w in app.warning)
    assert any('synthetic-citation' in c.value for c in app.caption)
    assert 'rr_case_id' not in app.session_state
    app.run(); assert len(client.calls)==2
    from domain.contracts import GuidanceResult
    monkeypatch.setattr(generation.knowledge,'retrieve_guidance',lambda *a,**k:GuidanceResult(answer='Revoked'))
    app.run()
    assert not any('synthetic-citation' in c.value for c in app.caption)

def test_danger_in_question_interrupts_before_generation(app,monkeypatch):
    def forbidden(*a,**k):raise AssertionError('Emergency must bypass services')
    monkeypatch.setattr(generation,'explain',forbidden)
    app.session_state['page']='Respond';app.run()
    next(t for t in app.text_input if t.label=='Question for reviewed guidance').input('We are trapped and water is rising').run()
    button(app,'Generate cited explanation').click().run()
    assert app.session_state['rr_emergency']
    assert not app.exception
    assert 'Call 911' in [b.label for b in app.get('link_button')]
    button(app,"I can't call 911").click().run()
    assert any('cannot send' in i.value for i in app.info)

def test_persisted_danger_blocks_guidance_after_return_to_app(app,monkeypatch):
    from ui import recovery_page
    case=SimpleNamespace(intake=SimpleNamespace(immediate_danger=True))
    monkeypatch.setattr(recovery_page,'repository',lambda:SimpleNamespace(get_case=lambda _:case))
    app.session_state['rr_case_id']=str(uuid4())
    app.session_state['rr_emergency']=False
    app.session_state['rr_pending_danger']=[]
    app.session_state['page']='Respond';app.run()
    assert not app.exception
    assert 'Generate cited explanation' not in [b.label for b in app.button]
    assert 'Call 911' in [b.label for b in app.get('link_button')]
