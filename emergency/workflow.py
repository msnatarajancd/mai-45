"""Idempotent session interruption; existing M5 code performs best-effort saves."""
from collections.abc import MutableMapping

from domain.contracts import RouteResult


def begin_emergency(state: MutableMapping[str, object], decision: RouteResult,
                    *, entrypoint: str, event_id: str) -> None:
    if not decision.interrupt_routine:
        return
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError('An emergency event ID is required.')
    seen = list(state.get('rr_emergency_event_ids', []))
    if state.get('rr_last_emergency_event_id') == event_id or event_id in seen:
        return
    state['rr_emergency_event_ids'] = seen + [event_id]
    state['rr_last_emergency_event_id'] = event_id
    state['rr_emergency_epoch'] = int(state.get('rr_emergency_epoch', 0)) + 1
    state['rr_emergency'] = True
    state['rr_emergency_decision'] = decision.model_dump(mode='json')
    state['rr_emergency_entrypoint'] = entrypoint
    # Cancel optional background work without importing its framework. The
    # emergency epoch also prevents a late worker result from being published.
    progress_run = state.pop('rp_run', None)
    if progress_run is not None:
        try:
            progress_run.cancel.set()
            if progress_run.future is not None:
                progress_run.future.cancel()
        except (AttributeError, RuntimeError):
            pass
    for key in list(state):
        if (key.startswith('tour_') or key.endswith('_generated_guidance')
                or key.startswith(('rr_revision', 'rr_reviewed', 'rr_extraction'))
                or key in {'assistant_pending', 'assistant_result_notice', 'assistant_result',
                           'guidance', 'resources', 'route_result'}):
            state.pop(key, None)
    if decision.persist_danger and state.get('rr_case_id'):
        pending = list(state.get('rr_pending_danger', []))
        if state['rr_case_id'] not in pending:
            pending.append(state['rr_case_id'])
        state['rr_pending_danger'] = pending
