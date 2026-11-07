"""Deterministic category-first recommendations over read-only projections."""
from .models import (ActionCandidate, ExecutionState, ProgressInput, SignalState,
                     SpecialistResult)

_ORDER = {'housing': 0, 'utilities': 1, 'insurance': 2, 'funding': 2, 'rebuild': 3}
_TERMINAL_USABLE = {ExecutionState.COMPLETE, ExecutionState.NEEDS_INFORMATION}
_SERVICES = {'electricity', 'water', 'gas'}
_UNRESOLVED = {SignalState.RED, SignalState.YELLOW, SignalState.UNKNOWN}


def _intent(key: str) -> str | None:
    """Known persisted planner/reassessment keys and their specialist intent.

    Deliberately avoid title guesses and broad prefix matching: a new kind of
    housing or insurance task must not silently become equivalent work.
    """
    if key in {'housing', 'housing_review', 'need:temporary housing', 'housing:confirm-accommodation'}:
        return 'housing'
    if key in {'insurance', 'need:insurance preparation', 'insurance:prepare-evidence'}:
        return 'insurance:preparation'
    if key == 'utilities':
        return 'utilities:*'
    family, _, service = key.partition(':')
    if family in {'utility', 'utilities'} and service in _SERVICES:
        return 'utilities:' + service
    return None


def _category_order(key: str) -> int:
    return _ORDER.get((_intent(key) or key).split(':', 1)[0], 4)


def _equivalent(action, task) -> bool:
    if action.task_id == task.task_id or action.key == task.key:
        return True
    action_intent, task_intent = _intent(action.key), _intent(task.key)
    return action_intent is not None and (action_intent == task_intent or
           action_intent.startswith('utilities:') and task_intent == 'utilities:*')


def _followup(action, task, inputs, result) -> ActionCandidate | None:
    """Closed review work is history, not proof that a household need is met."""
    intent = _intent(action.key)
    if intent == 'housing' and inputs.accommodation_status in {'needed', 'unknown'}:
        key, title = 'housing:reassess-accommodation', 'Reassess the current accommodation need'
        explanation = 'Current accommodation remains needed or unconfirmed. Completing an options review does not establish a suitable place to stay.'
    elif intent == 'insurance:preparation' and any(item.id == 'preparation' and item.state in _UNRESOLVED for item in result.items):
        key, title = 'insurance:follow-up-preparation', 'Review remaining preparation evidence'
        explanation = 'Preparation evidence remains missing or unconfirmed. Completing an insurer discussion does not establish evidence adequacy, approval or coverage.'
    elif intent and intent.startswith('utilities:') and any(item.id == intent.split(':')[1] and item.state in _UNRESOLVED for item in result.items):
        service = intent.split(':')[1]
        key = 'utilities:reassess-status' if task.key == 'utilities' else f'utilities:follow-up-{service}'
        title = 'Reassess continuing essential utility needs' if task.key == 'utilities' else f'Review continuing {service} needs'
        explanation = f'{service.title()} still needs confirmation or support. Completing a record/review task does not establish service restoration or drinking-water safety.'
    else:
        return None
    prior = 'completed' if task.completed else 'no longer applicable'
    return ActionCandidate(key=key, title=title, reason=f'Earlier task "{task.title}" is {prior}. {explanation} Current finding: {action.title}: {action.reason}',
                           tier=max(1, action.tier), destination='My Recovery Plan',
                           dependencies=list(action.dependencies))


def select_next_actions(inputs: ProgressInput, results: tuple[SpecialistResult, ...]) -> tuple[ActionCandidate, ...]:
    if inputs.immediate_danger is True:
        return (ActionCandidate(key='emergency:immediate-danger', title='Use emergency help now',
                                reason='Immediate danger is reported. Attend to emergency needs before routine recovery work.',
                                tier=0, destination='Emergency help'),)
    if inputs.immediate_danger is None:
        return (ActionCandidate(key='safety:confirm-danger', title='Confirm whether anyone is in immediate danger',
                                reason='Immediate safety has not been assessed. Confirm safety before prioritizing routine recovery work.',
                                tier=0, destination='My Recovery Plan'),)
    tasks = inputs.reviewed_tasks
    blocked_ids = {t.task_id for t in tasks if t.completed or not t.applicable}
    blocked_keys = {t.key for t in tasks if t.completed or not t.applicable}
    candidates, consumed = [], set()
    for result in sorted(results, key=lambda result: _ORDER[result.specialist]):
        if result.execution_state not in _TERMINAL_USABLE or result.source_mode != inputs.source_mode:
            continue
        for action in result.actions:
            equivalents = [task for task in tasks if _equivalent(action, task)]
            candidate = action.model_copy(deep=True)
            if equivalents:
                # An outstanding equivalent wins over a closed historical task.
                # A broad current utility task covers all its service findings.
                equivalents.sort(key=lambda task: (task.completed or not task.applicable,
                                  not (action.task_id == task.task_id or action.key == task.key),
                                  task.key != 'utilities', task.task_id))
                linked = equivalents[0]
                consumed.update(task.task_id for task in equivalents)
                if linked.completed or not linked.applicable:
                    # Repeating the identical work is suppressed. A distinct
                    # reassessment is possible only for a known continuing need.
                    if action.task_id == linked.task_id or action.key == linked.key:
                        continue
                    candidate = _followup(action, linked, inputs, result)
                    if candidate is None:
                        continue
                else:
                    candidate = candidate.model_copy(update={
                        'key': linked.key, 'task_id': linked.task_id, 'title': linked.title,
                        'reason': f'{linked.reason or "Existing reviewed recovery task"}. Current finding: {action.title}: {action.reason}',
                        'destination': linked.destination, 'tier': min(max(1, linked.tier), max(1, action.tier)),
                        'dependencies': list(dict.fromkeys([*linked.dependencies, *action.dependencies]))})
            # Combine service findings linked to the same broad reviewed task
            # and same follow-up key, rather than silently dropping explanations.
            existing = next((item for item in candidates if item.key == candidate.key or
                             candidate.task_id is not None and item.task_id == candidate.task_id), None)
            if existing is not None:
                existing.reason += ' Additional finding: ' + candidate.reason
                existing.tier = min(existing.tier, candidate.tier)
                existing.dependencies = list(dict.fromkeys([*existing.dependencies, *candidate.dependencies]))
            else:
                candidates.append(candidate)
    for task in tasks:
        if task.task_id in consumed or task.completed or not task.applicable:
            continue
        candidates.append(ActionCandidate(key=task.key, title=task.title, reason=task.reason or 'Existing reviewed recovery task',
                          tier=max(1, task.tier), destination=task.destination, task_id=task.task_id,
                          dependencies=task.dependencies))
    candidates.sort(key=lambda action: (max(1, action.tier), _category_order(action.key), action.key))
    selected, seen_keys, seen_tasks = [], set(), set()
    for action in candidates:
        if action.task_id in blocked_ids or action.task_id is None and action.key in blocked_keys:
            continue
        if action.key in seen_keys or action.task_id is not None and action.task_id in seen_tasks:
            continue
        seen_keys.add(action.key)
        if action.task_id is not None:
            seen_tasks.add(action.task_id)
        selected.append(action.model_copy(update={'tier': max(1, action.tier)}, deep=True))
        if len(selected) == 3:
            break
    usable = {r.specialist for r in results if r.execution_state in _TERMINAL_USABLE and r.source_mode == inputs.source_mode}
    absent = [name for name in ('housing', 'utilities', 'insurance', 'rebuild') if name not in usable]
    if absent:
        disclosure = f'Partial check: {", ".join(absent)} could not be checked; recommendation uses the remaining information.'
        selected = [a.model_copy(update={'reason': f'{a.reason} {disclosure}'}) for a in selected]
        if not selected:
            selected = [ActionCandidate(key='progress:review-missing', title='Review the information needed for recovery',
                        reason=disclosure, tier=2, destination='Recovery Progress')]
    return tuple(selected)
