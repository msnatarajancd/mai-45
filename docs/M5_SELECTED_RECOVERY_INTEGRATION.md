# Selected Recovery integration

Base: Insurance checkpoint `2553619` (prior Python baseline: 1003 passed, 11 skipped, 10 subtests passed).
Contributions adapted from teammate commit `822767153da5c59a08eb3b79995bb6de6650840d`.

- `recovery/task_view.py`: teammate detached effective task projection. Applied to guided task cards, assistant, legacy screen and plan download. Counts exclude historical work while retaining saved completion.
- `recovery/database.py`: selected teammate records-version transaction guard, accepted-event table/hooks and injectable aware test clock. Existing Insurance tables and APIs are preserved.
- `recovery/timeline.py`: teammate accepted-event projection and descriptions, adapted to existing models. Optional assessment/date fields were not imported.
- `recovery/reassessment.py`: teammate completed-task applicability, resource categories and dependencies; no task status reset or approval contract change.
- Tests retain/adapt teammate rollback, projection, race and historical-progress coverage, plus combined guided/Insurance checks.

The compact read-only timeline lives inside Track Progress. It records actual case creation, confirmed Recovery records, plan approval, changed task status, accepted reassessment and persisted danger. Each event is committed in the same transaction as its operation. Drafts, previews and no-op status writes do not create milestones. Legacy events are never backfilled. Insurance events are not duplicated into this Recovery timeline. Timestamps are UTC; recorded activity is user-reported, never external verification.

Excluded: all replay/session switching, demo controls/databases, replacement dashboard, optional assessment facts/dates, M3 task renderer, new model clients and agents. No source approvals or emergency interfaces changed. The original guided stages, explicit confirmations and Insurance attachment/export pipeline remain intact.

Verification uses isolated synthetic databases and browser-only explicitly labeled synthetic extraction. No paid model calls or real emergency calls. No final integration commit, push or merge is authorized.

Compatibility correction: guided and legacy task forms retain the records version actually displayed, alongside the existing displayed progress version. The repository checks both under BEGIN IMMEDIATE; a later tab update cannot be accepted merely because Streamlit reruns and reloads newer records. Assistant proposals bind the records snapshot too.

## Verification

- Combined targeted Recovery/timeline/Insurance/safety run: 134 passed; final displayed-record-version regressions: 2 passed (guided and legacy).
- Final full Python: 1024 passed, 11 skipped, 10 subtests passed.
- Final full visual suite: 62 passed, 1 existing mobile sidebar skip. No screenshot baseline or tolerance changes.
- Desktop 1440x1000 and mobile 390x844 Chromium acceptance passed with the existing explicitly synthetic browser provider. Verified guided review/approval, saved progress, accepted timeline, additive damage/reassessment, full refresh/exact-case reopen, Insurance navigation and emergency access. Actual screenshots were inspected under ignored artifacts/selected-integration-desktop and artifacts/selected-integration-mobile.
- Existing danger-persistence-failure/retry and transactional event-failure tests pass; replay exit controls were never imported.
- Visual verification exposed an existing county-dropdown selection race. The test helper now waits for completion, opens the explicit dropdown control and verifies the selected value with bounded field-only retries. No submit operation is retried and no emergency production code changes.
- A displayed-record-version gap was reproduced before correction: task updates could accept records reloaded on a submit rerun. Both task UIs now retain the actually displayed records version and reject changed-record submissions without task/history/timeline writes.
- git diff --check passes. Original Insurance branch remains clean at 2553619. All changes are deliberately uncommitted and unstaged.

Limitations: no backfilled legacy history; no Insurance event duplication; timestamps are UTC; local SQLite remains a fictional, unauthenticated course prototype. No additional live Qwen, official-provider, dispatch or submission verification was performed. Event-write failures roll back the corresponding operation; failed danger persistence retains the existing emergency/pending-report guards.
