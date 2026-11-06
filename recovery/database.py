import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .reassessment import ReassessmentPreview
from pathlib import Path
from typing import Iterator
from uuid import UUID

from .models import PlanStatus, RecoveryCase, RecoveryPlan, RecoveryTask, TaskStatus, RecoveryRecords


class SQLiteRecoveryRepository:
    def __init__(self, database_path: str | Path, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._injected_clock = clock is not None
        self._database_path = str(database_path)
        self._initialize_database()

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('repository clock must return a timezone-aware datetime')
        return value.astimezone(timezone.utc)

    def _append_journey_event(self, connection, case_id, kind, title, detail, *, occurred_at=None):
        connection.execute(
            'INSERT INTO recovery_journey_events (case_id,kind,title,detail,occurred_at) VALUES (?,?,?,?,?)',
            (str(case_id), kind, title, detail, (occurred_at or self._now()).isoformat()))

    def list_journey_events(self, case_id: UUID) -> list[dict]:
        """Recorded accepted changes only; legacy history is never backfilled."""
        with self._connection() as connection:
            rows = connection.execute(
                'SELECT event_id,kind,title,detail,occurred_at FROM recovery_journey_events '
                'WHERE case_id = ? ORDER BY event_id', (str(case_id),)).fetchall()
        return [dict(zip(('event_id', 'kind', 'title', 'detail', 'occurred_at'), row)) for row in rows]

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
            connection.execute('''CREATE TABLE IF NOT EXISTS recovery_insurance_workspaces (
                case_id TEXT PRIMARY KEY REFERENCES recovery_cases(case_id), workspace_json TEXT NOT NULL)''')
            connection.execute('''CREATE TABLE IF NOT EXISTS recovery_insurance_attachments (
                attachment_id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES recovery_cases(case_id),
                metadata_json TEXT NOT NULL, content BLOB NOT NULL)''')
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
            connection.execute("""CREATE TABLE IF NOT EXISTS recovery_task_events (
                event_id INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES recovery_cases(case_id),
                plan_id TEXT NOT NULL REFERENCES recovery_plans(plan_id), task_id TEXT NOT NULL,
                previous_status TEXT NOT NULL, new_status TEXT NOT NULL, changed_at TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS recovery_journey_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES recovery_cases(case_id),
                kind TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
                occurred_at TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS recovery_progress_profiles (
                case_id TEXT PRIMARY KEY REFERENCES recovery_cases(case_id), profile_json TEXT NOT NULL)""")
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
                              explicitly_confirmed: bool = False,
                              expected_case: RecoveryCase | None = None) -> RecoveryRecords:
        """Persist only confirmed records, with safety and concurrency under one lock.

        Intake, plan approvals and task progress are deliberately never written here.
        Existing damage IDs must be carried forward; this API does not delete records.
        """
        if explicitly_confirmed is not True:
            raise ValueError('explicit confirmation is required')
        records = RecoveryRecords.model_validate_json(records.model_dump_json())
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            return self._write_recovery_records(connection, records, expected_version, expected_case)

    def _write_recovery_records(self, connection, records, expected_version, expected_case=None):
        """Called only inside the caller's write transaction, including reassessment."""
        records = RecoveryRecords.model_validate_json(records.model_dump_json())
        row = connection.execute('SELECT case_json FROM recovery_cases WHERE case_id = ?',
                                     (str(records.case_id),)).fetchone()
        if row is None:
            raise ValueError('recovery case does not exist')
        case = RecoveryCase.model_validate_json(row[0])
        if case.intake.immediate_danger is not False:
            raise ValueError('record changes require an explicit no-immediate-danger assessment')
        if expected_case is not None and case != expected_case:
            raise ValueError('stale records: saved assessment changed')
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
        unchanged = records == current
        saved = records.model_copy(deep=True, update={'version': current.version + 1})
        connection.execute('INSERT INTO recovery_records (case_id, records_json) VALUES (?, ?) '
                               'ON CONFLICT(case_id) DO UPDATE SET records_json = excluded.records_json',
                               (str(records.case_id), saved.model_dump_json()))
        from .timeline import describe_records_changes, records_change_title
        if not unchanged:
            self._append_journey_event(connection, records.case_id, 'records_confirmed',
                records_change_title(current, saved), describe_records_changes(current, saved))
        return saved

    def create_case(self, case: RecoveryCase, *, confirmed_records: RecoveryRecords | None = None,
                    explicitly_confirmed: bool = False) -> None:
        if confirmed_records is not None and explicitly_confirmed is not True:
            raise ValueError('explicit confirmation is required for initial recovery records')
        # Preserve existing caller timestamps unless the replay clock was requested.
        if self._injected_clock:
            now = self._now()
            case.created_at = now
            case.updated_at = now
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute(
                "INSERT INTO recovery_cases (case_id, case_json) VALUES (?, ?)",
                (str(case.case_id), case.model_dump_json()),
            )
            self._append_journey_event(connection, case.case_id, 'case_created',
                'Recovery situation saved', 'User-reported situation recorded.', occurred_at=case.created_at)
            if confirmed_records is not None:
                if confirmed_records.case_id != case.case_id:
                    raise ValueError('records do not belong to this case')
                self._write_recovery_records(connection, confirmed_records, 0, case)

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

    def approve_plan(self, plan_id: UUID, *, new_draft: RecoveryPlan | None = None, explicitly_approved: bool = False) -> RecoveryPlan:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if new_draft is not None:
                if explicitly_approved is not True or new_draft.plan_id != plan_id or new_draft.approval_status is not PlanStatus.DRAFT:
                    raise ValueError('matching draft and explicit approval are required')
                ids = [t.task_id for t in new_draft.proposed_tasks]
                titles = [' '.join(t.title.casefold().split()) for t in new_draft.proposed_tasks]
                if len(set(ids)) != len(ids) or len(set(titles)) != len(titles):
                    raise ValueError('duplicate tasks are not permitted')
                existing_ids = {t.task_id for row in connection.execute('SELECT plan_json FROM recovery_plans') for t in RecoveryPlan.model_validate_json(row[0]).proposed_tasks}
                if existing_ids.intersection(ids):
                    raise ValueError('new initial tasks require unique IDs')
                connection.execute('INSERT INTO recovery_plans (plan_id,case_id,plan_json) VALUES (?,?,?)',
                    (str(plan_id),str(new_draft.case_id),new_draft.model_dump_json()))
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

            if plan.planning_basis is not None and case != plan.planning_basis:
                raise ValueError('stale draft: confirmed assessment changed; generate a fresh plan')
            if plan.records_version is not None:
                records_row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id = ?', (str(case.case_id),)).fetchone()
                version = RecoveryRecords.model_validate_json(records_row[0]).version if records_row else 0
                if version != plan.records_version:
                    raise ValueError('stale draft: confirmed records changed; generate a fresh plan')
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

            self._append_journey_event(connection, plan.case_id, 'plan_approved',
                'Recovery plan approved', f'{len(plan.proposed_tasks)} tasks approved for tracking.')

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
        expected_records_version: int | None = None,
    ) -> RecoveryTask:
        """Update one task atomically.

        Interactive callers must pass the progress version displayed to the user.
        Record-bound proposals also pass their confirmed-record version. Omitting
        either guard retains the legacy API for trusted serial callers.
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
            if expected_records_version is not None:
                records_row = connection.execute(
                    'SELECT records_json FROM recovery_records WHERE case_id = ?', (row[0],)
                ).fetchone()
                records_version = RecoveryRecords.model_validate_json(records_row[0]).version if records_row else 0
                if records_version != expected_records_version:
                    raise ValueError('stale task update: confirmed records changed; review the current plan')
            applicability = plan.task_reviews.get(str(task_id))
            if applicability is not None and not applicability.applicable:
                raise ValueError('this task is no longer applicable; preserve its historical status')
            try:
                status = TaskStatus(new_status)
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid task status: {new_status!r}") from error

            previous_status = None
            updated_task = None
            updated_tasks = []
            for task in plan.proposed_tasks:
                if task.task_id == task_id:
                    previous_status = task.status
                    updated_task = task.model_copy(update={"status": status})
                    updated_tasks.append(updated_task)
                else:
                    updated_tasks.append(task)
            if updated_task is None:
                raise ValueError(f"task {task_id} does not belong to plan {plan_id}")

            if previous_status == status:
                return updated_task
            changed_at = self._now()
            if previous_status != status:
                connection.execute('INSERT INTO recovery_task_events (case_id,plan_id,task_id,previous_status,new_status,changed_at) VALUES (?,?,?,?,?,?)',
                    (row[0],str(plan_id),str(task_id),previous_status.value,status.value,changed_at.isoformat()))
            self._append_journey_event(connection, row[0], 'task_status_changed',
                updated_task.title, f'{previous_status.value.replace("_", " ").title()} → {status.value.replace("_", " ").title()}. User-reported task progress.', occurred_at=changed_at)
            updated_plan = plan.model_copy(update={"proposed_tasks": updated_tasks, "progress_version": plan.progress_version + 1})
            connection.execute(
                "UPDATE recovery_plans SET plan_json = ? WHERE plan_id = ?",
                (updated_plan.model_dump_json(), str(plan_id)),
            )

        return updated_task

    def list_task_history(self, case_id: UUID) -> list[dict]:
        with self._connection() as connection:
            rows = connection.execute('SELECT task_id,plan_id,previous_status,new_status,changed_at FROM recovery_task_events WHERE case_id = ? ORDER BY event_id', (str(case_id),)).fetchall()
        return [dict(zip(('task_id','plan_id','previous_status','new_status','changed_at'), row)) for row in rows]

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
        confirmed_records: RecoveryRecords | None = None,
        expected_records_version: int | None = None,
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
            if confirmed_records is not None and (confirmed_records.case_id != case.case_id
                                                  or expected_records_version is None):
                raise ValueError('case-bound records and their displayed version are required')
            if expected_records_version is not None:
                records_row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id = ?',
                                                  (str(case.case_id),)).fetchone()
                version = RecoveryRecords.model_validate_json(records_row[0]).version if records_row else 0
                if version != expected_records_version:
                    raise ValueError('stale reassessment: recovery records changed')
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
            if preview.previous_records is not None:
                records_row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id = ?', (str(case.case_id),)).fetchone()
                records = RecoveryRecords.model_validate_json(records_row[0]) if records_row else RecoveryRecords(case_id=case.case_id)
                if records != preview.previous_records:
                    raise ValueError('stale reassessment: confirmed records changed')
                if preview.updated_records != records and confirmed_records != preview.updated_records:
                    raise ValueError('updated records require the matching explicit confirmation')
                if confirmed_records is not None and confirmed_records != preview.updated_records:
                    raise ValueError('confirmed records differ from the reviewed proposal')
            expected = preview_reassessment(case, current, preview.updated_intake,
                previous_records=preview.previous_records, updated_records=preview.updated_records)
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
            if confirmed_records is not None:
                self._write_recovery_records(connection, confirmed_records, expected_records_version, case)
            approved = proposed.model_copy(deep=True, update={'approval_status': PlanStatus.APPROVED})
            accepted_case = case.model_copy(deep=True, update={
                'intake': preview.updated_intake.model_copy(deep=True),
                'updated_at': self._now(),
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
            from .timeline import describe_intake_changes, intake_change_title
            self._append_journey_event(connection, case.case_id, 'revision_approved',
                intake_change_title(case.intake, accepted_case.intake), describe_intake_changes(case.intake, accepted_case.intake),
                occurred_at=accepted_case.updated_at)
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
            case.updated_at = self._now()
            connection.execute("UPDATE recovery_cases SET case_json = ? WHERE case_id = ?",
                               (case.model_dump_json(), str(case_id)))
            self._append_journey_event(connection, case_id, 'danger_reported',
                'Immediate danger reported', 'Routine recovery work paused for emergency support.',
                occurred_at=case.updated_at)

    def _insurance_snapshot(self, connection, case_id):
        from .insurance_models import InsuranceWorkspace, InsuranceSnapshot, SavedPhoto, InsuranceAttachment
        row = connection.execute('SELECT case_json FROM recovery_cases WHERE case_id=?', (str(case_id),)).fetchone()
        if row is None:
            raise ValueError('Recovery case does not exist.')
        case = RecoveryCase.model_validate_json(row[0])
        if case.intake.immediate_danger is not False:
            raise ValueError('Insurance preparation is paused until the required safety assessment permits routine work.')
        row = connection.execute('SELECT records_json FROM recovery_records WHERE case_id=?', (str(case_id),)).fetchone()
        records = RecoveryRecords.model_validate_json(row[0]) if row else RecoveryRecords(case_id=case_id)
        row = connection.execute('SELECT workspace_json FROM recovery_insurance_workspaces WHERE case_id=?', (str(case_id),)).fetchone()
        workspace = InsuranceWorkspace.model_validate_json(row[0]) if row else InsuranceWorkspace(case_id=case_id)
        photos = [SavedPhoto(metadata=InsuranceAttachment.model_validate_json(meta), content=bytes(content))
                  for meta, content in connection.execute('SELECT metadata_json,content FROM recovery_insurance_attachments WHERE case_id=? ORDER BY rowid', (str(case_id),))]
        snapshot = InsuranceSnapshot(case=case, records=records, workspace=workspace, attachments=photos)
        self._validate_insurance_snapshot(snapshot)
        return snapshot

    @staticmethod
    def _validate_insurance_snapshot(snapshot):
        from .insurance_models import EvidenceStatus
        from .attachments import verify_saved_photo, MAX_ATTACHMENTS, MAX_CASE_BYTES
        case_id = snapshot.case.case_id
        workspace, records = snapshot.workspace, snapshot.records
        if workspace.case_id != case_id or records.case_id != case_id:
            raise ValueError('Insurance records do not belong to this case.')
        damage_ids = {item.damage_id for item in records.damage_records}
        photos = {photo.metadata.attachment_id: photo for photo in snapshot.attachments}
        if len(photos) != len(snapshot.attachments) or len(photos) > MAX_ATTACHMENTS:
            raise ValueError('Duplicate attachments or the 20-attachment limit was exceeded.')
        if sum(len(photo.content) for photo in photos.values()) > MAX_CASE_BYTES:
            raise ValueError('Attachments exceed the 50 MiB case limit.')
        for photo in photos.values():
            meta = photo.metadata
            if meta.case_id != case_id or (meta.damage_id is not None and meta.damage_id not in damage_ids):
                raise ValueError('Attachment does not belong to this case and damaged item.')
            verify_saved_photo(photo)
        if len({p.metadata.sha256 for p in photos.values()}) != len(photos):
            raise ValueError('This photograph is already saved in the case.')
        for collection, attribute in ((workspace.items, 'damage_id'), (workspace.evidence, 'evidence_id'),
                                       (workspace.communications, 'communication_id')):
            ids = [getattr(entry, attribute) for entry in collection]
            if len(ids) != len(set(ids)):
                raise ValueError('Duplicate insurance record IDs.')
        if any(item.damage_id not in damage_ids for item in workspace.items):
            raise ValueError('Item preparation details reference an unknown damaged item.')
        referenced = []
        for evidence in workspace.evidence:
            if evidence.case_id != case_id or (evidence.damage_id is not None and evidence.damage_id not in damage_ids):
                raise ValueError('Evidence does not belong to this case and damaged item.')
            if evidence.status is EvidenceStatus.FILE_SAVED:
                photo = photos.get(evidence.attachment_id)
                if photo is None or photo.metadata.damage_id != evidence.damage_id or photo.metadata.evidence_type != evidence.evidence_type:
                    raise ValueError('File saved requires a matching actual saved attachment.')
                referenced.append(evidence.attachment_id)
            elif evidence.attachment_id is not None:
                raise ValueError('Only File saved evidence can reference an attachment.')
        if len(referenced) != len(set(referenced)) or set(referenced) != set(photos):
            raise ValueError('Every saved attachment requires exactly one matching evidence record.')

    def get_insurance_snapshot(self, case_id: UUID):
        """One consistent saved read, including actual verified original bytes. No insertion."""
        with self._connection() as connection:
            connection.execute('BEGIN')
            return self._insurance_snapshot(connection, case_id)

    def save_insurance_workspace(self, workspace, *, expected_case, expected_records_version,
                                 expected_workspace_version, explicitly_confirmed=False,
                                 additions=(), removals=()):
        """One atomic case/records/workspace CAS; never modifies intake, tasks or damage."""
        from .insurance_models import InsuranceWorkspace, SavedPhoto, EvidenceRecord, EvidenceStatus
        if explicitly_confirmed is not True:
            raise ValueError('Explicit confirmation is required before saving Insurance changes.')
        workspace = InsuranceWorkspace.model_validate_json(workspace.model_dump_json())
        additions = [SavedPhoto.model_validate(photo.model_dump()) for photo in additions]
        removals = list(removals)
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            current = self._insurance_snapshot(connection, workspace.case_id)
            if (current.case != expected_case or current.records.version != expected_records_version
                    or current.workspace.version != expected_workspace_version
                    or workspace.version != expected_workspace_version):
                raise ValueError('Stale Insurance workspace. Reload saved information before editing.')
            if len(removals) != len(set(removals)) or not set(removals).issubset({p.metadata.attachment_id for p in current.attachments}):
                raise ValueError('Removal references an attachment outside this case.')
            # Historical communications cannot silently disappear or be rewritten.
            for entry in current.workspace.communications:
                if entry not in workspace.communications:
                    raise ValueError('Preserve historical communication entries; append a correction instead.')
            if not {e.evidence_id for e in current.workspace.evidence}.issubset({e.evidence_id for e in workspace.evidence}):
                raise ValueError('Existing evidence records must be preserved.')
            for evidence in workspace.evidence:
                if evidence.attachment_id in removals:
                    evidence.attachment_id = None
                    evidence.status = EvidenceStatus.NOT_COLLECTED
            for photo in additions:
                meta = photo.metadata
                if connection.execute('SELECT 1 FROM recovery_insurance_attachments WHERE attachment_id=?', (str(meta.attachment_id),)).fetchone():
                    raise ValueError('Attachment ID already exists; it cannot be overwritten or moved across cases.')
                workspace.evidence.append(EvidenceRecord(case_id=workspace.case_id, damage_id=meta.damage_id,
                    evidence_type=meta.evidence_type, status=EvidenceStatus.FILE_SAVED,
                    attachment_id=meta.attachment_id, description=meta.description))
            proposed = current.model_copy(deep=True, update={'workspace': workspace,
                'attachments': [p for p in current.attachments if p.metadata.attachment_id not in removals] + additions})
            self._validate_insurance_snapshot(proposed)
            for attachment_id in removals:
                connection.execute('DELETE FROM recovery_insurance_attachments WHERE case_id=? AND attachment_id=?',
                                   (str(workspace.case_id), str(attachment_id)))
            for photo in additions:
                connection.execute('INSERT INTO recovery_insurance_attachments VALUES (?,?,?,?)',
                    (str(photo.metadata.attachment_id), str(workspace.case_id), photo.metadata.model_dump_json(), photo.content))
            workspace.version += 1
            connection.execute('INSERT INTO recovery_insurance_workspaces VALUES (?,?) ON CONFLICT(case_id) DO UPDATE SET workspace_json=excluded.workspace_json',
                               (str(workspace.case_id), workspace.model_dump_json()))
            return workspace.model_copy(deep=True)

    def get_progress_profile(self, case_id: UUID):
        from .progress.profiles import ProgressProfile
        case_id = UUID(str(case_id))
        with self._connection() as connection:
            if connection.execute('SELECT 1 FROM recovery_cases WHERE case_id=?', (str(case_id),)).fetchone() is None:
                raise ValueError('Recovery case does not exist.')
            row = connection.execute('SELECT profile_json FROM recovery_progress_profiles WHERE case_id=?', (str(case_id),)).fetchone()
        profile = ProgressProfile.model_validate_json(row[0]) if row else ProgressProfile(case_id=case_id)
        if profile.case_id != case_id:
            raise ValueError('Progress profile does not belong to this case.')
        return profile

    def save_progress_profile(self, profile, *, expected_version, expected_case, explicitly_confirmed=False):
        """Explicit profile-only CAS. Never changes intake, tasks, plan, or records."""
        from .progress.profiles import ProgressProfile
        if explicitly_confirmed is not True:
            raise ValueError('Explicit confirmation is required before saving household details.')
        profile = ProgressProfile.model_validate_json(profile.model_dump_json())
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT case_json FROM recovery_cases WHERE case_id=?', (str(profile.case_id),)).fetchone()
            if row is None:
                raise ValueError('Recovery case does not exist.')
            case = RecoveryCase.model_validate_json(row[0])
            if case.intake.immediate_danger is not False:
                raise ValueError('Profile changes are paused pending the safety assessment.')
            if case != expected_case:
                raise ValueError('Stale household details: the saved assessment changed.')
            row = connection.execute('SELECT profile_json FROM recovery_progress_profiles WHERE case_id=?', (str(profile.case_id),)).fetchone()
            current = ProgressProfile.model_validate_json(row[0]) if row else ProgressProfile(case_id=profile.case_id)
            if current.case_id != case.case_id:
                raise ValueError('Progress profile does not belong to this case.')
            if current.version != expected_version or profile.version != expected_version:
                raise ValueError('Stale household details: reload before reviewing changes.')
            saved = profile.model_copy(update={'version': current.version + 1, 'updated_at': self._now()})
            connection.execute('INSERT INTO recovery_progress_profiles VALUES (?,?) '
                'ON CONFLICT(case_id) DO UPDATE SET profile_json=excluded.profile_json',
                (str(profile.case_id), saved.model_dump_json()))
        return saved

    def _progress_revision(self, connection, case_id):
        """Cheap consistent invalidation token. Never selects attachment BLOBs."""
        import hashlib
        import json
        case_id = UUID(str(case_id))
        row = connection.execute('SELECT case_json,active_plan_id FROM recovery_cases WHERE case_id=?', (str(case_id),)).fetchone()
        if row is None:
            raise ValueError('Recovery case does not exist.')
        case = RecoveryCase.model_validate_json(row[0])
        if case.intake.immediate_danger is not False:
            raise ValueError('Recovery Progress is paused until the safety assessment permits routine work.')
        payload = {'case': json.loads(row[0]), 'active_plan_id': row[1]}
        for name, query in (
            ('records', 'SELECT records_json FROM recovery_records WHERE case_id=?'),
            ('profile', 'SELECT profile_json FROM recovery_progress_profiles WHERE case_id=?'),
            ('insurance', 'SELECT workspace_json FROM recovery_insurance_workspaces WHERE case_id=?'),
            ('plan', 'SELECT p.plan_json FROM recovery_plans p JOIN recovery_cases c '
                     'ON p.plan_id=c.active_plan_id AND p.case_id=c.case_id WHERE c.case_id=?')):
            item = connection.execute(query, (str(case_id),)).fetchone()
            payload[name] = json.loads(item[0]) if item else None
        payload['attachments'] = [json.loads(item[0]) for item in connection.execute(
            'SELECT metadata_json FROM recovery_insurance_attachments WHERE case_id=? ORDER BY attachment_id', (str(case_id),))]
        payload['journey_events'] = list(connection.execute(
            'SELECT event_id,kind,title,detail,occurred_at FROM recovery_journey_events WHERE case_id=? ORDER BY event_id',
            (str(case_id),)))
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def get_progress_revision(self, case_id: UUID):
        with self._connection() as connection:
            connection.execute('BEGIN')
            return self._progress_revision(connection, case_id)

    def get_progress_snapshot(self, case_id: UUID):
        """Atomic explicit-refresh read; verify saved files, return metadata only.

        Polling consumers use get_progress_revision instead. Reuses the Insurance
        validators for attachment hashes, decoded content, ownership and evidence.
        """
        from .progress.profiles import ProgressCaseSnapshot, ProgressProfile
        case_id = UUID(str(case_id))
        with self._connection() as connection:
            connection.execute('BEGIN')
            insurance = self._insurance_snapshot(connection, case_id)
            row = connection.execute('SELECT p.plan_json FROM recovery_plans p JOIN recovery_cases c '
                'ON p.plan_id=c.active_plan_id AND p.case_id=c.case_id WHERE c.case_id=?', (str(case_id),)).fetchone()
            plan = RecoveryPlan.model_validate_json(row[0]) if row else None
            row = connection.execute('SELECT profile_json FROM recovery_progress_profiles WHERE case_id=?', (str(case_id),)).fetchone()
            profile = ProgressProfile.model_validate_json(row[0]) if row else ProgressProfile(case_id=case_id)
            if profile.case_id != case_id or (plan is not None and plan.case_id != case_id):
                raise ValueError('Progress information does not belong to this case.')
            return ProgressCaseSnapshot(case=insurance.case, records=insurance.records, plan=plan,
                workspace=insurance.workspace, attachment_metadata=tuple(photo.metadata for photo in insurance.attachments),
                journey_events=tuple(dict(zip(('event_id', 'kind', 'title', 'detail', 'occurred_at'), event))
                    for event in connection.execute('SELECT event_id,kind,title,detail,occurred_at '
                        'FROM recovery_journey_events WHERE case_id=? ORDER BY event_id', (str(case_id),))),
                profile=profile, revision=self._progress_revision(connection, case_id))
