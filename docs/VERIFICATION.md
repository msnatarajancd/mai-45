# Verification record — November 2, 2026

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
