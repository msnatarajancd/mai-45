"""Accessible, display-only Recovery Progress components.

HTML is limited to escaped presentation. Widgets remain native Streamlit controls.
"""
from html import escape
from typing import Any

import streamlit as st

SPECIALISTS = {
    'housing': ('Temporary housing', 'A place to land', '⌂'),
    'utilities': ('Utility health checker', 'The everyday essentials', 'ϟ'),
    'insurance': ('Insurance & funding', 'Make the next step possible', '▤'),
    'rebuild': ('Rebuild my life', 'People who can help', '⚒'),
}
STATE_LABELS = {'RED': 'Action needed', 'YELLOW': 'In progress', 'GREEN': 'Condition met',
                'UNKNOWN': 'Unknown', 'NOT_APPLICABLE': 'Not applicable'}
EXECUTION_LABELS = {'QUEUED': 'Queued', 'CHECKING': 'Checking', 'COMPLETE': 'Complete',
                    'NEEDS_INFORMATION': 'Needs information', 'FAILED': "Couldn't update",
                    'CANCELLED': 'Cancelled'}


def value(item: Any) -> str:
    return str(getattr(item, 'value', item))


def esc(item: Any) -> str:
    return escape(str(item))


def display_state(result: Any) -> tuple[str, str]:
    execution = value(result.execution_state).upper()
    if execution in ('FAILED', 'CANCELLED', 'QUEUED', 'CHECKING', 'NEEDS_INFORMATION'):
        return 'UNKNOWN', EXECUTION_LABELS.get(execution, execution)
    state = value(result.state).upper()
    return state, STATE_LABELS.get(state, 'Unknown')


def snapshot_is_current(snapshot: Any, input_fingerprint: str, context_key: str,
                        unsafe: bool, *, attempt: dict | None = None) -> bool:
    if (snapshot is not None and attempt and attempt.get("state") in ("checking", "failed", "cancelled", "interrupted")
            and attempt.get("context_key") == context_key
            and attempt.get("input_fingerprint") == input_fingerprint
            and attempt["at"] >= snapshot.created_at):
        return False
    return bool(snapshot is not None and not unsafe
                and snapshot.input_fingerprint == input_fingerprint
                and snapshot.context_key == context_key)


def filtered_items(items: list, category: str) -> list:
    return list(items) if category == 'All' else [i for i in items if i.category == category]


def timestamp(when: Any) -> str:
    return when.strftime('%b %d, %Y · %H:%M %Z').strip() if when else 'Unknown'


def card_html(result: Any, *, historical: bool = False) -> str:
    name, strap, icon = SPECIALISTS.get(result.specialist, (result.specialist, '', '•'))
    state, label = display_state(result)
    if historical:
        state, label = 'UNKNOWN', 'Historical observation'
    return (f'<article class="rp-card rp-state-{esc(state.lower())}" data-testid="rp-card">'
            f'<div class="rp-card-top"><span class="rp-card-icon" aria-hidden="true">{icon}</span>'
            f'<span class="rp-signal"><i aria-hidden="true"></i>{esc(label)}</span></div>'
            f'<h3>{esc(name)}</h3><div class="rp-card-strap">{esc(strap)}</div>'
            f'<h4>{esc(result.headline)}</h4><p>{esc(result.summary)}</p>'
            + card_facts_html(result, historical=historical) + '</article>')


def card_facts_html(result: Any, *, historical: bool = False) -> str:
    historical = historical or value(result.execution_state).upper() in ('FAILED', 'CANCELLED')
    if result.specialist == 'utilities':
        tiles = []
        for item in result.items:
            state = 'UNKNOWN' if historical else value(item.state).upper()
            label = 'Historical' if historical else STATE_LABELS.get(state, 'Unknown')
            tiles.append(f'<div class="rp-service-tile rp-state-{esc(state.lower())}"><strong>{esc(item.title)}</strong>'
                         f'<span><i aria-hidden="true"></i>{esc(label)}</span><small>{esc(item.summary)}</small></div>')
        return '<div class="rp-service-grid">' + ''.join(tiles) + '</div>'
    if result.specialist == 'insurance':
        rows = []
        for item in result.items:
            if item.id not in ('preparation', 'funding'):
                continue
            state = 'UNKNOWN' if historical else value(item.state).upper()
            rows.append(f'<div class="rp-fact-row rp-state-{esc(state.lower())}"><span class="rp-fact-dot" aria-hidden="true"></span>'
                        f'<div><strong>{esc(item.title)}</strong><small>{esc(item.summary)}</small></div></div>')
        return '<div class="rp-facts">' + ''.join(rows) + '</div>'
    if result.specialist == 'housing':
        rows = []
        first_by_category = {}
        for item in result.items:
            first_by_category.setdefault(item.category, item)
        for item in first_by_category.values():
            unit = item.fields.get('Capacity unit', 'units unknown')
            available = item.fields.get('Available units', 'Unknown')
            required = item.fields.get('Units required', 'Unknown')
            rows.append(f'<div class="rp-housing-row"><strong>{esc(item.category.title())} example: {esc(item.title)}</strong>'
                        f'<span>{esc(available)} {esc(unit)} listed · {esc(required)} needed</span></div>')
        return '<div class="rp-facts">' + ''.join(rows) + '</div>'
    if result.specialist == 'rebuild':
        trades = list(dict.fromkeys(item.category for item in result.items))
        return '<div class="rp-trades">' + ''.join(f'<span>{esc(trade)}</span>' for trade in trades) + '</div>'
    return ''


def render_run_status(update: Any) -> None:
    nodes = []
    for key in (*SPECIALISTS, 'next_action'):
        label = SPECIALISTS[key][0] if key in SPECIALISTS else 'Next best action'
        state = value(update.statuses.get(key, 'QUEUED')).upper()
        nodes.append(f'<div class="rp-run-node rp-exec-{esc(state.lower())}">'
                     f'<span aria-hidden="true">{"✓" if state == "COMPLETE" else "•"}</span>'
                     f'<strong>{esc(label)}</strong><small>{esc(EXECUTION_LABELS.get(state, state))}</small></div>')
    st.markdown('<div class="rp-run-strip" role="status" aria-live="polite">' + ''.join(nodes) + '</div>', unsafe_allow_html=True)
    if update.events:
        st.caption('Latest activity: ' + str(update.events[-1].get('message', 'Checking progress.')))


def render_milestones(view: Any, *, synthetic: bool, historical: bool = False) -> None:
    tracks = []
    for label, milestones in [('Home & daily life', view.home), ('Costs & funding', view.funding)]:
        dots = ''.join(f'<li class="rp-milestone rp-state-{esc("unknown" if historical else value(m.state).lower())}">'
                       f'<span class="rp-milestone-dot" aria-hidden="true"></span><div><strong>{esc(m.title)}</strong>'
                       f'<small>{esc(m.detail)}</small><span class="rp-milestone-state">{esc("Historical" if historical else STATE_LABELS.get(value(m.state).upper(), "Unknown"))}</span></div></li>'
                       for m in milestones)
        tracks.append(f'<section class="rp-track"><h3>{esc(label)}</h3><ol>{dots}</ol></section>')
    st.markdown('<section class="rp-journey rp-journey-tracks">' + ''.join(tracks) + '</section>', unsafe_allow_html=True)
    with st.expander('Timing & assumptions'):
        label = 'Illustrative synthetic ranges' if synthetic else 'Timing estimates'
        st.write(f'**{label}**')
        st.write(f'Insurance: {view.insurance_range}')
        st.write(f'Recovery: {view.recovery_range}')
        if synthetic:
            st.caption('Authored story ranges for demonstration. These are not forecasts or promises of payment, approval or return home.')
        for assumption in view.assumptions:
            st.write('• ' + assumption)


def _navigate_action(destination: str, action_key: str = "") -> None:
    if destination == 'Recovery Progress':
        specialist = action_key.split(':', 1)[0]
        if specialist in SPECIALISTS:
            st.session_state['rp_focus_specialist'] = specialist
        st.rerun()
    from ui.components import navigate_destination
    navigate_destination(destination)
    st.rerun()


def render_actions(actions: list, *, partial: bool = False) -> None:
    if not actions:
        st.info('No next action is available from these checks. Review the details for missing information.')
        return
    first = actions[0]
    st.markdown('<section class="rp-next-action"><div class="rp-overline">ONE MANAGEABLE NEXT STEP</div>'
                f'<h2>{esc(first.title)}</h2><p>{esc(first.reason)}</p>'
                + (f'<div class="rp-dependency">Depends on: {esc(" · ".join(getattr(first, "dependencies", [])))}</div>'
                   if getattr(first, 'dependencies', []) else '') + '</section>', unsafe_allow_html=True)
    if partial:
        st.caption('Partial recommendation: one or more specialist checks could not be completed. Review the missing information before acting.')
    if st.button('Open next step →', key='rp_next_action', type='primary'):
        _navigate_action(first.destination, first.key)
    if len(actions) > 1:
        with st.expander('Two more things to keep in view'):
            for action in actions[1:3]:
                st.write(f'**{action.title}**')
                st.write(action.reason)
                if st.button('Open this step', key='rp_secondary_' + action.key):
                    _navigate_action(action.destination, action.key)


def render_specialist_details(result: Any, *, historical: bool = False,
                              inputs: Any = None, store: Any = None) -> None:
    state, label = display_state(result)
    st.write(f'**{"Historical observation" if historical else label}** — {result.summary}')
    observation = ('No new observation' if value(result.execution_state).upper() in ('FAILED', 'CANCELLED')
                   else f'Observed: {timestamp(result.observed_at)}')
    st.caption(f'Source: {value(result.source_mode)} · {observation}')
    if historical:
        st.warning('These observations describe earlier inputs. Refresh checks before using them for this context.')
    if result.missing:
        st.write('**Information that would help**')
        for missing in result.missing:
            st.write('• ' + missing)
    categories = list(dict.fromkeys(item.category for item in result.items))
    selected = 'All'
    if len(categories) > 1:
        selected = st.selectbox('Housing category' if result.specialist == 'housing' else 'Trade' if result.specialist == 'rebuild' else 'Filter details',
                                ['All', *categories], key='rp_filter_' + result.specialist + ('_historical' if historical else ''))
    for item in filtered_items(result.items, selected):
        with st.container(border=True):
            st.write(f'**{item.title}** · {STATE_LABELS.get(value(item.state).upper(), "Unknown")}')
            st.write(item.summary)
            for key, entry in item.fields.items():
                st.write(f'**{key}:** {entry}')
            for reason in item.reasons:
                st.write('• ' + reason)
            for evidence in getattr(item, 'provenance', []):
                _render_provenance(evidence)
            if result.specialist == 'rebuild' and not historical and inputs is not None and store is not None:
                _provider_simulation(item, inputs, store)
    evidence = getattr(result, 'provenance', []) or getattr(result, 'evidence', [])
    if evidence:
        st.write('**Why this result / provenance**')
        for entry in evidence:
            _render_provenance(entry)


def _render_provenance(entry: Any) -> None:
    if hasattr(entry, 'source'):
        source_label = 'Synthetic' if value(entry.source_mode).lower() == 'synthetic' else 'User-reported saved case'
        st.caption(f'{source_label} · {entry.source} · Scope: {entry.scope} · Observed: {timestamp(entry.observed_at)}'
                   + (f' · Valid until: {timestamp(entry.valid_until)}' if entry.valid_until else ''))
    else:
        st.caption(str(entry))


def _provider_simulation(item: Any, inputs: Any, store: Any) -> None:
    if value(inputs.source_mode).upper() != 'SYNTHETIC':
        return
    # Domain exposes allowed transitions; controls cannot invent acceptance/work.
    try:
        from recovery.progress.rebuild import allowed_provider_events
    except ImportError:
        return
    current = next((entry.state for entry in inputs.interactions if entry.provider_id == item.id), None)
    events = allowed_provider_events(current)
    if not events:
        return
    st.caption('Synthetic provider interaction · stored only for this story checkpoint.')
    event = st.selectbox('Simulated update', events, format_func=lambda event: 'Simulate: ' + event.replace('_', ' '), key='rp_provider_event_' + item.id)
    if st.button('Record simulated update', key='rp_provider_record_' + item.id):
        from ui.recovery_progress_page import _unsafe
        if _unsafe():
            st.warning('Routine checks are paused; the simulated update was not saved.')
            return
        store.save_interaction(inputs.context_key, inputs.checkpoint_id, item.id, event)
        st.session_state['rp_interaction_notice'] = 'Simulated update recorded. Refresh checks to recompute this dashboard.'
        st.rerun()


def render_dashboard(snapshot: Any, *, historical: bool = False, inputs: Any = None,
                     store: Any = None) -> None:
    synthetic = value(snapshot.source_mode).upper() == 'SYNTHETIC'
    view = snapshot.milestones
    if historical:
        st.warning('Historical snapshot — these tracks and observations come from an earlier saved check. Current recommendations are hidden until you refresh successfully.')
    days = str(view.elapsed_days) if view.elapsed_days is not None else '—'
    timing_label = 'ILLUSTRATIVE SYNTHETIC RANGES' if synthetic else 'TIMING ESTIMATES'
    elapsed_text = view.elapsed_label
    if view.elapsed_days is not None:
        prefix = str(view.elapsed_days) + ' days '
        elapsed_text = ('day ' if view.elapsed_days == 1 else 'days ') + (elapsed_text[len(prefix):] if elapsed_text.startswith(prefix) else elapsed_text)
    st.markdown(f'<div class="rp-time-strip"><div><strong>{esc(days)}</strong><span>{esc(elapsed_text)}</span></div>'
                f'<div><small>{timing_label}</small><span>Insurance: {esc(view.insurance_range)} · Recovery: {esc(view.recovery_range)}</span></div></div>', unsafe_allow_html=True)
    st.subheader('What changed')
    if historical:
        st.warning('Outdated results — refresh checks to see current recommendations.')
    elif snapshot.changes:
        st.markdown('<div class="rp-changes">' + ''.join(f'<div><span aria-hidden="true">↗</span>{esc(change)}</div>' for change in snapshot.changes) + '</div>', unsafe_allow_html=True)
    else:
        st.caption('Your first saved check for this context. Future comparable checks will show what changed here.')
    if not historical:
        render_actions(snapshot.actions, partial=snapshot.partial)
    st.markdown('<div class="rp-section-title"><div class="rp-overline">FOUR CHECKS, ONE CLEARER PICTURE</div><h2>Your recovery at a glance</h2></div>', unsafe_allow_html=True)
    by_name = {r.specialist: r for r in snapshot.results}
    names = list(SPECIALISTS)
    for row in (names[:2], names[2:]):
        for column, name in zip(st.columns(2, gap='medium'), row):
            with column:
                result = by_name.get(name)
                if result is None:
                    st.info(f'{SPECIALISTS[name][0]} · No result')
                    continue
                st.markdown(card_html(result, historical=historical), unsafe_allow_html=True)
                with st.expander('View details · ' + SPECIALISTS[name][0],
                                 expanded=st.session_state.get('rp_focus_specialist') == name):
                    render_specialist_details(result, historical=historical, inputs=inputs, store=store)
                    if value(result.execution_state).upper() == 'FAILED':
                        previous = next((old for old in getattr(snapshot, 'historical_results', [])
                                         if old.specialist == name), None)
                        if previous is not None:
                            with st.expander('Earlier successful observation — outdated'):
                                render_specialist_details(previous, historical=True)
    st.subheader('Your two recovery tracks')
    render_milestones(snapshot.milestones, synthetic=synthetic, historical=historical)
    st.markdown('<div class="rp-legend"><strong>Reading the signals</strong><span><i class="rp-dot red"></i>Action needed</span><span><i class="rp-dot yellow"></i>In progress</span><span><i class="rp-dot green"></i>Condition met</span><span><i class="rp-dot gray"></i>Unknown / outdated</span><span>Not applicable is separate.</span></div>', unsafe_allow_html=True)
    st.caption('Each signal describes its named condition. It does not certify home safety, claim approval or a completed recovery.')
