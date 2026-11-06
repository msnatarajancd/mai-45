"""Separate local result storage; never writes accepted Recovery records."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

from pydantic import BaseModel, ConfigDict, Field

from .models import SourceMode, SpecialistResult, ActionCandidate, MilestoneView


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: int = 1
    run_id: str
    context_key: str
    checkpoint_id: str | None = None
    source_mode: SourceMode
    input_fingerprint: str
    created_at: datetime
    scenario_as_of: datetime
    results: list[SpecialistResult]
    historical_results: list[SpecialistResult] = Field(default_factory=list)
    actions: list[ActionCandidate]
    milestones: MilestoneView
    changes: list[str] = Field(default_factory=list)
    partial: bool = False


def default_store_path() -> Path:
    configured = os.environ.get('READYRELIEF_PROGRESS_DB_PATH')
    if configured:
        return Path(configured).expanduser().resolve()
    # Isolated recovery test/demo databases get an equally isolated preview file.
    if os.environ.get('READYRELIEF_DB_PATH'):
        base = Path(os.environ['READYRELIEF_DB_PATH']).expanduser().resolve()
        return base.with_name(base.stem + '-progress.sqlite3')
    return Path(__file__).resolve().parents[2] / '.local' / 'recovery-progress.sqlite3'


class SQLiteProgressStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS snapshots (sequence INTEGER PRIMARY KEY, '
                         'run_id TEXT UNIQUE NOT NULL, context_key TEXT NOT NULL, payload TEXT NOT NULL)')
            conn.execute('CREATE INDEX IF NOT EXISTS snapshot_context ON snapshots(context_key,sequence)')
            conn.execute('CREATE TABLE IF NOT EXISTS interactions (context_key TEXT NOT NULL, '
                         'checkpoint_id TEXT NOT NULL, provider_id TEXT NOT NULL, status TEXT NOT NULL, '
                         'PRIMARY KEY(context_key,checkpoint_id,provider_id))')
            conn.execute('CREATE TABLE IF NOT EXISTS attempts (context_key TEXT PRIMARY KEY, '
                         'input_fingerprint TEXT NOT NULL, state TEXT NOT NULL, message TEXT NOT NULL, '
                         'attempted_at TEXT NOT NULL, statuses TEXT NOT NULL)')

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(str(self.path), timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def latest(self, context_key: str) -> DashboardSnapshot | None:
        with self.connection() as conn:
            row = conn.execute('SELECT payload FROM snapshots WHERE context_key=? ORDER BY sequence DESC LIMIT 1',
                               (context_key,)).fetchone()
        return DashboardSnapshot.model_validate_json(row[0]) if row else None

    def history(self, context_key: str) -> list[DashboardSnapshot]:
        with self.connection() as conn:
            rows = conn.execute('SELECT payload FROM snapshots WHERE context_key=? ORDER BY sequence',
                                (context_key,)).fetchall()
        return [DashboardSnapshot.model_validate_json(row[0]) for row in rows]

    def save(self, snapshot: DashboardSnapshot) -> None:
        with self.connection() as conn:
            conn.execute('INSERT OR IGNORE INTO snapshots(run_id,context_key,payload) VALUES(?,?,?)',
                         (snapshot.run_id, snapshot.context_key, snapshot.model_dump_json()))

    def save_interaction(self, context_key: str, checkpoint_id: str, provider_id: str, status: str) -> None:
        if not context_key.startswith(('demo:', 'synthetic:')):
            raise ValueError('Only fictional provider interactions are supported.')
        allowed = {'shortlisted', 'enquiry_recorded', 'awaiting_reply', 'declined',
                   'quote_received', 'quote_accepted', 'work_committed'}
        if status not in allowed or not checkpoint_id or not provider_id:
            raise ValueError('Choose a supported simulated interaction.')
        with self.connection() as conn:
            conn.execute('INSERT INTO interactions VALUES(?,?,?,?) ON CONFLICT(context_key,checkpoint_id,provider_id) '
                         'DO UPDATE SET status=excluded.status', (context_key, checkpoint_id, provider_id, status))

    def interactions(self, context_key: str, checkpoint_id: str) -> dict[str, str]:
        with self.connection() as conn:
            return dict(conn.execute('SELECT provider_id,status FROM interactions WHERE context_key=? AND checkpoint_id=?',
                                     (context_key, checkpoint_id)).fetchall())

    def save_attempt(self, context_key: str, input_fingerprint: str, state: str, message: str,
                     *, at: datetime | None = None, statuses: dict | None = None) -> dict:
        if state not in {'checking', 'complete', 'failed', 'cancelled', 'interrupted'}:
            raise ValueError('Unsupported run attempt state.')
        at = at or datetime.now(timezone.utc)
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError('Attempt timestamps require a timezone.')
        at = at.astimezone(timezone.utc)
        with self.connection() as conn:
            conn.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?) ON CONFLICT(context_key) DO UPDATE SET '
                         'input_fingerprint=excluded.input_fingerprint,state=excluded.state,message=excluded.message,'
                         'attempted_at=excluded.attempted_at,statuses=excluded.statuses '
                         'WHERE excluded.attempted_at>=attempts.attempted_at',
                         (context_key, input_fingerprint, state, message, at.isoformat(), json.dumps(statuses or {})))
        return self.latest_attempt(context_key)

    def latest_attempt(self, context_key: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute('SELECT input_fingerprint,state,message,attempted_at,statuses FROM attempts '
                               'WHERE context_key=?', (context_key,)).fetchone()
        if not row:
            return None
        return dict(context_key=context_key, input_fingerprint=row[0], state=row[1], message=row[2],
                    at=datetime.fromisoformat(row[3]), statuses=json.loads(row[4]))
