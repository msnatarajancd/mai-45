"""Accessible change-first presentation over the existing Recovery repository."""
from datetime import date, datetime
from html import escape
from pathlib import Path
import sqlite3

import streamlit as st

from .assessment_summary import summary_items
from .dashboard import build_dashboard


def scenario_picker():
    from .demo import list_scenarios, load_checkpoint
    from .demo_session import demo_database_path, enter_demo
    scenarios = list_scenarios()
    by_id = {s.scenario_id: s for s in scenarios}
    with st.expander('Explore six fictional recovery journeys', expanded=False, key='rr_scenario_controls:'+str(st.session_state.get('rr_case_id', 'new'))):
        st.caption('SYNTHETIC DEMO · Three first-week stories and three month-long stories. Loading creates a separate replay case; your original case is kept.')
        first, second = st.columns([2, 1])
        chosen = first.selectbox('Fictional household', list(by_id),
            format_func=lambda value: by_id[value].label, key='rr_scenario_picker')
        scenario = by_id[chosen]
        day = second.selectbox('Story checkpoint', scenario.checkpoint_days,
            format_func=lambda value: 'Day '+str(value), key='rr_checkpoint_picker:'+chosen)
        st.write(scenario.description)
        if st.button('Load fictional checkpoint', type='primary'):
            try:
                path = demo_database_path()
                path.parent.mkdir(parents=True, exist_ok=True)
                selection = load_checkpoint(path, chosen, day)
                enter_demo(st.session_state, selection, path)
                st.rerun()
            except (OSError, sqlite3.Error, ValueError):
                st.error('This fictional checkpoint could not be loaded. Your current case has not been replaced.')
        with st.form('rr_resume_replay'):
            replay_id = st.text_input('Replay case ID', placeholder='Return to an existing fictional replay')
            resume = st.form_submit_button('Resume fictional replay')
        st.caption('Loading a checkpoint starts a fresh replay. Resume by its case ID to keep your saved edits after a refresh.')
        if resume:
            from .demo import resume_checkpoint
            try:
                path = demo_database_path()
                selection = resume_checkpoint(path, replay_id.strip())
                enter_demo(st.session_state, selection, path)
                st.rerun()
            except (OSError, sqlite3.Error, ValueError):
                st.error('Enter a valid saved replay case ID from this machine. No replay was changed.')


def render_situation(intake, records):
    for label, value in summary_items(intake, records):
        st.text(label + ': ' + value)
    st.caption('These are your reported details. Utility availability and task completion do not establish home safety, insurance coverage or service outcomes.')


def _date_label(value: str) -> str:
    return datetime.fromisoformat(value).strftime('%b %d')


def _excerpt(value: str) -> str:
    return value if len(value) <= 240 else value[:237].rsplit(' ', 1)[0] + '…'


def render_overview(repo, case, plan):
    """Read and render; the only button here updates a browser-session cursor."""
    from .demo_session import selection_for_case
    selection = selection_for_case(st.session_state, case.case_id)
    records = repo.get_recovery_records(case.case_id)
    as_of = date.fromisoformat(selection['as_of']) if selection else None
    cursor_key = 'rr_journey_seen:'+str(case.case_id)
    view = build_dashboard(case, records, plan, repo.list_journey_events(case.case_id),
        as_of=as_of, since_event_id=st.session_state.get(cursor_key))
    st.markdown('<style>'+Path(__file__).with_name('dashboard.css').read_text()+'</style>', unsafe_allow_html=True)
    st.markdown('<div class="rj-kicker">YOUR RECOVERY JOURNEY</div>', unsafe_allow_html=True)
    st.title('Your recovery, one step at a time.')
    if selection:
        st.caption(f'SYNTHETIC DEMO · {selection["scenario_label"]} · Story as of {view.as_of:%B %d, %Y}. All household events are fictional.')
    else:
        st.caption('Your reported changes, the steps you have taken, and what comes next.')
    elapsed = str(view.elapsed_days) if view.elapsed_days is not None else '—'
    elapsed_label = 'days since your reported incident' if view.elapsed_days is not None else 'incident date not confirmed'
    if view.incident_date_state == 'future':
        elapsed_label = 'incident date needs review'
    if view.target_days is None:
        target, target_label = 'Your pace', 'Choose a check-in when it helps'
    elif view.target_days > 0:
        target, target_label = f'In {view.target_days} days', 'Your next check-in target'
    elif view.target_days == 0:
        target, target_label = 'Today', 'Your chosen check-in day'
    else:
        target, target_label = f'{abs(view.target_days)} days ago', 'Your check-in target passed; you can choose another'
    timing = f'<section class="rj-hero" aria-label="Recovery timing"><div><span class="rj-day">{elapsed}</span><span class="rj-day-label">{elapsed_label}</span><p>One step at a time. Your earlier work stays with you.</p></div><div class="rj-target"><span class="rj-kicker">LOOKING AHEAD</span><strong>{escape(target)}</strong><span>{escape(target_label)}</span><small>A planning target, not a recovery forecast.</small></div></section>'
    st.subheader('What changed since your last review')
    if view.first_visit:
        st.caption('First visit in this browser session: showing your recorded history. Mark updates reviewed to set a starting point.')
    else:
        st.caption('Compared with your last reviewed checkpoint in this browser session.')
    if view.changes:
        latest = list(reversed(view.changes))[:3]
        cards = ''.join(f'<article class="rj-change"><span class="rj-event-date">{escape(_date_label(e.occurred_at))}</span><strong>{escape(e.title)}</strong><p>{escape(_excerpt(e.detail))}</p></article>' for e in latest)
        st.markdown('<div class="rj-changes">'+cards+'</div>', unsafe_allow_html=True)
        if len(view.changes) > 3:
            st.caption(f'{len(view.changes)} recorded updates since this checkpoint; the full timeline is below.')
        if st.button('Mark updates reviewed', key='rr_mark_reviewed:'+str(case.case_id)):
            st.session_state[cursor_key] = view.latest_event_id
            st.rerun()
    else:
        st.info('No new updates recorded. Your earlier progress is still here; you can take the next step when you are ready.')
    if selection and selection.get('pending_change_description') and 'rr_revision' in st.session_state:
        st.warning('Fictional update awaiting your review: '+selection['pending_change_description'])
        st.caption('This proposal is not a completed milestone. Open Circumstances changed? Review an update below to review and confirm it.')
    if 'rr_revision' in st.session_state or 'rr_extraction_ready' in st.session_state:
        st.info('You have proposed changes awaiting confirmation. Your accepted plan remains active until you approve them.')
    st.markdown(timing, unsafe_allow_html=True)
    left, right = st.columns([1.65, 1], gap='large')
    with left:
        st.subheader('Your timeline')
        if view.timeline:
            timeline = []
            for event in reversed(view.timeline[-6:]):
                timeline.append(f'<li><span class="rj-timeline-dot" aria-hidden="true"></span><time>{escape(_date_label(event.occurred_at))}</time><strong>{escape(event.title)}</strong><p>{escape(_excerpt(event.detail))}</p></li>')
            st.markdown('<ol class="rj-timeline">'+''.join(timeline)+'</ol>', unsafe_allow_html=True)
            if len(view.timeline) > 6 or any(len(event.detail) > 240 for event in view.timeline):
                with st.expander(f'All {len(view.timeline)} recorded milestones'):
                    for event in view.timeline:
                        st.text(_date_label(event.occurred_at)+' · '+event.title+'\n'+event.detail)
        else:
            st.info('No dated milestones were recorded for this older case. Saved tasks and earlier plan history remain available below.')
    with right:
        with st.container(border=True):
            st.caption('ONE MANAGEABLE NEXT STEP')
            if view.next_task:
                st.subheader(view.next_task.task.title)
                st.write(view.next_task.description)
                st.caption('Why now: '+view.next_task.explanation)
                st.caption('Update this step in your task list below.')
            elif view.counts.blocked:
                st.subheader('Review what is blocking progress')
                st.write('Your blocked tasks are saved. Report a change to review support needs and possible follow-ups.')
            else:
                st.subheader('Your recorded work is here')
                st.write('Review your situation when something changes. Completing this checklist does not determine whether recovery is finished.')
        with st.expander('Your confirmed situation'):
            render_situation(case.intake, records)
        if st.button('Review or edit your situation', key='rr_edit_situation'):
            st.session_state['rr_open_situation'] = True
            st.rerun()
        if st.button('Edit household details and dates', key='rr_edit_household'):
            st.session_state['rr_focus'] = 'Document damage'
            st.rerun()
    return view
