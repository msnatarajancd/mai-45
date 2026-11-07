"""Read-only translation of saved fictional reports into conservative progress facts."""
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID
from zoneinfo import ZoneInfo

from recovery.demo_planner import accommodation_arranged
from recovery.insurance_exports import missing_information
from recovery.models import TaskPriority, TaskStatus
from recovery.task_view import current_task_views
from .profiles import ProgressCaseSnapshot
from .models import (EvidenceRecord, HouseholdContext, ProgressInput, Provenance,
                     ReviewedTask, SourceMode, UtilityObservation)


def current_progress_revision(repo, case_id: UUID | str) -> str:
    """Polling-safe revision and persisted safety check; no photograph reads."""
    return repo.get_progress_revision(UUID(str(case_id)))


def load_saved_input(repo, case_id: UUID | str) -> ProgressInput:
    """Load one verified aggregate; unknown suitability, availability and cash stay unknown."""
    snapshot: ProgressCaseSnapshot = repo.get_progress_snapshot(UUID(str(case_id)))
    case, records, profile = snapshot.case, snapshot.records, snapshot.profile
    adults, children = records.household.adults, records.household.children
    total = profile.total
    assumptions = ['Saved utility observations are user reports, not verified address restoration.',
                   'Saved insurance preparation does not establish coverage, checklist suitability, or payment.',
                   'A repair contribution band is not an exact cash allocation.']
    if adults is not None and children is not None:
        if total is not None and total != adults + children:
            total = None
            assumptions.append('Household total conflicts with confirmed adult and child counts; total is unknown until reviewed.')
    household = HouseholdContext(label='Saved fictional household', total=total, adults=adults, children=children,
        zip_code=profile.zip_code, address=profile.address, county=records.reported_county,
        accessibility=profile.accessibility, pets=profile.pets, has_vehicle=profile.has_vehicle,
        housing_budget=profile.housing_budget, contribution_band=profile.contribution_band)
    utilities = []
    for service in ('electricity', 'water', 'gas'):
        available = case.intake.utility_availability.get(service)
        observed = case.updated_at
        status = 'available' if available is True else 'outage' if available is False else 'unknown'
        if service == 'gas':
            available = profile.gas_available
            status = ('not_applicable' if profile.gas_applicable is False else
                      'available' if available is True else 'outage' if available is False else 'unknown')
            observed = profile.updated_at or case.updated_at
        utilities.append(UtilityObservation(service=service, status=status,
            provider='User-reported saved case', provenance=Provenance(source_mode=SourceMode.SAVED_CASE,
                source='Confirmed household report', scope='user_report', observed_at=observed),
            note='Not independently verified. Water availability does not establish potability.' if service == 'water' else 'Not independently verified.'))
    status_map = {'File saved': 'saved', 'Reported available, not uploaded': 'reported_available',
                  'Not yet collected': 'not_collected', 'Unavailable': 'unavailable', 'Not applicable': 'not_applicable'}
    evidence = [EvidenceRecord(id=str(item.evidence_id), status=status_map[item.status.value],
        description=item.description) for item in snapshot.workspace.evidence]
    preparation = SimpleNamespace(case=case, records=records, workspace=snapshot.workspace,
                                  attachments=snapshot.attachment_metadata)
    tasks = []
    if snapshot.plan:
        tiers = {TaskPriority.URGENT: 1, TaskPriority.HIGH: 2, TaskPriority.MEDIUM: 3, TaskPriority.LOW: 4}
        tasks = [ReviewedTask(task_id=str(view.task.task_id), key=view.task.planning_key or str(view.task.task_id),
            title=view.task.title, reason=view.explanation, tier=tiers[view.priority],
            completed=view.task.status is TaskStatus.COMPLETED, applicable=view.applicable,
            dependencies=view.task.dependencies) for view in current_task_views(snapshot.plan)]
    reported_accommodation = case.intake.temporary_accommodation_status.strip().casefold()
    accommodation = ('arranged' if accommodation_arranged(case.intake) else
                     'needed' if reported_accommodation in {'needed', 'no lodging arranged'} else 'unknown')
    return ProgressInput(context_key='case:'+str(case.case_id), source_mode=SourceMode.SAVED_CASE,
        as_of=datetime.now(ZoneInfo('America/New_York')).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc),
        recovery_started=profile.recovery_started, household=household, immediate_danger=case.intake.immediate_danger,
        profile_version=profile.version, case_version=snapshot.revision, accommodation_status=accommodation,
        utilities=utilities, evidence=evidence, reviewed_tasks=tasks,
        general_preparation_missing=[category+': '+message for category, message in missing_information(preparation)],
        timing_assumptions=assumptions)
