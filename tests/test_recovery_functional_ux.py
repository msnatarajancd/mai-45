"""Fictional end-to-end UI navigation; no model or live resource calls."""
from uuid import UUID

import pytest
from recovery.database import SQLiteRecoveryRepository
from test_recovery_landing import app, button
from test_recovery_records import dump


@pytest.mark.parametrize('action', ['Document damage', 'Prepare for insurance'])
def test_no_case_action_explains_requirement_and_opens_entry(app, action):
    path = __import__('os').environ['READYRELIEF_DB_PATH']
    before = dump(path)
    button(app, action).click().run()
    assert not app.exception
    assert any('require a recovery case' in w.value for w in app.info)
    assert 'rr_case_id' not in app.session_state
    button(app, 'Create Recovery Case').click().run()
    entry = next(w for w in app.expander if w.label == 'Use structured intake or resume a saved case')
    assert entry.proto.expanded
    assert any(w.label == 'Create draft plan' for w in app.button)
    button(app, 'Resume Existing Case').click().run()
    assert any(w.label == 'Saved fictional case ID' for w in app.text_input)
    assert dump(path) == before


def test_browse_filters_do_not_become_household_facts(app):
    button(app, 'Find Help Now').click().run()
    assert any('Directory category filters only' in w.value and 'never saved' in w.value for w in app.caption)
    assert next(w for w in app.multiselect if w.label == 'Household recovery needs').value == []
    for label in ['Electricity availability', 'Water availability', 'Temporary accommodation']:
        assert next(w for w in app.selectbox if w.label == label).value == 'Unknown'
    assert 'rr_case_id' not in app.session_state


def test_create_damage_confirm_insurance_download_and_resume(app):
    path = __import__('os').environ['READYRELIEF_DB_PATH']
    repo = SQLiteRecoveryRepository(path)
    button(app, 'Prepare for insurance').click().run()
    assert any('No confirmed damage records are loaded' in w.value for w in app.info)
    button(app, 'Document damage for insurance').click().run()
    button(app, 'Create Recovery Case').click().run()
    next(w for w in app.selectbox if w.label == 'Immediate danger assessment').select('No immediate danger reported')
    before_preview = dump(path)
    button(app, 'Create draft plan').click().run()
    assert not app.exception
    assert 'rr_case_id' not in app.session_state
    assert dump(path) == before_preview
    button(app, 'Confirm situation and create draft').click().run()
    assert not app.exception
    case_id = UUID(app.session_state['rr_case_id'])
    original_case = repo.get_case(case_id)
    assert original_case.intake.utility_availability == {'electricity': None, 'water': None}
    assert original_case.intake.household_recovery_needs == []
    assert any(w.label == 'Item or area description' for w in app.text_input)
    button(app, 'Prepare for insurance').click().run()
    assert any('No confirmed damaged items have been recorded' in w.value for w in app.info)
    button(app, 'Document damage for insurance').click().run()
    button(app, 'Add Damaged Item').click().run()
    next(w for w in app.text_input if w.label == 'Item or area description').input('Refrigerator')
    next(w for w in app.text_area if w.label == 'User-reported damage description').input('Previously reported flood damage')
    before = dump(path)
    button(app, 'Save confirmed damage record').click().run()
    assert dump(path) == before
    assert any('Confirm the damage record first' in w.value for w in app.error)
    next(w for w in app.checkbox if w.label == 'I confirm this damage record').check()
    button(app, 'Save confirmed damage record').click().run()
    assert not app.exception
    assert len(repo.get_recovery_records(case_id).damage_records) == 1
    button(app, 'Prepare for insurance').click().run()
    assert any('Item / area: Refrigerator' in w.value and 'No insurance claim has been submitted' in w.value for w in app.text)
    download = next(w for w in app.get('download_button') if w.label == 'Download insurance discussion draft')
    assert download.proto.url
    saved = dump(path)
    app.session_state['page'] = 'Home'
    app.run()
    app.session_state['page'] = 'Recover'
    del app.session_state['rr_case_id']
    app.run()
    button(app, 'Continue my recovery').click().run()
    next(w for w in app.text_input if w.label == 'Saved fictional case ID').input(str(case_id))
    button(app, 'Resume saved case').click().run()
    button(app, 'Document damage').click().run()
    assert any('Refrigerator' in w.value for w in app.text)
    button(app, 'Prepare for insurance').click().run()
    assert any('Item / area: Refrigerator' in w.value for w in app.text)
    assert repo.get_case(case_id) == original_case
    assert dump(path) == saved
    assert 'Call 911' in [w.label for w in app.get('link_button')]
    assert "I Can't Call 911" in [w.label for w in app.button]
    assert not app.exception
