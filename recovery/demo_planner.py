"""Deterministic organization tasks from confirmed reports, never safety verification."""
from .assessment import RecoveryAssessmentOutcome, RecoveryIntakeNotPermitted, evaluate_recovery_intake
from .models import RecoveryCase, RecoveryRecords, RecoveryPlan, RecoveryTask, TaskPriority


ACCOMMODATED = {'staying with others', 'staying in temporary lodging', 'temporary lodging', 'not needed'}


def accommodation_arranged(intake):
    return intake.temporary_accommodation_status.strip().casefold() in ACCOMMODATED


def create_demo_draft_plan(case: RecoveryCase, records: RecoveryRecords | None = None) -> RecoveryPlan:
    assessment = evaluate_recovery_intake(case.intake)
    if assessment.outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
        raise RecoveryIntakeNotPermitted(assessment)
    if records is not None and records.case_id != case.case_id:
        raise ValueError('records must belong to this recovery case')
    i = case.intake
    needs = {n.strip().casefold() for n in i.household_recovery_needs}
    tasks = []
    def add(key, title, description, reason, priority=TaskPriority.MEDIUM, categories=(), dependencies=()):
        tasks.append(RecoveryTask(planning_key=key, title=title, description=description,
            priority=priority, reason_for_recommendation=reason, resource_categories=list(categories),
            dependencies=list(dependencies)))
    if not accommodation_arranged(i):
        needed = i.temporary_accommodation_status.casefold() in {'needed', 'no lodging arranged'} or 'temporary housing' in needs
        add('housing', 'Review temporary housing options' if needed else 'Clarify accommodation arrangements',
            'Review official housing information from a safe location and record options to discuss. No room, placement or eligibility is established.',
            'Accommodation reported: '+i.temporary_accommodation_status,
            TaskPriority.HIGH if needed else TaskPriority.MEDIUM, ('Housing',))
    gaps = [name for name,v in sorted(i.utility_availability.items()) if v is False]
    unknown = [name for name,v in sorted(i.utility_availability.items()) if v is None]
    if gaps or unknown or not i.utility_availability:
        categories = tuple(n.capitalize() for n in gaps+unknown if n in {'electricity','water'})
        add('utilities', 'Record utility availability and gaps',
            'Identify the correct provider using a bill or official lookup. Record follow-ups for '+(', '.join(gaps) or 'unknown utilities')+'. Do not attempt repairs. Availability does not establish household safety or water potability.',
            'Reported unavailable: '+(', '.join(gaps) or 'none')+'; unknown: '+(', '.join(unknown) or ('not reported' if not i.utility_availability else 'none')),
            TaskPriority.HIGH if gaps else TaskPriority.MEDIUM, categories,
            ('Confirm the household provider before contacting it; no provider is assumed.',))
    add('safety', 'Review safe recovery boundaries',
        'Keep emergency controls accessible. Review reported hazards and official reentry information before any in-person activity. This plan does not authorize entry or utility work.',
        'Incident reported: '+i.disaster_type+'; housing: '+i.housing_condition,
        TaskPriority.HIGH, dependencies=('Any new immediate danger interrupts recovery; use emergency assistance.',))
    items = [d.item_description for d in records.damage_records] if records else []
    damage = bool(items or (records and records.household.reported_property_damage)) or any(t in i.housing_condition.casefold() for t in ('damage','flood','destroy')) and i.housing_condition.casefold() != 'no damage reported'
    if damage:
        add('damage', 'Organize known damage information',
            'Record confirmed item details'+(' for '+', '.join(items) if items else '')+' and information already known from a safe location. Do not enter a damaged building to inspect it or handle hazardous items.',
            'Confirmed damaged items: '+(', '.join(items) or 'not itemized')+'; housing: '+i.housing_condition,
            dependencies=('Document only when safe; do not enter or handle hazards to collect information.',))
    if any(t in n for n in needs for t in ('transport','vehicle','transit')):
        add('transport', 'Review reported transportation needs', 'Record confirmed transportation barriers and arrangements to discuss. No ride or pickup is promised.', 'Transportation was explicitly reported as a recovery need.')
    if 'water and household supplies' in needs:
        add('supplies', 'Prepare a household supplies checklist', 'List the supplies the household reports needing and record options to review.', 'Water and household supplies were explicitly reported.')
    if (records and (records.household.wants_insurance_help is True or records.damage_records)) or 'insurance preparation' in needs:
        add('insurance', 'Prepare an insurance discussion draft', 'Review the existing summary of confirmed damage and missing policy information before speaking with an insurer. No coverage, claim submission or outcome is established.', 'Confirmed damage or an explicit insurance-preparation request is on record.', TaskPriority.LOW,
            dependencies=('Review and confirm damaged-item records before including them in the discussion summary.',))
    add('followup', 'Review saved recovery records and follow-ups', 'Keep the case ID, review saved information and decide which follow-ups to undertake. Official disaster-assistance information is a pathway only, not an eligibility decision.', 'Saved recovery information is available for household review.', TaskPriority.LOW, ('Disaster assistance',))
    order = {TaskPriority.URGENT:0,TaskPriority.HIGH:1,TaskPriority.MEDIUM:2,TaskPriority.LOW:3}
    tasks.sort(key=lambda t: order[t.priority])
    return RecoveryPlan(case_id=case.case_id, proposed_tasks=tasks[:7], planning_basis=case.model_copy(deep=True),
        records_version=records.version if records else None,
        confirmed_damage_ids=[d.damage_id for d in records.damage_records] if records else [],
        planning_disclosure='Deterministic organization plan from confirmed household reports. Official directory pathways are not M3-reviewed guidance or checks of live availability, eligibility, coverage or household safety. No external submission is made.')
