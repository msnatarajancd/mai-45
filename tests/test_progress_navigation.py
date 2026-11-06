"""Isolation of the new route from staged existing Recovery work."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

from streamlit.testing.v1 import AppTest


def test_progress_entry_preserves_drafts_and_emergency_origin(tmp_path, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'recovery.sqlite3'))
    monkeypatch.setenv('READYRELIEF_PROGRESS_PREVIEW', '1')
    # Route contract does not depend on the specialist page implementation.
    import streamlit as st
    monkeypatch.setitem(sys.modules, 'ui.recovery_progress_page', SimpleNamespace(render=lambda: st.title('Recovery Progress route')))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    staged = {'rr_draft': 'staged draft', 'rr_extraction_review': {'unchanged': True},
              'rr_case_id': 'selected-case', 'rr_focus': 'Document damage'}
    for key, value in staged.items():
        app.session_state[key] = value
    next(button for button in app.sidebar.button if button.label == 'Recovery Progress · Preview').click().run()
    assert app.session_state['page'] == 'Recovery Progress'
    assert all(app.session_state[key] == value for key, value in staged.items())
    assert 'Call 911' in [button.label for button in app.get('link_button')]
    assert not app.exception
    next(button for button in app.button if button.label == 'Immediate danger').click().run()
    assert app.session_state['rr_emergency_entrypoint'] == 'recovery'


def test_disabled_direct_progress_route_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'recovery.sqlite3'))
    monkeypatch.setenv('READYRELIEF_PROGRESS_PREVIEW', 'off')
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.session_state['page'] = 'Recovery Progress'
    app.run()
    assert app.session_state['page'] == 'Recover'
    assert not any(button.label == 'Recovery Progress · Preview' for button in app.button)
    assert not app.exception


@pytest.mark.parametrize('destination,focus,expected', [
    ('Recover', 'Prepare for insurance', 'Prepare for insurance'),
    ('Insurance & Documents', None, 'Prepare for insurance'),
    ('My Recovery Plan', None, 'Continue my recovery')])
def test_focus_aware_navigation_preserves_staged_review(monkeypatch, destination, focus, expected):
    import ui.components as components
    state = {'page': 'Home', 'rr_draft': object(), 'rr_extraction_review': object()}
    before = dict(state)
    monkeypatch.setattr(components.st, 'session_state', state)
    components.navigate_destination(destination, focus)
    assert state['page'] == 'Recover'
    assert state['rr_focus'] == expected
    assert state['rr_draft'] is before['rr_draft']
    assert state['rr_extraction_review'] is before['rr_extraction_review']


def test_emergency_stops_before_progress_page_io(tmp_path, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'recovery.sqlite3'))
    monkeypatch.setenv('READYRELIEF_PROGRESS_PREVIEW', '1')
    def forbidden():
        raise AssertionError('Optional page work must not run during an emergency')
    monkeypatch.setitem(sys.modules, 'ui.recovery_progress_page', SimpleNamespace(render=forbidden))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
    app.session_state['page'] = 'Recovery Progress'
    app.session_state['rr_emergency'] = True
    app.run()
    assert not app.exception
    assert app.session_state['rr_emergency_entrypoint'] == 'recovery'
    assert 'Call 911' in [button.label for button in app.get('link_button')]


@pytest.mark.parametrize('destination,focus', [('Insurance & Documents', 'Prepare for insurance'), ('My Recovery Plan', 'Continue my recovery')])
def test_browser_suggestion_dispatch_preserves_focus(monkeypatch, destination, focus):
    import ui.search_component as component
    state = {'page': 'Recover', 'rr_focus': 'Document damage'}
    monkeypatch.setattr(component.st, 'session_state', state)
    monkeypatch.setattr(component.st, 'rerun', lambda: None)
    monkeypatch.setattr(component, '_suggestions', lambda **kwargs: SimpleNamespace(destination=destination))
    component.render_suggestions()
    assert state['page'] == 'Recover'
    assert state['rr_focus'] == focus
    assert state['_clear_nav_search']
