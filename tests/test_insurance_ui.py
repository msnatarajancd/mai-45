"""Integrated synthetic Insurance forms; real file upload is exercised by Chromium."""
from pathlib import Path
import sqlite3
import pytest
from streamlit.testing.v1 import AppTest
from test_insurance_workspace import insurance
from test_recovery_landing import button
from test_recovery_records import saved, dump


def launch(path, case, monkeypatch):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    monkeypatch.delenv('NEBIUS_API_KEY', raising=False)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    app.session_state['page']='Recover'
    app.session_state['rr_case_id']=str(case.case_id)
    app.session_state['rr_focus']='Prepare for insurance'
    return app.run()


def stage(app, name):
    next(w for w in app.radio if w.label=='Insurance workspace stage').set_value(name).run()
    assert not app.exception


def test_profile_explicit_confirmation_persists_and_downloads_are_saved_only(insurance, monkeypatch):
    path,repo,case=insurance
    app=launch(path,case,monkeypatch)
    before=dump(path)
    next(w for w in app.text_input if w.label=='Insurer name (optional)').input('Fictional Mutual')
    button(app,'Save Insurance Details').click().run()
    assert dump(path)==before and not app.success
    next(w for w in app.checkbox if w.label=='I confirm these Insurance details').check()
    button(app,'Save Insurance Details').click().run()
    assert not app.exception and app.success
    assert repo.get_insurance_snapshot(case.case_id).workspace.profile.insurer_name=='Fictional Mutual'
    reopened=launch(path,case,monkeypatch)
    assert next(w for w in reopened.text_input if w.label=='Insurer name (optional)').value=='Fictional Mutual'
    stage(reopened,'Damage Inventory')
    assert len([w for w in reopened.button if w.label=='Edit Details'])==2
    next(w for w in reopened.button if w.label=='Edit Details').click().run()
    next(w for w in reopened.text_input if w.label=='Brand (optional)').input('Demo Brand')
    next(w for w in reopened.checkbox if w.label=='I confirm these item details').check()
    button(reopened,'Save Item Details').click().run()
    assert repo.get_insurance_snapshot(case.case_id).workspace.items[0].brand=='Demo Brand'
    stage(reopened,'Review & Download')
    assert {w.label for w in reopened.get('download_button')} >= {'Download Preparation PDF','Download Damage Inventory CSV','Download Evidence ZIP'}
    assert any('Unknown' in w.value for w in reopened.text)


def test_evidence_and_communications_are_user_reported_not_files(insurance,monkeypatch):
    path,repo,case=insurance; app=launch(path,case,monkeypatch)
    stage(app,'Evidence & Documents')
    next(w for w in app.selectbox if w.label=='Evidence type').select('Receipt')
    next(w for w in app.selectbox if w.label=='Evidence status').select('Reported available, not uploaded')
    next(w for w in app.text_area if w.label=='Evidence description').input('Paper receipt')
    next(w for w in app.checkbox if w.label=='I confirm this evidence record').check()
    button(app,'Save Evidence Record').click().run()
    next(w for w in app.text_area if w.label=='Communication summary').input('Fictional call about documentation')
    next(w for w in app.checkbox if w.label=='I confirm this user-reported communication').check()
    button(app,'Save Communication').click().run()
    snapshot=repo.get_insurance_snapshot(case.case_id)
    assert len(snapshot.workspace.evidence)==1 and snapshot.attachments==[]
    assert len(snapshot.workspace.communications)==1
    assert any('Fictional call' in w.value for w in app.text)


@pytest.mark.parametrize('failure',['stale','pending_danger','danger_failure','persisted_danger','database'])
def test_rejected_insurance_writes_never_claim_success(insurance,monkeypatch,failure):
    path,repo,case=insurance; app=launch(path,case,monkeypatch)
    next(w for w in app.text_input if w.label=='Insurer name (optional)').input('Must not save')
    next(w for w in app.checkbox if w.label=='I confirm these Insurance details').check()
    if failure=='stale':
        snapshot=repo.get_insurance_snapshot(case.case_id)
        from test_insurance_workspace import save
        save(repo,snapshot)
    elif failure in {'pending_danger','danger_failure'}:
        app.session_state['rr_pending_danger']=[str(case.case_id)]
        if failure=='danger_failure':
            def unavailable(*a,**k):raise sqlite3.OperationalError('synthetic unavailable')
            monkeypatch.setattr(type(repo),'report_immediate_danger',unavailable)
    elif failure=='persisted_danger':
        repo.report_immediate_danger(case.case_id)
    else:
        def unavailable(*a,**k):raise sqlite3.OperationalError('synthetic unavailable')
        monkeypatch.setattr(type(repo),'save_insurance_workspace',unavailable)
    before=repo.get_recovery_records(case.case_id)
    button(app,'Save Insurance Details').click().run()
    assert not app.exception and not app.success
    assert repo.get_recovery_records(case.case_id)==before
    with sqlite3.connect(path) as connection:
        row=connection.execute('SELECT workspace_json FROM recovery_insurance_workspaces').fetchone()
        assert row is None or 'Must not save' not in row[0]
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]
    if failure=='danger_failure':
        assert app.session_state['rr_pending_danger']==[str(case.case_id)]


def test_empty_case_stays_usable_without_profile_damage_or_plan(saved,monkeypatch):
    path,repo,case=saved
    app=launch(path,case,monkeypatch)
    assert any(w.label=='Insurer name (optional)' for w in app.text_input)
    assert any(w.label=='Document damage for insurance' for w in app.button)
    stage(app,'Review & Download')
    assert any(w.label=='Download Evidence ZIP' for w in app.get('download_button'))
    assert repo.get_insurance_snapshot(case.case_id).workspace.version==0


def test_pending_danger_at_actual_submit_interrupts_insurance_save(insurance,monkeypatch):
    import streamlit as st
    path,repo,case=insurance;app=launch(path,case,monkeypatch)
    next(w for w in app.text_input if w.label=='Insurer name (optional)').input('Must not save')
    next(w for w in app.checkbox if w.label=='I confirm these Insurance details').check()
    original=st.form_submit_button
    def submit(*args,**kwargs):
        result=original(*args,**kwargs)
        if result and args[0]=='Save Insurance Details':
            app.session_state['rr_pending_danger']=[str(case.case_id)]
        return result
    monkeypatch.setattr(st,'form_submit_button',submit)
    button(app,'Save Insurance Details').click().run()
    assert not app.exception and not app.success
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT count(*) FROM recovery_insurance_workspaces').fetchone()[0]==0
    assert 'Call 911' in [w.label for w in app.get('link_button')]


def test_first_insurance_entry_shows_its_workspace_header_immediately(insurance,monkeypatch):
    path,repo,case=insurance;app=launch(path,case,monkeypatch)
    button(app,'Continue my recovery').click().run()
    before=dump(path)
    button(app,'Prepare for insurance').click().run()
    assert not app.exception
    assert any(w.value=='Insurance Preparation Workspace' for w in app.title)
    assert not any(w.label=='Update My Situation' for w in app.button)
    assert any(w.label=='Insurance workspace stage' for w in app.radio)
    assert dump(path)==before
