"""Task-specific reviewed excerpts, using M3's live publication checks, without AI."""
from domain.contracts import GuidanceResult
from recovery.models import RecoveryCase, RecoveryRecords, RecoveryTask
from services.knowledge import retrieve_guidance


def guidance_for_task(task: RecoveryTask, case: RecoveryCase, records: RecoveryRecords,
                      *, service=None) -> GuidanceResult:
    if records.case_id != case.case_id:
        raise ValueError('Guidance records must belong to the current case.')
    hazard = {'flood': 'flood', 'hurricane': 'hurricane'}.get(case.intake.disaster_type.casefold())
    if not hazard or records.reported_county != 'Miami-Dade':
        return GuidanceResult(answer='Confirm the incident type and county to look up reviewed task guidance.',
            retrieval_status='INSUFFICIENT_EVIDENCE')
    key = task.planning_key or ''
    topics = {'housing': 'temporary housing', 'safety': 'building inspector',
              'damage': 'document flood damage photos', 'insurance': 'insurance claim documentation',
              'followup': 'disaster assistance', 'transport': 'transportation assistance',
              'supplies': 'household supplies'}
    topic = topics.get(key)
    if key == 'utilities' or key.startswith('utility:'):
        topic = 'tap water' if key == 'utility:water' or task.resource_categories == ['Water'] else 'electrician electrical'
    if topic is None:
        return GuidanceResult(answer='No reviewed guidance is attached to this organization step.',
            retrieval_status='NO_RELEVANT_EVIDENCE')
    return retrieve_guidance(topic, 'recover', hazard=hazard,
                             jurisdiction='US-FL-MIAMI-DADE', service=service)
