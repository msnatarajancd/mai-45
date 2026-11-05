"""Read-only, deterministic reassessment. Callers must load current state from SQLite.

Preview drafts are deliberately not saved or activated by this service.
"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .assessment import RecoveryAssessmentOutcome, evaluate_recovery_intake
from .models import (PlanStatus, RecoveryCase, RecoveryIntake, RecoveryPlan,
                     RecoveryTask, TaskPriority, TaskStatus, TaskReview, RecoveryRecords)


class CircumstanceChange(BaseModel):
    field: str
    previous: Any
    updated: Any
    explanation: str


class TaskRecommendation(BaseModel):
    task: RecoveryTask
    explanation: str


class ReassessmentPreview(BaseModel):
    outcome: RecoveryAssessmentOutcome
    case_id: UUID
    previous_plan_id: UUID
    updated_intake: RecoveryIntake
    previous_case: RecoveryCase | None = None
    previous_plan: RecoveryPlan | None = None
    changed_circumstances: list[CircumstanceChange] = Field(default_factory=list)
    relevant_tasks: list[TaskRecommendation] = Field(default_factory=list)
    new_tasks: list[TaskRecommendation] = Field(default_factory=list)
    potentially_irrelevant_tasks: list[TaskRecommendation] = Field(default_factory=list)
    completed_tasks: list[TaskRecommendation] = Field(default_factory=list)
    proposed_revision: RecoveryPlan | None = None
    previous_records: RecoveryRecords | None = None
    updated_records: RecoveryRecords | None = None


def _normal(value: str) -> str:
    return " ".join(value.casefold().split())


def preview_reassessment(
    case: RecoveryCase, current_plan: RecoveryPlan, updated_intake: RecoveryIntake,
    *, previous_records: RecoveryRecords | None = None, updated_records: RecoveryRecords | None = None,
) -> ReassessmentPreview:
    """Compare a persisted case and approved plan with newly reported circumstances.

    Every existing task is retained in the draft, including tasks flagged for review.
    Unknown free-text circumstances are never interpreted as proof of safety.
    No repository calls, approval, removal or status resets occur. Proposed current descriptions, priorities and applicability are stored separately from original task history.
    """
    from .demo_planner import accommodation_arranged
    updated_intake = updated_intake.model_copy(deep=True)
    if (case.intake.temporary_accommodation_status != updated_intake.temporary_accommodation_status
            and accommodation_arranged(updated_intake)):
        updated_intake.household_recovery_needs = [n for n in updated_intake.household_recovery_needs if _normal(n) != 'temporary housing']
    if (previous_records is None) != (updated_records is None):
        raise ValueError('both original and updated records snapshots are required')
    if previous_records and (previous_records.case_id != case.case_id or updated_records.case_id != case.case_id):
        raise ValueError('records must belong to the recovery case')
    assessment = evaluate_recovery_intake(updated_intake)
    current_assessment = evaluate_recovery_intake(case.intake)
    # Ordinary reassessment cannot clear persisted danger or a missing assessment.
    # A danger report from either intake still takes emergency precedence.
    if (current_assessment.outcome is RecoveryAssessmentOutcome.EMERGENCY_HANDOFF
            or assessment.outcome is RecoveryAssessmentOutcome.CONTINUE_RECOVERY):
        assessment = current_assessment
    result = ReassessmentPreview(
        outcome=assessment.outcome, case_id=case.case_id,
        previous_plan_id=current_plan.plan_id,
        updated_intake=updated_intake.model_copy(deep=True),
        previous_case=case.model_copy(deep=True),
        previous_plan=current_plan.model_copy(deep=True),
        previous_records=previous_records.model_copy(deep=True) if previous_records else None,
        updated_records=updated_records.model_copy(deep=True) if updated_records else None,
    )
    if assessment.outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
        return result
    if current_plan.case_id != case.case_id:
        raise ValueError("the approved plan must belong to the recovery case")
    if current_plan.approval_status is not PlanStatus.APPROVED:
        raise ValueError("reassessment requires an approved plan")

    old = case.intake
    for field in ("disaster_type", "housing_condition", "temporary_accommodation_status"):
        before, after = getattr(old, field), getattr(updated_intake, field)
        if _normal(before) != _normal(after):
            result.changed_circumstances.append(CircumstanceChange(
                field=field, previous=before, updated=after,
                explanation=f"{field.replace('_', ' ').capitalize()} changed from '{before}' to '{after}'; review the related recovery arrangements.",
            ))
    for name in sorted(old.utility_availability.keys() | updated_intake.utility_availability.keys()):
        before = old.utility_availability.get(name)
        after = updated_intake.utility_availability.get(name)
        if before != after or (name in old.utility_availability) != (name in updated_intake.utility_availability):
            label = {True: "available", False: "unavailable", None: "unknown"}[after]
            result.changed_circumstances.append(CircumstanceChange(
                field=f"utility_availability.{name}", previous=before, updated=after,
                explanation=f"{name.capitalize()} is now reported as {label}. Review the previous utility task's priority; this does not establish household safety.",
            ))
    old_needs = {_normal(n): n for n in old.household_recovery_needs}
    new_needs = {_normal(n): n for n in updated_intake.household_recovery_needs}
    if old_needs.keys() != new_needs.keys():
        result.changed_circumstances.append(CircumstanceChange(
            field="household_recovery_needs", previous=old.household_recovery_needs,
            updated=updated_intake.household_recovery_needs,
            explanation="Reported household needs changed; review added needs and confirm whether omitted needs are resolved.",
        ))

    def add(title: str, explanation: str, description: str) -> None:
        # Reuse outstanding equivalents; a genuinely recurring report gets a new
        # follow-up instead of silently reopening previously completed work.
        base = _normal(title)
        equivalents = [t for t in current_plan.proposed_tasks if _normal(t.title) == base or _normal(t.title).startswith(base+' (new report ')]
        if any(t.status is not TaskStatus.COMPLETED for t in equivalents):
            return
        planning_key = ('utility:'+base.removeprefix('review ').removesuffix(' availability gap')) if base.endswith(' availability gap') else (
            'transport' if 'transportation' in base else 'need:'+base.removeprefix('review household need: ') if base.startswith('review household need: ') else None)
        if equivalents:
            title += ' (new report '+str(len(equivalents)+1)+')'
        if any(_normal(r.task.title) == _normal(title) for r in result.new_tasks):
            return
        task = RecoveryTask(title=title, description=description, planning_key=planning_key,
                            priority=TaskPriority.HIGH,
                            reason_for_recommendation=explanation)
        result.new_tasks.append(TaskRecommendation(task=task, explanation=explanation))

    changed_fields = {c.field for c in result.changed_circumstances}
    if changed_fields & {"housing_condition", "temporary_accommodation_status"}:
        add("Review changed housing arrangements",
            f"Housing is now reported as '{updated_intake.housing_condition}' and accommodation as '{updated_intake.temporary_accommodation_status}'. Confirm whether current arrangements meet household needs.",
            "Review accommodation needs and reported damage without entering damaged or unsafe buildings.")
    for change in result.changed_circumstances:
        if change.field.startswith("utility_availability.") and change.updated is not True:
            name = change.field.split(".", 1)[1]
            add(f"Review {name} availability gap", change.explanation,
                "Record the reported gap or uncertainty and review available household support options. Do not attempt utility repairs.")
    for key in sorted(new_needs.keys() - old_needs.keys()):
        need = new_needs[key]
        # The demo planner already supplies a transportation task.
        title = ("Review reported transportation needs" if any(
            term in key for term in ("transport", "vehicle", "transit"))
            else f"Review household need: {key}")
        add(title, f"The household newly reports '{need}'; review options to address this need.",
            "Record the reported need and options for household review; no external request is submitted.")

    all_available = bool(updated_intake.utility_availability) and all(
        v is True for v in updated_intake.utility_availability.values())
    removed_needs = old_needs.keys() - new_needs.keys()
    for original in current_plan.proposed_tasks:
        task = original.model_copy(deep=True)
        title = _normal(task.title)
        explanation = "Retained for review; the updated intake does not establish that this task is resolved."
        category = result.relevant_tasks
        if task.status is TaskStatus.COMPLETED:
            category = result.completed_tasks
            explanation = "Previously completed; its identity and completion status are preserved."
        elif ("utility" in title and all_available):
            category = result.potentially_irrelevant_tasks
            explanation = "All listed utilities are now reported available. Confirm whether utility follow-up is still needed; this does not establish household safety."
        elif ("transportation" in title and any("transport" in n or "vehicle" in n or "transit" in n for n in removed_needs)
              and not any("transport" in n or "vehicle" in n or "transit" in n for n in new_needs)):
            category = result.potentially_irrelevant_tasks
            explanation = "Transportation is no longer a reported need. Confirm resolution before removing the task."
        elif title.startswith("review household need: ") and title.removeprefix("review household need: ") in removed_needs:
            category = result.potentially_irrelevant_tasks
            explanation = "This need was omitted from the updated report. Confirm resolution before removing the task."
        elif "housing" in title and "temporary housing" in removed_needs:
            category = result.potentially_irrelevant_tasks
            explanation = "Temporary housing is no longer a reported need. Confirm accommodation needs before removing the task."
        category.append(TaskRecommendation(task=task, explanation=explanation))

    # Persist reviewed applicability separately from user-reported task status.
    # Old task objects and historical plans remain byte-for-byte meaningful.
    reviews = {}
    for task in current_plan.proposed_tasks:
        key = task.planning_key or ('housing' if 'housing' in _normal(task.title) else
            'utilities' if 'utility' in _normal(task.title) else None)
        prior_review = current_plan.task_reviews.get(str(task.task_id))
        applicable = prior_review.applicable if prior_review else True
        description = task.description
        explanation = prior_review.explanation if prior_review and not prior_review.applicable else 'Continue this task; no related confirmed circumstance has resolved its purpose.'
        if key == 'housing':
            applicable = not accommodation_arranged(updated_intake)
        if key == 'housing' and accommodation_arranged(updated_intake):
            applicable = False
            explanation = 'Temporary accommodation is now reported arranged. Seeking temporary housing is no longer a current unmet need; this does not verify household safety.'
        elif key == 'utilities':
            gaps = [n for n,v in updated_intake.utility_availability.items() if v is False]
            unknown = [n for n,v in updated_intake.utility_availability.items() if v is None]
            applicable = bool(gaps or unknown or not updated_intake.utility_availability)
            description = ('Reported unavailable: '+(', '.join(gaps) or 'none')+'; unknown: '+(', '.join(unknown) or 'none')+'. Follow up only on those gaps or questions; do not attempt repairs.')
            explanation = description+' Restored utilities do not establish household safety or drinking-water safety.'
        elif (task.planning_key and task.planning_key.startswith('utility:')) or (_normal(task.title).startswith('review ') and _normal(task.title).endswith(' availability gap')):
            name = task.planning_key.removeprefix('utility:') if task.planning_key else _normal(task.title).removeprefix('review ').removesuffix(' availability gap').strip()
            applicable = updated_intake.utility_availability.get(name) is not True
            explanation = name.capitalize()+' is now reported '+str(updated_intake.utility_availability.get(name))+'. Keep history; restoration does not establish safety.'
        elif task.planning_key and task.planning_key.startswith('need:'):
            applicable = task.planning_key.removeprefix('need:') in new_needs
            explanation = 'This reported need remains current.' if applicable else 'This need is no longer reported; keep the task history.'
        elif task.planning_key == 'transport':
            applicable = any('transport' in n or 'vehicle' in n or 'transit' in n for n in new_needs)
            explanation = 'Transportation follow-up remains current.' if applicable else 'Transportation is no longer reported as a current need; preserve historical status.'
        elif task.planning_key == 'supplies':
            applicable = 'water and household supplies' in new_needs
            explanation = 'Supplies follow-up remains current.' if applicable else 'Supplies are no longer a reported current need; preserve historical status.'
        elif any(r.task.task_id == task.task_id for r in result.potentially_irrelevant_tasks):
            applicable = False
            explanation = next(r.explanation for r in result.potentially_irrelevant_tasks if r.task.task_id == task.task_id)
        if task.status is not TaskStatus.COMPLETED:
            reviews[str(task.task_id)] = TaskReview(applicable=applicable, description=description, explanation=explanation,
                priority=(TaskPriority.HIGH if any(v is False for v in updated_intake.utility_availability.values()) else TaskPriority.MEDIUM) if key == 'utilities' else task.priority)
            # Category lists describe the actual persisted revision, including arranged housing.
            for category in (result.relevant_tasks, result.potentially_irrelevant_tasks):
                category[:] = [r for r in category if r.task.task_id != task.task_id]
            (result.relevant_tasks if applicable else result.potentially_irrelevant_tasks).append(
                TaskRecommendation(task=task.model_copy(deep=True), explanation=explanation))
    if updated_records and (updated_records.damage_records != previous_records.damage_records or
            any(d.damage_id not in current_plan.confirmed_damage_ids for d in updated_records.damage_records)):
        result.changed_circumstances.append(CircumstanceChange(field='damage_records',
            previous=[d.item_description for d in previous_records.damage_records],
            updated=[d.item_description for d in updated_records.damage_records],
            explanation='Damage-record changes are proposed for approval; existing damage and task progress are preserved.'))
        old_ids = set(current_plan.confirmed_damage_ids)
        for item in updated_records.damage_records:
            if item.damage_id not in old_ids:
                add('Document newly reported damage: '+item.item_description,
                    'The proposed update reports additional damage to '+item.item_description+'. Earlier completed documentation stays completed.',
                    'Once confirmed, review the reported item and insurance discussion records from a safe location. Do not enter or handle hazards to inspect this item.')
    result.proposed_revision = RecoveryPlan(
        case_id=case.case_id,
        task_reviews=reviews,
        confirmed_damage_ids=list(dict.fromkeys(current_plan.confirmed_damage_ids + ([d.damage_id for d in updated_records.damage_records] if updated_records else []))),
        planning_disclosure=current_plan.planning_disclosure,
        proposed_tasks=[t.model_copy(deep=True) for t in current_plan.proposed_tasks]
        + [r.task.model_copy(deep=True) for r in result.new_tasks],
    )
    return result
