import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .reassessment import ReassessmentPreview
from pathlib import Path
from typing import Iterator
from uuid import UUID

from .models import PlanStatus, RecoveryCase, RecoveryPlan, RecoveryTask, TaskStatus, RecoveryRecords


class SQLiteRecoveryRepository:
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = str(database_path)
        self._initialize_database()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_database(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_cases (
                    case_id TEXT PRIMARY KEY,
                    case_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_plans (
                    plan_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    FOREIGN KEY (case_id) REFERENCES recovery_cases (case_id)
                )
                """
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS recovery_reassessments (
                    plan_id TEXT PRIMARY KEY REFERENCES recovery_plans (plan_id),
                    preview_json TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS recovery_records (
                    case_id TEXT PRIMARY KEY REFERENCES recovery_cases (case_id),
                    records_json TEXT NOT NULL
                )"""
            )
            evidence_columns = {row[1] for row in connection.execute(
                "PRAGMA table_info(recovery_reassessments)")}
            if "approval_action" not in evidence_columns:
                connection.execute("ALTER TABLE recovery_reassessments ADD COLUMN approval_action TEXT NOT NULL DEFAULT 'legacy_unspecified'")
            case_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(recovery_cases)")
            }
            if "active_plan_id" not in case_columns:
                connection.execute(
                    """
                    ALTER TABLE recovery_cases
                    ADD COLUMN active_plan_id TEXT
                    REFERENCES recovery_plans (plan_id)
                    """
                )

    def get_recovery_records(self, case_id: UUID) -> RecoveryRecords:
        with self._connection() as connection:
            if connection.execute('SELECT 1 FROM recovery_cases WHERE case_id = ?',
                                  (str(case_id),)).fetchone() is None:
                raise ValueError('recovery case does not exist')
            row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id = ?',
                                     (str(case_id),)).fetchone()
        return RecoveryRecords.model_validate_json(row[0]) if row else RecoveryRecords(case_id=case_id)

    def save_recovery_records(self, records: RecoveryRecords, *, expected_version: int,
                              explicitly_confirmed: bool = False) -> RecoveryRecords:
        """Persist only confirmed records, with safety and concurrency under one lock.

        Intake, plan approvals and task progress are deliberately never written here.
        Existing damage IDs must be carried forward; this API does not delete records.
        """
        if explicitly_confirmed is not True:
            raise ValueError('explicit confirmation is required')
        records = RecoveryRecords.model_validate_json(records.model_dump_json())
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT case_json FROM recovery_cases WHERE case_id = ?',
                                     (str(records.case_id),)).fetchone()
            if row is None:
                raise ValueError('recovery case does not exist')
            case = RecoveryCase.model_validate_json(row[0])
            if case.intake.immediate_danger is not False:
                raise ValueError('record changes require an explicit no-immediate-danger assessment')
            row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id = ?',
                                     (str(records.case_id),)).fetchone()
            current = RecoveryRecords.model_validate_json(row[0]) if row else RecoveryRecords(case_id=records.case_id)
            if expected_version != current.version or records.version != current.version:
                raise ValueError('stale records: reload saved information before editing')
            ids = [item.damage_id for item in records.damage_records]
            if len(ids) != len(set(ids)) or any(item.case_id != records.case_id for item in records.damage_records):
                raise ValueError('damage IDs must be unique and belong to this case')
            if not {item.damage_id for item in current.damage_records}.issubset(ids):
                raise ValueError('existing damage records must be preserved')
            foreign_ids = {
                item.damage_id
                for other in connection.execute('SELECT records_json FROM recovery_records WHERE case_id != ?',
                                                 (str(records.case_id),))
                for item in RecoveryRecords.model_validate_json(other[0]).damage_records
            }
            if set(ids) & foreign_ids:
                raise ValueError('damage IDs cannot cross recovery cases')
            saved = records.model_copy(deep=True, update={'version': current.version + 1})
            connection.execute('INSERT INTO recovery_records (case_id, records_json) VALUES (?, ?) '
                               'ON CONFLICT(case_id) DO UPDATE SET records_json = excluded.records_json',
                               (str(records.case_id), saved.model_dump_json()))
        return saved

    def create_case(self, case: RecoveryCase) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO recovery_cases (case_id, case_json) VALUES (?, ?)",
                (str(case.case_id), case.model_dump_json()),
            )

    def get_case(self, case_id: UUID) -> RecoveryCase | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT case_json FROM recovery_cases WHERE case_id = ?",
                (str(case_id),),
            ).fetchone()

        if row is None:
            return None
        return RecoveryCase.model_validate_json(row[0])

    def save_draft_plan(self, plan: RecoveryPlan) -> None:
        if plan.approval_status is not PlanStatus.DRAFT:
            raise ValueError("only draft plans can be saved")

        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            ids = [task.task_id for task in plan.proposed_tasks]
            if len(ids) != len(set(ids)):
                raise ValueError("duplicate task IDs")
            foreign_ids = {
                task.task_id
                for row in connection.execute("SELECT plan_json FROM recovery_plans WHERE case_id != ?", (str(plan.case_id),))
                for task in RecoveryPlan.model_validate_json(row[0]).proposed_tasks
            }
            if set(ids) & foreign_ids:
                raise ValueError("task IDs cannot cross recovery cases")
            connection.execute(
                """
                INSERT INTO recovery_plans (plan_id, case_id, plan_json)
                VALUES (?, ?, ?)
                """,
                (str(plan.plan_id), str(plan.case_id), plan.model_dump_json()),
            )

    def get_plan(self, plan_id: UUID) -> RecoveryPlan | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT plan_json FROM recovery_plans WHERE plan_id = ?",
                (str(plan_id),),
            ).fetchone()

        if row is None:
            return None
        return RecoveryPlan.model_validate_json(row[0])

    def approve_plan(self, plan_id: UUID) -> RecoveryPlan:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT p.plan_json, c.case_json
                FROM recovery_plans AS p
                JOIN recovery_cases AS c ON c.case_id = p.case_id
                WHERE p.plan_id = ?
                """,
                (str(plan_id),),
            ).fetchone()
            if row is None:
                raise ValueError(f"recovery plan {plan_id} does not exist")

            plan = RecoveryPlan.model_validate_json(row[0])
            case = RecoveryCase.model_validate_json(row[1])
            if plan.approval_status is not PlanStatus.DRAFT:
                raise ValueError(f"recovery plan {plan_id} is not a draft")
            if not plan.proposed_tasks:
                raise ValueError("an empty recovery plan cannot be approved")
            if case.intake.immediate_danger is True:
                raise ValueError("approval is blocked while immediate danger is reported")
            if case.intake.immediate_danger is None:
                raise ValueError("immediate danger must be explicitly assessed before approval")

            active = connection.execute(
                "SELECT active_plan_id FROM recovery_cases WHERE case_id = ?",
                (str(case.case_id),),
            ).fetchone()[0]
            if active is not None:
                raise ValueError("an active plan exists; use reassessment approval")
            approved_plan = plan.model_copy(
                update={"approval_status": PlanStatus.APPROVED}
            )
            connection.execute(
                "UPDATE recovery_plans SET plan_json = ? WHERE plan_id = ?",
                (approved_plan.model_dump_json(), str(plan_id)),
            )
            connection.execute(
                "UPDATE recovery_cases SET active_plan_id = ? WHERE case_id = ?",
                (str(plan_id), str(plan.case_id)),
            )

        return approved_plan

    def get_active_plan(self, case_id: UUID) -> RecoveryPlan | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT p.plan_json
                FROM recovery_cases AS c
                JOIN recovery_plans AS p
                  ON p.plan_id = c.active_plan_id AND p.case_id = c.case_id
                WHERE c.case_id = ?
                """,
                (str(case_id),),
            ).fetchone()

        if row is None:
            return None
        return RecoveryPlan.model_validate_json(row[0])

    def update_task_status(
        self,
        plan_id: UUID,
        task_id: UUID,
        new_status: TaskStatus,
        *, expected_progress_version: int | None = None,
    ) -> RecoveryTask:
        """Update one task atomically.

        Interactive callers must pass the version displayed to the user. Omitting
        it retains the legacy unconditional-write API for trusted serial callers.
        """
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT case_id, plan_json FROM recovery_plans WHERE plan_id = ?",
                (str(plan_id),),
            ).fetchone()
            if row is None:
                raise ValueError(f"recovery plan {plan_id} does not exist")

            plan = RecoveryPlan.model_validate_json(row[1])
            if plan.approval_status is not PlanStatus.APPROVED:
                raise ValueError("task status can only be changed on an approved plan")

            active_row = connection.execute(
                "SELECT active_plan_id FROM recovery_cases WHERE case_id = ?",
                (row[0],),
            ).fetchone()
            if active_row is None or active_row[0] != str(plan_id):
                raise ValueError("task status can only be changed on the active plan")

            case_row = connection.execute(
                "SELECT case_json FROM recovery_cases WHERE case_id = ?", (row[0],)
            ).fetchone()
            if RecoveryCase.model_validate_json(case_row[0]).intake.immediate_danger is not False:
                raise ValueError("task updates require an explicit no-immediate-danger assessment")
            if expected_progress_version is not None and plan.progress_version != expected_progress_version:
                raise ValueError("stale task update: progress changed; review the current plan")
            try:
                status = TaskStatus(new_status)
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid task status: {new_status!r}") from error

            updated_task = None
            updated_tasks = []
            for task in plan.proposed_tasks:
                if task.task_id == task_id:
                    updated_task = task.model_copy(update={"status": status})
                    updated_tasks.append(updated_task)
                else:
                    updated_tasks.append(task)
            if updated_task is None:
                raise ValueError(f"task {task_id} does not belong to plan {plan_id}")

            updated_plan = plan.model_copy(update={"proposed_tasks": updated_tasks, "progress_version": plan.progress_version + 1})
            connection.execute(
                "UPDATE recovery_plans SET plan_json = ? WHERE plan_id = ?",
                (updated_plan.model_dump_json(), str(plan_id)),
            )

        return updated_task

    def list_approved_plans(self, case_id: UUID) -> list[RecoveryPlan]:
        """Return approved plans, including historical plans, in insertion order."""
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT plan_json FROM recovery_plans WHERE case_id = ? ORDER BY rowid",
                (str(case_id),),
            ).fetchall()
        return [plan for row in rows
                if (plan := RecoveryPlan.model_validate_json(row[0])).approval_status
                is PlanStatus.APPROVED]

    def approve_reassessment(
        self, preview: "ReassessmentPreview", *, explicitly_approved: bool = False,
    ) -> RecoveryPlan:
        """Accept the reviewed preview atomically, rejecting stale or altered drafts.

        Snapshots include the task progress version to detect even status changes
        subsequently reverted. Historical plans and assessment evidence are retained.
        """
        from .assessment import (RecoveryAssessmentOutcome, RecoveryIntakeNotPermitted,
                                 evaluate_recovery_intake)
        from .reassessment import ReassessmentPreview, preview_reassessment

        if explicitly_approved is not True:
            raise ValueError("explicit user approval is required")
        preview = ReassessmentPreview.model_validate_json(preview.model_dump_json())
        assessment = evaluate_recovery_intake(preview.updated_intake)
        if assessment.outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
            raise RecoveryIntakeNotPermitted(assessment)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT case_json, active_plan_id FROM recovery_cases WHERE case_id = ?",
                (str(preview.case_id),),
            ).fetchone()
            if row is None:
                raise ValueError("recovery case does not exist")
            case = RecoveryCase.model_validate_json(row[0])
            # Authoritative safety check under the same write lock as acceptance.
            # Incoming intake and caller snapshots cannot clear a persisted flag.
            current_assessment = evaluate_recovery_intake(case.intake)
            if current_assessment.outcome is not RecoveryAssessmentOutcome.CONTINUE_RECOVERY:
                raise RecoveryIntakeNotPermitted(current_assessment)
            if row[1] != str(preview.previous_plan_id):
                raise ValueError("stale reassessment: active plan changed; generate a new preview")
            plan_row = connection.execute(
                "SELECT plan_json FROM recovery_plans WHERE plan_id = ? AND case_id = ?",
                (row[1], str(case.case_id)),
            ).fetchone()
            if plan_row is None:
                raise ValueError("active recovery plan does not exist")
            current = RecoveryPlan.model_validate_json(plan_row[0])
            if case != preview.previous_case or current != preview.previous_plan:
                raise ValueError("stale reassessment: assessment or task progress changed; generate a new preview")
            expected = preview_reassessment(case, current, preview.updated_intake)
            proposed = preview.proposed_revision
            if (proposed is None or proposed.case_id != case.case_id
                    or proposed.approval_status is not PlanStatus.DRAFT
                    or proposed.plan_id == current.plan_id or proposed.progress_version != 0):
                raise ValueError("a new draft revision is required")
            # Only accept the reviewed deterministic proposal; no arbitrary task edits.
            expected_tasks = expected.proposed_revision.proposed_tasks
            old_count = len(current.proposed_tasks)
            if (len(proposed.proposed_tasks) != len(expected_tasks)
                    or proposed.proposed_tasks[:old_count] != current.proposed_tasks):
                raise ValueError("revision must preserve existing tasks and progress")
            for task, generated in zip(proposed.proposed_tasks[old_count:], expected_tasks[old_count:]):
                if task.model_dump(exclude={'task_id'}) != generated.model_dump(exclude={'task_id'}):
                    raise ValueError("revision tasks differ from the reassessment proposal")
            ids = [t.task_id for t in proposed.proposed_tasks]
            titles = [" ".join(t.title.casefold().split()) for t in proposed.proposed_tasks]
            if len(ids) != len(set(ids)) or len(titles) != len(set(titles)):
                raise ValueError("revision contains duplicate tasks")
            historical_ids = {
                task.task_id
                for historical_row in connection.execute(
                    "SELECT plan_json FROM recovery_plans")
                for task in RecoveryPlan.model_validate_json(historical_row[0]).proposed_tasks
            }
            if any(t.task_id in historical_ids for t in proposed.proposed_tasks[old_count:]):
                raise ValueError("new tasks require new task IDs")
            # Check the displayed explanations as well as executable tasks.
            expected.proposed_revision.plan_id = proposed.plan_id
            for index, recommendation in enumerate(expected.new_tasks):
                task_id = proposed.proposed_tasks[old_count + index].task_id
                recommendation.task.task_id = task_id
                expected.proposed_revision.proposed_tasks[old_count + index].task_id = task_id
            if preview != expected:
                raise ValueError("review evidence differs from the reassessment proposal")
            approved = proposed.model_copy(deep=True, update={'approval_status': PlanStatus.APPROVED})
            accepted_case = case.model_copy(deep=True, update={
                'intake': preview.updated_intake.model_copy(deep=True),
                'updated_at': datetime.now(timezone.utc),
            })
            connection.execute(
                "INSERT INTO recovery_plans (plan_id, case_id, plan_json) VALUES (?, ?, ?)",
                (str(approved.plan_id), str(case.case_id), approved.model_dump_json()),
            )
            connection.execute(
                "INSERT INTO recovery_reassessments (plan_id, preview_json, approval_action) VALUES (?, ?, 'explicit_user_approval')",
                (str(approved.plan_id), preview.model_dump_json()),
            )
            connection.execute(
                "UPDATE recovery_cases SET case_json = ?, active_plan_id = ? WHERE case_id = ?",
                (accepted_case.model_dump_json(), str(approved.plan_id), str(case.case_id)),
            )
        return approved

    def report_immediate_danger(self, case_id: UUID) -> None:
        """Persist an interruption so other sessions cannot continue routine writes."""
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT case_json FROM recovery_cases WHERE case_id = ?",
                                     (str(case_id),)).fetchone()
            if row is None:
                raise ValueError("recovery case does not exist")
            case = RecoveryCase.model_validate_json(row[0])
            if case.intake.immediate_danger is True:
                return
            case.intake.immediate_danger = True
            case.updated_at = datetime.now(timezone.utc)
            connection.execute("UPDATE recovery_cases SET case_json = ? WHERE case_id = ?",
                               (case.model_dump_json(), str(case_id)))
