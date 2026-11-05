# Verification record

## PR #4 conflict resolution — November 4, 2026

Merged `main` at `1653ae6` into `feature/M4-EmergencyAssistance`. The conflict was
the assistant danger precheck: main added M5-approved, non-executing recovery
extraction while CAP-04 introduced the shared clause-qualified routing policy.
Both features remain present. Policy `cap04-rules-1.1` recognizes explicit
personal reports such as “I'm in danger” while retaining negation and
hypothetical scope. The extraction-specific shared-policy check permits routine
utility updates, pauses current threats and medical/flood concerns, and changes
neither session state nor persisted danger. The extraction DTOs and fingerprints
remain unchanged.

Fresh combined verification: **779 passed, 11 skipped, 10 subtests passed** in
10.52 seconds. Golden evaluation **24/24** and development evaluation **48/48**
passed with proposed labels; compilation and whitespace checks passed. Added
regressions reproduced the integration failures before correction, including
ordinary restored-electricity reports and current danger mixed with planning.
Independent review confirmed the final precheck preserves both workflows.
No live provider call or source approval was performed for this merge.

## CAP-04 implementation — November 4, 2026

Environment: macOS arm64, Python 3.12.15, repository-pinned dependencies, Node 22.23.4 and Playwright Chromium. The integrated app runs at `http://127.0.0.1:8501` with the AI key removed from its process environment and `.local/cap04-demo.sqlite3` as its isolated demo database. The health endpoint returned HTTP 200. See [implementation handoff](CAP04_IMPLEMENTATION.md) for all seven delivery areas.

- Full Python regression: **684 passed, 11 skipped, 10 subtests passed** in 10.87 seconds. The skipped tests are optional HTTP integration coverage. This includes original M1–M5 tests and new routing, workflow, publication, synthetic-data and UI coverage.
- Golden evaluation: **24/24**; development evaluation: **48/48**. Both report zero critical misses, bounded forbidden claims, provider calls and network calls. Dataset version `2026-11-04.1`, policy `cap04-rules-1.0`. Labels remain **PROPOSED**, `human_reviewed=false`; no real-world reliability or human safety review is claimed.
- CAP-04 browser suite: **15/15**, desktop 1440×1000, tablet 1024×900 and mobile 390×844. Tests inspect `tel:911` without activating it, action ordering and focus, interruption, geography, connectivity limits, scrolling below the toolbar and enlarged text. No real calls or texts were initiated.
- Bright/dark readability checks pass on all seven pages at all three sizes (**6/6**). The clipping assertion now excludes the existing intentionally hidden accessible brand label; pointer and keyboard brand navigation retain separate coverage.
- Final complete functional browser run: **56 passed, 1 skipped** in 1.1 minutes, exit 0 (`npm run test:visual -- --ignore-snapshots --output=artifacts/browser-accepted-tests`). The one skip is the desktop/sidebar-animation test on mobile, where the compact menu is used. This includes all 15 emergency checks, both navigation tours, and narration lifecycle checks.
- Python compilation and both Node regression scripts passed. `git diff --check` passed.

Independent review found and reproduced newline/colon routing downgrades, planning wording overriding a separate current hazard, concatenated directory needs, and event context overridden by negated flood mentions. Regression tests failed before the fixes and now pass. Directory tests exercise publication and revocation in isolated TEST ONLY stores; no production source, candidate or listing approval was performed.

Browser testing found that Streamlit's wrapper constrained sticky positioning and that mobile toolbar height exceeded the old fixed offset. The emergency strip now sticks through the layout wrapper with the actual responsive header offset. Current desktop and mobile screenshots were visually inspected. Native screen-reader and actual phone-handler operation were not tested.

The tour now measures toolbar and emergency-strip clearance when locating its target. On smaller screens, an oversized card highlights its actual control so it fits above the tour panel. The test waits for complete unobstructed geometry instead of checking a transient partial position. All three focused tour checks and the Node tour lifecycle regression passed after restarting Streamlit to reload its imported JavaScript asset.

A broader run exposed a test race where speech's asynchronous start message replaced a successful locate message. Both navigation tests now verify the correct step marker and unobstructed control geometry rather than transient narration copy. Six bounded repeated tablet checks passed before the final full browser run; production narration behavior was not changed.

All eight directory listings remain PENDING, with seven acquired-source-backed records and one failed FCC acquisition. The app presently offers official entry links rather than verified EEAP timing/service cards. [The source review packet](CAP04_SOURCE_REVIEW.md) records the remaining content release gate. Golden expectations also need actual human safety review. Online access remains required.

Existing pixel baselines were captured on Windows. Functional browser runs on this Mac use `--ignore-snapshots` for the older experience suite; they do not approve pixel differences. Windows baseline refresh/review and the Windows visual CI job remain unverified. Baselines were not overwritten with Mac screenshots.

## Original M1 verification — November 2, 2026

Environment: Windows, Python 3.12.15, Streamlit 1.66.1, Pydantic 2.14.2, pytest 9.2.0. The existing pinned M5 requirements were retained.

## Automated checks

Final run: **189 passed in 26.26 seconds** (`python -m pytest -q --tb=short`). Compile checks and whitespace checks passed.

The full suite covers existing M5 model, repository, planner, assessment, AI and preview UI behavior, plus M1 service boundaries and integrated AppTest journeys. New regression checks include:

- All six screens render with immediate emergency access.
- Live mode never displays the fictional warning; mode/area changes clear stale results and update the banner.
- Starting the demo resets existing live-mode/area widgets.
- Intake and reassessment require explicit current danger assessment.
- Initial plan acceptance requires review confirmation.
- Progress saves, resumes, and rejects writes from an outdated display version.
- Reassessment preserves extra utility fields in pre-existing M5 cases.
- A failed danger save remains pending and is retried before routine recovery is allowed.
- Unknown location and unsupported knowledge queries produce honest unavailable/abstention states.

Compile checks and `git diff --check` are run alongside the full suite. Independent read-only review found three material issues (reassessment danger selection, transient danger-save failure, and omitted extra utility fields); each was reproduced with a failing test and fixed. Additional stale-progress, mode-banner and demo-reset regressions were covered during implementation. The original `recovery/` code is unchanged.

## Browser checks

Headless Microsoft Edge at 1440×1100 and a mobile viewport of 390×844. Home, Protect and recovery intake were visually inspected. Mobile has no horizontal document overflow and emergency calling access is visible. The header spacing and default sidebar behavior were corrected after inspection. Local screenshots live in ignored `artifacts/`. A browser journey also created and explicitly approved a five-task plan, saved one completed task, reloaded the browser, resumed by case ID, and confirmed the same 1-completed / 4-remaining counts with zero browser page errors. Reassessment is covered by AppTest and repository tests; its additional browser automation encountered rerender/locator timing issues and is not counted as a passed browser check.

## Limits

This is functional M1 integration evidence, not M4's completed 20–24-case safety evaluation or validation for real emergencies. No live NWS integration, verified RAG corpus, resource capacity, provider success, production hosting, or contest result is claimed. The default template journey needs no API key. Existing M5 AI tests use controlled clients rather than proving a live provider connection.

Windows sandbox execution stalled Streamlit AppTest and denied some temporary-directory cleanup; verification was rerun successfully with authorized execution outside that sandbox. The local server logged a Windows connection-reset message when an automated browser disconnected; the application continued serving subsequent checks.

A subsequent full-suite run encountered one transient Windows socket buffer error (`WinError 10055`) in the original M5 `test_reassessment_dashboard_actions[danger]`. The final rerun was performed after browser work finished.

Final rerun result after browser completion: all 189 tests passed. No test failures remain.


## Search and assistant extension

Full combined suite: **212 passed** after adding searchable navigation, a six-step product tour, Nebius action proposals and confirmed execution. Tests cover structured-action rejection, product questions without writes, emergency bypass, explicit confirmation, duplicate action rejection, stale case/context detection, draft approval, pending danger, and actual saved task changes. Independent review identified a race between snapshot comparison and task writes; a failing regression reproduced it, and writes now use the proposal's original plan ID/version for atomic repository validation.

Live Nebius smoke checks used fictional inputs only. Product help returned no action after the question guard; household updates and area/mode updates returned validated proposals; an exact recovery task title resolved to its real saved task ID and COMPLETED status. The live task proposal was not executed. Chat uses the school-planning reference's Qwen/Qwen3-235B-A22B-Instruct-2507 default through M5's bounded transport. API keys were read from the existing environment and never copied into source files or printed.

Desktop browser inspection confirmed menu filtering, tour navigation and the AI household update card with explicit Confirm/Cancel controls. The basic tour and Local guide work without any API request. Model answers are generative product guidance, not a verified emergency knowledge source. Ambiguous operations may ask for clarification instead of producing an action.

Final extension verification: **212 passed in 22.06 seconds**. Browser checks passed search filtering, tour Next/End, a live Nebius household proposal and explicit confirmed update. The 390×844 assistant view had no horizontal document overflow. Compile and whitespace checks passed.

## Compact shell and chat dock

215 tests passed, including dock expand/minimize/close/reopen state, pending confirmation preservation, assistant-mode preservation, toolbar search and appearance selection. Desktop (1920×1080) and mobile (390×844) browser checks verified the floating panel, full chat view and themes; mobile had no horizontal overflow. Contrast and top-toolbar clipping found during visual checks were corrected. Chat settings collapse to keep the conversation prominent. Theme selection lasts for the current browser session.

## Grounded integration — 2026-11-03

Full integrated suite: **482 passed, 11 optional HTTP tests skipped, 10 subtests passed** in 40.49 seconds. Used the dedicated short Windows `--basetemp="D:/Documents/Code Repos/.t-m1"`; longer default fixture paths exceed the host path limit. Test import mode is configured for M2/M5 duplicate filenames. Production-store tests do not run concurrently with browser/live retrieval because M3 correctly fails closed when its administrative lock is busy.

Real Nebius generation + entailment check and actual NWS alert retrieval were verified separately from mocked tests. Browser checks covered the same live paths and deterministic emergency override. See [M1 completion handoff](M1_COMPLETION_HANDOFF.md) and [recorded public Qwen trace](evidence/m1-qwen-live-2026-11-03.json). Independent review identified the persisted-danger cross-screen gap; the shared panel now checks that case assessment and fails closed on unavailable assessment. M5 persistence code is unchanged.

## Polished workspace and spoken guide — 2026-11-03

Full suite: **487 passed, 11 optional HTTP tests skipped, 10 subtests passed** in 46.87 seconds. The Node lifecycle regression also passes and is now part of CI. Compile and whitespace checks pass.

Browser checks covered bright/dark desktop screens, mobile navigation, and no horizontal document overflow at 1440×1000 and 390×844. All six mobile tour targets were measured clear of the floating guide. The guide scrolls to actual controls and reserves enough room for the final chat input. Native Edge speech synthesis reported three voices and fired its narration-start callback after an explicit Listen click. A separate simulated-unsupported-browser check disabled Listen and retained written guidance. Speech-event tests with an explicitly injected browser stub verified no initial speech, step continuation after opt-in, Stop behavior, and End cleanup; these are distinct from the native voice check.

Independent review identified potential overlap between mobile highlights and the fixed guide; start alignment, scroll margins and tour-only bottom clearance resolve it. Browser testing also found stale spotlight elements across component data updates; explicit idempotent resource ownership fixes that and has a Node regression test. Emergency interruption ends the tour, and a fresh tour started from either navigation or confirmed chat resets narration consent.
