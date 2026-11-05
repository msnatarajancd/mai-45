"""Simulated M1 5a6391d DTOs; never call Qwen or enable extraction."""
import sqlite3
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from streamlit.testing.v1 import AppTest

from recovery.database import SQLiteRecoveryRepository
from recovery.extraction_consumer import (confirmed_context, context_fingerprint, prepare_review,
    selected_changes, accept_review, revision_for_selection)
from recovery.models import RecoveryRecords, HouseholdRecoveryDetails, RecoveryCase
from test_recovery_records import saved, inventory, dump

NEW = 'Our apartment flooded in Miami-Dade. We have two children, no electricity, and nowhere to stay tonight. Our furniture is damaged and I need insurance help.'
RETURNING = 'Electricity came back, but our refrigerator is damaged.'


def wire(case=None, records=None, *, changes=None, damage=None, message=NEW, status='SUCCESS'):
    context = confirmed_context(case, records)
    fields = {name: dict(state='UNCHANGED' if value is not None else 'UNKNOWN', value=value, source_quote=None)
              for name, value in context.items() if name not in ('reported_damage', 'danger_reported')}
    for name, (value, quote) in (changes or {}).items():
        fields[name] = dict(state='PROPOSED', value=value, source_quote=quote)
    return dict(status=status, base_context_fingerprint=context_fingerprint(context), fields=fields,
                new_damage=[dict(state='PROPOSED', value=value, source_quote=quote) for value, quote in (damage or [])],
                clarification_questions=[], error_code=None)


def new_review():
    return prepare_review(wire(changes={'disaster_type': ('Flood', 'apartment flooded'),
        'reported_county': ('Miami-Dade', 'Miami-Dade'), 'housing_condition': ('Flooded', 'apartment flooded'),
        'children': (2, 'two children'), 'electricity': ('Unavailable', 'no electricity'),
        'temporary_accommodation': ('Needed', 'nowhere to stay tonight'),
        'insurance_preparation_requested': (True, 'I need insurance help')},
        damage=[('furniture', 'Our furniture is damaged')]), NEW)


def returning_review(repo, case):
    records = repo.get_recovery_records(case.case_id)
    return prepare_review(wire(case, records, changes={'electricity': ('Available', 'Electricity came back')},
        damage=[('refrigerator', 'our refrigerator is damaged')]), RETURNING,
        case=case, records=records, plan=repo.get_active_plan(case.case_id))


def test_context_fingerprint_matches_m1_empty_context_golden():
    assert context_fingerprint(confirmed_context()) == 'f32e38896f8b3fea3731290e2722dc4919fdf0a0216d01059a98d9b5e6a9d0c9'


def test_delivery_is_bound_to_original_case_and_record_version(saved):
    from ui.recovery_page import stage_extraction_result
    path, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    result = wire(case, records, changes={'electricity': ('Available', 'Electricity came back')})
    plan = repo.get_active_plan(case.case_id)
    state = {'rr_case_id': str(case.case_id)}
    before = dump(path)
    stage_extraction_result(state, repo, result, RETURNING, case_snapshot=case,
                            records_snapshot=records, plan_snapshot=plan)
    assert 'rr_extraction_review' in state and dump(path) == before
    state.pop('rr_extraction_review')
    other = case.model_copy(update={'case_id': uuid4()})
    repo.create_case(other)
    state['rr_case_id'] = str(other.case_id)
    with pytest.raises(ValueError, match='active case changed'):
        stage_extraction_result(state, repo, result, RETURNING, case_snapshot=case,
                                records_snapshot=records, plan_snapshot=plan)
    state['rr_case_id'] = str(case.case_id)
    # A reverted value has the same M1 DTO hash but a newer record version.
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    with pytest.raises(ValueError, match='saved information changed'):
        stage_extraction_result(state, repo, result, RETURNING, case_snapshot=case,
                                records_snapshot=records, plan_snapshot=plan)
    assert 'rr_extraction_review' not in state


def test_available_m1_contract_parity_without_calling_extractor(saved, monkeypatch):
    import subprocess
    import sys
    import types
    try:
        source = subprocess.check_output(['git', 'show', '5a6391d:services/assistant.py'],
                                         text=True, encoding='utf-8', stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        pytest.skip('optional pinned Git-object contract check unavailable in shallow checkout')
    module = types.ModuleType('m5_contract_parity')
    monkeypatch.setitem(sys.modules, module.__name__, module)
    # Load definitions in memory only. Do not invoke M1 extraction or alter its files.
    exec(compile(source, '5a6391d:services/assistant.py', 'exec'), module.__dict__)
    _, repo, case = saved
    for context in [confirmed_context(), confirmed_context(case, repo.get_recovery_records(case.case_id))]:
        dto = module.RecoveryConfirmedContext.model_validate(context)
        assert dto.model_dump(mode='json') == context
        assert module.recovery_context_fingerprint(dto) == context_fingerprint(context)
    model_result = module.RecoveryExtractionResult.model_validate(new_review().result)
    assert prepare_review(model_result, NEW).proposed == new_review().proposed


def test_new_proposal_no_writes_unknown_adults_and_explicit_safety(tmp_path):
    path = tmp_path / 'new.sqlite3'
    repo = SQLiteRecoveryRepository(path)
    before = dump(path)
    review = new_review()
    intake, records = selected_changes(review, list(review.proposed))
    assert records.household.children == 2 and records.household.adults is None
    assert records.reported_county == 'Miami-Dade'
    assert intake.immediate_danger is None
    assert review.quotes['damage:0'] == 'Our furniture is damaged'
    with pytest.raises(ValueError, match='confirmation'):
        accept_review(repo, review, list(review.proposed), safety_answer=False)
    with pytest.raises(ValueError, match='safety assessment'):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True)
    assert dump(path) == before
    case = accept_review(repo, review, list(review.proposed), explicitly_confirmed=True, safety_answer=False)
    reopened = SQLiteRecoveryRepository(path)
    saved_records = reopened.get_recovery_records(case.case_id)
    assert saved_records.household.adults is None
    assert saved_records.reported_county == 'Miami-Dade'
    assert saved_records.damage_records[0].damage_description == 'Our furniture is damaged'
    assert reopened.get_active_plan(case.case_id) is None
    after = dump(path)
    with pytest.raises(sqlite3.IntegrityError):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True, safety_answer=False)
    assert dump(path) == after


def test_returning_reassessment_atomic_preserves_history_progress_and_damage(saved):
    path, repo, case = saved
    old = inventory(repo, case)
    old.household.adults = 5
    repo.save_recovery_records(old, expected_version=0, explicitly_confirmed=True)
    records = repo.get_recovery_records(case.case_id)
    original_plan = repo.get_active_plan(case.case_id)
    review = returning_review(repo, case)
    assert review.result['fields']['adults']['state'] == 'UNCHANGED'
    before = dump(path)
    revision = revision_for_selection(review, list(review.proposed))
    assert dump(path) == before
    accept_review(repo, review, list(review.proposed), explicitly_confirmed=True,
                  safety_answer=False, approved_revision=revision)
    current = repo.get_recovery_records(case.case_id)
    assert current.household.adults == 5 and current.household.children == 2
    assert current.damage_records[0] == records.damage_records[0]
    assert [d.item_description for d in current.damage_records] == ['Furniture', 'refrigerator']
    assert repo.get_case(case.case_id).intake.utility_availability['electricity'] is True
    assert repo.get_case(case.case_id).intake.immediate_danger is False
    assert repo.get_plan(original_plan.plan_id) == original_plan
    assert repo.get_active_plan(case.case_id).proposed_tasks[:len(original_plan.proposed_tasks)] == original_plan.proposed_tasks
    assert SQLiteRecoveryRepository(path).get_recovery_records(case.case_id) == current


def test_session_five_person_default_is_never_adult_context(saved):
    from domain.contracts import Household
    _, repo, case = saved
    household = Household(members=5)
    review = returning_review(repo, case)
    assert review.result['fields']['adults']['value'] is None
    assert household.members == 5


def test_selected_edits_and_damage_duplicate_protection(saved):
    _, repo, case = saved
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    records = repo.get_recovery_records(case.case_id)
    result = wire(case, records, changes={'children': (2, 'two children')},
        damage=[('Furniture', 'Our furniture is damaged'), ('furniture', 'Our furniture is damaged')])
    review = prepare_review(result, NEW, case=case, records=records)
    accept_review(repo, review, list(review.proposed), corrections={'children': 3}, explicitly_confirmed=True)
    current = repo.get_recovery_records(case.case_id)
    assert len(current.damage_records) == 1 and current.household.children == 3
    with pytest.raises(ValueError, match='stale'):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True)


@pytest.mark.parametrize('mutation', ['records', 'case', 'fingerprint'])
def test_stale_reviews_rejected(saved, mutation):
    path, repo, case = saved
    review = returning_review(repo, case)
    if mutation == 'records':
        repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    elif mutation == 'case':
        repo.report_immediate_danger(case.case_id)
    else:
        review.result['base_context_fingerprint'] = '0' * 64
    before = dump(path)
    with pytest.raises(ValueError, match='stale|unavailable|interrupted'):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True)
    assert dump(path) == before


def test_unsupported_values_remain_unresolved_not_guessed():
    message = 'We are in Broward. Power is back.'
    review = prepare_review(wire(changes={'reported_county': ('Broward', 'Broward'),
        'electricity': ('Safe', 'Power is back')}), message)
    assert set(review.unresolved) == {'reported_county', 'electricity'}
    assert not review.proposed
    with pytest.raises(ValueError, match='resolved'):
        selected_changes(review, ['electricity'])


@pytest.mark.parametrize('status,code', [('UNAVAILABLE', 'timeout'), ('ERROR', 'invalid_model_output')])
def test_failure_status_no_writes(saved, status, code):
    path, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    result = wire(case, records, status=status)
    result['error_code'] = code
    review = prepare_review(result, NEW, case=case, records=records)
    before = dump(path)
    with pytest.raises(ValueError, match='unavailable'):
        accept_review(repo, review, [], explicitly_confirmed=True)
    assert dump(path) == before


@pytest.mark.parametrize('danger', [True, None])
def test_persisted_safety_never_cleared(saved, danger):
    path, repo, case = saved
    if danger is True:
        repo.report_immediate_danger(case.case_id)
    else:
        case.intake.immediate_danger = None
        with sqlite3.connect(path) as connection:
            connection.execute('UPDATE recovery_cases SET case_json = ?', (case.model_dump_json(),))
    current = repo.get_case(case.case_id)
    review = returning_review(repo, current)
    before = dump(path)
    with pytest.raises(ValueError):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True, safety_answer=False)
    assert dump(path) == before


def test_explicit_danger_cannot_be_smuggled_through_successful_result():
    review = prepare_review(wire(), "I'm in danger")
    assert review.result['status'] == 'DANGER_DETECTED' and not review.proposed


def test_records_checked_within_same_revision_transaction_and_rollback(saved):
    path, repo, case = saved
    review = returning_review(repo, case)
    revision = revision_for_selection(review, list(review.proposed))
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_accept BEFORE UPDATE ON recovery_cases BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    before = dump(path)
    with pytest.raises(sqlite3.Error):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True,
                      safety_answer=False, approved_revision=revision)
    assert dump(path) == before
    with sqlite3.connect(path) as connection:
        connection.execute('DROP TRIGGER fail_accept')
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    before = dump(path)
    # Bypass the UI fingerprint deliberately: database acceptance is authoritative.
    with pytest.raises(ValueError, match='records changed'):
        repo.approve_reassessment(revision, explicitly_approved=True,
            confirmed_records=review.previous_records, expected_records_version=0)
    assert dump(path) == before


def test_case_creation_with_records_requires_confirmation_and_rolls_back(saved):
    path, repo, original = saved
    case = original.model_copy(update={'case_id': uuid4()})
    records = RecoveryRecords(case_id=case.case_id, reported_county='Miami-Dade')
    before = dump(path)
    with pytest.raises(ValueError, match='confirmation'):
        repo.create_case(case, confirmed_records=records)
    assert dump(path) == before
    records.case_id = uuid4()
    with pytest.raises(ValueError, match='belong'):
        repo.create_case(case, confirmed_records=records, explicitly_confirmed=True)
    assert dump(path) == before


def test_new_case_and_records_roll_back_together(tmp_path):
    path = tmp_path / 'atomic-new.sqlite3'
    repo = SQLiteRecoveryRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TRIGGER fail_new_records BEFORE INSERT ON recovery_records BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END")
    before = dump(path)
    review = new_review()
    with pytest.raises(sqlite3.Error):
        accept_review(repo, review, list(review.proposed), explicitly_confirmed=True, safety_answer=False)
    assert dump(path) == before


@pytest.mark.parametrize('mutation', ['danger', 'records', 'assessment'])
def test_records_save_checks_authoritative_state_after_fingerprint(saved, monkeypatch, mutation):
    path, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    review = prepare_review(wire(case, records, changes={'reported_county': ('Miami-Dade', 'Miami-Dade')}),
                            NEW, case=case, records=records)
    original = repo.save_recovery_records
    after_external_change = []
    def racing_save(*args, **kwargs):
        if mutation == 'danger':
            repo.report_immediate_danger(case.case_id)
        elif mutation == 'records':
            original(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
        else:
            changed = case.model_copy(deep=True)
            changed.intake.housing_condition = 'Synthetic later reported damage'
            with sqlite3.connect(path) as connection:
                connection.execute('UPDATE recovery_cases SET case_json = ?', (changed.model_dump_json(),))
        after_external_change.extend(dump(path))
        return original(*args, **kwargs)
    monkeypatch.setattr(repo, 'save_recovery_records', racing_save)
    with pytest.raises(ValueError, match='assessment|stale'):
        accept_review(repo, review, ['reported_county'], explicitly_confirmed=True)
    assert dump(path) == after_external_change


def test_county_old_json_and_new_confirmation_no_city_inference(saved):
    path, repo, case = saved
    old = RecoveryRecords.model_validate_json('{"case_id":"'+str(case.case_id)+'"}')
    assert old.reported_county is None
    result = wire(case, old, changes={'reported_county': ('Miami-Dade', 'Miami-Dade')})
    review = prepare_review(result, NEW, case=case, records=old)
    accept_review(repo, review, ['reported_county'], explicitly_confirmed=True)
    assert SQLiteRecoveryRepository(path).get_recovery_records(case.case_id).reported_county == 'Miami-Dade'
    assert repo.get_case(case.case_id) == case


def button(app, label):
    return next(w for w in app.button if w.label == label)


def ui(tmp_path, monkeypatch, review):
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'ui.sqlite3'))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_extraction_review'] = review.model_dump_json()
    return app.run()


def test_ui_new_review_edit_confirmation_and_cancellation(tmp_path, monkeypatch):
    review = new_review()
    app = ui(tmp_path, monkeypatch, review)
    assert not app.exception
    next(w for w in app.number_input if w.label == 'Children').set_value(3)
    button(app, 'Review selected changes').click().run()
    assert 'rr_case_id' not in app.session_state
    assert next(w for w in app.selectbox if w.label == 'Disaster type').value == 'Flood'
    assert next(w for w in app.selectbox if w.label == 'Electricity availability').value == 'Unavailable'
    button(app, 'Confirm selected changes').click().run()
    assert 'rr_case_id' not in app.session_state
    next(w for w in app.selectbox if w.label == 'Safety assessment for selected changes').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label == 'I confirm the selected changes shown above').check()
    button(app, 'Confirm selected changes').click().run()
    assert not app.exception
    repo = SQLiteRecoveryRepository(tmp_path / 'ui.sqlite3')
    records = repo.get_recovery_records(UUID(app.session_state['rr_case_id']))
    assert records.household.children == 3 and records.household.adults is None
    assert records.reported_county == 'Miami-Dade'
    assert repo.get_active_plan(records.case_id) is None
    assert 'Call 911' in [w.label for w in app.get('link_button')]


def test_reviewed_values_can_use_existing_structured_intake(tmp_path, monkeypatch):
    app = ui(tmp_path, monkeypatch, new_review())
    button(app, 'Review selected changes').click().run()
    next(w for w in app.selectbox if w.label == 'Immediate danger assessment').select('No immediate danger reported')
    button(app, 'Create draft plan').click().run()
    assert 'rr_case_id' not in app.session_state
    next(w for w in app.checkbox if w.label == 'I confirm the selected household and damage details with this intake').check()
    before_preview = dump(tmp_path / 'ui.sqlite3')
    button(app, 'Create draft plan').click().run()
    assert not app.exception
    assert 'rr_case_id' not in app.session_state
    assert dump(tmp_path / 'ui.sqlite3') == before_preview
    button(app, 'Confirm situation and create draft').click().run()
    assert not app.exception
    repo = SQLiteRecoveryRepository(tmp_path / 'ui.sqlite3')
    case_id = UUID(app.session_state['rr_case_id'])
    assert repo.get_case(case_id).intake.disaster_type == 'Flood'
    assert repo.get_recovery_records(case_id).household.children == 2
    assert len(repo.get_recovery_records(case_id).damage_records) == 1
    assert repo.get_active_plan(case_id) is None


def test_ui_reject_leaves_structured_fallback_and_no_writes(tmp_path, monkeypatch):
    app = ui(tmp_path, monkeypatch, new_review())
    path = tmp_path / 'ui.sqlite3'
    before = dump(path)
    button(app, 'Reject proposal and use structured input').click().run()
    assert not app.exception and dump(path) == before
    assert 'rr_extraction_review' not in app.session_state
    assert any(w.label == 'Create draft plan' for w in app.button)


def test_ui_unavailable_does_not_need_model(tmp_path, monkeypatch):
    from recovery.llm_client import NebiusClient
    def forbidden(*args, **kwargs):
        raise AssertionError('consumer must not call a model')
    monkeypatch.setattr(NebiusClient, 'complete', forbidden)
    result = wire(status='UNAVAILABLE')
    result['error_code'] = 'missing_key'
    app = ui(tmp_path, monkeypatch, prepare_review(result, NEW))
    assert not app.exception
    assert any('Extraction is unavailable' in w.value for w in app.warning)
    assert any(w.label == 'Create draft plan' for w in app.button)


def test_ui_returning_review_approves_existing_reassessment_path(saved, monkeypatch):
    path, repo, case = saved
    repo.save_recovery_records(inventory(repo, case), expected_version=0, explicitly_confirmed=True)
    review = returning_review(repo, case)
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(path))
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20).run()
    app.session_state['page'] = 'Recover'
    app.session_state['rr_case_id'] = str(case.case_id)
    app.session_state['rr_extraction_review'] = review.model_dump_json()
    app.run()
    before = dump(path)
    button(app, 'Review selected changes').click().run()
    assert not app.exception and dump(path) == before
    next(w for w in app.selectbox if w.label == 'Safety assessment for selected changes').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label == 'I confirm the selected changes shown above').check()
    button(app, 'Confirm selected changes').click().run()
    assert not app.exception
    assert repo.get_case(case.case_id).intake.utility_availability['electricity'] is True
    assert [d.item_description for d in repo.get_recovery_records(case.case_id).damage_records] == ['Furniture', 'refrigerator']
    assert len(repo.list_approved_plans(case.case_id)) == 2
    assert any(w.label == 'Save progress' for w in app.button)
