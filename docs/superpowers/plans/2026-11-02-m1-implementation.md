# ReadyRelief M1 Implementation Plan

> Execute inline using the executing-plans and test-driven-development skills.

**Goal:** Deliver the complete M1 app and usable integration seams for M2–M5.
**Architecture:** Streamlit shell + typed service adapters + existing M5 domain and SQLite. UI remains independent of unavailable external services.
**Tech Stack:** Python 3.12, Streamlit 1.66.1, Pydantic 2.14.2, pytest 9.2.0.
**Spec:** ../specs/2026-11-02-m1-design.md

## Constraints and review focus
Miami-Dade hurricane/flood only; guest-first; synthetic data; no dispatch, shelter availability claims, or hidden AI dependency. Verify mode/area invalidation, storage failures, immediate danger across pages, explicit plan approval, and stale reassessment/task writes.

## Tasks
1. [x] Test and implement contracts, context invalidation, M2/M3/M4 fallback adapters, safe external links. Files: domain/contracts.py, services/*.py, ui/state.py, tests/test_m1_services.py. Run pytest on the new tests; expect initial missing module failure then passing behavior.
2. [x] Test and implement app shell, navigation, household inputs, Protect/Respond/Evidence and demo guide. Files: app.py, ui/components.py, ui/pages.py, ui/styles.css, assets/journey.svg, .streamlit/config.toml. AppTest must render every route with persistent emergency controls, disclose fixtures, and clear stale results.
3. [x] Test and implement polished M5 recovery UI using its public services, with intake, explicit approval, progress, resume, and reviewable reassessment. File: ui/recovery_page.py. Verify SQLite reload and preserved completed task identities; keep M5 source unchanged.
4. [x] Document run/deploy steps, service contracts and owner TODOs, benchmark findings, rehearsal and known limitations. Run all tests, compile checks, and browser desktop/mobile walkthrough. Review final diff independently and resolve material findings.

## Execution notes
The user's supplied master plan and explicit request to complete M1 authorize implementation; no additional scope/design approval is required. Work is on feature/m1-app-integration in a fresh clone of the specified repository. Existing M5 source and tests are preserved.
