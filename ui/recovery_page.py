"""M1 presentation over M5's public domain/repository APIs; no duplicate persistence."""
import os
import re
import sqlite3
from pathlib import Path
from uuid import UUID
import streamlit as st
from recovery.assessment import start_recovery_case, RecoveryIntakeNotPermitted
from recovery.database import SQLiteRecoveryRepository
from recovery.demo_planner import create_demo_draft_plan
from recovery.models import (RecoveryIntake, RecoveryPlan, TaskStatus, RecoveryRecords,
                             HouseholdRecoveryDetails, DamageRecord)
from recovery.insurance import insurance_discussion_summary
from recovery.reassessment import preview_reassessment, ReassessmentPreview
from ui.components import heading
from recovery.extraction_consumer import (ExtractionReview, CHOICES, prepare_review,
    require_current, selected_changes, revision_for_selection, accept_review, confirmed_context)


NEEDS = ['Temporary housing', 'Water and household supplies', 'Transportation', 'Damage documentation']
DANGER = ['Choose an assessment', 'No immediate danger reported', 'Immediate danger reported']


def repository():
    path = Path(os.environ.get('READYRELIEF_DB_PATH', Path(__file__).resolve().parents[1] / '.local/recovery.sqlite3')).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteRecoveryRepository(path)


def clear_view():
    from ui.state import clear_recovery_view
    clear_recovery_view(st.session_state)


def guard_pending_danger():
    """Fail closed before rendering/each write; the global emergency workflow retries.

    Do not clear the pending report here. Only successful danger persistence may
    acknowledge it. Invalidating transient approvals prevents replay after reruns.
    """
    if not (st.session_state.get('rr_pending_danger') or st.session_state.get('rr_emergency')):
        return
    for key in ('rr_extraction_review', 'rr_extraction_ready', 'rr_extraction_message', 'rr_revision', 'rr_notice'):
        st.session_state.pop(key, None)
    st.session_state['rr_emergency'] = True
    st.rerun()


def intake_fields(prefix, defaults=None):
    default_needs = defaults.household_recovery_needs if defaults else []
    a, b = st.columns(2)
    disaster_options = ['Unknown', 'Hurricane', 'Flood']
    disaster_default = defaults.disaster_type if defaults else 'Unknown'
    disaster = a.selectbox('Disaster type', list(dict.fromkeys(disaster_options + [disaster_default])), index=(disaster_options + ([] if disaster_default in disaster_options else [disaster_default])).index(disaster_default), key=prefix+'disaster')
    housing_options = ['Unknown', 'Minor reported damage', 'Major reported damage', 'No damage reported']
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
    accommodations = ['Unknown', 'Staying with others', 'Staying in temporary lodging', 'No lodging arranged']
    default_accommodation = defaults.temporary_accommodation_status if defaults else accommodations[0]
    accommodations = list(dict.fromkeys(accommodations + [default_accommodation]))
    accommodation = st.selectbox('Temporary accommodation', accommodations, index=accommodations.index(default_accommodation), key=prefix+'accommodation')
    needs = st.multiselect('Household recovery needs', list(dict.fromkeys(NEEDS + default_needs)), default=default_needs, key=prefix+'needs')
    return dict(disaster_type=disaster, housing_condition=housing, utility_availability=utility, temporary_accommodation_status=accommodation, household_recovery_needs=needs)


def new_case(repo):
    guard_pending_danger()
    seed = None
    ready = st.session_state.get('rr_extraction_ready')
    if ready and st.session_state.get('rr_extraction_review'):
        candidate = ExtractionReview.model_validate_json(st.session_state['rr_extraction_review'])
        if candidate.previous_case is None and ready['review_id'] == candidate.review_id:
            seed = candidate
    defaults = selected_changes(seed, ready['selected'], ready['corrections'])[0] if seed else None
    a, b = st.columns([1.3, 1], gap='large')
    with a:
        st.subheader('Tell us what has changed.')
        st.caption('Review these details before creating a case. Unknown values can stay unknown. Use fictional information only.')
        # Outside a form: a danger selection interrupts immediately, before submit.
        danger = st.selectbox('Immediate danger assessment', DANGER, key='rr_initial_danger')
        if danger == DANGER[2]:
            from ui.emergency_page import _report_danger
            _report_danger('recovery')
            st.rerun()
        with st.form('rr_intake'):
            fields = intake_fields('new_'+seed.review_id if seed else 'new_', defaults)
            seed_confirmed = False
            if seed:
                st.caption('The intake is prefilled from your selected review. Household, county and damage changes shown in that review will also be saved only when you confirm and create the case.')
                seed_confirmed = st.checkbox('I confirm the selected household and damage details with this intake')
            submitted = st.form_submit_button('Create draft plan', type='primary')
        if submitted:
            if danger != DANGER[1]:
                st.error('Select an explicit danger assessment before creating a case. Nothing has been saved.')
                return
            intake = RecoveryIntake(**fields, immediate_danger=False)
            guard_pending_danger()
            if seed:
                case = accept_review(repo, seed, ready['selected'], corrections=ready['corrections'],
                    explicitly_confirmed=seed_confirmed, safety_answer=False, reviewed_intake=intake)
                st.session_state.pop('rr_extraction_review', None)
                st.session_state.pop('rr_extraction_ready', None)
            else:
                case = start_recovery_case(intake, repo)
            clear_view()
            st.session_state['rr_case_id'] = str(case.case_id)
            st.session_state['rr_draft'] = create_demo_draft_plan(case, repo.get_recovery_records(case.case_id)).model_dump_json()
            st.rerun()
    with b, st.container(border=True):
        st.subheader('Your plan, your decision.')
        st.markdown('1. **Share reported needs**\n\n2. **Review a small draft plan**\n\n3. **Accept what comes next**\n\n4. **Save progress as you go**')
        st.caption('The initial plan is generated by deterministic rules from your confirmed reports, not verified official guidance. It makes no external requests or benefit applications.')
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
                guard_pending_danger()
                clear_view()
                st.session_state['rr_case_id'] = str(case.case_id)
                st.rerun()
            except ValueError:
                st.error('Enter a valid saved case ID from this machine. No case was changed.')


def evidence(task, county=None, review=None):
    st.caption('Why this step: ' + (review.explanation if review else task.reason_for_recommendation))
    for dependency in task.dependencies:
        st.caption('Before this step: '+dependency)
    if task.resource_categories:
        from services.assistance_pathways import find_resources
        st.caption('Official directory pathways, not M3-reviewed task instructions or live availability.')
        for resource in find_resources(' '.join(task.resource_categories), county=county):
            st.link_button('Official pathway: '+resource.title, resource.url)
            st.caption(resource.organization+' / '+resource.geography+' / checked '+resource.last_checked+' / '+resource.caveat)
    if task.source_reference:
        st.write('Source reference: ' + task.source_reference)
    else:
        st.caption('Evidence: demonstration template / reported needs. No verified official source is attached.')


def planning(repo, case):
    guard_pending_danger()
    st.subheader('Review Your Personalized Recovery Plan')
    st.info('SIMULATED RECOVERY · These organization steps are not official guidance. Review every task before approving.')
    if 'rr_draft' not in st.session_state:
        st.session_state['rr_draft'] = create_demo_draft_plan(case, repo.get_recovery_records(case.case_id)).model_dump_json()
    draft = RecoveryPlan.model_validate_json(st.session_state['rr_draft'])
    if draft.case_id != case.case_id:
        st.session_state.pop('rr_draft', None)
        st.rerun()
    records = repo.get_recovery_records(case.case_id)
    if (draft.planning_basis is not None and draft.planning_basis != case) or (draft.records_version is not None and draft.records_version != records.version):
        st.warning('Confirmed circumstances changed. This draft is stale; generate a fresh plan and review it before approval.')
        if st.button('Generate fresh recovery plan'):
            st.session_state.pop('rr_draft', None)
            st.session_state['rr_reviewed'] = False
            st.rerun()
        return
    for i, task in enumerate(draft.proposed_tasks, 1):
        with st.container(border=True):
            st.caption(f'STEP {i:02d} · {task.priority.value} PRIORITY')
            st.subheader(task.title)
            st.write(task.description)
            evidence(task, records.reported_county)
    if draft.planning_disclosure:
        st.warning(draft.planning_disclosure)
    approved = st.checkbox('I reviewed these tasks and want to accept this plan', key='rr_reviewed')
    if st.button('Approve my recovery plan', type='primary', width='stretch'):
        if not approved:
            st.error('Review every task and check the approval box first. The draft is not active.')
        else:
            guard_pending_danger()
            if repo.get_plan(draft.plan_id) is None:
                repo.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True)
            else:
                repo.approve_plan(draft.plan_id)
            clear_view()
            st.session_state['rr_notice'] = 'Plan approved and saved locally. You can now track your next steps.'
            st.rerun()
    st.caption('For source-supported explanations, use Ask Qwen about reviewed guidance above. Explanations do not create or change saved tasks; review and approve the organization plan separately.')


def reassessment(repo, case, plan):
    guard_pending_danger()
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
                records = repo.get_recovery_records(case.case_id)
                preview = preview_reassessment(case, plan, updated, previous_records=records, updated_records=records)
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
                st.write('**No longer current after approval; historical status retained:** ' + task.task.title)
                st.caption(task.explanation)
            for recommendation in preview.relevant_tasks:
                st.caption('Continue/update: '+recommendation.task.title+' / '+recommendation.explanation)
            st.success(f'{len(preview.completed_tasks)} completed tasks preserved. No existing tasks will be removed.')
            if st.button('Approve this revision', type='primary'):
                guard_pending_danger()
                repo.approve_reassessment(preview, explicitly_approved=True)
                st.session_state.pop('rr_revision', None)
                st.session_state['rr_notice'] = 'Revision approved. Your earlier progress and plan history are preserved.'
                st.rerun()


def dashboard(repo, case, plan):
    guard_pending_danger()
    county = repo.get_recovery_records(case.case_id).reported_county
    version_key = 'rr_displayed_version:' + str(plan.plan_id)
    rendered_version = st.session_state.get(version_key, plan.progress_version)
    current_tasks = [t for t in plan.proposed_tasks if str(t.task_id) not in plan.task_reviews or plan.task_reviews[str(t.task_id)].applicable]
    completed = sum(t.status == TaskStatus.COMPLETED for t in plan.proposed_tasks)
    blocked = sum(t.status == TaskStatus.BLOCKED for t in current_tasks)
    a, b, c = st.columns(3)
    a.metric('Steps completed', str(completed))
    b.metric('Steps remaining', str(sum(t.status != TaskStatus.COMPLETED for t in current_tasks)))
    c.metric('Needs attention', str(blocked))
    st.caption('No-longer-applicable tasks retain their recorded status and history but are excluded from remaining/blocked counts.')
    st.progress(completed / max(1, len(current_tasks)), text='Progress through your accepted plan — not a measure of safety')
    st.subheader('Your Recovery Progress')
    if plan.planning_disclosure:
        st.warning(plan.planning_disclosure)
    st.caption('Locally saved fictional recovery plan · Changes require your approval')
    order = {'URGENT':0, 'HIGH':1, 'MEDIUM':2, 'LOW':3}
    displayed_tasks = sorted(plan.proposed_tasks, key=lambda task: order[(plan.task_reviews[str(task.task_id)].priority if str(task.task_id) in plan.task_reviews and plan.task_reviews[str(task.task_id)].priority else task.priority).value])
    for i, task in enumerate(displayed_tasks, 1):
        review = plan.task_reviews.get(str(task.task_id))
        if review and not review.applicable:
            with st.expander('No longer applicable: '+task.title):
                st.write(review.explanation)
                st.caption('Historical user-reported status retained: '+task.status.value)
            continue
        with st.container(border=True):
            left, right = st.columns([2.2, 1])
            with left:
                st.caption(f'STEP {i:02d} · {(review.priority if review and review.priority else task.priority).value} PRIORITY · {task.status.value.replace("_", " ")}')
                st.subheader(task.title)
                st.write(review.description if review else task.description)
                if review:
                    st.caption(review.explanation)
                with st.expander('Why this step / evidence', key='evidence_'+str(task.task_id)):
                    evidence(task, county, review)
            with right, st.form('task_'+str(plan.plan_id)+'_'+str(task.task_id)):
                options = list(TaskStatus)
                status = st.selectbox('Status · ' + task.title, options, index=options.index(task.status), format_func=lambda s:s.value.replace('_', ' ').title(), key=f'rr_progress:{task.task_id}:{plan.progress_version}')
                if st.form_submit_button('Save progress', width='stretch'):
                    guard_pending_danger()
                    repo.update_task_status(plan.plan_id, task.task_id, status, expected_progress_version=rendered_version)
                    st.session_state['rr_notice'] = 'Progress saved locally.'
                    st.rerun()
    with st.expander('User-reported task status history'):
        history = repo.list_task_history(case.case_id)
        for event in history:
            st.text(event['changed_at']+' / '+next((t.title for t in plan.proposed_tasks if str(t.task_id) == event['task_id']), event['task_id'])+' / '+event['previous_status']+' -> '+event['new_status'])
        if not history:
            st.caption('No recorded status transitions. Earlier legacy updates are not reconstructed.')
    st.session_state[version_key] = plan.progress_version
    reassessment(repo, case, plan)
    with st.expander('Plan history and take-away copy'):
        st.caption('The download contains fictional case information. Keep it to resume on this same machine.')
        text = 'READYRELIEF — FICTIONAL DEMO RECOVERY PLAN\nCase ID: ' + str(case.case_id) + '\nNot official guidance. Not a safety assessment.\n\n'
        for i, task in enumerate(plan.proposed_tasks, 1):
            review = plan.task_reviews.get(str(task.task_id))
            label = ('NO LONGER APPLICABLE; historical status '+task.status.value) if review and not review.applicable else task.status.value
            text += f'\n\n{i}. [{label}] {task.title}\n'+(review.description if review else task.description)+'\nReason: '+(review.explanation if review else task.reason_for_recommendation)+'\nSource: '+(task.source_reference or 'No verified guidance reference attached')
        st.download_button('Download my demo plan', text, file_name='readyrelief-demo-plan.txt', mime='text/plain')
        histories = repo.list_approved_plans(case.case_id)
        st.caption(f'{len(histories)} approved plan version(s). Historical versions remain in SQLite.')
        for historical in histories[:-1]:
            st.write(f'Previous version · {historical.plan_id}')
            for task in historical.proposed_tasks:
                st.caption(task.title + ' · ' + task.status.value)


def insurance_preview(repo, case):
    guard_pending_danger()
    st.subheader('Prepare for an insurance discussion')
    st.caption('Only confirmed saved information is included. Coverage has not been determined and no claim has been submitted.')
    saved_case = repo.get_case(case.case_id)
    records = repo.get_recovery_records(case.case_id)
    if not records.damage_records:
        st.info('No confirmed damaged items have been recorded. Document damage to include item details in your insurance discussion draft.')
        if st.button('Document damage for insurance'):
            st.session_state['rr_focus'] = 'Document damage'
            st.rerun()
    summary = insurance_discussion_summary(saved_case, records)
    st.text(summary)
    st.download_button('Download insurance discussion draft', summary,
                       file_name='readyrelief-insurance-discussion.txt', mime='text/plain')
    if st.button('Add or update household and damage details'):
        st.session_state['rr_focus'] = 'Document damage'
        st.rerun()


def recovery_records(repo, case):
    guard_pending_danger()
    st.subheader('Household details and damage records')
    st.caption('Use fictional information only. Save only details you have reviewed. Unknown values stay unknown. No photographs are uploaded here.')
    current = repo.get_recovery_records(case.case_id)
    snapshot_key = 'rr_records_snapshot:' + str(case.case_id)
    if snapshot_key not in st.session_state:
        st.session_state[snapshot_key] = current.model_dump_json()
    snapshot = RecoveryRecords.model_validate_json(st.session_state[snapshot_key])
    if snapshot.version != current.version:
        st.warning('Saved records changed in another session. Reload before making further edits.')
    if st.button('Reload saved household and damage records'):
        st.session_state[snapshot_key] = current.model_dump_json()
        st.session_state[snapshot_key + ':reload'] = st.session_state.get(snapshot_key + ':reload', 0) + 1
        st.rerun()
    prefix = f'rr_records:{case.case_id}:{snapshot.version}:{st.session_state.get(snapshot_key + ":reload", 0)}:'
    h = snapshot.household
    with st.expander('Optional household details'), st.form(prefix + 'household'):
        st.caption('Leave a count blank if unknown. Do not infer adults or total household size.')
        children = st.text_input('Number of children (if known)', '' if h.children is None else str(h.children))
        adults = st.text_input('Number of adults (if known)', '' if h.adults is None else str(h.adults))
        damage = st.text_area('Reported property damage', h.reported_property_damage or '', max_chars=2000)
        options = ['Unknown', 'Yes', 'No']
        insurance = st.selectbox('Would you like insurance preparation help?', options,
                                index=options.index({None: 'Unknown', True: 'Yes', False: 'No'}[h.wants_insurance_help]))
        county = st.selectbox('Confirmed county (optional)', ['Unknown', 'Miami-Dade'],
                              index=1 if snapshot.reported_county else 0)
        confirmed = st.checkbox('I confirm these household details')
        save = st.form_submit_button('Save confirmed household details')
    if save:
        if not confirmed:
            st.error('Confirm the details first. Nothing was saved.')
        else:
            def count(text):
                if not text.strip():
                    return None
                if not text.strip().isascii() or not text.strip().isdigit():
                    raise ValueError('Household counts must be whole nonnegative numbers or blank.')
                return int(text.strip())
            proposal = snapshot.model_copy(deep=True)
            proposal.household = HouseholdRecoveryDetails(children=count(children), adults=count(adults),
                reported_property_damage=damage.strip() or None,
                wants_insurance_help={'Unknown': None, 'Yes': True, 'No': False}[insurance])
            proposal.reported_county = None if county == 'Unknown' else county
            guard_pending_danger()
            saved = repo.save_recovery_records(proposal, expected_version=snapshot.version, explicitly_confirmed=True)
            st.session_state[snapshot_key] = saved.model_dump_json()
            st.session_state['rr_notice'] = 'Confirmed household details saved.'
            st.rerun()
    st.markdown('#### Confirmed saved damage')
    if not current.damage_records:
        st.info('No confirmed damaged items yet. Add an item below, review it, and confirm before saving.')
    for item in current.damage_records:
        with st.container(border=True):
            st.text(item.item_description + '\n' + item.damage_description)
            st.caption(f'Incident date: {item.incident_date or "Unknown"}')
            if item.notes:
                st.text(item.notes)
    options = ['New damage record'] + [str(item.damage_id) for item in snapshot.damage_records]
    labels = {str(item.damage_id): item.item_description for item in snapshot.damage_records}
    if st.button('Add Damaged Item'):
        st.session_state[prefix+'selection'] = 'New damage record'
    selected = st.selectbox('Add or edit a damage record', options,
                            format_func=lambda value: labels.get(value, value), key=prefix+'selection')
    item = next((item for item in snapshot.damage_records if str(item.damage_id) == selected), None)
    with st.form(prefix + selected):
        description = st.text_input('Item or area description', item.item_description if item else '', max_chars=500)
        reported = st.text_area('User-reported damage description', item.damage_description if item else '', max_chars=2000)
        incident = st.date_input('Incident date (leave blank if unknown)', value=item.incident_date if item else None)
        notes = st.text_area('Optional notes', (item.notes or '') if item else '', max_chars=2000)
        confirmed = st.checkbox('I confirm this damage record')
        save = st.form_submit_button('Save confirmed damage record')
    if save:
        if not confirmed:
            st.error('Confirm the damage record first. Nothing was saved.')
        else:
            fields = dict(case_id=case.case_id, item_description=description,
                          damage_description=reported, incident_date=incident, notes=notes.strip() or None)
            if item:
                fields['damage_id'] = item.damage_id
            updated = DamageRecord(**fields)
            proposal = snapshot.model_copy(deep=True)
            proposal.damage_records = [updated if old.damage_id == updated.damage_id else old for old in proposal.damage_records]
            if item is None:
                proposal.damage_records.append(updated)
            guard_pending_danger()
            saved = repo.save_recovery_records(proposal, expected_version=snapshot.version, explicitly_confirmed=True)
            st.session_state[snapshot_key] = saved.model_dump_json()
            st.session_state['rr_notice'] = 'Confirmed damage record saved.'
            st.rerun()
    st.caption('Unsubmitted edits are not saved. Reload saved records to discard edits; reopening uses saved information only.')


def recovery_landing():
    """One primary description-to-approved-plan path; secondary tools stay optional."""
    heading('03 / Recover', 'Recovery Copilot')
    st.caption('Describe > Review Details > Review Plan > Approve Plan > Track Progress')
    st.caption('Fictional data only. Uses Nebius/Qwen when configured. Review before saving.')
    saved = bool(st.session_state.get('rr_case_id'))
    review = bool(st.session_state.get('rr_extraction_review'))
    focus = st.session_state.get('rr_focus', 'Continue my recovery' if saved else 'Start recovery')
    if not review and (not saved or st.session_state.get('rr_update_mode')):
        if saved:
            st.subheader('Update My Situation')
        with st.form('rr_start_description', border=True):
            description = st.text_area("Describe what's happening or what you need help with.", max_chars=2500)
            submitted = st.form_submit_button('Continue to Review', type='primary', key='rr_continue_review')
        with st.expander('How your description is used'):
            st.caption('Continue sends your description and confirmed recovery context to Nebius/Qwen when configured. Extraction proposes reported facts; it does not verify safety. Nothing is saved without confirmation.')
        if submitted:
            if interrupt_recovery_report(description):
                description = ''  # Pause extraction while keeping independent help visible.
            if not description.strip():
                st.info('Describe your situation, or use the structured input below.')
            elif os.getenv('NEBIUS_API_KEY'):
                st.session_state['rr_extraction_message'] = description
                st.session_state['rr_focus'] = 'Continue my recovery'
                focus = 'Continue my recovery'
            else:
                st.warning('AI extraction is not configured. Use the structured input below to review and confirm your details.')
                st.session_state['rr_case_entry'] = True
        if st.session_state.get('rr_safety_question'):
            st.warning('Please clarify the current risk before extraction: is water rising or entering, is anyone trapped, or is there an immediate threat? Emergency actions remain above. You may edit your description or use the structured safety assessment. No safety or danger clearance is inferred.')
    if saved and not review and st.button('Update My Situation'):
        st.session_state['rr_update_mode'] = True
        st.rerun()
    if st.button('Find Help Now'):
        st.session_state['rr_focus'] = 'Find assistance'
        focus = 'Find assistance'
    if not review:
        with st.expander('Other Recovery tools', expanded=False):
            for label in ['Find assistance', 'Document damage', 'Prepare for insurance', 'Continue my recovery']:
                if st.button(label, width='stretch'):
                    st.session_state['rr_focus'] = label
                    focus = label
    return focus


def assistance(county=None):
    guard_pending_danger()
    st.subheader('Official assistance pathways')
    st.info('Verified official links, not live availability. ReadyRelief cannot confirm shelter openings, placement, eligibility, restoration times or application outcomes. No application is submitted here.')
    st.caption('Using confirmed Miami-Dade county.' if county == 'Miami-Dade' else
               'County is unknown. Showing general US and Florida pathways; no county or utility provider is assumed.')
    st.caption('Directory category filters only: all categories are shown initially for browsing. These selections are not reported household needs or utility status and are never saved to your case.')
    needs = st.multiselect('What assistance would you like to find?',
        ['Housing', 'Disaster assistance', 'Electricity', 'Water'],
        default=['Housing', 'Disaster assistance', 'Electricity', 'Water'])
    from services.assistance_pathways import find_resources
    try:
        resources = find_resources(' '.join(needs), county=county)
    except (OSError, ValueError):
        resources = []
        st.warning('The official pathway directory is unavailable. No availability or eligibility has been checked.')
    if not resources:
        st.info('No matching official pathways in this small directory. Try another category. This does not mean assistance is unavailable.')
    for resource in resources:
        with st.container(border=True):
            st.caption('OFFICIAL INFORMATION PATHWAY / Not a live availability check')
            st.subheader(resource.title)
            st.caption(resource.organization + ' · ' + resource.geography + ' · ' + resource.category)
            st.write(resource.purpose)
            st.link_button('Open Official Resource: ' + resource.title, resource.url, type='primary', width='stretch')
            st.caption('Official URL and purpose checked: ' + resource.last_checked + '. Not checked live on this visit.')
            st.write(resource.caveat)
    st.caption('Directory links are not M3-reviewed guidance and are not supplied to Qwen as verified evidence. Separately reviewed guidance remains available below.')
    from ui.guidance import render as grounded_guidance
    grounded_guidance('recover')


def interrupt_recovery_report(message):
    """Use M4's recovery-specific screen and preserve its persistence decision."""
    from emergency.service import recovery_requires_emergency, screen_report
    from emergency.workflow import begin_emergency
    from uuid import uuid4
    if recovery_requires_emergency(message):
        decision = screen_report(message, entrypoint='recovery')
        if (not decision.persist_danger and decision.reason_codes == ['unresolved_hazard_context']
                and {kind.value for kind in decision.incident_types} == {'flood'}):
            st.session_state['rr_safety_question'] = True
            st.warning('The current risk needs clarification. Please edit your report or use the structured safety assessment; nothing was saved.')
            return True
        begin_emergency(st.session_state, decision, entrypoint='recovery', event_id=str(uuid4()))
        st.rerun()


def request_extraction(repo, message):
    """One explicit request; retain original snapshots across the model call."""
    from services.assistant import extract_recovery_needs, RecoveryConfirmedContext
    guard_pending_danger()
    if interrupt_recovery_report(message):
        return
    st.session_state.pop('rr_safety_question', None)
    case_id = st.session_state.get('rr_case_id')
    case = repo.get_case(UUID(case_id)) if case_id else None
    if case_id and case is None:
        raise ValueError('The saved case is unavailable; reopen it before requesting extraction.')
    if case and case.intake.immediate_danger is True:
        st.session_state['rr_emergency'] = True
        st.rerun()
    if case and case.intake.immediate_danger is None:
        raise ValueError('The saved safety assessment is incomplete. Use structured input before routine updates.')
    records = repo.get_recovery_records(case.case_id) if case else None
    plan = repo.get_active_plan(case.case_id) if case else None
    context = RecoveryConfirmedContext.model_validate(confirmed_context(case, records))
    guard_pending_danger()
    emergency_epoch = st.session_state.get('rr_emergency_epoch', 0)
    try:
        with st.spinner('Qwen is preparing details for your review. Nothing is being saved.'):
            result = extract_recovery_needs(message, confirmed_context=context)
    except Exception:
        st.warning('Recovery extraction is unavailable. Nothing was saved. Use the structured input below.')
        return
    guard_pending_danger()
    if st.session_state.get('rr_emergency_epoch', 0) != emergency_epoch:
        raise ValueError('Emergency state changed during extraction. Request a fresh proposal after interruption.')
    current = repo.get_case(case.case_id) if case else None
    if result.status == 'DANGER_DETECTED' or (current and current.intake.immediate_danger is True):
        st.session_state['rr_emergency'] = True
        st.rerun()
    if case and repo.get_active_plan(case.case_id) != plan:
        raise ValueError('Task progress or the active plan changed during extraction. Request a fresh proposal.')
    stage_extraction_result(st.session_state, repo, result, message,
        case_snapshot=case, records_snapshot=records, plan_snapshot=plan)
    st.rerun()


def stage_extraction_result(state, repo, result, message, *, case_snapshot=None,
                            records_snapshot=None, plan_snapshot=None):
    """Validated M1 delivery boundary. Never invokes extraction or writes recovery data."""
    if state.get('rr_pending_danger') or state.get('rr_emergency'):
        raise ValueError('recovery proposals are paused while danger is pending or reported')
    case_id = state.get('rr_case_id')
    expected_id = str(case_snapshot.case_id) if case_snapshot else None
    if case_id != expected_id:
        raise ValueError('stale extraction: active case changed or original snapshots are missing')
    review = prepare_review(result, message, case=case_snapshot,
                            records=records_snapshot, plan=plan_snapshot)
    require_current(repo, review)
    state['rr_extraction_review'] = review.model_dump_json()
    state.pop('rr_extraction_ready', None)


def extraction_confirmation(repo):
    guard_pending_danger()
    raw = st.session_state.get('rr_extraction_review')
    if not raw:
        return
    review = ExtractionReview.model_validate_json(raw)
    st.subheader('Review What We Understood')
    if st.button('Reject proposal and use structured input'):
        st.session_state.pop('rr_extraction_review', None)
        st.session_state.pop('rr_extraction_ready', None)
        st.rerun()
    expected_id = str(review.previous_case.case_id) if review.previous_case else None
    if st.session_state.get('rr_case_id') != expected_id:
        st.warning('This proposal belongs to a different recovery context. Reject it and request a fresh proposal.')
        return
    try:
        require_current(repo, review)
    except ValueError:
        st.warning('Saved information changed. Reject this stale proposal and request a fresh one. Structured input remains available.')
        return
    status = review.result['status']
    if status == 'DANGER_DETECTED':
        st.session_state['rr_emergency'] = True
        st.rerun()
    if status in {'UNAVAILABLE', 'ERROR'}:
        st.session_state.pop('rr_extraction_review', None)
        st.session_state['rr_case_entry'] = True
        st.session_state['rr_extraction_error'] = 'Extraction is unavailable or invalid. No proposed information was saved. Use the structured input below.'
        st.rerun()
    st.caption('Nothing is saved automatically. Select changes, correct them, and review the preview before confirming.')
    if review.previous_case:
        st.caption('Unmentioned saved information and existing damage records will be preserved.')
    for question in review.result['clarification_questions']:
        st.text(question)
    for name in review.unresolved:
        st.warning(name.replace('_', ' ').capitalize() + ' remains unresolved. Use structured input to clarify it.')
    if not review.proposed:
        st.info('No supported changes were extracted. Review the questions and use the structured input below, or reject this proposal to describe your situation again.')
    selected, corrections = [], {}
    with st.form('rr_extraction_edit:' + review.review_id):
        for name, value in review.proposed.items():
            label = ('Damaged item ' + name.split(':')[1] if name.startswith('damage:') else name.replace('_', ' ').capitalize())
            if st.checkbox('Include ' + label, value=True, key=review.review_id+':select:'+name):
                selected.append(name)
            if name in CHOICES and name != 'household_recovery_needs':
                corrections[name] = st.selectbox(label, CHOICES[name], index=CHOICES[name].index(value), key=review.review_id+':value:'+name)
            elif name == 'household_recovery_needs':
                corrections[name] = st.multiselect(label, CHOICES[name], default=value, key=review.review_id+':value:'+name)
            elif name in ('adults', 'children'):
                corrections[name] = st.number_input(label, min_value=0, max_value=100, value=value, step=1, key=review.review_id+':value:'+name)
            elif name == 'insurance_preparation_requested':
                answer = st.selectbox(label, ['Yes', 'No'], index=0 if value else 1, key=review.review_id+':value:'+name)
                corrections[name] = answer == 'Yes'
            else:
                corrections[name] = st.text_input(label, value=value, key=review.review_id+':value:'+name)
            st.text('Supporting quote: ' + review.quotes[name])
        unknown = [name.replace('_', ' ') for name, field in review.result['fields'].items() if field['state'] == 'UNKNOWN']
        st.caption('Unknown (not inferred): ' + (', '.join(unknown) or 'none'))
        preview = st.form_submit_button('Review selected changes', disabled=not bool(review.proposed))
    if preview:
        st.session_state.pop('rr_extraction_ready', None)
        if not selected:
            st.error('Select at least one resolved change. Nothing was saved.')
        else:
            intake, _ = selected_changes(review, selected, corrections)
            revision = revision_for_selection(review, selected, corrections)
            st.session_state['rr_extraction_ready'] = dict(review_id=review.review_id, selected=selected,
                corrections=corrections, revision=revision.model_dump_json() if revision else None,
                needs_safety=review.previous_case is None or intake != review.previous_case.intake or revision is not None)
    ready = st.session_state.get('rr_extraction_ready')
    if not ready or ready['review_id'] != review.review_id:
        return
    st.markdown('#### Selected changes awaiting confirmation')
    st.caption('Confirmation applies to this displayed preview. After editing, use Review selected changes again.')
    for name in ready['selected']:
        st.text(name.replace('_', ' ') + ': ' + str(ready['corrections'][name]))
    revision = ReassessmentPreview.model_validate_json(ready['revision']) if ready['revision'] else None
    if revision:
        for change in revision.changed_circumstances:
            st.write(change.explanation)
        for recommendation in revision.potentially_irrelevant_tasks:
            st.text('No longer current after approval: '+recommendation.task.title)
            st.caption(recommendation.explanation)
        for recommendation in revision.relevant_tasks:
            st.caption('Continue: '+recommendation.task.title+' / '+recommendation.explanation)
        for recommendation in revision.new_tasks:
            st.text('Proposed task: ' + recommendation.task.title)
        st.caption('Approval creates a revised approved plan and preserves existing tasks and history.')
    danger = None
    if ready['needs_safety']:
        answer = st.selectbox('Safety assessment for selected changes', DANGER, key='rr_extraction_safety:'+review.review_id)
        if answer == DANGER[2]:
            st.session_state['rr_emergency'] = True
            st.rerun()
        danger = False if answer == DANGER[1] else None
    revision_approved = st.checkbox('I approve the proposed plan revision') if revision else True
    confirmed = st.checkbox('I confirm the selected changes shown above', key='rr_extraction_confirm:'+review.review_id+str(ready['selected'])+str(ready['corrections']))
    if st.button('Confirm selected changes', type='primary'):
        guard_pending_danger()
        if not revision_approved:
            st.error('Review and explicitly approve the plan revision before saving. Nothing was saved.')
            return
        case = accept_review(repo, review, ready['selected'], corrections=ready['corrections'],
            explicitly_confirmed=confirmed, safety_answer=danger, approved_revision=revision)
        st.session_state['rr_case_id'] = str(case.case_id)
        st.session_state.pop('rr_extraction_review', None)
        st.session_state.pop('rr_extraction_ready', None)
        st.session_state.pop('rr_records_snapshot:'+str(case.case_id), None)
        clear_view()
        st.session_state['rr_notice'] = 'Selected recovery changes confirmed and saved. No external submission was made.'
        st.session_state['rr_focus'] = 'Continue my recovery'
        st.session_state.pop('rr_update_mode', None)
        st.rerun()


def render():
    guard_pending_danger()
    focus = recovery_landing()
    error_notice = st.session_state.pop('rr_extraction_error', None)
    if error_notice:
        st.warning(error_notice)
    notice = st.session_state.pop('rr_notice', None)
    if notice:
        st.success(notice)
    message = st.session_state.pop('rr_extraction_message', None)
    try:
        repo = repository()
        guard_pending_danger()
        if message is not None:
            request_extraction(repo, message)
        if st.session_state.get('rr_extraction_review') and st.session_state.get('rr_focus') == 'Find assistance':
            assistance()
            if st.button('Return to Review Details'):
                st.session_state['rr_focus'] = 'Continue my recovery'
                st.rerun()
            return
        extraction_confirmation(repo)
        if st.session_state.get('rr_extraction_review'):
            with st.expander('Use structured input instead'):
                if not st.session_state.get('rr_case_id'):
                    new_case(repo)
                else:
                    st.caption('Reject the proposal above to use existing structured case controls. No proposal has been saved.')
            return
        case_id = st.session_state.get('rr_case_id')
        if not case_id:
            if focus == 'Find assistance':
                assistance()
            elif focus != 'Start recovery':
                st.subheader('Document damage' if focus == 'Document damage' else
                             'Prepare for an insurance discussion' if focus == 'Prepare for insurance' else
                             'Continue your recovery')
                if focus == 'Prepare for insurance':
                    st.info('No confirmed damage records are loaded. An insurance draft uses only confirmed saved information; no coverage or submission is implied.')
                    if st.button('Document damage for insurance'):
                        st.session_state['rr_focus'] = 'Document damage'
                        st.rerun()
                st.info('Saving damage records and preparing a saved insurance discussion require a recovery case. Create a case or resume an existing one. Nothing has been saved from your description.')
                create, resume = st.columns(2)
                if create.button('Create Recovery Case', width='stretch'):
                    st.session_state['rr_case_entry'] = True
                if resume.button('Resume Existing Case', width='stretch'):
                    st.session_state['rr_case_entry'] = True
            st.markdown('#### Returning household or prefer a form?')
            st.caption('Resume with your saved case ID, or open the optional structured intake. Review and confirmation are required before saving.')
            with st.expander('Use structured intake or resume a saved case', expanded=focus == 'Continue my recovery' or st.session_state.get('rr_case_entry', False)):
                new_case(repo)
            return
        guard_pending_danger()
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
                st.caption('Using your saved confirmed case. Your description does not overwrite it.')
                if focus == 'Find assistance':
                    assistance(repo.get_recovery_records(case.case_id).reported_county)
                elif focus == 'Document damage':
                    recovery_records(repo, case)
                elif focus == 'Prepare for insurance':
                    insurance_preview(repo, case)
                else:
                    plan = repo.get_active_plan(case.case_id)
                    if plan:
                        dashboard(repo, case, plan)
                    else:
                        planning(repo, case)
        if st.button('Open a different case'):
            guard_pending_danger()
            st.session_state.pop('rr_case_id', None)
            clear_view()
            st.rerun()
    except (OSError, sqlite3.Error):
        st.error('Local recovery storage is unavailable. No successful save is claimed. Emergency access remains available above. Check the configured database path.')
    except (ValueError, RecoveryIntakeNotPermitted) as error:
        st.error('This change could not be saved: ' + str(error))
