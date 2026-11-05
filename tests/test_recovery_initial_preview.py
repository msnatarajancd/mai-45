"""Initial confirmation must commit the household facts in its displayed summary."""
import os
import sqlite3
from uuid import UUID

import pytest

from recovery.database import SQLiteRecoveryRepository
from recovery.extraction_consumer import prepare_review
from services.assistant import extract_recovery_needs
from test_recovery_extraction import FakeClient, NEW
from test_recovery_landing import app, button


def seed_summary(app):
    review = prepare_review(extract_recovery_needs(NEW, client=FakeClient()), NEW)
    app.session_state['rr_extraction_review'] = review.model_dump_json()
    app.run()
    button(app, 'Review selected changes').click().run()
    next(w for w in app.selectbox if w.label == 'Immediate danger assessment').select('No immediate danger reported')
    next(w for w in app.checkbox if w.label == 'I confirm the selected household and damage details with this intake').check()
    button(app, 'Create draft plan').click().run()
    assert not app.exception
    assert app.session_state['rr_initial_preview']['records']['household']['children'] == 2


def assert_no_case_saved():
    with sqlite3.connect(os.environ['READYRELIEF_DB_PATH']) as connection:
        assert connection.execute('SELECT COUNT(*) FROM recovery_cases').fetchone()[0] == 0


def test_changed_extraction_corrections_require_fresh_initial_summary(app):
    seed_summary(app)
    next(w for w in app.number_input if w.label == 'Children').set_value(3)
    button(app, 'Review selected changes').click().run()
    assert not app.exception
    assert 'rr_initial_preview' not in app.session_state
    assert not any(w.label == 'Confirm situation and create draft' for w in app.button)
    assert_no_case_saved()
    next(w for w in app.checkbox if w.label == 'I confirm the selected household and damage details with this intake').check()
    button(app, 'Create draft plan').click().run()
    assert app.session_state['rr_initial_preview']['records']['household']['children'] == 3
    button(app, 'Confirm situation and create draft').click().run()
    assert not app.exception
    records = SQLiteRecoveryRepository(os.environ['READYRELIEF_DB_PATH']).get_recovery_records(UUID(app.session_state['rr_case_id']))
    assert records.household.children == 3


@pytest.mark.parametrize('change', ['removed', 'replaced'])
def test_removed_or_replaced_extraction_invalidates_initial_summary(app, change):
    seed_summary(app)
    if change == 'removed':
        button(app, 'Reject proposal and use structured input').click().run()
    else:
        replacement = prepare_review(extract_recovery_needs(NEW, client=FakeClient()), NEW)
        app.session_state['rr_extraction_review'] = replacement.model_dump_json()
        app.run()
        button(app, 'Review selected changes').click().run()
    assert not app.exception
    assert 'rr_initial_preview' not in app.session_state
    assert not any(w.label == 'Confirm situation and create draft' for w in app.button)
    assert_no_case_saved()
