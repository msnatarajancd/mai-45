"""Fictional offline records, transactional safety and integrated UI regressions."""
import sqlite3
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from streamlit.testing.v1 import AppTest

from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.insurance import insurance_discussion_summary
from recovery.models import (DamageRecord, HouseholdRecoveryDetails, RecoveryCase,
                             RecoveryIntake, TaskStatus)


@pytest.fixture
def saved(tmp_path):
    path = tmp_path / 'records.sqlite3'
    repo = SQLiteRecoveryRepository(path)
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Apartment flooded',
        utility_availability={'electricity': False, 'water': None}, temporary_accommodation_status='No lodging arranged',
        immediate_danger=False, household_recovery_needs=['Damage documentation']))
    repo.create_case(case)
    plan = create_demo_draft_plan(case)
    repo.save_draft_plan(plan)
    repo.approve_plan(plan.plan_id)
    repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.COMPLETED)
    return path, repo, case


def inventory(repo, case):
    records = repo.get_recovery_records(case.case_id)
    records.household = HouseholdRecoveryDetails(children=2, wants_insurance_help=True)
    records.damage_records.append(DamageRecord(case_id=case.case_id, item_description='Furniture',
                                             damage_description='Reported water damage'))
    return records


def dump(path):
    with sqlite3.connect(path) as connection:
        return list(connection.iterdump())


def test_confirmed_records_edits_reopen_and_do_not_change_plan(saved):
    path, repo, case = saved
    before_case = repo.get_case(case.case_id)
    before_plan = repo.get_active_plan(case.case_id)
    records = inventory(repo, case)
    saved_records = repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    damage_id = saved_records.damage_records[0].damage_id
    saved_records.damage_records[0].notes = 'Synthetic household report'
    saved_records.damage_records[0].incident_date = date(2026, 11, 1)
    updated = repo.save_recovery_records(saved_records, expected_version=1, explicitly_confirmed=True)
    reopened = SQLiteRecoveryRepository(path)
    assert reopened.get_recovery_records(case.case_id) == updated
    assert updated.damage_records[0].damage_id == damage_id
    assert updated.household.adults is None
    assert reopened.get_case(case.case_id) == before_case
    assert reopened.get_active_plan(case.case_id) == before_plan
    assert len(reopened.list_approved_plans(case.case_id)) == 1


def test_read_and_unconfirmed_changes_do_not_write(saved):
    path, repo, case = saved
    before = dump(path)
    assert repo.get_recovery_records(case.case_id).household == HouseholdRecoveryDetails()
    proposal = inventory(repo, case)
    with pytest.raises(ValueError, match='confirmation'):
        repo.save_recovery_records(proposal, expected_version=0)
    assert dump(path) == before


def test_stale_edits_fail_without_side_effects(saved):
    path, repo, case = saved
    stale = inventory(repo, case)
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    before = dump(path)
    with pytest.raises(ValueError, match='stale'):
        repo.save_recovery_records(stale, expected_version=0, explicitly_confirmed=True)
    assert dump(path) == before


@pytest.mark.parametrize('danger', [True, None])
def test_persisted_safety_blocks_new_records_under_transaction(saved, danger):
    path, repo, case = saved
    proposal = inventory(repo, case)  # displayed before danger was persisted
    if danger:
        repo.report_immediate_danger(case.case_id)
    else:
        case.intake.immediate_danger = None
        with sqlite3.connect(path) as connection:
            connection.execute('UPDATE recovery_cases SET case_json = ?', (case.model_dump_json(),))
    before = dump(path)
    with pytest.raises(ValueError, match='assessment'):
        repo.save_recovery_records(proposal, expected_version=0, explicitly_confirmed=True)
    assert dump(path) == before
    with pytest.raises(ValueError, match='paused'):
        insurance_discussion_summary(repo.get_case(case.case_id), proposal)


@pytest.mark.parametrize('defect', ['foreign_case', 'duplicate', 'foreign_id', 'delete'])
def test_damage_identity_is_case_bound_and_preserved(saved, defect):
    path, repo, case = saved
    records = repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    if defect == 'foreign_case':
        records.damage_records[0].case_id = uuid4()
    elif defect == 'duplicate':
        records.damage_records.append(records.damage_records[0].model_copy())
    elif defect == 'delete':
        records.damage_records.clear()
    else:
        other = case.model_copy(update={'case_id': uuid4()})
        repo.create_case(other)
        foreign = repo.save_recovery_records(inventory(repo, other), expected_version=0, explicitly_confirmed=True)
        records.damage_records.append(foreign.damage_records[0].model_copy(update={'case_id': case.case_id}))
    before = dump(path)
    with pytest.raises(ValueError):
        repo.save_recovery_records(records, expected_version=1, explicitly_confirmed=True)
    assert dump(path) == before


def test_database_failure_rolls_back(saved):
    path, repo, case = saved
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_records BEFORE INSERT ON recovery_records BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    before = dump(path)
    with pytest.raises(sqlite3.Error):
        repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    assert dump(path) == before


def test_summary_only_saved_reports_unknowns_and_disclosures(saved):
    _, repo, case = saved
    unsaved = inventory(repo, case)
    before = insurance_discussion_summary(case, repo.get_recovery_records(case.case_id))
    assert 'Children: Unknown' in before
    assert 'Item / area: Furniture' not in before
    records = repo.save_recovery_records(unsaved, expected_version=0, explicitly_confirmed=True)
    summary = insurance_discussion_summary(case, records)
    assert 'Children: 2' in summary and 'Adults: Unknown' in summary
    assert 'Item / area: Furniture' in summary
    assert 'Incident date: Unknown' in summary
    assert 'electricity: Reported unavailable' in summary
    assert 'water: Unknown' in summary
    assert 'Insurance coverage has not been determined.' in summary
    assert 'No insurance claim has been submitted.' in summary
    assert 'repair costs and replacement values: Unknown' in summary
    assert 'restoration does not establish household safety' in summary
    with pytest.raises(ValueError, match='belong'):
        insurance_discussion_summary(case.model_copy(update={'case_id': uuid4()}), records)


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


def test_integrated_records_confirmation_edit_cancel_and_reopen(saved, monkeypatch):
    path, repo, case = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    app.run()
    button(app, 'Document damage').click().run()
    assert not app.exception
    next(w for w in app.text_input if w.label == 'Number of children (if known)').input('2')
    button(app, 'Save confirmed household details').click().run()
    assert repo.get_recovery_records(case.case_id).version == 0
    next(w for w in app.checkbox if w.label == 'I confirm these household details').check()
    button(app, 'Save confirmed household details').click().run()
    assert repo.get_recovery_records(case.case_id).household.children == 2
    next(w for w in app.text_input if w.label == 'Item or area description').input('Furniture')
    next(w for w in app.text_area if w.label == 'User-reported damage description').input('Wet upholstery')
    next(w for w in app.checkbox if w.label == 'I confirm this damage record').check()
    button(app, 'Save confirmed damage record').click().run()
    assert not app.exception
    record = repo.get_recovery_records(case.case_id).damage_records[0]
    next(w for w in app.selectbox if w.label == 'Add or edit a damage record').select(str(record.damage_id)).run()
    next(w for w in app.text_area if w.label == 'Optional notes').input('Confirmed synthetic note')
    next(w for w in app.checkbox if w.label == 'I confirm this damage record').check()
    button(app, 'Save confirmed damage record').click().run()
    assert repo.get_recovery_records(case.case_id).damage_records[0].notes == 'Confirmed synthetic note'
    next(w for w in app.text_input if w.label == 'Number of children (if known)').input('7')
    button(app, 'Reload saved household and damage records').click().run()
    assert next(w for w in app.text_input if w.label == 'Number of children (if known)').value == '2'
    button(app, 'Open a different case').click().run()
    next(w for w in app.text_input if w.label == 'Saved fictional case ID').input(str(case.case_id))
    button(app, 'Resume saved case').click().run()
    assert not app.exception
    assert any('Wet upholstery' in t.value for t in app.text)
    assert any('Confirmed synthetic note' in t.value for t in app.text)
    button(app, 'Prepare for insurance').click().run()
    assert any('Children: 2' in t.value and 'Adults: Unknown' in t.value for t in app.text)
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I can't call 911" in [w.label for w in app.button]


@pytest.mark.parametrize('failure', ['stale', 'danger', 'database'])
def test_integrated_rejected_save_never_claims_success(saved, monkeypatch, failure):
    path, repo, case = saved
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    app.run()
    button(app, 'Document damage').click().run()
    if failure == 'stale':
        repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    elif failure == 'danger':
        repo.report_immediate_danger(case.case_id)
    else:
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TRIGGER fail_ui BEFORE INSERT ON recovery_records BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    before = dump(path)
    next(w for w in app.text_input if w.label == 'Number of children (if known)').input('7')
    next(w for w in app.checkbox if w.label == 'I confirm these household details').check()
    button(app, 'Save confirmed household details').click().run()
    assert not app.exception
    assert dump(path) == before
    assert not any('details saved' in success.value for success in app.success)
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I can't call 911" in [w.label for w in app.button]
