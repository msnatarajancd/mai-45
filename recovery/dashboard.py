"""Pure dashboard projection: confirmed history, current work, and user targets.

No pending proposals or inferred recovery milestones enter this view. Counts describe
user-reported task tracking, never safety, service delivery, or recovery completion.
"""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from .models import PlanStatus, RecoveryCase, RecoveryPlan, RecoveryRecords, TaskStatus
from .task_view import CurrentTaskView, current_task_views
from .timeline import JourneyEvent, build_timeline, normalize_as_of


@dataclass(frozen=True)
class TaskCounts:
    total: int = 0
    current: int = 0
    completed: int = 0
    in_progress: int = 0
    blocked: int = 0
    not_started: int = 0
    historical: int = 0
    completed_historical: int = 0


@dataclass(frozen=True)
class DashboardView:
    """Detached read-only projection; consumers should treat nested task views as read-only.

    elapsed_days is absent for unknown/future incident dates. target_days is a
    user-chosen check-in offset (negative means overdue), never a completion forecast.
    timeline contains accepted dated events only; changes filters it by the browser's
    last explicitly reviewed cursor. A None cursor is the first visit, not a claim
    about a previous login. An empty legacy timeline remains empty.
    """
    as_of: date
    incident_date: date | None
    elapsed_days: int | None
    incident_date_state: Literal['unknown', 'future', 'known']
    next_check_in_date: date | None
    target_days: int | None
    changes: tuple[JourneyEvent, ...]
    timeline: tuple[JourneyEvent, ...]
    latest_event_id: int | None
    first_visit: bool
    counts: TaskCounts
    next_task: CurrentTaskView | None
    emergency: bool
    danger_unassessed: bool


def build_dashboard(case: RecoveryCase, records: RecoveryRecords, plan: RecoveryPlan | None,
                    events: Iterable[Mapping | JourneyEvent], *, as_of: date | datetime | None = None,
                    since_event_id: int | None = None) -> DashboardView:
    """Project supplied current snapshots; this function performs no persistence.

    Historical simulation callers must supply snapshots from their chosen checkpoint;
    as_of filters event visibility and sets calendar arithmetic, not state replay.
    """
    if records.case_id != case.case_id or (plan is not None and plan.case_id != case.case_id):
        raise ValueError('dashboard records and plan must belong to the case')
    day, cutoff = normalize_as_of(as_of)
    timeline = build_timeline(events, as_of=cutoff)
    changes = tuple(event for event in timeline if since_event_id is None or event.event_id > since_event_id)
    views = current_task_views(plan) if plan is not None and plan.approval_status is PlanStatus.APPROVED else ()
    applicable = tuple(view for view in views if view.applicable)
    historical = tuple(view for view in views if not view.applicable)
    counts = TaskCounts(total=len(views), current=len(applicable),
        completed=sum(view.task.status is TaskStatus.COMPLETED for view in applicable),
        in_progress=sum(view.task.status is TaskStatus.IN_PROGRESS for view in applicable),
        blocked=sum(view.task.status is TaskStatus.BLOCKED for view in applicable),
        not_started=sum(view.task.status is TaskStatus.NOT_STARTED for view in applicable),
        historical=len(historical),
        completed_historical=sum(view.task.status is TaskStatus.COMPLETED for view in historical))
    next_task = next((view for view in applicable if view.task.status in
                     (TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS)), None) if case.intake.immediate_danger is False else None
    state = 'unknown' if records.incident_date is None else 'future' if records.incident_date > day else 'known'
    return DashboardView(as_of=day, incident_date=records.incident_date,
        elapsed_days=(day - records.incident_date).days if state == 'known' else None,
        incident_date_state=state, next_check_in_date=records.next_check_in_date,
        target_days=(records.next_check_in_date - day).days if records.next_check_in_date is not None else None,
        changes=changes, timeline=timeline, latest_event_id=timeline[-1].event_id if timeline else None,
        first_visit=since_event_id is None, counts=counts, next_task=next_task,
        emergency=case.intake.immediate_danger is True, danger_unassessed=case.intake.immediate_danger is None)
