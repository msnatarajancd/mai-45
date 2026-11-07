"""Manual, read-only specialist dashboard with background lifecycle polling."""
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import streamlit as st

from recovery.progress.models import ProviderInteraction, SourceMode, fingerprint
from ui.recovery_progress_components import (
    SPECIALISTS, card_html, render_dashboard, render_run_status,
    snapshot_is_current, timestamp,
)


def cancel_incompatible_run(state, current_fingerprint, epoch, unsafe, *, store=None):
    """Discard workers before any emergency rerun or changed-context rendering."""
    handle = state.get('rp_run')
    if handle is None:
        return False
    if (unsafe or current_fingerprint != state.get('rp_run_fingerprint')
            or epoch != state.get('rp_run_epoch')):
        from recovery.progress.orchestrator import cancel_run
        cancel_run(handle)
        state.pop('rp_run', None)
        context = getattr(handle, 'context_key', None) or state.get('rp_run_context')
        attempt = {'state': 'cancelled', 'at': datetime.now(timezone.utc),
                   'context_key': context, 'input_fingerprint': state.get('rp_run_fingerprint'),
                   'message': 'Inputs or safety context changed. Previous check cancelled.'}
        state['rp_last_attempt'] = attempt
        if store is not None and context:
            try:
                store.save_attempt(context, attempt['input_fingerprint'], 'cancelled', attempt['message'], at=attempt['at'])
            except Exception:
                pass  # Cancellation and recommendation suppression must still succeed.
        return True
    return False


def _record_attempt(store, context_key, input_fingerprint, state, message, *, statuses=None):
    attempt = {'context_key': context_key, 'input_fingerprint': input_fingerprint,
               'state': state, 'message': message, 'at': datetime.now(timezone.utc),
               'statuses': statuses or {}}
    st.session_state['rp_last_attempt'] = attempt
    store.save_attempt(context_key, input_fingerprint, state, message,
                       at=attempt['at'], statuses=attempt['statuses'])
    return attempt


def _latest_attempt(store, context_key, *, running):
    persisted = store.latest_attempt(context_key)
    local = st.session_state.get('rp_last_attempt')
    attempt = local if (local and local.get('context_key') == context_key
                        and (persisted is None or local['at'] >= persisted['at'])) else persisted
    if attempt and attempt['state'] == 'checking' and not running:
        attempt = {**attempt, 'state': 'interrupted',
                   'message': 'The previous attempt is unavailable in this session. Select Refresh checks to run again.'}
    return attempt


def _unsafe():
    if st.session_state.get('rr_pending_danger') or st.session_state.get('rr_emergency'):
        return True
    case_id = st.session_state.get('rr_case_id')
    if case_id:
        # A fictional story is not clearance for the selected saved household.
        # Reuse the authoritative persisted-safety check, never a session cache.
        try:
            from recovery.progress.case_reader import current_progress_revision
            from ui.recovery_page import repository
            current_progress_revision(repository(), case_id)
        except Exception:
            return True
    return False


def _apply_interactions(inputs, store):
    if inputs.source_mode != SourceMode.SYNTHETIC:
        return inputs
    overrides = store.interactions(inputs.context_key, inputs.checkpoint_id)
    interactions = {item.provider_id: item for item in inputs.interactions}
    for provider_id, state in overrides.items():
        previous = interactions.get(provider_id)
        interactions[provider_id] = (previous.model_copy(update={'state': state}) if previous
                                     else ProviderInteraction(provider_id=provider_id, state=state))
    return inputs.model_copy(update={'interactions': list(interactions.values())})


def _load_current_inputs(store, *, force=False):
    if _unsafe():
        raise ValueError('Routine checks are paused pending authoritative safety assessment.')
    if st.session_state.get('rp_source_mode', 'Synthetic stories') == 'Synthetic stories':
        from recovery.progress.fixtures import load_scenario
        inputs = load_scenario(st.session_state.get('rp_scenario', 'rivera'),
                               st.session_state.get('rp_checkpoint', 'initial'))
        return _apply_interactions(inputs, store)
    case_id = st.session_state.get('rr_case_id')
    if not case_id:
        return None
    try:
        from recovery.progress.case_reader import load_saved_input, current_progress_revision
    except ImportError:
        return None
    from ui.recovery_page import repository
    repo = repository()
    revision = current_progress_revision(repo, case_id)
    cache_key = (str(case_id), revision, datetime.now(ZoneInfo('America/New_York')).date().isoformat())
    if force or st.session_state.get('rp_saved_input_key') != cache_key:
        st.session_state['rp_saved_input'] = load_saved_input(repo, case_id)
        st.session_state['rp_saved_input_key'] = cache_key
    return st.session_state['rp_saved_input']


def _select_context():
    from recovery.progress.fixtures import list_scenarios
    left, right = st.columns([1, 2], gap='large')
    with left:
        st.radio('Dashboard source', ['Synthetic stories', 'Saved recovery case'],
                 horizontal=True, key='rp_source_mode')
    if st.session_state['rp_source_mode'] == 'Synthetic stories':
        scenarios = list_scenarios()
        by_id = {scenario.id: scenario for scenario in scenarios}
        with right:
            a, b = st.columns([1.4, 1])
            a.selectbox('Household story', list(by_id),
                        format_func=lambda key: by_id[key].label + (' · Featured' if by_id[key].featured else ''),
                        key='rp_scenario')
            scenario = by_id[st.session_state['rp_scenario']]
            # Stories share authored checkpoint IDs; choosing never runs checks.
            b.selectbox('Story checkpoint', scenario.checkpoints,
                        format_func=lambda key: {'initial': '1 · Starting point', 'update': '2 · An update', 'later': '3 · Later in recovery'}.get(key, key),
                        key='rp_checkpoint')
        st.caption(scenario.description)
    else:
        with right:
            st.caption('Uses the selected saved case and confirmed facts. Unsupported availability and timing stay unknown.')


def _poll_fragment(store):
    @st.fragment(run_every=0.5)
    def poll():
        from recovery.progress.orchestrator import poll_run, publish_run
        handle = st.session_state.get('rp_run')
        if handle is None:
            return
        epoch = st.session_state.get('rr_emergency_epoch', 0)
        try:
            inputs = _load_current_inputs(store)
            current = fingerprint(inputs) if inputs is not None else None
        except Exception:
            inputs, current = None, None
        if cancel_incompatible_run(st.session_state, current, epoch,
                                   _unsafe() or inputs is None or inputs.immediate_danger is not False, store=store):
            st.rerun()
        update = poll_run(handle)
        render_run_status(update)
        if not update.done:
            return
        message = update.error or 'Checks complete.'
        state = 'cancelled' if update.cancelled else 'failed' if update.error else 'complete'
        if not update.cancelled:
            try:
                if _unsafe():
                    cancel_incompatible_run(st.session_state, None, epoch, True, store=store)
                    st.rerun()
                snapshot = publish_run(handle, inputs, emergency_epoch=epoch, store=store)
                if snapshot is None:
                    state, message = 'failed', update.error or 'No current result was produced. Earlier observations remain historical.'
            except ValueError:
                state, message = 'cancelled', 'The case or safety context changed. Results were discarded.'
            except Exception:
                state, message = 'failed', 'The checks finished, but the result could not be saved. Try Refresh checks again.'
        try:
            _record_attempt(store, inputs.context_key, current, state, message, statuses=update.statuses)
        except Exception:
            st.session_state['rp_last_attempt']['message'] += ' The attempt summary could not be saved.'
        st.session_state.pop('rp_run', None)
        st.rerun()
    poll()


def _empty_dashboard(*, synthetic=True):
    st.markdown('<div class="rp-empty-intro"><div class="rp-overline">A CLEARER PICTURE, ONE STEP AT A TIME</div>'
                '<h2>Your next chapter starts with a check.</h2><p>Refresh to bring four specialist views together. '
                + ('Your selected story stays at the same checkpoint until you choose another.' if synthetic else 'Saved facts stay unknown where no observation is connected.') + '</p></div>', unsafe_allow_html=True)
    names = list(SPECIALISTS)
    for row in (names[:2], names[2:]):
        for column, name in zip(st.columns(2, gap='medium'), row):
            with column:
                st.markdown(card_html(SimpleNamespace(specialist=name, state='unknown',
                            execution_state='needs_information', items=[], headline='Ready when you are',
                            summary='No saved checks for this context yet. Select Refresh checks to begin.')), unsafe_allow_html=True)


def render():
    # The application has already rendered global emergency controls.
    epoch = st.session_state.get('rr_emergency_epoch', 0)
    if _unsafe():
        cancel_incompatible_run(st.session_state, None, epoch, True)
    from ui.recovery_page import guard_pending_danger
    guard_pending_danger()
    if _unsafe():
        st.warning('Routine checks are paused because the selected case reports danger or its safety assessment could not be verified. '
                   'Use the emergency controls if help is needed. Synthetic stories do not clear saved danger.')
        return
    with st.container(key='recovery_progress_workspace'):
        st.markdown('<div class="rp-overline">RECOVER / PROGRESS PREVIEW</div><h1>Your recovery, coming into view.</h1>'
                    '<p class="rp-lede">See what changed. Find your next step. Keep moving at your own pace.</p>', unsafe_allow_html=True)
        with st.expander('Choose story or saved case'):
            _select_context()
        try:
            from recovery.progress.store import SQLiteProgressStore, default_store_path
            store = SQLiteProgressStore(default_store_path())
            inputs = _load_current_inputs(store)
        except Exception:
            cancel_incompatible_run(st.session_state, None, epoch, True)
            st.error('Recovery Progress could not read the selected context. Your saved Recovery case has not been changed.')
            return
        if inputs is None:
            cancel_incompatible_run(st.session_state, None, epoch, False)
            st.info('Select or create a saved case in Recover to view its progress. No synthetic results are substituted for a saved case.')
            if st.button('Open Recover', key='rp_open_recover'):
                from ui.components import navigate
                navigate('Recover')
                st.rerun()
            return
        unsafe = inputs.immediate_danger is not False or _unsafe()
        current_fingerprint = fingerprint(inputs)
        cancel_incompatible_run(st.session_state, current_fingerprint, epoch, unsafe, store=store)
        synthetic = inputs.source_mode == SourceMode.SYNTHETIC
        source = 'SYNTHETIC STORY' if synthetic else 'SAVED CASE · USER-REPORTED FACTS'
        import html
        household_context = f'{inputs.household.total} people' if inputs.household.total is not None else 'Household size unconfirmed'
        if inputs.household.county:
            household_context += ' · ' + inputs.household.county
        if not synthetic and inputs.household.address:
            household_context += ' · Address saved, hidden'
        st.markdown(f'<div class="rp-context"><span class="rp-source-badge">{source}</span>'
                    f'<strong>{html.escape(inputs.household.label)}</strong><span>{html.escape(household_context)}</span><span>Source as of {html.escape(timestamp(inputs.as_of))}</span></div>', unsafe_allow_html=True)
        st.caption('Fictional people, capacities, providers, prices and timing. No booking, outreach or submissions.' if synthetic else 'No live provider availability is connected. Unsupported facts stay unknown.')
        if unsafe:
            st.warning('Routine checks are paused. Confirm no immediate danger in the existing Recovery assessment before continuing.')
        try:
            snapshot = store.latest(inputs.context_key)
        except Exception:
            snapshot = None
            st.warning('Saved progress could not be read. You can retry with Refresh checks.')
        a, b = st.columns([1, 3], vertical_alignment='center')
        running = st.session_state.get('rp_run') is not None
        if a.button('Refresh checks', type='primary', key='rp_refresh', disabled=running or unsafe,
                    use_container_width=True):
            from recovery.progress.orchestrator import start_run
            try:
                inputs = _load_current_inputs(store, force=True)
                current_fingerprint = fingerprint(inputs)
                if inputs.immediate_danger is not False or _unsafe():
                    st.rerun()
                _record_attempt(store, inputs.context_key, current_fingerprint, 'checking', 'Manual refresh started.')
                st.session_state['rp_run'] = start_run(inputs, emergency_epoch=epoch)
                st.session_state['rp_run_fingerprint'] = current_fingerprint
                st.session_state['rp_run_epoch'] = epoch
                st.session_state['rp_run_context'] = inputs.context_key
                st.rerun()
            except Exception:
                try:
                    _record_attempt(store, inputs.context_key, current_fingerprint, 'failed', 'Checks could not start. Select Refresh checks to retry.')
                except Exception:
                    pass
                st.error('Checks could not start. Try again; no case records were changed.')
        with b:
            note = 'Last saved run finished: ' + timestamp(snapshot.created_at) if snapshot else 'Checks run only when you select Refresh checks.'
            if synthetic:
                note += ' · Local checks with simulated response delays. Story time does not advance.'
            st.caption(note)
        if notice := st.session_state.pop('rp_interaction_notice', None):
            st.info(notice)
        if running:
            if st.button('Cancel checks', key='rp_cancel'):
                cancel_incompatible_run(st.session_state, None, epoch, True, store=store)
                st.rerun()
            _poll_fragment(store)
        attempt = _latest_attempt(store, inputs.context_key, running=running)
        if not running and attempt:
            if attempt['state'] != 'complete':
                st.caption(f'Last attempt: {attempt["state"].replace("_", " ").title()} · {timestamp(attempt["at"])} · {attempt["message"]}')
        current = snapshot_is_current(snapshot, current_fingerprint, inputs.context_key, unsafe,
                                      attempt=attempt)
        if _unsafe():
            cancel_incompatible_run(st.session_state, None, epoch, True, store=store)
            st.warning('Routine checks are paused. Saved safety changed or could not be verified; no recommendations are shown.')
            return
        if snapshot:
            render_dashboard(snapshot, historical=not current, inputs=inputs, store=store)
        else:
            _empty_dashboard(synthetic=synthetic)
        if not running and attempt and attempt.get('statuses'):
            with st.expander('Last run activity · ' + attempt['state'].title() + ' · ' + timestamp(attempt['at'])):
                render_run_status(SimpleNamespace(statuses=attempt['statuses'], events=[]))
        st.divider()
        if not synthetic and st.button('Edit household details', key='rp_edit_profile'):
            from ui.components import navigate_destination
            navigate_destination('My Recovery Plan')
            st.rerun()
        left, right = st.columns(2)
        if left.button('My Recovery Plan', key='rp_plan'):
            from ui.components import navigate_destination
            navigate_destination('My Recovery Plan')
            st.rerun()
        if right.button('Insurance & Documents', key='rp_documents'):
            from ui.components import navigate_destination
            navigate_destination('Insurance & Documents')
            st.rerun()
