"""Exercise the real local MCP boundary and graph publication rules."""
import asyncio
from datetime import datetime, timezone

import pytest


def test_local_mcp_tools_are_read_only_and_return_bound_housing_result():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.mcp_client import RecoveryToolClient
    from recovery.progress.models import fingerprint

    async def exercise():
        inputs = load_scenario('rivera', 'initial')
        async with RecoveryToolClient() as client:
            tools = await client.list_tools()
            assert {t.name for t in tools} == {
                'find_temporary_housing', 'check_utility_health',
                'assess_insurance_readiness', 'assess_funding_gap', 'search_repair_providers'}
            assert all(t.annotations.read_only_hint for t in tools)
            result = await client.check('housing', inputs)
            assert result.specialist == 'housing'
            assert result.source_mode == inputs.source_mode
            assert result.items
            assert client.last_fingerprint == fingerprint(inputs)
    asyncio.run(exercise())


def test_another_mcp_client_can_select_a_named_synthetic_story():
    from recovery.progress.mcp_client import RecoveryToolClient
    async def exercise():
        async with RecoveryToolClient() as client:
            response = await client.client.call_tool('find_temporary_housing',
                {'scenario_id': 'rivera', 'checkpoint_id': 'initial'})
            assert not response.is_error
            assert response.structured_content['source_mode'] == 'synthetic'
            assert response.structured_content['result']['specialist'] == 'housing'
    asyncio.run(exercise())


def test_unsafe_input_cannot_run_mcp_specialist():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.mcp_client import RecoveryToolClient

    async def exercise():
        inputs = load_scenario('rivera').model_copy(update={'immediate_danger': True})
        async with RecoveryToolClient() as client:
            with pytest.raises(ValueError, match='paused|danger|safety'):
                await client.check('housing', inputs)
    asyncio.run(exercise())


def test_real_graph_runs_four_specialists_then_next_action_with_partial_failure():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.orchestrator import run_once
    from recovery.progress.models import ExecutionState, SignalState
    inputs = load_scenario('rivera').model_copy(update={'specialist_failures': ['utilities']})
    events = []
    result = run_once(inputs, event_callback=events.append, simulation_delay=0)
    assert {r.specialist for r in result.results} == {'housing', 'utilities', 'insurance', 'rebuild'}
    utility = next(r for r in result.results if r.specialist == 'utilities')
    assert utility.execution_state is ExecutionState.FAILED
    assert utility.state is SignalState.UNKNOWN
    assert utility.observed_at is None
    assert result.partial
    assert result.actions
    checking = [e['specialist'] for e in events if e['state'] == 'checking']
    assert checking[0] == 'housing'
    assert checking[-1] == 'next_action'


def test_store_resume_keeps_observation_dates_and_scopes_interactions(tmp_path):
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.orchestrator import run_once
    from recovery.progress.store import SQLiteProgressStore
    snapshot = run_once(load_scenario('chen'), simulation_delay=0)
    path = tmp_path / 'preview.sqlite3'
    store = SQLiteProgressStore(path)
    store.save(snapshot)
    store.save_interaction('demo:chen', 'later', 'provider-1', 'quote_received')
    resumed = SQLiteProgressStore(path)
    assert resumed.latest(snapshot.context_key) == snapshot
    assert resumed.latest('other-household') is None
    assert resumed.interactions('demo:chen', 'initial') == {}
    assert resumed.interactions('demo:chen', 'later') == {'provider-1': 'quote_received'}
    with pytest.raises(ValueError):
        store.save_interaction('saved:case', 'initial', 'provider-1', 'quote_received')


def test_cancelled_or_context_changed_run_never_publishes(tmp_path):
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.orchestrator import start_run, cancel_run, publish_run
    from recovery.progress.store import SQLiteProgressStore
    inputs = load_scenario('rivera')
    handle = start_run(inputs, emergency_epoch=2, simulation_delay=0)
    handle.future.result(timeout=30)
    store = SQLiteProgressStore(tmp_path / 'preview.sqlite3')
    with pytest.raises(ValueError, match='changed|stale'):
        publish_run(handle, load_scenario('chen'), emergency_epoch=2, store=store)
    with pytest.raises(ValueError, match='changed|stale'):
        publish_run(handle, inputs, emergency_epoch=3, store=store)
    assert store.latest(inputs.context_key) is None
    cancel_run(handle)
    with pytest.raises(ValueError, match='cancel'):
        publish_run(handle, inputs, emergency_epoch=2, store=store)


def test_successful_publication_is_idempotent(tmp_path):
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.orchestrator import start_run, publish_run
    from recovery.progress.store import SQLiteProgressStore
    inputs = load_scenario('morgan')
    handle = start_run(inputs, simulation_delay=0)
    handle.future.result(timeout=30)
    store = SQLiteProgressStore(tmp_path / 'preview.sqlite3')
    one = publish_run(handle, inputs, emergency_epoch=0, store=store)
    two = publish_run(handle, inputs, emergency_epoch=0, store=store)
    assert one.run_id == two.run_id
    assert len(store.history(inputs.context_key)) == 1


def test_partial_failure_retains_previous_observation_without_reusing_its_actions(tmp_path):
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.orchestrator import run_once, start_run, publish_run
    from recovery.progress.store import SQLiteProgressStore
    from recovery.progress.models import ExecutionState
    inputs = load_scenario('rivera')
    store = SQLiteProgressStore(tmp_path / 'preview.sqlite3')
    earlier = run_once(inputs)
    store.save(earlier)
    failed_inputs = inputs.model_copy(update={'specialist_failures': ['utilities']})
    handle = start_run(failed_inputs, simulation_delay=0)
    handle.future.result(timeout=30)
    saved = publish_run(handle, failed_inputs, emergency_epoch=0, store=store)
    previous_utility = next(r for r in earlier.results if r.specialist == 'utilities')
    assert saved.historical_results == [previous_utility]
    assert next(r for r in saved.results if r.specialist == 'utilities').execution_state is ExecutionState.FAILED
    assert not any(a.key.startswith('utilities:') for a in saved.actions)
    assert saved.historical_results[0].observed_at == previous_utility.observed_at


def test_failed_attempt_is_resumable_without_restamping_the_old_snapshot(tmp_path):
    from recovery.progress.store import SQLiteProgressStore
    path = tmp_path / 'preview.sqlite3'
    when = datetime(2026, 11, 6, 18, tzinfo=timezone.utc)
    store = SQLiteProgressStore(path)
    store.save_attempt('synthetic:rivera', 'input-version', 'failed', 'Local tools unavailable', at=when)
    resumed = SQLiteProgressStore(path)
    attempt = resumed.latest_attempt('synthetic:rivera')
    assert attempt['at'] == when and attempt['state'] == 'failed'
    assert attempt['input_fingerprint'] == 'input-version'
    assert resumed.latest_attempt('synthetic:chen') is None
    assert resumed.latest('synthetic:rivera') is None
