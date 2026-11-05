"""M5 consumer of the shared M1 recovery extraction contract. No model or network calls.

The wire boundary is checked without copying M1's generic DTO classes or importing
its extraction DTOs. The original result/message live only in an ephemeral review.
"""
import hashlib
import json
import re
from typing import Any
from uuid import UUID, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field

from .assessment import evaluate_recovery_intake, RecoveryAssessmentOutcome
from .models import RecoveryCase, RecoveryRecords, RecoveryIntake, RecoveryPlan, DamageRecord
from .reassessment import preview_reassessment


CHOICES = {
    'disaster_type': ['Flood', 'Hurricane'],
    'housing_condition': ['Flooded', 'Minor reported damage', 'Major reported damage', 'Destroyed', 'No damage reported'],
    'electricity': ['Available', 'Unavailable'], 'water': ['Available', 'Unavailable'],
    'temporary_accommodation': ['Needed', 'Staying with others', 'Temporary lodging', 'Not needed'],
    'household_recovery_needs': ['Temporary housing', 'Water and household supplies', 'Transportation', 'Damage documentation', 'Insurance preparation'],
}
FIELDS = tuple(['disaster_type', 'reported_county', 'housing_condition', 'electricity', 'water',
                'temporary_accommodation', 'household_recovery_needs', 'children', 'adults',
                'insurance_preparation_requested'])
STATUSES = {'SUCCESS', 'NEEDS_CLARIFICATION', 'DANGER_DETECTED', 'UNAVAILABLE', 'ERROR'}
ERROR_CODES = {None, 'invalid_context', 'invalid_message', 'invalid_model_output',
               'unsupported_extraction', 'missing_key', 'timeout', 'provider_error'}


def _valid(name, value):
    if name in ('children', 'adults'):
        return type(value) is int and 0 <= value <= 100
    if name == 'insurance_preparation_requested':
        return type(value) is bool
    if name == 'reported_county':
        return type(value) is str and bool(value.strip()) and len(value) <= 80
    if name == 'household_recovery_needs':
        return type(value) is list and len(value) <= 5 and all(type(v) is str and v in CHOICES[name] for v in value)
    return type(value) is str and value in CHOICES[name]


def confirmed_context(case=None, records=None):
    """Exact M1 context keys/defaults. Unrepresentable legacy facts stay in M5."""
    context = dict.fromkeys(FIELDS)
    context.update(reported_damage=[], danger_reported=None)
    if case is None:
        if records is not None:
            raise ValueError('records require a case')
        return context
    if records is None or records.case_id != case.case_id:
        raise ValueError('case-bound records are required')
    i, h = case.intake, records.household
    source = dict(disaster_type=i.disaster_type, housing_condition=i.housing_condition,
                  temporary_accommodation={'Staying in temporary lodging': 'Temporary lodging'}.get(
                      i.temporary_accommodation_status, i.temporary_accommodation_status),
                  household_recovery_needs=i.household_recovery_needs,
                  children=h.children, adults=h.adults, reported_county=records.reported_county,
                  insurance_preparation_requested=h.wants_insurance_help)
    for utility in ('electricity', 'water'):
        value = i.utility_availability.get(utility)
        source[utility] = {True: 'Available', False: 'Unavailable', None: None}[value]
    for name, value in source.items():
        if value is not None and _valid(name, value):
            context[name] = value
    damage = [d.item_description for d in records.damage_records]
    if len(damage) > 50 or any(len(d) > 120 for d in damage):
        raise ValueError('saved damage exceeds M1 context limits; use structured editing')
    context.update(reported_damage=damage, danger_reported=i.immediate_danger)
    return context


def context_fingerprint(context):
    return hashlib.sha256(json.dumps(context, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class ExtractionReview(BaseModel):
    """M5 review snapshot, not another extraction or saved-household model."""
    model_config = ConfigDict(extra='forbid')
    review_id: str = Field(default_factory=lambda: uuid4().hex)
    new_case_id: UUID = Field(default_factory=uuid4)
    result: dict[str, Any]
    message: str
    previous_case: RecoveryCase | None = None
    previous_records: RecoveryRecords | None = None
    previous_plan: RecoveryPlan | None = None
    proposed: dict[str, Any] = Field(default_factory=dict)
    quotes: dict[str, str] = Field(default_factory=dict)
    unresolved: list[str] = Field(default_factory=list)


def prepare_review(result, message, *, case=None, records=None, plan=None):
    """Validate a supplied M1 result; produce no writes, approvals or model calls."""
    wire = result.model_dump(mode='json') if isinstance(result, BaseModel) else result
    wire = json.loads(json.dumps(wire))
    keys = {'status', 'base_context_fingerprint', 'fields', 'new_damage', 'clarification_questions', 'error_code'}
    if (not isinstance(wire, dict) or set(wire) != keys or type(wire['status']) is not str
            or wire['status'] not in STATUSES or type(wire['error_code']) not in (str, type(None))
            or wire['error_code'] not in ERROR_CODES):
        raise ValueError('unsupported M1 extraction envelope')
    if not isinstance(message, str) or len(message) > 2500:
        raise ValueError('invalid extraction message')
    context = confirmed_context(case, records)
    if wire['status'] != 'ERROR' or wire['error_code'] != 'invalid_context':
        if wire['base_context_fingerprint'] != context_fingerprint(context):
            raise ValueError('stale extraction context fingerprint')
    if not isinstance(wire['fields'], dict) or set(wire['fields']) != set(FIELDS):
        raise ValueError('unsupported extraction fields')
    review = ExtractionReview(result=wire, message=message, previous_case=case,
                              previous_records=records, previous_plan=plan)
    if case:
        legacy = {'disaster_type': case.intake.disaster_type,
                  'housing_condition': case.intake.housing_condition,
                  'temporary_accommodation': case.intake.temporary_accommodation_status,
                  'household_recovery_needs': case.intake.household_recovery_needs,
                  'children': records.household.children, 'adults': records.household.adults}
        for name, value in legacy.items():
            if value not in (None, 'Unknown') and context[name] is None:
                review.unresolved.append('Saved ' + name + ' (preserved; outside M1 vocabulary)')
    from emergency.service import recovery_requires_emergency
    if context['danger_reported'] is True or recovery_requires_emergency(message):
        review.result['status'] = 'DANGER_DETECTED'
        return review.model_copy(deep=True)
    if wire['status'] == 'ERROR' and wire['error_code'] == 'invalid_context':
        return review.model_copy(deep=True)
    for name, item in wire['fields'].items():
        if not isinstance(item, dict) or set(item) != {'state', 'value', 'source_quote'}:
            raise ValueError('invalid field proposal')
        state, value, quote = item['state'], item['value'], item['source_quote']
        if state == 'UNKNOWN':
            if value is not None or quote is not None or context[name] is not None:
                raise ValueError('unknown field conflicts with confirmed context')
        elif state == 'UNCHANGED':
            if quote is not None or value is None or type(value) is not type(context[name]) or value != context[name]:
                raise ValueError('unchanged field conflicts with confirmed context')
        elif state == 'PROPOSED':
            if wire['status'] not in {'SUCCESS', 'NEEDS_CLARIFICATION'}:
                raise ValueError('failure results cannot contain proposals')
            if not isinstance(quote, str) or not quote.strip() or quote not in message:
                raise ValueError('proposal has no exact supporting quote')
            if name == 'reported_county' and type(value) is str and not re.search(
                    r'(?<!\w)' + re.escape(value) + r'(?!\w)', quote, re.I):
                raise ValueError('county was not explicitly reported')
            review.quotes[name] = quote
            if not _valid(name, value) or (name == 'reported_county' and value != 'Miami-Dade'):
                review.unresolved.append(name)
            else:
                review.proposed[name] = value
        else:
            raise ValueError('unsupported field state')
    damage = wire['new_damage']
    if not isinstance(damage, list) or len(damage) > 20:
        raise ValueError('invalid damage proposals')
    for index, item in enumerate(damage):
        if (not isinstance(item, dict) or set(item) != {'state', 'value', 'source_quote'}
                or item['state'] != 'PROPOSED' or type(item['value']) is not str
                or not item['value'].strip() or len(item['value']) > 120
                or type(item['source_quote']) is not str or not item['source_quote'].strip()
                or item['source_quote'] not in message or not re.search(
                    r'(?<!\w)' + re.escape(item['value']) + r'(?!\w)', item['source_quote'], re.I)):
            raise ValueError('invalid damage proposal or quote')
        if wire['status'] not in {'SUCCESS', 'NEEDS_CLARIFICATION'}:
            raise ValueError('failure results cannot contain damage proposals')
        review.proposed[f'damage:{index}'] = item['value']
        review.quotes[f'damage:{index}'] = item['source_quote']
    if (not isinstance(wire['clarification_questions'], list) or len(wire['clarification_questions']) > 11
            or any(type(q) is not str or not 0 < len(q) <= 250 for q in wire['clarification_questions'])):
        raise ValueError('invalid clarification questions')
    return review.model_copy(deep=True)


def require_current(repo, review):
    if review.previous_case is None:
        return
    case = repo.get_case(review.previous_case.case_id)
    records = repo.get_recovery_records(review.previous_case.case_id)
    if case != review.previous_case or records != review.previous_records:
        raise ValueError('stale extraction: saved information changed; review a fresh proposal')
    if review.previous_plan is not None and repo.get_active_plan(case.case_id) != review.previous_plan:
        raise ValueError('stale extraction: active plan or task progress changed')
    if review.result['status'] == 'ERROR' and review.result['error_code'] == 'invalid_context':
        return
    if context_fingerprint(confirmed_context(case, records)) != review.result['base_context_fingerprint']:
        raise ValueError('stale extraction fingerprint')


def selected_changes(review, selected, corrections=None):
    """Merge explicitly selected, editable proposals onto the complete M5 snapshots."""
    corrections = corrections or {}
    if not set(selected) <= set(review.proposed):
        raise ValueError('only resolved proposed changes can be selected')
    case_id = review.previous_case.case_id if review.previous_case else review.new_case_id
    intake = (review.previous_case.intake.model_copy(deep=True) if review.previous_case else
              RecoveryIntake(disaster_type='Unknown', housing_condition='Unknown', utility_availability={},
                  temporary_accommodation_status='Unknown', immediate_danger=None, household_recovery_needs=[]))
    records = (review.previous_records.model_copy(deep=True) if review.previous_records else RecoveryRecords(case_id=case_id))
    seen = {' '.join(d.item_description.casefold().split()) for d in records.damage_records}
    for name in selected:
        value = corrections.get(name, review.proposed[name])
        if name.startswith('damage:'):
            if type(value) is not str or not value.strip() or len(value) > 120:
                raise ValueError('a reported damaged item is required')
            key = ' '.join(value.casefold().split())
            if key not in seen:
                records.damage_records.append(DamageRecord(damage_id=uuid5(review.new_case_id, name), case_id=case_id, item_description=value,
                    damage_description=review.quotes[name]))
                seen.add(key)
        else:
            if not _valid(name, value):
                raise ValueError('unsupported corrected value: ' + name)
            if name in ('electricity', 'water'):
                intake.utility_availability[name] = {'Available': True, 'Unavailable': False}[value]
            elif name == 'temporary_accommodation':
                intake.temporary_accommodation_status = value
            elif name in ('disaster_type', 'housing_condition'):
                setattr(intake, name, value)
            elif name == 'household_recovery_needs':
                intake.household_recovery_needs = list(dict.fromkeys(intake.household_recovery_needs + value))
            elif name in ('children', 'adults'):
                setattr(records.household, name, value)
            elif name == 'insurance_preparation_requested':
                records.household.wants_insurance_help = value
            elif name == 'reported_county':
                if value != 'Miami-Dade':
                    raise ValueError('county is not supported; use structured input')
                records.reported_county = value
    from .demo_planner import accommodation_arranged
    if 'temporary_accommodation' in selected and accommodation_arranged(intake):
        intake.household_recovery_needs = [n for n in intake.household_recovery_needs if n.strip().casefold() != 'temporary housing']
    return intake, RecoveryRecords.model_validate_json(records.model_dump_json())


def accept_review(repo, review, selected, *, corrections=None, explicitly_confirmed=False,
                  safety_answer=None, approved_revision=None, reviewed_intake=None):
    """Explicit acceptance only; intake changes require the displayed reassessment."""
    if explicitly_confirmed is not True:
        raise ValueError('explicit user confirmation is required')
    # Revalidate even when a stored review was reconstructed or model_copy bypassed validation.
    validated = prepare_review(review.result, review.message, case=review.previous_case,
                               records=review.previous_records, plan=review.previous_plan)
    validated.new_case_id = review.new_case_id
    if validated.result['status'] not in {'SUCCESS', 'NEEDS_CLARIFICATION'}:
        raise ValueError('extraction is unavailable or interrupted; use structured input')
    require_current(repo, validated)
    intake, records = selected_changes(validated, selected, corrections)
    if not selected:
        raise ValueError('select at least one change')
    if validated.previous_case is None:
        if safety_answer is not False:
            raise ValueError('an explicit safety assessment is required before creating a case')
        if reviewed_intake is not None:
            intake = RecoveryIntake.model_validate_json(reviewed_intake.model_dump_json())
            if intake.immediate_danger is not False:
                raise ValueError('an explicit no-danger intake is required')
        intake.immediate_danger = False
        case = RecoveryCase(case_id=records.case_id, intake=intake)
        if evaluate_recovery_intake(intake).outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
            raise ValueError('routine recovery is not permitted')
        repo.create_case(case, confirmed_records=records, explicitly_confirmed=True)
        return case
    if reviewed_intake is not None:
        raise ValueError('returning intake changes require reassessment')
    case = validated.previous_case
    if case.intake.immediate_danger is not False:
        raise ValueError('persisted safety assessment blocks routine updates')
    if intake != case.intake or (approved_revision is not None and records != validated.previous_records):
        if safety_answer is not False or approved_revision is None:
            raise ValueError('review and explicitly approve a reassessment first')
        if (approved_revision.previous_case != case or approved_revision.previous_plan != validated.previous_plan
                or approved_revision.updated_intake != intake):
            raise ValueError('revision does not match selected changes')
        repo.approve_reassessment(approved_revision, explicitly_approved=True,
            confirmed_records=records, expected_records_version=validated.previous_records.version)
    else:
        repo.save_recovery_records(records, expected_version=validated.previous_records.version,
                                   expected_case=case, explicitly_confirmed=True)
    return repo.get_case(case.case_id)


def revision_for_selection(review, selected, corrections=None):
    intake, _ = selected_changes(review, selected, corrections)
    if review.previous_case is None or (intake == review.previous_case.intake and selected_changes(review, selected, corrections)[1].damage_records == review.previous_records.damage_records):
        return None
    if review.previous_plan is None:
        if intake == review.previous_case.intake:
            return None
        raise ValueError('approve the existing initial plan before changing its intake')
    return preview_reassessment(review.previous_case, review.previous_plan, intake,
        previous_records=review.previous_records, updated_records=selected_changes(review, selected, corrections)[1])
