"""Recovery Progress presentation guards and manual-refresh integration."""
from types import SimpleNamespace as NS

from ui.recovery_progress_components import (
    card_html, display_state, filtered_items, snapshot_is_current,
)


def result(**changes):
    values = dict(specialist='housing', state='GREEN', headline='A place to stay',
                  summary='Reported room availability', execution_state='COMPLETE',
                  items=[], missing=[], observed_at=None)
    values.update(changes)
    return NS(**values)


def test_failed_execution_never_displays_green_household_state():
    assert display_state(result(execution_state='FAILED')) == ('UNKNOWN', "Couldn't update")
    assert display_state(result(execution_state='NEEDS_INFORMATION')) == ('UNKNOWN', 'Needs information')
    assert display_state(result(state='RED')) == ('RED', 'Action needed')


def test_card_text_is_escaped_and_historical_state_is_explicit():
    html = card_html(result(headline='<script>bad()</script>', summary='A & B'), historical=True)
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    assert 'Historical observation' in html
    assert 'rp-state-green' not in html
    assert 'A &amp; B' in html


def test_snapshot_matches_complete_fingerprint_and_safety():
    snap = NS(input_fingerprint='abc', context_key='demo:rivera')
    assert snapshot_is_current(snap, 'abc', 'demo:rivera', False)
    assert not snapshot_is_current(snap, 'def', 'demo:rivera', False)
    assert not snapshot_is_current(snap, 'abc', 'demo:chen', False)
    assert not snapshot_is_current(snap, 'abc', 'demo:rivera', True)
    assert not snapshot_is_current(None, 'abc', 'demo:rivera', False)


def test_category_filter_keeps_unknown_and_nonmatching_items_out():
    items = [NS(category='Hotel'), NS(category='Church'), NS(category='Hotel')]
    assert filtered_items(items, 'All') == items
    assert filtered_items(items, 'Hotel') == [items[0], items[2]]
    assert filtered_items(items, 'School') == []


def test_typed_lowercase_domain_enums_keep_trafficlight_semantics():
    from recovery.progress.models import ExecutionState, SignalState
    assert display_state(result(state=SignalState.RED, execution_state=ExecutionState.COMPLETE)) == ('RED', 'Action needed')
    assert display_state(result(state=SignalState.GREEN, execution_state=ExecutionState.FAILED)) == ('UNKNOWN', "Couldn't update")


def test_context_or_epoch_change_cancels_handle_without_publishing(monkeypatch):
    import sys
    from ui.recovery_progress_page import cancel_incompatible_run
    calls = []
    monkeypatch.setitem(sys.modules, 'recovery.progress.orchestrator', NS(cancel_run=calls.append))
    handle = object()
    state = {'rp_run': handle, 'rp_run_fingerprint': 'abc', 'rp_run_epoch': 1}
    assert not cancel_incompatible_run(state, 'abc', 1, False)
    assert cancel_incompatible_run(state, 'abc', 2, False)
    assert calls == [handle]
    assert 'rp_run' not in state
    assert 'cancelled' in state['rp_last_attempt']['state']


def test_emergency_cancels_even_when_context_is_unchanged(monkeypatch):
    import sys
    from ui.recovery_progress_page import cancel_incompatible_run
    calls = []
    monkeypatch.setitem(sys.modules, 'recovery.progress.orchestrator', NS(cancel_run=calls.append))
    state = {'rp_run': 'handle', 'rp_run_fingerprint': 'abc', 'rp_run_epoch': 1}
    assert cancel_incompatible_run(state, 'abc', 1, True)
    assert calls == ['handle']


def test_page_entry_details_and_checkpoint_changes_do_not_run_checks(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from streamlit.testing.v1 import AppTest
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.models import ActionCandidate, MilestoneView, SpecialistResult, fingerprint
    from recovery.progress.store import DashboardSnapshot, SQLiteProgressStore
    import recovery.progress.orchestrator as runtime

    path = tmp_path / 'progress.sqlite3'
    monkeypatch.setenv('READYRELIEF_PROGRESS_DB_PATH', str(path))
    calls = []
    monkeypatch.setattr(runtime, 'start_run', lambda *a, **k: calls.append((a, k)))
    inputs = load_scenario('rivera', 'initial')
    snapshot = DashboardSnapshot(run_id='saved-test', context_key=inputs.context_key,
        checkpoint_id='initial', source_mode=inputs.source_mode, input_fingerprint=fingerprint(inputs),
        created_at=datetime.now(timezone.utc), scenario_as_of=inputs.as_of,
        results=[SpecialistResult(specialist=name, state='green', headline='Saved observation', summary='Fixture test observation',
                    source_mode=inputs.source_mode, observed_at=inputs.as_of) for name in ('housing','utilities','insurance','rebuild')],
        actions=[ActionCandidate(key='sample', title='Current sample action', reason='Saved facts', tier=1, destination='My Recovery Plan')],
        milestones=MilestoneView(elapsed_days=3, elapsed_label='Since the story started', insurance_range='Illustrative', recovery_range='Illustrative'))
    SQLiteProgressStore(path).save(snapshot)

    def page():
        from ui.recovery_progress_page import render
        render()
    app = AppTest.from_function(page).run()
    assert not app.exception
    assert calls == []
    assert len([x for x in app.expander if x.label.startswith('View details')]) == 4
    assert any('Current sample action' in x.value for x in app.markdown)
    app.run()  # returning/reloading the page retains saved observations
    assert calls == []
    app.selectbox(key='rp_checkpoint').select('update').run()
    assert not app.exception
    assert calls == []
    assert any('Outdated results' in x.value for x in app.warning)
    assert not any('Current sample action' in x.value for x in app.markdown)
    assert 'rr_focus' not in app.session_state
    assert 'rr_case_id' not in app.session_state


def test_saved_case_without_case_never_substitutes_synthetic_results(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('READYRELIEF_PROGRESS_DB_PATH', str(tmp_path / 'no-case.sqlite3'))
    def page():
        from ui.recovery_progress_page import render
        render()
    app = AppTest.from_function(page).run()
    app.radio(key='rp_source_mode').set_value('Saved recovery case').run()
    assert not app.exception
    assert any('No synthetic results are substituted' in item.value for item in app.info)
    assert not any(item.label == 'Refresh checks' for item in app.button)


def test_failed_new_attempt_makes_earlier_success_historical():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    snap = NS(input_fingerprint='abc', context_key='demo:rivera', created_at=now)
    failed = dict(state='failed', input_fingerprint='abc', context_key='demo:rivera', at=now + timedelta(seconds=1))
    assert not snapshot_is_current(snap, 'abc', 'demo:rivera', False, attempt=failed)
    assert snapshot_is_current(snap, 'abc', 'demo:rivera', False, attempt={**failed, 'context_key':'demo:chen'})


def test_refresh_is_explicit_nonblocking_and_changed_checkpoint_cancels(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    import recovery.progress.orchestrator as runtime
    monkeypatch.setenv('READYRELIEF_PROGRESS_DB_PATH', str(tmp_path / 'manual.sqlite3'))
    monkeypatch.setenv('READYRELIEF_DB_PATH', str(tmp_path / 'case.sqlite3'))
    from recovery.database import SQLiteRecoveryRepository
    from recovery.models import RecoveryCase, RecoveryIntake
    repo = SQLiteRecoveryRepository(tmp_path / 'case.sqlite3')
    selected_case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Flooded',
        utility_availability={}, temporary_accommodation_status='Needed', immediate_danger=False,
        household_recovery_needs=[]))
    repo.create_case(selected_case)
    started, cancelled = [], []
    handle = object()
    monkeypatch.setattr(runtime, 'start_run', lambda inputs, **kw: (started.append(inputs), handle)[1])
    monkeypatch.setattr(runtime, 'cancel_run', cancelled.append)
    monkeypatch.setattr(runtime, 'poll_run', lambda handle: NS(statuses={'housing':'checking'}, events=[{'message':'Actual test lifecycle event'}], done=False))
    def page(case_id):
        import streamlit as st
        from ui.recovery_progress_page import render
        st.session_state.setdefault('rr_case_id', case_id)
        st.session_state.setdefault('rr_focus', 'staged-focus-is-not-edited')
        render()
    app = AppTest.from_function(page, args=(str(selected_case.case_id),)).run()
    assert started == []
    app.button(key='rp_refresh').click().run()
    assert not app.exception
    assert len(started) == 1
    assert app.button(key='rp_refresh').disabled
    assert any('Actual test lifecycle event' in x.value for x in app.caption)
    app.run()
    assert len(started) == 1
    app.selectbox(key='rp_checkpoint').select('later').run()
    assert not app.exception
    assert cancelled == [handle]
    assert 'rp_run' not in app.session_state
    assert app.session_state['rr_case_id'] == str(selected_case.case_id)
    assert app.session_state['rr_focus'] == 'staged-focus-is-not-edited'


def test_saved_case_polling_reads_only_revision_until_changed(monkeypatch):
    from recovery.progress.fixtures import load_scenario
    from ui import recovery_progress_page as page
    import recovery.progress.case_reader as reader
    import ui.recovery_page as recovery_page
    inputs = load_scenario('rivera')
    state = {'rp_source_mode':'Saved recovery case', 'rr_case_id':'case-1'}
    monkeypatch.setattr(page.st, 'session_state', state)
    monkeypatch.setattr(recovery_page, 'repository', lambda: 'repo')
    version = ['revision-1']
    loads = []
    monkeypatch.setattr(reader, 'current_progress_revision', lambda repo, case: version[0])
    monkeypatch.setattr(reader, 'load_saved_input', lambda repo, case: (loads.append(case), inputs)[1])
    assert page._load_current_inputs(None) is inputs
    assert page._load_current_inputs(None) is inputs
    assert loads == ['case-1']
    version[0] = 'revision-2'
    page._load_current_inputs(None)
    assert loads == ['case-1', 'case-1']
    page._load_current_inputs(None, force=True)
    assert loads == ['case-1', 'case-1', 'case-1']


def test_overview_utility_tiles_and_insurance_substatuses_keep_named_signals():
    from ui.recovery_progress_components import card_facts_html
    utility = result(specialist='utilities', items=[NS(id='electricity', title='Electricity', state='red', summary='Interruption', fields={}), NS(id='water', title='Water', state='yellow', summary='Potability unknown', fields={}), NS(id='gas', title='Gas', state='not_applicable', summary='Not used', fields={})])
    html = card_facts_html(utility)
    assert 'Electricity' in html and 'Water' in html and 'Gas' in html
    assert 'rp-state-red' in html and 'Not applicable' in html
    historical = card_facts_html(utility, historical=True)
    assert 'rp-state-red' not in historical
    insurance = result(specialist='insurance', items=[NS(id='preparation', title='Preparation', state='green', summary='Prepared, not approved', fields={}), NS(id='funding', title='Funding for the next stage', state='red', summary='Funding gap', fields={})])
    html = card_facts_html(insurance)
    assert 'Preparation' in html and 'Funding for the next stage' in html
    assert 'Prepared, not approved' in html and 'Funding gap' in html


def test_failed_card_exposes_old_observation_separately_without_old_actions(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from streamlit.testing.v1 import AppTest
    from recovery.progress.models import MilestoneView, SpecialistResult
    now = datetime.now(timezone.utc)
    old = SpecialistResult(specialist='housing', state='green', headline='Earlier suitable capacity', summary='Earlier observation only', source_mode='synthetic', observed_at=now - timedelta(days=1))
    failed = SpecialistResult(specialist='housing', state='unknown', execution_state='failed', headline="Couldn't update", summary='Latest attempt failed', source_mode='synthetic', observed_at=now)
    snapshot = NS(source_mode='synthetic', milestones=MilestoneView(elapsed_days=None, elapsed_label='Start date unknown', insurance_range='Not enough information', recovery_range='Not enough information'), changes=[], actions=[], results=[failed], partial=True, historical_results=[old])
    def page(snapshot):
        from ui.recovery_progress_components import render_dashboard
        render_dashboard(snapshot)
    app = AppTest.from_function(page, args=(snapshot,)).run()
    assert not app.exception
    assert any(e.label == 'Earlier successful observation — outdated' for e in app.expander)
    assert any('Earlier observation only' in x.value for x in app.markdown)
    assert any('Historical observation' in x.value for x in app.markdown)
    assert any("Couldn't update" in x.value for x in app.markdown)
    assert any('No new observation' in x.value for x in app.caption)
    from ui.recovery_progress_components import timestamp
    assert not any('Observed: ' + timestamp(now) in x.value for x in app.caption)
    assert any('Observed: ' + timestamp(old.observed_at) in x.value for x in app.caption)
    assert not any(item.label == 'Open next step →' for item in app.button)


def test_failed_attempt_survives_browser_session_reload(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from streamlit.testing.v1 import AppTest
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.models import ActionCandidate, MilestoneView, SpecialistResult, fingerprint
    from recovery.progress.store import DashboardSnapshot, SQLiteProgressStore
    path = tmp_path / 'persisted-failure.sqlite3'
    monkeypatch.setenv('READYRELIEF_PROGRESS_DB_PATH', str(path))
    inputs = load_scenario('rivera')
    store = SQLiteProgressStore(path)
    snapshot = DashboardSnapshot(run_id='before-failure', context_key=inputs.context_key,
        source_mode=inputs.source_mode, input_fingerprint=fingerprint(inputs), created_at=datetime.now(timezone.utc),
        scenario_as_of=inputs.as_of, results=[SpecialistResult(specialist='housing', state='green', headline='Earlier observation', summary='Earlier facts', source_mode='synthetic', observed_at=inputs.as_of)],
        actions=[ActionCandidate(key='old', title='Old action must stay hidden', reason='Old context', tier=1, destination='My Recovery Plan')],
        milestones=MilestoneView(elapsed_days=None, elapsed_label='Unknown', insurance_range='Illustrative', recovery_range='Illustrative'))
    store.save(snapshot)
    store.save_attempt(inputs.context_key, fingerprint(inputs), 'failed', 'MCP connection unavailable')
    def page():
        from ui.recovery_progress_page import render
        render()
    for _ in range(2):
        app = AppTest.from_function(page).run()
        assert not app.exception
        assert any('Outdated results' in w.value for w in app.warning)
        assert any('MCP connection unavailable' in c.value for c in app.caption)
        assert not any('Old action must stay hidden' in m.value for m in app.markdown)
        assert 'rp_run' not in app.session_state
    store.save_attempt(inputs.context_key, fingerprint(inputs), 'checking', 'Started before browser closed')
    app = AppTest.from_function(page).run()
    assert not app.exception
    assert any('Interrupted' in c.value for c in app.caption)
    assert not any('Old action must stay hidden' in m.value for m in app.markdown)
    assert not app.button(key='rp_refresh').disabled


def test_start_failure_records_a_terminal_attempt_and_does_not_leave_worker(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from recovery.progress.store import SQLiteProgressStore
    import recovery.progress.orchestrator as runtime
    path = tmp_path / 'start-failure.sqlite3'
    monkeypatch.setenv('READYRELIEF_PROGRESS_DB_PATH', str(path))
    def fail(*args, **kwargs):
        raise RuntimeError('Unavailable runtime')
    monkeypatch.setattr(runtime, 'start_run', fail)
    def page():
        from ui.recovery_progress_page import render
        render()
    app = AppTest.from_function(page).run()
    app.button(key='rp_refresh').click().run()
    assert not app.exception
    assert 'rp_run' not in app.session_state
    attempt = SQLiteProgressStore(path).latest_attempt('synthetic:rivera')
    assert attempt['state'] == 'failed'


def test_housing_overview_names_one_example_per_category_including_official_shelter():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    from ui.recovery_progress_components import card_facts_html
    inputs = load_scenario('williams')
    housing = check_housing(inputs, now=inputs.as_of)
    assert len(housing.items) > len({item.category for item in housing.items})
    first_by_category = {}
    for item in housing.items:
        first_by_category.setdefault(item.category, item)
    assert set(first_by_category) == {'hotel', 'church', 'school', 'official shelter'}
    html = card_facts_html(housing)
    for category, item in first_by_category.items():
        assert category.title() in html
        assert item.title in html
        assert item.fields['Capacity unit'] in html
        assert item.fields['Units required'] in html
    assert html.count('rp-housing-row') == 4
    for item in housing.items:
        if item is not first_by_category[item.category]:
            assert item.title not in html
