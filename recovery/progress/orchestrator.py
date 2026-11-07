"""LangGraph orchestration through a genuine local stdio MCP tool boundary.

Graph checkpoints are not authority to write case state. Publication remains
an explicit application check against the current fingerprint and emergency epoch.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
import operator
from threading import Event, Lock
from typing import Annotated, Callable, TypedDict
from uuid import uuid4

from langgraph.graph import StateGraph, START, END
from langsmith.run_helpers import tracing_context

from .models import (ProgressInput, SpecialistResult, SignalState, ExecutionState,
                     ActionCandidate, MilestoneView, SourceMode, fingerprint)
from .mcp_client import RecoveryToolClient
from .store import DashboardSnapshot, SQLiteProgressStore

SPECIALISTS = ('housing', 'utilities', 'insurance', 'rebuild')
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix='recovery-progress')


class GraphState(TypedDict):
    results: Annotated[list[SpecialistResult], operator.add]
    actions: list[ActionCandidate]
    milestones: MilestoneView


def _failed_result(name: str, inputs: ProgressInput) -> SpecialistResult:
    return SpecialistResult(specialist=name, state=SignalState.UNKNOWN,
        headline="Couldn't update", summary='This check is unavailable. Earlier observations are historical, not a fresh result.',
        source_mode=inputs.source_mode, observed_at=None, execution_state=ExecutionState.FAILED,
        missing=['A successful check for this context'])


async def _run_graph(inputs, emit, cancel, simulation_delay, run_id):
    from .priorities import select_next_actions
    from .milestones import build_milestones
    if inputs.immediate_danger is not False:
        raise ValueError('Routine checks are paused until safety is explicitly assessed.')
    for name in (*SPECIALISTS, 'next_action'):
        emit(name, 'queued', 'Waiting for this run')
    if cancel.is_set():
        raise ValueError('Run cancelled.')
    async with RecoveryToolClient() as client:
        await client.list_tools()
        graph = StateGraph(GraphState)

        def make_node(name):
            async def node(state):
                if cancel.is_set():
                    raise ValueError('Run cancelled.')
                emit(name, 'checking', f'Calling {name} through local MCP')
                # Explicitly simulated response time, never applied to saved cases.
                if inputs.source_mode is SourceMode.SYNTHETIC and simulation_delay:
                    await asyncio.sleep(min(max(simulation_delay, 0), 2))
                try:
                    async with asyncio.timeout(15):
                        result = await client.check(name, inputs)
                except Exception:
                    result = _failed_result(name, inputs)
                if cancel.is_set():
                    emit(name, 'cancelled', 'Context changed or run cancelled')
                    raise ValueError('Run cancelled.')
                emit(name, result.execution_state.value, result.headline)
                return {'results': [result]}
            return node

        for name in SPECIALISTS:
            graph.add_node(name, make_node(name))

        async def next_action(state):
            if cancel.is_set():
                raise ValueError('Run cancelled.')
            emit('next_action', 'checking', 'Comparing needs, dependencies and available information')
            results = tuple(state['results'])
            actions = list(select_next_actions(inputs, results))
            milestones = build_milestones(inputs, results)
            emit('next_action', 'complete', 'Priorities explained; no commitments made')
            return {'actions': actions, 'milestones': milestones}

        graph.add_node('next_action', next_action)
        graph.add_edge(START, 'housing')
        for name in SPECIALISTS[1:]:
            graph.add_edge('housing', name)
        graph.add_edge(list(SPECIALISTS[1:]), 'next_action')
        graph.add_edge('next_action', END)
        compiled = graph.compile()
        with tracing_context(enabled=False):
            state = await compiled.ainvoke({'results': []}, config={'recursion_limit': 10})
    order = {name: index for index, name in enumerate(SPECIALISTS)}
    results = sorted(state['results'], key=lambda result: order[result.specialist])
    return DashboardSnapshot(run_id=run_id, context_key=inputs.context_key,
        checkpoint_id=inputs.checkpoint_id, source_mode=inputs.source_mode,
        input_fingerprint=fingerprint(inputs), created_at=datetime.now(timezone.utc),
        scenario_as_of=inputs.as_of, results=results, actions=state['actions'], milestones=state['milestones'],
        partial=any(r.execution_state is ExecutionState.FAILED for r in results))


def run_once(inputs: ProgressInput, *, event_callback: Callable[[dict], None] | None = None,
             simulation_delay: float = 0, cancel: Event | None = None, run_id: str | None = None) -> DashboardSnapshot:
    copied = ProgressInput.model_validate_json(inputs.model_dump_json())
    def emit(name, state, message):
        if event_callback:
            event_callback({'specialist': name, 'state': state, 'message': message,
                            'time': datetime.now(timezone.utc).isoformat()})
    async def bounded():
        async with asyncio.timeout(45):
            return await _run_graph(copied, emit, cancel or Event(), simulation_delay, run_id or str(uuid4()))
    return asyncio.run(bounded())


@dataclass
class RunHandle:
    run_id: str
    input_fingerprint: str
    emergency_epoch: int
    context_key: str = ''
    cancel: Event = field(default_factory=Event)
    events: list[dict] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)
    future: Future | None = None


@dataclass
class RunUpdate:
    statuses: dict[str, str]
    events: list[dict]
    done: bool
    snapshot: DashboardSnapshot | None = None
    error: str | None = None
    cancelled: bool = False


def start_run(inputs: ProgressInput, *, emergency_epoch: int = 0, simulation_delay: float = .4) -> RunHandle:
    if inputs.immediate_danger is not False:
        raise ValueError('Safety assessment required before routine checks.')
    handle = RunHandle(str(uuid4()), fingerprint(inputs), emergency_epoch, context_key=inputs.context_key)
    def record(event):
        with handle.lock:
            handle.events.append(event)
    copied = ProgressInput.model_validate_json(inputs.model_dump_json())
    handle.future = _EXECUTOR.submit(run_once, copied, event_callback=record,
        simulation_delay=simulation_delay, cancel=handle.cancel, run_id=handle.run_id)
    return handle


def poll_run(handle: RunHandle) -> RunUpdate:
    with handle.lock:
        events = list(handle.events)
    statuses = {name: 'queued' for name in (*SPECIALISTS, 'next_action')}
    for event in events:
        statuses[event['specialist']] = event['state']
    if handle.cancel.is_set():
        return RunUpdate({key: 'cancelled' for key in statuses}, events, True, cancelled=True)
    done = handle.future is not None and handle.future.done()
    if not done:
        return RunUpdate(statuses, events, False)
    try:
        return RunUpdate(statuses, events, True, snapshot=handle.future.result())
    except Exception:
        statuses = {key: ('failed' if value in {'queued', 'checking'} else value) for key, value in statuses.items()}
        return RunUpdate(statuses, events, True, error='Local recovery checks could not finish. Previous results remain historical. Try Refresh checks again.')


def cancel_run(handle: RunHandle) -> None:
    handle.cancel.set()
    if handle.future is not None:
        handle.future.cancel()


def publish_run(handle: RunHandle, inputs: ProgressInput, *, emergency_epoch: int,
                store: SQLiteProgressStore) -> DashboardSnapshot | None:
    if handle.cancel.is_set():
        raise ValueError('This check was cancelled; no results were published.')
    if (inputs.immediate_danger is not False or emergency_epoch != handle.emergency_epoch
            or fingerprint(inputs) != handle.input_fingerprint):
        raise ValueError('Recovery context changed; these stale results were not published.')
    update = poll_run(handle)
    if not update.done or update.snapshot is None:
        return None
    snapshot = update.snapshot
    previous = store.latest(snapshot.context_key)
    changes = []
    if previous and previous.run_id != snapshot.run_id and previous.source_mode == snapshot.source_mode:
        old = {item.specialist: item for item in previous.results}
        for item in snapshot.results:
            before = old.get(item.specialist)
            if before and (before.state != item.state or before.headline != item.headline):
                changes.append(f'{item.specialist.replace("_", " ").title()}: {before.headline} → {item.headline}')
    elif not previous:
        changes.append('First saved check for this household. Future changes will appear here.')
    historical = []
    failed = {item.specialist for item in snapshot.results if item.execution_state is ExecutionState.FAILED}
    if failed:
        for earlier in reversed(store.history(snapshot.context_key)):
            if earlier.source_mode != snapshot.source_mode or earlier.checkpoint_id != snapshot.checkpoint_id:
                continue
            for item in earlier.results:
                if item.specialist in failed and item.execution_state in {ExecutionState.COMPLETE, ExecutionState.NEEDS_INFORMATION}:
                    historical.append(item)
                    failed.remove(item.specialist)
            if not failed:
                break
    # Historical results retain their own timestamps and never enter ranking.
    snapshot = snapshot.model_copy(update={'changes': changes, 'historical_results': historical})
    store.save(snapshot)
    return store.latest(snapshot.context_key)
