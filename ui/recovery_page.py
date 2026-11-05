"""M1 presentation over M5's public domain/repository APIs; no duplicate persistence."""
import os
import sqlite3
from pathlib import Path
from uuid import UUID
import streamlit as st
from recovery.assessment import start_recovery_case, RecoveryIntakeNotPermitted
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import RecoveryIntake, RecoveryPlan, TaskStatus
from recovery.reassessment import preview_reassessment, ReassessmentPreview
from ui.components import heading


NEEDS = ['Temporary housing', 'Water and household supplies', 'Transportation', 'Damage documentation']
DANGER = ['Choose an assessment', 'No immediate danger reported', 'Immediate danger reported']


def repository():
    path = Path(os.environ.get('READYRELIEF_DB_PATH', Path(__file__).resolve().parents[1] / '.local/recovery.sqlite3')).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteRecoveryRepository(path)


def clear_view():
    from ui.state import clear_recovery_view
    clear_recovery_view(st.session_state)

def intake_fields(prefix, defaults=None):
    h = st.session_state['household']
    default_needs = defaults.household_recovery_needs if defaults else ['Temporary housing', 'Water and household supplies'] + ([] if h.has_vehicle else ['Transportation'])
    a, b = st.columns(2)
    disaster_options = ['Hurricane', 'Flood']
    disaster_default = defaults.disaster_type if defaults else 'Hurricane'
    disaster = a.selectbox('Disaster type', list(dict.fromkeys(disaster_options + [disaster_default])), index=(disaster_options + ([] if disaster_default in disaster_options else [disaster_default])).index(disaster_default), key=prefix+'disaster')
    housing_options = ['Minor reported damage', 'Major reported damage', 'No damage reported']
    housing_default = defaults.housing_condition if defaults else housing_options[0]
    housing_options = list(dict.fromkeys(housing_options + [housing_default]))
    housing = b.selectbox('Housing condition', housing_options, index=housing_options.index(housing_default), key=prefix+'housing')
    utility = {}
    utility_names = list(dict.fromkeys(['electricity', 'water'] + (list(defaults.utility_availability) if defaults else [])))
    utility_columns = st.columns(2)
    for index, name in enumerate(utility_names):
        col = utility_columns[index % 2]
        options = ['Unknown', 'Available', 'Unavailable']
        value = defaults.utility_availability.get(name) if defaults else None
        selected = {None: 'Unknown', True: 'Available', False: 'Unavailable'}[value]
        answer = col.selectbox(name.capitalize() + ' availability', options, index=options.index(selected), key=prefix+name)
        utility[name] = {'Unknown': None, 'Available': True, 'Unavailable': False}[answer]
    accommodations = ['Staying with others', 'Staying in temporary lodging', 'No lodging arranged']
    default_accommodation = defaults.temporary_accommodation_status if defaults else accommodations[0]
    accommodations = list(dict.fromkeys(accommodations + [default_accommodation]))
    accommodation = st.selectbox('Temporary accommodation', accommodations, index=accommodations.index(default_accommodation), key=prefix+'accommodation')
    needs = st.multiselect('Household recovery needs', list(dict.fromkeys(NEEDS + default_needs)), default=default_needs, key=prefix+'needs')
    return dict(disaster_type=disaster, housing_condition=housing, utility_availability=utility, temporary_accommodation_status=accommodation, household_recovery_needs=needs)


def new_case(repo):
    a, b = st.columns([1.3, 1], gap='large')
    with a:
        st.subheader('Tell us what has changed.')
        st.caption('Use this intake only for a fictional post-storm scenario. Your household preferences prefill reported transportation needs.')
        # Outside a form: a danger selection interrupts immediately, before submit.
        danger = st.selectbox('Immediate danger assessment', DANGER, key='rr_initial_danger')
        if danger == DANGER[2]:
            from ui.emergency_page import _report_danger
            _report_danger('recovery')
            st.rerun()
        with st.form('rr_intake'):
            fields = intake_fields('new_')
            submitted = st.form_submit_button('Create draft plan', type='primary')
        if submitted:
            if danger != DANGER[1]:
                st.error('Select an explicit danger assessment before creating a case. Nothing has been saved.')
                return
            case = start_recovery_case(RecoveryIntake(**fields, immediate_danger=False), repo)
            clear_view()
            st.session_state['rr_case_id'] = str(case.case_id)
            st.session_state['rr_draft'] = create_demo_draft_plan(case).model_dump_json()
            st.rerun()
    with b, st.container(border=True):
        st.subheader('Your plan, your decision.')
        st.markdown('1. **Share reported needs**\n\n2. **Review a small draft plan**\n\n3. **Accept what comes next**\n\n4. **Save progress as you go**')
        st.caption('The initial plan is a deterministic demonstration template, not verified official guidance. It makes no external requests or benefit applications.')
        st.divider()
        st.subheader('Pick up where you left off')
        with st.form('rr_resume'):
            case_id = st.text_input('Saved fictional case ID', placeholder='Paste the case ID from your saved plan')
            resume = st.form_submit_button('Resume saved case')
        if resume:
            try:
                case = repo.get_case(UUID(case_id.strip()))
                if not case:
                    raise ValueError('No saved case was found on this machine.')
                clear_view()
                st.session_state['rr_case_id'] = str(case.case_id)
                st.rerun()
            except ValueError:
                st.error('Enter a valid saved case ID from this machine. No case was changed.')


def evidence(task):
    st.caption('Why this step: ' + task.reason_for_recommendation)
    if task.source_reference:
        st.write('Source reference: ' + task.source_reference)
    else:
        st.caption('Evidence: demonstration template / reported needs. No verified official source is attached.')


def planning(repo, case):
    st.subheader('A manageable plan. Ready for your review.')
    st.info('SIMULATED RECOVERY · These organization steps are not official guidance. Review every task before approving.')
    if 'rr_draft' not in st.session_state:
        st.session_state['rr_draft'] = create_demo_draft_plan(case).model_dump_json()
    draft = RecoveryPlan.model_validate_json(st.session_state['rr_draft'])
    if draft.case_id != case.case_id:
        st.session_state.pop('rr_draft', None)
        st.rerun()
    for i, task in enumerate(draft.proposed_tasks, 1):
        with st.container(border=True):
            st.caption(f'STEP {i:02d} · {task.priority.value} PRIORITY')
            st.subheader(task.title)
            st.write(task.description)
            evidence(task)
    if draft.planning_disclosure:
        st.warning(draft.planning_disclosure)
    approved = st.checkbox('I reviewed these tasks and want to accept this plan', key='rr_reviewed')
    if st.button('Approve my recovery plan', type='primary', width='stretch'):
        if not approved:
            st.error('Review every task and check the approval box first. The draft is not active.')
        else:
            if repo.get_plan(draft.plan_id) is None:
                repo.save_draft_plan(draft)
            repo.approve_plan(draft.plan_id)
            clear_view()
            st.session_state['rr_notice'] = 'Plan approved and saved locally. You can now track your next steps.'
            st.rerun()
    st.caption('For source-supported explanations, use Ask Qwen about reviewed guidance above. Explanations do not create or change saved tasks; review and approve the organization plan separately.')


def reassessment(repo, case, plan):
    with st.expander('Circumstances changed? Review an update'):
        st.caption('Your accepted plan stays active until you approve a revision. Existing tasks and completed progress are retained.')
        danger = st.selectbox('Updated immediate danger assessment', DANGER, key='rr_update_danger')
        if danger == DANGER[2]:
            st.session_state.pop('rr_revision', None)
            from ui.emergency_page import _report_danger
            _report_danger('recovery')
            st.rerun()
        if danger != DANGER[1]:
            st.session_state.pop('rr_revision', None)
        with st.form('rr_reassessment'):
            fields = intake_fields('updated_'+str(plan.plan_id), case.intake)
            submitted = st.form_submit_button('Preview proposed changes')
        if submitted:
            st.session_state.pop('rr_revision', None)
            if danger != DANGER[1]:
                st.error('An explicit no-immediate-danger report is required before routine reassessment.')
            else:
                updated = RecoveryIntake(**fields, immediate_danger=False)
                preview = preview_reassessment(case, plan, updated)
                st.session_state['rr_revision'] = preview.model_dump_json()
        if 'rr_revision' in st.session_state:
            preview = ReassessmentPreview.model_validate_json(st.session_state['rr_revision'])
            if preview.previous_case != case or preview.previous_plan != plan:
                st.session_state.pop('rr_revision', None)
                st.warning('Task progress or circumstances changed. Generate a fresh preview before approval.')
                return
            if not preview.changed_circumstances:
                st.info('No changed circumstances were reported. Your current plan is unchanged.')
                return
            st.markdown('#### Proposed update')
            for change in preview.changed_circumstances:
                st.write('• ' + change.explanation)
            for task in preview.new_tasks:
                st.write('**Add:** ' + task.task.title)
                st.caption(task.explanation)
            for task in preview.potentially_irrelevant_tasks:
                st.write('**Keep for review:** ' + task.task.title)
                st.caption(task.explanation)
            st.success(f'{len(preview.completed_tasks)} completed tasks preserved. No existing tasks will be removed.')
            if st.button('Approve this revision', type='primary'):
                repo.approve_reassessment(preview, explicitly_approved=True)
                st.session_state.pop('rr_revision', None)
                st.session_state['rr_notice'] = 'Revision approved. Your earlier progress and plan history are preserved.'
                st.rerun()


def dashboard(repo, case, plan):
    version_key = 'rr_displayed_version:' + str(plan.plan_id)
    rendered_version = st.session_state.get(version_key, plan.progress_version)
    completed = sum(t.status == TaskStatus.COMPLETED for t in plan.proposed_tasks)
    blocked = sum(t.status == TaskStatus.BLOCKED for t in plan.proposed_tasks)
    a, b, c = st.columns(3)
    a.metric('Steps completed', str(completed))
    b.metric('Steps remaining', str(len(plan.proposed_tasks) - completed))
    c.metric('Needs attention', str(blocked))
    st.progress(completed / max(1, len(plan.proposed_tasks)), text='Progress through your accepted plan — not a measure of safety')
    st.subheader('One step at a time.')
    if plan.planning_disclosure:
        st.warning(plan.planning_disclosure)
    st.caption('Locally saved fictional recovery plan · Changes require your approval')
    for i, task in enumerate(plan.proposed_tasks, 1):
        with st.container(border=True):
            left, right = st.columns([2.2, 1])
            with left:
                st.caption(f'STEP {i:02d} · {task.priority.value} PRIORITY · {task.status.value.replace("_", " ")}')
                st.subheader(task.title)
                st.write(task.description)
                with st.expander('Why this step / evidence', key='evidence_'+str(task.task_id)):
                    evidence(task)
            with right, st.form('task_'+str(plan.plan_id)+'_'+str(task.task_id)):
                options = list(TaskStatus)
                status = st.selectbox('Status · ' + task.title, options, index=options.index(task.status), format_func=lambda s:s.value.replace('_', ' ').title(), key=f'rr_progress:{task.task_id}:{plan.progress_version}')
                if st.form_submit_button('Save progress', width='stretch'):
                    repo.update_task_status(plan.plan_id, task.task_id, status, expected_progress_version=rendered_version)
                    st.session_state['rr_notice'] = 'Progress saved locally.'
                    st.rerun()
    st.session_state[version_key] = plan.progress_version
    reassessment(repo, case, plan)
    with st.expander('Plan history and take-away copy'):
        st.caption('The download contains fictional case information. Keep it to resume on this same machine.')
        text = 'READYRELIEF — FICTIONAL DEMO RECOVERY PLAN\nCase ID: ' + str(case.case_id) + '\nNot official guidance. Not a safety assessment.\n\n'
        text += '\n\n'.join(f'{i}. [{t.status.value}] {t.title}\n{t.description}\nReason: {t.reason_for_recommendation}\nSource: {t.source_reference or "No verified source attached"}' for i, t in enumerate(plan.proposed_tasks, 1))
        st.download_button('Download my demo plan', text, file_name='readyrelief-demo-plan.txt', mime='text/plain')
        histories = repo.list_approved_plans(case.case_id)
        st.caption(f'{len(histories)} approved plan version(s). Historical versions remain in SQLite.')
        for historical in histories[:-1]:
            st.write(f'Previous version · {historical.plan_id}')
            for task in historical.proposed_tasks:
                st.caption(task.title + ' · ' + task.status.value)


def render():
    heading('03 / Recover', 'Small steps. Steady progress.', 'Turn reported needs into a plan you can review, accept, and return to.')
    st.caption('SIMULATED RECOVERY · Fictional local single-user demonstration in both alert modes')
    notice = st.session_state.pop('rr_notice', None)
    if notice:
        st.success(notice)
    try:
        repo = repository()
        case_id = st.session_state.get('rr_case_id')
        if not case_id:
            new_case(repo)
            from ui.guidance import render as grounded_guidance
            grounded_guidance('recover')
            return
        pending = set(st.session_state.get('rr_pending_danger', []))
        if case_id in pending:
            repo.report_immediate_danger(UUID(case_id))
            pending.discard(case_id)
            st.session_state['rr_pending_danger'] = list(pending)
        case = repo.get_case(UUID(case_id))
        if case is None:
            st.error('This case is not available on this machine. Resume a saved case or start a new fictional case.')
        else:
            with st.expander('Saved case · Keep this ID to resume'):
                st.code(str(case.case_id), language=None)
                st.caption('No account or cross-device access. A case ID is not authentication. Only fictional data belongs here.')
            if case.intake.immediate_danger is not False:
                st.warning('This case has a danger report or an incomplete assessment. Routine changes are paused. Emergency controls remain above; this UI cannot clear a saved danger report.')
            else:
                from ui.guidance import render as grounded_guidance
                grounded_guidance('recover')
                plan = repo.get_active_plan(case.case_id)
                if plan:
                    dashboard(repo, case, plan)
                else:
                    planning(repo, case)
        if st.button('Open a different case'):
            st.session_state.pop('rr_case_id', None)
            clear_view()
            st.rerun()
    except (OSError, sqlite3.Error):
        st.error('Local recovery storage is unavailable. No successful save is claimed. Emergency access remains available above. Check the configured database path.')
    except (ValueError, RecoveryIntakeNotPermitted) as error:
        st.error('This change could not be saved: ' + str(error))
