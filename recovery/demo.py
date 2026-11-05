"""Explicit, offline synthetic journey replay through the real repository APIs.

Reading definitions never opens a database. Each explicit checkpoint load creates
a fresh case in the caller's dedicated demo database. Day N means N elapsed days
after the fixed fictional incident, with all accepted writes stamped at noon UTC.
Checkpoint summaries and pending proposals are presentation data, never events.
"""
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .database import SQLiteRecoveryRepository
from .demo_planner import create_demo_draft_plan
from .models import (DamageRecord, HouseholdRecoveryDetails, RecoveryCase,
                     RecoveryIntake, RecoveryPlan, RecoveryRecords, TaskStatus)
from .reassessment import ReassessmentPreview, preview_reassessment


INCIDENT_DATE = date(2026, 10, 1)
_FIXTURE_PATH = Path(__file__).with_name("fixtures") / "journeys.json"


class _FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _synthetic_label(value: str) -> str:
    if not all(word in value.casefold() for word in ("synthetic", "fictional")):
        raise ValueError("synthetic fictional labeling is required")
    return value


class _SyntheticIntake(RecoveryIntake):
    model_config = ConfigDict(extra="forbid")
    disaster_type: Literal["Hurricane", "Flood"]


class IntakeChange(_FixtureModel):
    housing_condition: str | None = None
    utility_availability: dict[str, bool | None] | None = None
    temporary_accommodation_status: str | None = None
    household_recovery_needs: list[str] | None = None


class HouseholdChange(_FixtureModel):
    children: int | None = Field(default=None, ge=0, strict=True)
    adults: int | None = Field(default=None, ge=0, strict=True)
    reported_property_damage: str | None = None
    wants_insurance_help: bool | None = None
    housing_type: str | None = None
    accessibility_needs: list[str] | None = None
    insurer_contact_status: Literal["Unknown", "Not contacted", "Contacted", "Follow-up requested"] | None = None


class ReportedDamage(_FixtureModel):
    item_description: str = Field(min_length=1)
    damage_description: str = Field(min_length=1)
    notes: str | None = None


class JourneyCheckpoint(_FixtureModel):
    day: int = Field(ge=1, strict=True)
    summary: str
    task_statuses: dict[str, TaskStatus] = Field(default_factory=dict)
    approved_intake: IntakeChange | None = None
    confirmed_household: HouseholdChange | None = None
    confirmed_damage: tuple[ReportedDamage, ...] = ()
    next_check_in_date: date | None = None
    pending_intake: IntakeChange | None = None
    pending_change_description: str | None = None
    immediate_danger: bool = False

    _label_summary = field_validator("summary")(_synthetic_label)

    @model_validator(mode="after")
    def require_honest_proposals_and_danger(self):
        if (self.pending_intake is None) != (self.pending_change_description is None):
            raise ValueError("pending changes need both an unsaved proposal and description")
        if self.pending_change_description is not None:
            _synthetic_label(self.pending_change_description)
        if self.immediate_danger and (self.task_statuses or self.approved_intake
                or self.confirmed_household or self.confirmed_damage or self.pending_intake
                or "next_check_in_date" in self.model_fields_set):
            raise ValueError("danger checkpoints must interrupt ordinary writes")
        return self


class ScenarioDefinition(_FixtureModel):
    """Validated presentation definition; use checkpoint_days for UI options."""
    scenario_id: Literal["rivera", "bennett", "patel", "chen", "johnson", "lewis"]
    label: str
    description: str
    classification: Literal["SYNTHETIC_FICTIONAL"]
    incident_date: date
    intake: _SyntheticIntake
    household: HouseholdRecoveryDetails = Field(default_factory=HouseholdRecoveryDetails)
    damage_records: tuple[ReportedDamage, ...] = ()
    next_check_in_date: date | None = None
    checkpoints: tuple[JourneyCheckpoint, ...]

    _label_label = field_validator("label")(_synthetic_label)
    _label_description = field_validator("description")(_synthetic_label)

    @property
    def checkpoint_days(self) -> tuple[int, ...]:
        return tuple(checkpoint.day for checkpoint in self.checkpoints)

    @model_validator(mode="after")
    def require_fixed_replay(self):
        expected = (1, 3, 7) if self.scenario_id in {"rivera", "bennett", "patel"} else (1, 3, 7, 14, 30)
        if self.incident_date != INCIDENT_DATE or self.checkpoint_days != expected:
            raise ValueError("scenario must use the fixed incident date and required checkpoints")
        if self.intake.immediate_danger is not False:
            raise ValueError("journeys must begin with an explicit no-immediate-danger report")
        if any(cp.immediate_danger for cp in self.checkpoints[:-1]):
            raise ValueError("danger ends a replay; it cannot be cleared by a later checkpoint")
        return self


class _JourneyFixtures(_FixtureModel):
    classification: Literal["SYNTHETIC_FICTIONAL"]
    scenarios: tuple[ScenarioDefinition, ...]


@dataclass(frozen=True)
class DemoSelection:
    case_id: UUID
    scenario_id: str
    scenario_label: str
    day: int
    as_of: date
    previous_checkpoint_event_cursor: int | None
    pending_change_description: str | None
    immediate_danger: bool
    pending_revision_json: str | None = None


class _StoredSelection(_FixtureModel):
    """Strict persisted envelope; routine recovery tables never contain replay UI state."""
    case_id: UUID
    scenario_id: str
    scenario_label: str
    day: int = Field(ge=1, strict=True)
    as_of: date
    previous_checkpoint_event_cursor: int | None = Field(default=None, ge=1, strict=True)
    pending_change_description: str | None = None
    immediate_danger: bool = Field(strict=True)
    pending_revision_json: str | None = None

    _label_label = field_validator('scenario_label')(_synthetic_label)

    @model_validator(mode='after')
    def require_complete_pending_preview(self):
        if (self.pending_revision_json is None) != (self.pending_change_description is None):
            raise ValueError('saved pending previews need both review data and description')
        if self.pending_change_description is not None:
            _synthetic_label(self.pending_change_description)
        return self


def _save_selection(path: Path, selection: DemoSelection) -> None:
    """Only explicit fresh loads write replay metadata in their dedicated demo DB."""
    saved = _StoredSelection.model_validate(asdict(selection))
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('''CREATE TABLE IF NOT EXISTS recovery_demo_selections (
            case_id TEXT PRIMARY KEY REFERENCES recovery_cases(case_id),
            selection_json TEXT NOT NULL)''')
        connection.execute('INSERT INTO recovery_demo_selections (case_id, selection_json) VALUES (?, ?)',
                            (str(selection.case_id), saved.model_dump_json()))


def resume_checkpoint(database_path: str | Path, case_id: UUID | str) -> DemoSelection:
    """Resume an existing replay without writes, new IDs, or resetting saved progress.

    Read metadata and current domain snapshots in one read-only SQLite transaction.
    The original simulated day/cursor remains a presentation reference; actual case,
    plan and records always remain authoritative. Stale pending proposals are omitted
    from the returned selection without modifying either metadata or journey history.
    """
    try:
        requested_id = UUID(str(case_id))
        path = Path(database_path).expanduser().resolve()
        # mode=ro also prevents accidental file/schema creation for absent/legacy IDs.
        uri = path.as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.execute('BEGIN')
            row = connection.execute('SELECT selection_json FROM recovery_demo_selections WHERE case_id=?',
                                     (str(requested_id),)).fetchone()
            if row is None:
                raise ValueError('No saved fictional checkpoint matches this case ID.')
            saved = _StoredSelection.model_validate_json(row[0])
            if saved.case_id != requested_id:
                raise ValueError('Saved fictional checkpoint metadata belongs to a different case.')
            scenario = next((item for item in list_scenarios() if item.scenario_id == saved.scenario_id), None)
            if (scenario is None or saved.day not in scenario.checkpoint_days
                    or saved.as_of != scenario.incident_date + timedelta(days=saved.day)):
                raise ValueError('Saved fictional checkpoint metadata is invalid.')
            row = connection.execute('SELECT case_json, active_plan_id FROM recovery_cases WHERE case_id=?',
                                     (str(requested_id),)).fetchone()
            if row is None:
                raise ValueError('The saved fictional recovery case is unavailable.')
            case = RecoveryCase.model_validate_json(row[0])
            if case.case_id != requested_id:
                raise ValueError('Saved fictional recovery case identity is invalid.')
            plan = None
            if row[1] is not None:
                plan_row = connection.execute('SELECT plan_json FROM recovery_plans WHERE plan_id=? AND case_id=?',
                                              (row[1], str(requested_id))).fetchone()
                if plan_row is None:
                    raise ValueError('The saved fictional recovery plan is unavailable.')
                plan = RecoveryPlan.model_validate_json(plan_row[0])
                if plan.case_id != requested_id or str(plan.plan_id) != row[1]:
                    raise ValueError('Saved fictional recovery plan identity is invalid.')
            records_row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id=?',
                                              (str(requested_id),)).fetchone()
            records = (RecoveryRecords.model_validate_json(records_row[0]) if records_row
                       else RecoveryRecords(case_id=requested_id))
            if records.case_id != requested_id:
                raise ValueError('Saved fictional recovery records identity is invalid.')
            cursor = saved.previous_checkpoint_event_cursor
            if cursor is not None and connection.execute(
                    'SELECT 1 FROM recovery_journey_events WHERE case_id=? AND event_id=?',
                    (str(requested_id), cursor)).fetchone() is None:
                raise ValueError('Saved fictional checkpoint event cursor is invalid.')
            selection = DemoSelection(**saved.model_dump())
            pending = (ReassessmentPreview.model_validate_json(selection.pending_revision_json)
                       if selection.pending_revision_json is not None else None)
            if pending is not None and (pending.case_id != requested_id
                    or pending.previous_plan_id != (plan.plan_id if plan else None)
                    or pending.previous_case != case or pending.previous_plan != plan
                    or pending.previous_records != records or case.intake.immediate_danger is not False):
                selection = replace(selection, pending_revision_json=None, pending_change_description=None)
            return replace(selection, immediate_danger=case.intake.immediate_danger is True)
    except (OSError, sqlite3.Error) as error:
        raise ValueError('Saved fictional recovery storage is unavailable or has no replay metadata.') from error


def list_scenarios() -> tuple[ScenarioDefinition, ...]:
    """Read validated synthetic definitions without creating cases or making calls."""
    fixtures = _JourneyFixtures.model_validate(json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")))
    ids = [scenario.scenario_id for scenario in fixtures.scenarios]
    if ids != ["rivera", "bennett", "patel", "chen", "johnson", "lewis"]:
        raise ValueError("the six synthetic scenarios must appear exactly once in household order")
    return fixtures.scenarios


def _updated_intake(intake: RecoveryIntake, change: IntakeChange) -> RecoveryIntake:
    return RecoveryIntake.model_validate({
        **intake.model_dump(), **change.model_dump(exclude_unset=True)})


def _damage(case_id: UUID, reported: ReportedDamage, incident_date: date) -> DamageRecord:
    return DamageRecord(case_id=case_id, incident_date=incident_date, **reported.model_dump())


def load_checkpoint(database_path: str | Path, scenario_id: str, day: int) -> DemoSelection:
    """Create one fresh replay up to a validated checkpoint in a dedicated demo DB.

    The caller supplies the demo database path and calls only after an explicit UI
    load action. Repeated loads intentionally create different case/task IDs. No
    existing case, plan or danger report is selected for mutation or replacement.
    The cursor identifies the end of the preceding checkpoint in this new replay.
    A pending change is previewed in memory and never approved or persisted.
    """
    scenario = next((s for s in list_scenarios() if s.scenario_id == scenario_id), None)
    if scenario is None:
        raise ValueError(f"Unknown synthetic scenario: {scenario_id!r}")
    if type(day) is not int or day not in scenario.checkpoint_days:
        raise ValueError(f"Unknown checkpoint day {day!r} for {scenario_id}")
    checkpoint = next(cp for cp in scenario.checkpoints if cp.day == day)
    simulated_time = datetime.combine(scenario.incident_date + timedelta(days=1), time(12), timezone.utc)
    path = Path(database_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    repository = SQLiteRecoveryRepository(path, clock=lambda: simulated_time)
    case = RecoveryCase(intake=RecoveryIntake.model_validate(scenario.intake.model_dump()),
                        created_at=simulated_time, updated_at=simulated_time)
    records = RecoveryRecords(case_id=case.case_id, incident_date=scenario.incident_date,
                              next_check_in_date=scenario.next_check_in_date,
                              household=scenario.household.model_copy(deep=True),
                              damage_records=[_damage(case.case_id, item, scenario.incident_date)
                                              for item in scenario.damage_records])
    repository.create_case(case, confirmed_records=records, explicitly_confirmed=True)
    records = repository.get_recovery_records(case.case_id)
    draft = create_demo_draft_plan(case, records)
    repository.approve_plan(draft.plan_id, new_draft=draft, explicitly_approved=True)
    previous_cursor = None
    pending_revision_json = None
    for current in scenario.checkpoints:
        if current.day > day:
            break
        if current.day > 1:
            events = repository.list_journey_events(case.case_id)
            previous_cursor = events[-1]["event_id"] if events else None
        simulated_time = datetime.combine(scenario.incident_date + timedelta(days=current.day),
                                          time(12), timezone.utc)
        if current.immediate_danger:
            repository.report_immediate_danger(case.case_id)
            break
        # Apply real reported task transitions before a revision, preserving their IDs.
        for planning_key, status in current.task_statuses.items():
            plan = repository.get_active_plan(case.case_id)
            task = next((task for task in plan.proposed_tasks if task.planning_key == planning_key), None)
            if task is None:
                raise ValueError(f"synthetic checkpoint references absent task {planning_key!r}")
            repository.update_task_status(plan.plan_id, task.task_id, status,
                                          expected_progress_version=plan.progress_version)
        records = repository.get_recovery_records(case.case_id)
        record_changes = bool(current.confirmed_household or current.confirmed_damage
                              or "next_check_in_date" in current.model_fields_set)
        updated_records = records.model_copy(deep=True)
        if current.confirmed_household is not None:
            updated_records.household = HouseholdRecoveryDetails.model_validate({
                **records.household.model_dump(),
                **current.confirmed_household.model_dump(exclude_unset=True)})
        updated_records.damage_records.extend(_damage(case.case_id, item, scenario.incident_date)
                                              for item in current.confirmed_damage)
        if "next_check_in_date" in current.model_fields_set:
            updated_records.next_check_in_date = current.next_check_in_date
        if current.approved_intake is not None:
            case = repository.get_case(case.case_id)
            plan = repository.get_active_plan(case.case_id)
            preview = preview_reassessment(case, plan,
                _updated_intake(case.intake, current.approved_intake),
                previous_records=records, updated_records=updated_records)
            repository.approve_reassessment(preview, explicitly_approved=True,
                confirmed_records=updated_records if record_changes else None,
                expected_records_version=records.version)
        elif record_changes:
            repository.save_recovery_records(updated_records, expected_version=records.version,
                                             explicitly_confirmed=True,
                                             expected_case=repository.get_case(case.case_id))
        if current.pending_intake is not None:
            case = repository.get_case(case.case_id)
            records = repository.get_recovery_records(case.case_id)
            pending_preview = preview_reassessment(case, repository.get_active_plan(case.case_id),
                _updated_intake(case.intake, current.pending_intake),
                previous_records=records, updated_records=records)
            if current.day == day:
                pending_revision_json = pending_preview.model_dump_json()
    saved_case = repository.get_case(case.case_id)
    selection = DemoSelection(case_id=case.case_id, scenario_id=scenario.scenario_id,
                         scenario_label=scenario.label, day=day,
                         as_of=scenario.incident_date + timedelta(days=day),
                         previous_checkpoint_event_cursor=previous_cursor,
                         pending_change_description=checkpoint.pending_change_description,
                         immediate_danger=saved_case.intake.immediate_danger is True,
                         pending_revision_json=pending_revision_json)
    _save_selection(path, selection)
    return selection
