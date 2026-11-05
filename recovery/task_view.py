"""Shared read-only projection of current task reviews over preserved task history."""
from dataclasses import dataclass

from .models import RecoveryPlan, RecoveryTask, TaskPriority, TaskReview


@dataclass(frozen=True)
class CurrentTaskView:
    task: RecoveryTask
    priority: TaskPriority
    applicable: bool
    description: str
    explanation: str
    review: TaskReview | None


def current_task_views(plan: RecoveryPlan) -> tuple[CurrentTaskView, ...]:
    """Return detached views, stably ordered by effective reviewed priority.

    Applicability and user-reported status are independent. Historical tasks stay
    in this projection so every consumer can retain their recorded progress.
    Mutating a returned task/review cannot mutate the source plan.
    """
    order = {TaskPriority.URGENT: 0, TaskPriority.HIGH: 1,
             TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
    views = []
    for task in plan.proposed_tasks:
        review = plan.task_reviews.get(str(task.task_id))
        views.append(CurrentTaskView(
            task=task.model_copy(deep=True),
            priority=review.priority if review and review.priority else task.priority,
            applicable=review.applicable if review else True,
            description=review.description if review else task.description,
            explanation=review.explanation if review else task.reason_for_recommendation,
            review=review.model_copy(deep=True) if review else None,
        ))
    return tuple(sorted(views, key=lambda view: order[view.priority]))
