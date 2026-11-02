from .assessment import (
    RecoveryAssessmentOutcome,
    RecoveryIntakeNotPermitted,
    evaluate_recovery_intake,
)
from .models import (
    PlanStatus,
    RecoveryCase,
    RecoveryPlan,
    RecoveryTask,
    TaskPriority,
    TaskStatus,
)


def create_demo_draft_plan(case: RecoveryCase) -> RecoveryPlan:
    assessment = evaluate_recovery_intake(case.intake)
    if assessment.outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
        raise RecoveryIntakeNotPermitted(assessment)

    intake = case.intake
    reported_needs = ", ".join(intake.household_recovery_needs)
    if not reported_needs:
        reported_needs = "No specific household needs were listed."

    utility_summary = ", ".join(
        f"{name}: {('available' if available is True else 'unavailable' if available is False else 'unknown')}"
        for name, available in sorted(intake.utility_availability.items())
    )
    if not utility_summary:
        utility_summary = "No utility information was listed."

    tasks = [
        RecoveryTask(
            title="Review temporary housing options",
            description=(
                "List possible temporary accommodation options for household review. "
                "Do not enter any building reported damaged or unsafe."
            ),
            priority=TaskPriority.HIGH,
            reason_for_recommendation=(
                f"Housing condition: {intake.housing_condition}; "
                f"temporary accommodation: {intake.temporary_accommodation_status}."
            ),
            status=TaskStatus.NOT_STARTED,
            source_reference=None,
        ),
        RecoveryTask(
            title="Record utility availability and gaps",
            description=(
                "Record which household utilities are available, unavailable, or unknown "
                "for later follow-up."
            ),
            priority=TaskPriority.MEDIUM,
            reason_for_recommendation=f"Reported utility status: {utility_summary}.",
            status=TaskStatus.NOT_STARTED,
            source_reference=None,
        ),
        RecoveryTask(
            title="Prepare a household supplies checklist",
            description=(
                "Organize reported essential household needs into a checklist for review."
            ),
            priority=TaskPriority.MEDIUM,
            reason_for_recommendation=f"Reported household needs: {reported_needs}",
            status=TaskStatus.NOT_STARTED,
            source_reference=None,
        ),
        RecoveryTask(
            title="Organize known damage information",
            description=(
                "Record damage details already known or observed from a safe location. "
                "Do not enter a building to inspect it."
            ),
            priority=TaskPriority.MEDIUM,
            reason_for_recommendation=(
                f"Reported housing condition: {intake.housing_condition}."
            ),
            status=TaskStatus.NOT_STARTED,
            source_reference=None,
        ),
    ]

    transportation_terms = ("transport", "transportation", "vehicle", "transit")
    if any(
        term in need.casefold()
        for need in intake.household_recovery_needs
        for term in transportation_terms
    ):
        tasks.append(
            RecoveryTask(
                title="Review reported transportation needs",
                description=(
                    "Record reported transportation barriers and options for household review."
                ),
                priority=TaskPriority.MEDIUM,
                reason_for_recommendation=(
                    f"Reported household needs: {reported_needs}"
                ),
                status=TaskStatus.NOT_STARTED,
                source_reference=None,
            )
        )

    unique_tasks = list({task.title: task for task in tasks}.values())
    return RecoveryPlan(
        case_id=case.case_id,
        proposed_tasks=unique_tasks,
        approval_status=PlanStatus.DRAFT,
    )