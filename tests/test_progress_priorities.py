from datetime import datetime, timezone


def _inputs():
    from recovery.progress.models import ProgressInput, HouseholdContext, SourceMode
    return ProgressInput(context_key='saved:one', source_mode=SourceMode.SAVED_CASE,
                         as_of=datetime(2026,10,2,tzinfo=timezone.utc), immediate_danger=False, household=HouseholdContext(label='One'))


def test_emergency_suppresses_all_routine_recommendations():
    from recovery.progress.models import ReviewedTask
    from recovery.progress.priorities import select_next_actions
    inputs = _inputs()
    inputs.immediate_danger = True
    inputs.reviewed_tasks = [ReviewedTask(task_id='repair', key='repair', title='Repair', tier=1)]
    actions = select_next_actions(inputs, ())
    assert len(actions) == 1 and actions[0].tier == 0
    assert actions[0].key == 'emergency:immediate-danger'


def test_priorities_exclude_completed_and_inapplicable_deduplicate_and_cap_three():
    from recovery.progress.models import ActionCandidate, SpecialistResult, SignalState, ReviewedTask
    from recovery.progress.priorities import select_next_actions
    inputs = _inputs()
    inputs.reviewed_tasks = [ReviewedTask(task_id='done',key='housing:done',title='Done',completed=True),
                             ReviewedTask(task_id='na',key='housing:na',title='N/A',applicable=False),
                             ReviewedTask(task_id='open',key='housing:open',title='Housing',tier=1)]
    results=[]
    for specialist in ['housing','utilities','insurance','rebuild']:
        actions = [ActionCandidate(key=f'{specialist}:open',title=specialist,reason='Finding',tier={'housing':1,'utilities':1,'insurance':2,'rebuild':3}[specialist],destination='My Recovery Plan')]
        if specialist=='housing':
            actions.extend([ActionCandidate(key='housing:done',title='Done',reason='Old',tier=1,destination='My Recovery Plan'),
                            ActionCandidate(key='another-key',task_id='na',title='N/A',reason='Old',tier=1,destination='My Recovery Plan')])
        results.append(SpecialistResult(specialist=specialist,state=SignalState.RED,headline='Finding',summary='Finding',actions=actions,source_mode=inputs.source_mode,observed_at=inputs.as_of))
    actions=select_next_actions(inputs,tuple(reversed(results)))
    assert [a.key for a in actions] == ['housing:open','utilities:open','insurance:open']
    assert actions[0].task_id == 'open'
    assert inputs.reviewed_tasks[0].completed is True


def test_failed_specialist_yields_disclosed_partial_recommendation_and_never_uses_failed_actions():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.rebuild import check_rebuild
    from recovery.progress.housing import check_housing
    from recovery.progress.priorities import select_next_actions
    inputs=load_scenario('williams','update')
    inputs.immediate_danger=False
    actions=select_next_actions(inputs,(check_housing(inputs,now=inputs.as_of),check_rebuild(inputs,now=inputs.as_of)))
    assert actions and 'Partial check' in actions[0].reason and 'rebuild' in actions[0].reason


def test_unassessed_danger_offers_only_safety_assessment():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    from recovery.progress.priorities import select_next_actions
    inputs = load_scenario('williams')
    actions = select_next_actions(inputs, (check_housing(inputs, now=inputs.as_of),))
    assert len(actions) == 1
    assert actions[0].key == 'safety:confirm-danger'


def _real_plan_input(*, utility_availability=None):
    """Exercise the planner's real keys and the authoritative task projection."""
    from recovery.demo_planner import create_demo_draft_plan
    from recovery.models import RecoveryCase, RecoveryIntake, PlanStatus
    case = RecoveryCase(intake=RecoveryIntake(disaster_type='Flood', housing_condition='Major reported damage',
        utility_availability=utility_availability or {'electricity': False, 'water': False},
        temporary_accommodation_status='No lodging arranged', immediate_danger=False,
        household_recovery_needs=['Temporary housing', 'Insurance preparation']))
    plan = create_demo_draft_plan(case)
    plan.approval_status = PlanStatus.APPROVED
    inputs = _inputs()
    inputs.accommodation_status = 'needed'
    inputs.insurance_applicable = True
    inputs.repairs_complete = True  # no next-stage funding action in this task-intent test
    inputs.general_preparation_missing = ['Damage photographs are not linked']
    return case, plan, inputs


def _reviewed(plan, keys):
    from recovery.task_view import current_task_views
    from recovery.models import TaskPriority, TaskStatus
    from recovery.progress.models import ReviewedTask
    tiers = {TaskPriority.URGENT: 1, TaskPriority.HIGH: 2, TaskPriority.MEDIUM: 3, TaskPriority.LOW: 4}
    return [ReviewedTask(task_id=str(view.task.task_id), key=view.task.planning_key,
        title=view.task.title, reason=view.explanation, tier=tiers[view.priority],
        completed=view.task.status == TaskStatus.COMPLETED, applicable=view.applicable,
        dependencies=view.task.dependencies) for view in current_task_views(plan) if view.task.planning_key in keys]


def test_real_planner_open_housing_utilities_and_insurance_tasks_link_once():
    from recovery.progress.housing import check_housing
    from recovery.progress.utilities import check_utilities
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.priorities import select_next_actions
    _, plan, inputs = _real_plan_input()
    inputs.reviewed_tasks = _reviewed(plan, {'housing', 'utilities', 'insurance'})
    before = plan.model_dump_json()
    results = tuple(check(inputs, now=inputs.as_of) for check in (check_housing, check_utilities, check_insurance_and_funding))
    actions = select_next_actions(inputs, results)
    assert len(actions) == 3
    assert {action.task_id for action in actions} == {task.task_id for task in inputs.reviewed_tasks}
    assert len({action.task_id for action in actions}) == 3
    utility = next(action for action in actions if action.key == 'utilities')
    assert all(service in utility.reason for service in ['electricity', 'water', 'gas'])
    assert plan.model_dump_json() == before


def test_real_completed_reviews_get_distinct_unresolved_need_followups_not_reopened_work():
    from recovery.models import TaskStatus
    from recovery.progress.housing import check_housing
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.priorities import select_next_actions
    _, plan, inputs = _real_plan_input()
    for task in plan.proposed_tasks:
        if task.planning_key in {'housing', 'insurance'}:
            task.status = TaskStatus.COMPLETED
    inputs.reviewed_tasks = _reviewed(plan, {'housing', 'insurance'})
    before = plan.model_dump_json()
    results = (check_housing(inputs, now=inputs.as_of), check_insurance_and_funding(inputs, now=inputs.as_of))
    actions = select_next_actions(inputs, results)
    assert {action.key for action in actions} == {'housing:reassess-accommodation', 'insurance:follow-up-preparation'}
    assert all(action.task_id is None and 'completed' in action.reason.lower() for action in actions)
    assert all(action.title not in {task.title for task in inputs.reviewed_tasks} for action in actions)
    assert all(any(task.title in action.reason for task in inputs.reviewed_tasks) for action in actions)
    assert inputs.accommodation_status == 'needed'
    assert results[1].items[0].state.value == 'unknown'  # discussion completion is not evidence adequacy
    assert plan.model_dump_json() == before


def test_real_reassessment_specific_utility_task_links_and_closed_work_gets_explicit_followup():
    from recovery.reassessment import preview_reassessment
    from recovery.models import TaskStatus, TaskReview
    from recovery.progress.models import UtilityObservation, Provenance
    from recovery.progress.utilities import check_utilities
    from recovery.progress.priorities import select_next_actions
    case, plan, inputs = _real_plan_input(utility_availability={'electricity': True, 'water': True})
    updated = case.intake.model_copy(update={'utility_availability': {'electricity': False, 'water': True}})
    revised = preview_reassessment(case, plan, updated).proposed_revision
    target = next(task for task in revised.proposed_tasks if task.planning_key == 'utility:electricity')
    inputs.utilities = [UtilityObservation(service='electricity',status='outage',provider='Household report',
        provenance=Provenance(source_mode=inputs.source_mode,source='Confirmed report',scope='address',
                              observed_at=inputs.as_of,valid_until=inputs.as_of))]
    inputs.reviewed_tasks = _reviewed(revised, {'utility:electricity'})
    # Other service unknowns may also be offered, but this electricity intent must link once.
    actions = select_next_actions(inputs,(check_utilities(inputs,now=inputs.as_of),))
    linked = [a for a in actions if a.task_id == str(target.task_id)]
    assert len(linked) == 1
    assert not any(a.key == 'utility:electricity' and a.task_id is None for a in actions)
    target.status = TaskStatus.COMPLETED
    inputs.reviewed_tasks = _reviewed(revised, {'utility:electricity'})
    before = revised.model_dump_json()
    actions = select_next_actions(inputs,(check_utilities(inputs,now=inputs.as_of),))
    followup = next(a for a in actions if a.key == 'utilities:follow-up-electricity')
    assert followup.task_id is None and 'completed' in followup.reason.lower()
    assert not any(a.task_id == str(target.task_id) for a in actions)
    assert revised.model_dump_json() == before
    target.status = TaskStatus.NOT_STARTED
    revised.task_reviews[str(target.task_id)] = TaskReview(applicable=False,description='Old scope',explanation='No longer applicable')
    inputs.reviewed_tasks = _reviewed(revised, {'utility:electricity'})
    actions = select_next_actions(inputs,(check_utilities(inputs,now=inputs.as_of),))
    followup = next(a for a in actions if a.key == 'utilities:follow-up-electricity')
    assert 'no longer applicable' in followup.reason.lower()
    assert followup.task_id is None


def test_real_recurring_reassessment_same_key_preserves_completed_history_and_links_new_open_task():
    from recovery.reassessment import preview_reassessment
    from recovery.models import TaskStatus, PlanStatus
    from recovery.progress.utilities import check_utilities
    from recovery.progress.priorities import select_next_actions
    case, plan, inputs = _real_plan_input(utility_availability={'electricity': True, 'water': True})
    outage = case.intake.model_copy(update={'utility_availability': {'electricity': False, 'water': True}})
    first = preview_reassessment(case, plan, outage).proposed_revision
    first.approval_status = PlanStatus.APPROVED
    old = next(task for task in first.proposed_tasks if task.planning_key == 'utility:electricity')
    old.status = TaskStatus.COMPLETED
    outage_case = case.model_copy(update={'intake': outage})
    restored = case.intake.model_copy(deep=True)
    second = preview_reassessment(outage_case, first, restored).proposed_revision
    second.approval_status = PlanStatus.APPROVED
    restored_case = case.model_copy(update={'intake': restored})
    third = preview_reassessment(restored_case, second, outage).proposed_revision
    recurring = next(task for task in third.proposed_tasks if task.planning_key == 'utility:electricity' and task.status != TaskStatus.COMPLETED)
    inputs.reviewed_tasks = _reviewed(third, {'utility:electricity'})
    before = third.model_dump_json()
    actions = select_next_actions(inputs, (check_utilities(inputs,now=inputs.as_of),))
    assert sum(action.task_id == str(recurring.task_id) for action in actions) == 1
    assert not any(action.task_id == str(old.task_id) for action in actions)
    assert not any(action.key == 'utilities:follow-up-electricity' for action in actions)
    assert third.model_dump_json() == before
