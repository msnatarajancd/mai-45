# Recovery Journey Implementation Plan

> **For agentic workers:** Use the agreed design and task ownership below. Steps use checkbox syntax for tracking.

**Goal:** Deliver an integrated change-first Recovery dashboard with honest timelines and six repeatable synthetic journeys.

**Architecture:** Extend existing Recovery models/repository and add pure timeline/dashboard projections plus a Streamlit renderer. Keep the shared UI as the route/approval adapter. Reuse existing danger and evidence services.

**Tech Stack:** Python 3.12, Streamlit, SQLite, Pydantic, Playwright Chromium.

**Spec:** `docs/superpowers/specs/2026-11-05-recovery-journey-design.md`

## Global constraints

- Work in the clean user-selected feature/m6-M9 checkout; no separate checkout is needed for this requested branch.
- User authorized building the reviewed plan; proceed without a further approval question.
- Source artifacts and review approvals are not modified; AI/network calls are not required by tests or demos.
- Preserve old models, stored cases, approval/version guards and independent emergency access.
- Never equate task completion with safety or verified service outcomes; no recovery-duration forecasts.
- Parallel tasks own disjoint files. Root integrates UI only after the safety edit to that file is complete.

## Review focus

- Current danger in every editable narrative must interrupt before ordinary persistence (Task 1).
- Records edited after a proposed assistant action must invalidate its approval (Task 1).
- Legacy databases, empty history, timezone boundaries and unknown incident dates must remain honest (Task 2).
- Scenario switching must isolate cases and emergency state without clearing a real saved danger report (Tasks 3 and 4).
- Pending changes, targets and repeated visits must not fabricate completed milestones (Tasks 2 and 4).

## Task 1: Shared integration correctness

Files: `services/assistant.py`, `ui/recovery_page.py` (only danger writes initially), `recovery/reassessment.py`, new `recovery/task_view.py`, focused tests.
- [x] Reproduce structured-danger and stale-assistant-record defects with isolated tests.
- [x] Screen all structured narrative writes; include records in assistant snapshots/planning and use atomic draft approval.
- [x] Preserve initial-task prerequisites/pathways on revision tasks and expose `current_task_views(plan)` for effective priority/applicability.
- [x] Verify targeted regressions; hand off shared UI file before root edits it.

## Task 2: Persistent timeline and dashboard projection

Files: `recovery/models.py`, `recovery/database.py`, new `recovery/timeline.py`, `recovery/dashboard.py`, tests.
Interfaces: HouseholdRecoveryDetails adds nullable housing_type, accessibility_needs list[str], insurer_contact_status (Unknown/Not contacted/Contacted/Follow-up requested). RecoveryRecords adds incident_date and next_check_in_date (date | None). Repository accepts optional keyword `clock` returning aware datetime, and provides `list_journey_events(case_id)` with event_id, kind, title, detail, occurred_at. Events commit with real accepted writes.
- [x] Test additive JSON/DB compatibility, event rollback and stale writes.
- [x] Add event storage and atomic emission for accepted changes; no writes on read/proposal.
- [x] Implement `build_dashboard(case, records, plan, events, *, as_of=None, since_event_id=None)` returning a documented immutable/read-only view with elapsed days, target days, changes, timeline, counts and next task.
- [x] Test unknown/future dates, completed/historical applicability, pending proposals excluded, last-reviewed cursors and no forecast language.

## Task 3: Six synthetic journeys

Files: new `recovery/demo.py`, `recovery/fixtures/journeys.json`, tests.
Interface: `list_scenarios()` returns validated definitions; `load_checkpoint(database_path, scenario_id, day)` returns a selection with case_id, scenario label, as_of date, previous checkpoint event cursor and optional pending-change description. Uses a dedicated demo DB and repository clock/public APIs. Only explicit UI load creates a replay case.
- [x] Test all six scenarios, required checkpoints and strict fictional labeling.
- [x] Replay confirmed facts, task transitions and approved changes with a controlled clock; include unchanged and danger checkpoints.
- [x] Test deterministic projections, no network/model use, repeated loading isolation and preserved statuses across revised plans.

## Task 4: Main UI, assessment summary and guidance

Files: new `recovery/dashboard_ui.py`, `recovery/assessment_summary.py`, `recovery/task_guidance.py`, changes to `ui/recovery_page.py`, scoped styles, tests.
- [x] Add focused AppTest regressions for dashboard-first returning flow, manual preview/confirmation, optional facts and scenario loading.
- [x] Render changes/timeline/next step with accessible semantic labels, mobile stacking and separate targets; reuse existing status/approval controls.
- [x] Add explicit editable situation review, optional dates/facts and confirmed profile import without inferred household counts.
- [x] Attach task-specific reviewed evidence via existing retrieval; keep official directory pathways distinct and unavailable evidence explicit.
- [x] Use common effective task projection for display/export, retain compatibility wrappers and legacy controls.

## Task 5: End-to-end verification and handoff

Files: `tests/visual/recovery.spec.cjs`, documentation, appropriate screenshot baselines.
- [x] Run Python suite, both Node regressions, CAP-04 golden evaluation and compile checks.
- [x] Exercise desktop/tablet/mobile scenario loading, next checkpoint, approval, progress persistence, unknown/no-change states and danger interruption without dialing.
- [x] Inspect actual Recovery screenshots in bright/dark and mobile layouts; capture review artifacts. Retain the existing Windows pixel baselines unchanged for their matching CI platform.
- [x] Obtain independent review, fix material findings, verify the app locally and update documentation with actual evidence and limits.

## Execution ledger

- Baseline: 8c865d2, clean feature/m6-M9. Audit run: 953 passed, 11 skipped, 10 subtests passed.
- Ruling: use the requested existing feature checkout and parallel disjoint ownership; preserve the already configured environment and Git authentication.
- Ruling: interpret last visit as last explicitly reviewed updates within this browser session; returning with a case ID shows first-visit history honestly.
- Ruling: no additional approval gate; the user explicitly said “sounds good. Go ahead and build.”

- Tasks 1–4 implemented and reviewed. Two core review findings, demo metadata mismatch, demo danger-widget leakage, task filters and stale initial extraction summary were reproduced and fixed with regression tests.
- Added stored replay metadata and explicit Resume fictional replay so case/progress/history survive a browser refresh without restarting a checkpoint. Resume is read-only and rejects stale pending proposals.
- Browser verification uses portable behavior/layout assertions and screenshot attachments for the new Recovery screens. Existing Windows pixel baselines remain unchanged; no Mac image is substituted for a Windows baseline.
- Verification refinement: new Recovery screens have cross-platform behavior/layout regressions and inspected screenshots, not new Windows pixel baselines. No screenshot threshold or existing Windows comparison was relaxed. Windows baseline comparison was not run on this Mac.
- Coordinated Python run: 1,044 passed, 11 optional HTTP tests skipped, 10 subtests passed in 21.73 seconds. Subsequent presentation-order and portable URI changes passed their focused 9 UI and 32 scenario regressions. Both Node regressions, compilation, whitespace checks and proposed CAP-04 golden 24/24 passed. Existing emergency browser suite: 15 passed across desktop/tablet/mobile.
- Targeted checks: 32 scenario/replay tests, 59 final assessment/extraction/UI tests; both Node regressions and CAP-04 golden 24/24 passed.
- Final Recovery browser suite: 9 passed across desktop/tablet/mobile, 72 checkpoint loads, 18 inspected screenshots, explicit approval and full-refresh/replay-resume verified. No remaining review findings. Local guide and verification notes updated.
