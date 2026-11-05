# Recovery journey dashboard

User-approved direction on November 5, 2026: extend CAP-06–09 in `recovery/`, lead with what changed, show elapsed time and meaningful accomplishments, and provide six fictional households across both first-week and month-long stories. The user explicitly authorized implementation after reviewing the plan and scenario split.

## Experience

Returning households see changes since their last reviewed visit, a dated timeline, an actionable next step, current task counts and their editable reported situation. New households retain structured intake, optional reviewed AI extraction and independent assistance browsing. A compact “Report a change” control reveals the existing conversation and reassessment controls. The emergency path stays above all routine work.

Show days since a user-confirmed incident date and days until an optional user-chosen check-in. Never estimate a recovery completion date. Future targets are labeled separately from recorded events. Completed work stays visible through revisions. A no-change checkpoint states that nothing new was recorded, without judging the user. Color accompanies readable text and icons; mobile becomes a vertical timeline.

## Existing code and required corrections

Reuse SQLiteRecoveryRepository, deterministic planning, task statuses, version checks, approved revisions, M3 publication gates and CAP-04 interruption. Fix current-danger text bypasses in structured damage fields, missing confirmed-record snapshots in assistant draft/approval/reassessment, missing metadata on revision tasks, and divergent ordering in exports/chat.

CAP-06 gains optional housing type, explicitly reported accessibility needs, insurer contact status, incident date and next check-in date. Unknown remains unknown. Manual assessment gains an editable review before save/planning. Session household preferences are offered for explicit confirmation; never silently interpreted as current facts.

## Data and timeline

Use additive nullable/defaulted fields in existing JSON models. Add an append-only journey-event table in the same SQLite database, written atomically with accepted case, records, plan, progress, revision and danger changes. Existing task history remains compatible. No historical approval timestamps are invented for legacy plans. Store event cursors per case in the browser session; show changes since the last explicit “Mark updates reviewed” action and clearly label first visits. Cross-browser or cross-device last-visit continuity is not promised.

The projection is read-only: pending proposals never become milestones, counts derive from effective applicability, and emergency state overrides the next-step recommendation. UI, summaries and exports use the same effective task order. Task-specific guidance uses existing reviewed retrieval with explicit hazard/geography; unavailable evidence stays unavailable and directory links remain distinct. No source approvals or live availability claims are introduced.

## Fictional scenarios

Rivera, Bennett and Patel have checkpoints on days 1, 3 and 7. Chen, Johnson and Lewis also have days 14 and 30. Include arranged accommodation, renter documentation, sparse/unknown facts, insurer follow-up, restored utilities, blocked work, unchanged days and a current-danger interruption. Every scenario and its timeline is labeled synthetic. Loading requires an explicit action, uses a dedicated demo database, creates a fresh replay case and does not overwrite existing cases. Dates derive from a fixed demo incident date; show the simulated as-of date. Replay transitions through repository APIs with a controlled clock; no model/network calls.

## Approaches considered

Selected: change-first timeline plus next action and task groups, matching the user's preference for changes, elapsed days, hope and visible progress. A process-stage map is useful as a secondary orientation element but insufficient for dated personal changes. A task-board-first view supports editing but makes the recent story harder to see. No new frontend stack or AI planner is required.

## Boundaries and verification

Python 3.12, Streamlit, Pydantic and existing pinned Playwright. Work on the user-selected `feature/m6-M9` checkout. Keep source changes in Recovery where practical; shared safety/assistant corrections and a thin main-UI adapter are necessary. Preserve old JSON and databases. No dispatch, booking, claims submission, safety verdict, benefit eligibility or recovery forecast. Tests use fictional data and isolated stores. Verify full Python/Node regressions, targeted Recovery browser journeys and responsive screenshots; Windows baseline generation must use Windows, not renamed Mac images.
