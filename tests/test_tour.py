from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_tour_ends_when_emergency_interrupts():
    app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "tour_app.py")).run()
    app.button[0].click().run()
    next(b for b in app.button if b.label == 'Start exploring').click().run()
    assert app.session_state['tour_step'] == 0
    app.session_state['rr_emergency'] = True
    app.run()
    assert 'tour_step' not in app.session_state
    assert not app.exception


def test_steps_navigate_and_finish_without_ai(monkeypatch):
    calls = []
    def unexpected(*args, **kwargs):
        calls.append(args)
        raise AssertionError('A walkthrough must not request AI automatically')
    monkeypatch.setattr('services.assistant.propose', unexpected)
    app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "tour_app.py")).run()
    app.button[0].click().run()
    next(b for b in app.button if b.label == 'Start exploring').click().run()
    for page in ['Household', 'Protect', 'Respond', 'Recover', 'Assistant']:
        next(b for b in app.button if b.label == 'Next step').click().run()
        assert app.session_state['page'] == page
        assert not app.exception
    next(b for b in app.button if b.label == 'Finish tour').click().run()
    assert 'tour_step' not in app.session_state
    assert not calls



def test_previous_end_and_restart():
    app = AppTest.from_file(str(Path(__file__).parent / "fixtures" / "tour_app.py")).run()
    app.button[0].click().run()
    next(b for b in app.button if b.label == 'Start exploring').click().run()
    first_run = app.session_state['tour_run']
    next(b for b in app.button if b.label == 'Next step').click().run()
    next(b for b in app.button if b.label == 'Previous step').click().run()
    assert app.session_state['page'] == 'Home'
    next(b for b in app.button if b.label == 'End tour').click().run()
    assert 'tour_step' not in app.session_state
    app.button[0].click().run()
    next(b for b in app.button if b.label == 'Start exploring').click().run()
    assert app.session_state['tour_run'] != first_run
    assert app.session_state['tour_step'] == 0
    assert not app.exception
