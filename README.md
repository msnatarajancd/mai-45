# ReadyRelief — Protect. Respond. Recover.

**Recovery Progress preview:** a separate dashboard under Recover with LangGraph orchestration, a local read-only MCP server, 24 synthetic household stories across 72 checkpoints and confirmed saved-case projections. See [setup, MCP tools and limitations](docs/RECOVERY_PROGRESS.md) and the [demo walkthrough](docs/RECOVERY_PROGRESS_DEMO_GUIDE.md).

A Miami-Dade hurricane/flood course prototype. The Streamlit app integrates M2 Guardian county alerts, M3 reviewed CDC retrieval, CAP-04 local emergency routing, optional constrained Qwen explanations, and M5 recovery planning and SQLite persistence. Emergency routing requires no AI. The directory publication machinery is implemented; all eight prepared directory listings still await review.

## Run locally

Python **3.12** is the tested version. From this repository, create and activate a virtual environment:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On Windows PowerShell, use `py -3.12 -m venv .venv` and `.venv\Scripts\Activate.ps1`, then the same install and run commands. No API key is needed for the deterministic demonstration. Open the local URL printed by Streamlit and choose **Start guided demo**. The [rehearsal script](docs/DEMO_SCRIPT.md) includes CAP-04 and a separate fictional recovery scene.

## What is implemented

- Responsive bright/dark shell, searchable navigation, mobile menu, guided tour, and a floating assistant that expands into a full chat screen.
- Optional, session-only fictional household preferences and area selection.
- Explicit simulated/live alert modes. Live checks request official county-wide NWS alerts on demand; failures remain unavailable and never become simulated alerts.
- **I Need Help Now** workspace with **Call 911** first and **I Can't Call 911** second. Neither action requires AI, a profile, classification, location, or a database write. A user-initiated telephone link expresses call intent; it does not confirm connection or dispatch.
- Deterministic classification of multiple incident types and four urgency levels; uncertain requests retain emergency access. Current reported danger interrupts routine Guardian, chat, guidance, and recovery work, invalidates stale proposals, and queues best-effort danger persistence.
- Optional current incident county and communication needs, stable cannot-call information, desktop dialing fallback, and explicit connectivity limits. Saved or monitored location never establishes current incident location.
- Reviewed directory lookup with source, passage, listing, scope, expiry, and integrity gates. Pending entries stay hidden; official entry links are labeled separately from verified matches.
- M5 intake, deterministic draft, explicit approval, SQLite task updates, resume by case ID, reviewable reassessment, preserved history, and plan download.
- Retrieval-first Qwen explanations with approved citations, partial-evidence limits, provider-failure fallback, and revocation checks. Generation never supplies the emergency routing decision or automatically changes a recovery task.
- Six synthetic emergency demos, three fictional profiles, nine failure-state descriptions, 48 development cases, and 24 independently authored golden cases. Expectations are **PROPOSED**, not human-approved safety evidence.

## Review readiness and remaining work

| Area | Current state |
| --- | --- |
| M2 Guardian | Integrated county alerts; no continuous monitoring or household-level conditions |
| M3 guidance | Five approved CDC recovery passages; other phases and sources remain limited by their actual review state |
| CAP-04 routing | Local policy, shared interruptions, UI, and synthetic evaluation implemented; synthetic success is not real-world safety certification |
| CAP-04 directory | Eight PENDING listings: seven have acquired-source passages; FCC acquisition failed and has no publishable capture. No new source, passage, or listing approval was fabricated |
| M5 recovery | Local persistence and reassessment integrated; source-grounded task planning, durable household context, and an explicit danger-clearance workflow remain future work |

See [integration contracts](docs/INTEGRATION.md), [CAP-04 implementation](docs/CAP04_IMPLEMENTATION.md), and the [directory review packet](docs/CAP04_SOURCE_REVIEW.md). Returning from an emergency view does not clear a saved danger report or establish safety.

## Storage and configuration

The app defaults to `.local/recovery.sqlite3` (ignored by Git). Override with an absolute `READYRELIEF_DB_PATH`. Save the fictional case ID to resume after a browser/server restart on the same machine. Household preferences and chat are session-only; changing preferences does not rewrite existing recovery cases.

`.env.example` documents optional AI configuration; the app does **not** automatically load `.env` files. Set `NEBIUS_API_KEY` in the server environment only when using AI. `NEBIUS_CHAT_MODEL` selects the chat/tour model; `NEBIUS_MODEL` is also supported by the M5 client. Never commit keys. Missing or bad provider configuration produces an explicit unavailable/no-generation notice. Emergency access, local routing, and the deterministic demo make no provider calls.

## Verification

```sh
python -m pytest -q
python -m emergency.evaluation.run --dataset golden --output artifacts/cap04-evaluation.json
python -m emergency.evaluation.run --dataset development --output artifacts/cap04-development.json
python -m compileall -q app.py domain services ui recovery emergency knowledge m2_guardian
node tests/tour_lifecycle.mjs
node tests/search_suggestions.mjs
```

For browser checks, install the Node dependencies and Chromium with `npm ci` and `npx playwright install chromium`, then run `npm run test:visual`. The emergency suite is `npm run test:visual -- tests/visual/emergency.spec.cjs`; it inspects the telephone target without dialing.

The evaluator records type, urgency, routing, safety, critical misses, bounded forbidden-claim checks, and measured provider/network attempts with policy and dataset versions. Its guarded Python/provider boundaries are documented in [evaluation notes](emergency/evaluation/README.md); this is not an operating-system sandbox. [Verification notes](docs/VERIFICATION.md) hold the coordinated results and remaining limitations. On Windows, a short dedicated `--basetemp` path may be needed for M3 fixtures; pytest owns and clears that directory.

## Team layout

```text
app.py                 single application entry point
ui/                    shared shell, emergency workspace, tour and M5 presentation
domain/                application and directory contracts
services/              M2/M3/M4 adapters, constrained generation and assistant actions
emergency/             local policy, interruption state, demo loader and evaluation
knowledge/             acquired sources, review gates, retrieval and directory
recovery/              M5 domain, SQLite, planners and reassessment
m2_guardian/            official alert integration and simulated alert fixtures
data/emergency_demo/   explicitly synthetic presentation and failure inputs
data/official_sources/ original captures, review records and pending directory entries
tests/                 Python, JavaScript and browser regression checks
docs/                  integration, review packets, demo and verification records
```

## Scope and deployment

Use fictional data in a local single-user demonstration and keep a backup recording. This educational prototype has no authentication or private multi-user isolation; case IDs are not access credentials. Hosted local SQLite can disappear on restart or redeploy. External storage, access control, and retention need separate team work before any operational deployment.

The app is online only. Local deterministic routing means independence from AI, not offline operation or guaranteed server/browser connectivity. There is no automated dispatch, message sending, rescue confirmation, transport booking, guaranteed pickup, live shelter capacity, push alerting, insurance submission, benefit eligibility decision, or household safety verification. A successful click proves none of those outcomes. Simulated warnings are never current weather; no-alert responses do not establish safety.

## Optional grounded generation

In Recover, expand **Ask Qwen about reviewed guidance**, select **flood**, and request **electrical hazards**. Approved CDC evidence may support only a partial answer; keep that limitation visible. Unsupported eligibility questions produce no generated answer. Protect and Respond use their own phase and cannot silently reuse recovery evidence.

Historical real-provider evidence is recorded in [Qwen evidence](docs/evidence/m1-qwen-live-2026-11-03.json). `python scripts/verify_grounded_generation.py --live` explicitly makes paid calls using the server key; normal tests use labeled doubles. See the [M1 handoff](docs/M1_COMPLETION_HANDOFF.md) and [assistant guide](docs/ASSISTANT.md).
