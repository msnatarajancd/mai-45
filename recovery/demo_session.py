"""Explicit demo selection and return state; never delete or clear saved cases."""
from dataclasses import asdict
from pathlib import Path
import os


def demo_database_path() -> Path:
    primary = Path(os.environ.get('READYRELIEF_DB_PATH', Path(__file__).resolve().parents[1] / '.local/recovery.sqlite3')).expanduser().resolve()
    return primary.with_name(primary.stem + '-journey-demo.sqlite3')


def selection_for_case(state, case_id):
    """Bind simulated labels and clock to their exact replay case."""
    if not state.get('rr_demo_active'):
        return None
    selection = state.get('rr_demo_selection')
    if (not selection or not case_id or selection.get('case_id') != str(case_id)
            or state.get('rr_case_id') != str(case_id)):
        raise ValueError('The fictional replay does not match the selected case. Leave the fictional scenario before opening another case.')
    return selection


def reset_assessment_controls(state):
    """Discard prior-case widget answers without changing any saved assessment."""
    for key in ('rr_initial_danger', 'rr_update_danger'):
        state.pop(key, None)


def enter_demo(state, selection, path):
    if state.get('rr_emergency') or state.get('rr_pending_danger'):
        raise ValueError('Resolve the current view before loading another fictional story; saved danger is not cleared.')
    if not state.get('rr_demo_active'):
        state['rr_demo_return_case'] = state.get('rr_case_id')
    _clear_view(state)
    state['rr_demo_active'] = True
    state['rr_demo_database_path'] = str(path)
    payload = asdict(selection)
    payload['case_id'] = str(selection.case_id)
    payload['as_of'] = selection.as_of.isoformat()
    state['rr_demo_selection'] = payload
    state['rr_case_id'] = str(selection.case_id)
    state['rr_focus'] = 'Continue my recovery'
    state['page'] = 'Recover'
    state['rr_journey_seen:'+str(selection.case_id)] = selection.previous_checkpoint_event_cursor
    if selection.pending_revision_json:
        state['rr_revision'] = selection.pending_revision_json
    state['rr_update_danger'] = 'Choose an assessment'
    if selection.immediate_danger:
        # The replay case already contains its persisted report. The shared
        # emergency UI supplies access and does not infer a real service outcome.
        state['rr_emergency'] = True


def leave_demo(state):
    if not state.get('rr_demo_active'):
        return
    demo_case = state.get('rr_case_id')
    original_case = state.get('rr_demo_return_case')
    pending = [value for value in state.get('rr_pending_danger', []) if value != demo_case]
    _clear_view(state)
    for key in ('rr_demo_active', 'rr_demo_database_path', 'rr_demo_selection', 'rr_demo_return_case',
                'rr_emergency_decision', 'rr_emergency_entrypoint', 'rr_route_result'):
        state.pop(key, None)
    state['rr_pending_danger'] = pending
    state['rr_emergency'] = bool(pending)
    if original_case:
        state['rr_case_id'] = original_case
    else:
        state.pop('rr_case_id', None)
    state['rr_focus'] = 'Continue my recovery'
    state['page'] = 'Recover'


def _clear_view(state):
    reset_assessment_controls(state)
    for key in list(state):
        if key.startswith(('rr_draft', 'rr_revision', 'rr_reviewed', 'rr_progress', 'rr_records_snapshot',
                           'rr_displayed_version', 'rr_extraction', 'rr_initial_preview')):
            state.pop(key, None)
    state.pop('rr_notice', None)
