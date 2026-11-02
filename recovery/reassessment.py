"""Read-only, deterministic reassessment. Callers must load current state from SQLite.

Preview drafts are deliberately not saved or activated by this service.
"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .assessment import RecoveryAssessmentOutcome, evaluate_recovery_intake
from .models import (PlanStatus, RecoveryCase, RecoveryIntake, RecoveryPlan,
                     RecoveryTask, TaskPriority, TaskStatus)


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


def _normal(value: str) -> str:
    return " ".join(value.casefold().split())


def preview_reassessment(
    case: RecoveryCase, current_plan: RecoveryPlan, updated_intake: RecoveryIntake,
) -> ReassessmentPreview:
    """Compare a persisted case and approved plan with newly reported circumstances.

    Every existing task is retained in the draft, including tasks flagged for review.
    Unknown free-text circumstances are never interpreted as proof of safety.
    No repository calls, approval, removal, reprioritization, or status resets occur.
    """
    assessment = evaluate_recovery_intake(updated_intake)
    result = ReassessmentPreview(
        outcome=assessment.outcome, case_id=case.case_id,
        previous_plan_id=current_plan.plan_id,
        updated_intake=updated_intake.model_copy(deep=True),
        previous_case=case.model_copy(deep=True),
        previous_plan=current_plan.model_copy(deep=True),
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
        # A completed equivalent task is kept completed, never silently reopened.
        if any(_normal(t.title) == _normal(title) for t in current_plan.proposed_tasks):
            return
        if any(_normal(r.task.title) == _normal(title) for r in result.new_tasks):
            return
        task = RecoveryTask(title=title, description=description,
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

    result.proposed_revision = RecoveryPlan(
        case_id=case.case_id,
        proposed_tasks=[t.model_copy(deep=True) for t in current_plan.proposed_tasks]
        + [r.task.model_copy(deep=True) for r in result.new_tasks],
    )
    return result
