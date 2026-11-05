# Recovery journeys: CAP-06–09

The existing M5 Recovery implementation supplied assessment, deterministic planning, approved task updates, reassessment and SQLite persistence. This change extends those components and integrates a visual journey dashboard into the main **Recover** screen. Most new domain, fixture and presentation code lives in `recovery/`.

## Try it locally

Run `python -m streamlit run app.py` with the repository's Python 3.12 environment. No AI key is required for these flows.

1. Open **Recover**, then **Explore six fictional recovery journeys**.
2. Choose a household and checkpoint, then **Load fictional checkpoint**. Each load creates a fresh replay; it does not overwrite an existing case.
3. Review recent changes, elapsed days, the optional check-in target, timeline, next task and confirmed situation.
4. Use **Show tasks** and **Save progress** to record a task status. Completion is a user report, not a service outcome.
5. Use **Review or edit your situation** to preview a circumstance revision; recheck current danger before approving. Use **Edit household details and dates** for optional context, incident/check-in dates and damage records.
6. Save the ID under **Saved case · Keep this ID to resume**. After refreshing the browser, open the journey picker and use **Resume fictional replay**. This reopens the saved replay without resetting progress. Ordinary cases use **Resume saved case** in the structured intake.
7. **Leave fictional recovery scenario** restores the case that was open before the replay. Stored histories and danger reports remain saved.

The synthetic incident anchor is October 1, 2026. Day 1 is October 2; Day 30 is October 31. The simulated date appears on screen. New changes made inside a replay use that checkpoint's clock. There are no external requests, submissions, bookings or model calls in scenario loading or deterministic planning.

## The six households

| Fictional household | Checkpoints | Story and useful checks |
| --- | --- | --- |
| Rivera | 1, 3, 7 | Accommodation is arranged while mobility and transportation needs remain. Verify current needs and historical tasks remain distinct. |
| Bennett | 1, 3, 7 | Renter documentation and a proposed update at Day 7. The proposal is not a milestone until approved. |
| Patel | 1, 3, 7 | Sparse information, unknown household facts and an unchanged Day 3. Unknown values stay unknown. |
| Chen | 1, 3, 7, 14, 30 | Damage documentation, blocked insurer follow-up, additional damage and later follow-up requests. Contact never establishes coverage or claim acceptance. |
| Johnson | 1, 3, 7, 14, 30 | Reported utility changes and changing essential needs. Restored utilities do not establish home safety. |
| Lewis | 1, 3, 7, 14, 30 | Longer continuity, an unchanged checkpoint and new reported danger on Day 30. Emergency controls interrupt the dashboard. |

## What changed by capability

| Capability | Integrated behavior |
| --- | --- |
| CAP-06: assessment | Current-danger check, optional housing type, accessibility/support needs, insurer contact, county and dates. Profile suggestions require confirmation. Manual intake displays a summary before creating a case/draft. Important facts remain editable. |
| CAP-07: planning | Existing deterministic short plan, priority, rationale, dependencies and official directory pathways. Relevant reviewed excerpts are retrieved through existing M3 publication gates. The user approves the plan; no external commitment is created. |
| CAP-08: progress | Not started / In progress / Completed / Blocked; filtered effective tasks; saved status history; consistent ordering in dashboard, chat, legacy screen and export. No-longer-current work retains historical status. |
| CAP-09: continuity | Atomic dated events, explicit changes-since-review cursor, saved replay resume, reviewable revisions, completed-work preservation and persistent danger escalation. |

## Code map

```text
recovery/
  models.py                 additive facts and optional dates
  database.py               SQLite transactions, version checks, journey events
  timeline.py               accepted event projection and reported-change descriptions
  dashboard.py              read-only counts, recent changes, dates and next task
  task_view.py              effective task priority, applicability and ordering
  assessment_summary.py     reported-fact summary and optional profile suggestions
  assessment_ui.py          optional assessment/edit controls
  task_guidance.py           task-specific retrieval through existing review gates
  dashboard_ui.py           scenario picker and change-first dashboard renderer
  dashboard.css             scoped desktop/mobile and bright/dark styling
  demo.py                   validated replay loader and read-only saved replay resume
  demo_session.py           original-case restoration and demo state isolation
  fixtures/journeys.json     six explicitly fictional scenario definitions
ui/recovery_page.py          main route, forms, approvals and existing task controls
ui/emergency_page.py         always-available emergency controls and replay exit
services/assistant.py        context-bound proposals and guarded recovery operations
```

The main UI reads case/records/plan/events from the repository and calls `build_dashboard(...)`. This projection does not write data. Accepted case, records, plan, status, revision and danger operations append journey events in the same transaction as the underlying change. Drafts and previews never create completed milestones. Legacy databases receive an additive event table; missing historical timestamps are not reconstructed.

Replay loading uses the same public repository operations with a fixed clock. Its database is a sibling of the configured primary database, named `<primary-stem>-journey-demo.sqlite3`. A separate metadata table binds replay case ID, household, checkpoint, date and optional pending preview. Resume reads an existing snapshot without writing, rechecks saved danger, and discards a pending preview if its case, plan or records are stale.

## Honest timing and boundaries

- Elapsed days use the confirmed incident date. Missing or future dates are shown as unknown or needing review.
- Looking ahead shows an optional **user-chosen check-in**, never an estimated recovery completion date. Past targets are labeled as passed.
- Changes since last review use an explicit browser-session **Mark updates reviewed** cursor. A fresh browser shows recorded history; this is not cross-device visit tracking.
- Event details and task statuses are user-reported. Completing a task does not mean home safety, benefit eligibility, insurance coverage, connection to 911 or successful rescue.
- Official directory links and reviewed excerpts remain distinct. Unavailable or insufficient evidence stays explicit; no source approval is invented.
- Local SQLite and case IDs are a demonstration mechanism, not authenticated multi-user storage. Use fictional information only. The online-only application has no offline guarantee.

## Verification

Focused tests cover additive model/database compatibility, atomic rollback and stale updates, pending proposals, unchanged days, date boundaries, legacy empty history, effective task counts, demo isolation, replay resume and all 24 checkpoints. AppTest covers summary confirmation, filters, situation editing and emergency interruption. Browser checks in `tests/visual/recovery.spec.cjs` exercise the integrated controls at desktop, tablet and mobile sizes and attach screenshots for inspection.

Run the same commands listed in the main README. Existing Windows screenshot baselines are platform-specific; Mac captures must not replace them. New Recovery browser checks use cross-platform behavior/layout assertions and screenshot artifacts. Recorded execution results are in [verification notes](VERIFICATION.md).
