# ReadyRelief — Protect. Respond. Recover.

A Miami-Dade hurricane/flood course prototype for a five-person team. M1 provides a complete Streamlit application; M5's Recovery Copilot from PR #1 is integrated through its existing Python services. M2 Guardian and M3 reviewed CDC retrieval are integrated. M1 owns constrained Nebius/Qwen explanations; M4 safety review and the resource directory remain owner TODOs.

## Run the demo

Python **3.12** is the tested version. No API key is needed for the complete deterministic demonstration.

```powershell
cd "D:\Documents\Code Repos\mai-45"
uv venv --python 3.12
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app.py
```

Or use standard Python:

```sh
python -m venv .venv
# Activate .venv for your operating system, then:
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit. Choose **Start guided demo**. The sidebar walks through Protect → Respond → Recover → Evidence. [Rehearsal script](docs/DEMO_SCRIPT.md) covers a 6–8 minute presentation.

## What is implemented

- Polished bright/dark workspace with an icon theme switch, searchable navigation, a mobile menu, and a floating assistant that expands into a full chat screen.
- Responsive home and searchable top-toolbar navigation (names and synonyms such as tasks, weather, mobility); persistent emergency access on all six pages.
- Optional fictional household preferences and supported Miami-Dade area selection.
- Explicit simulated/live alert modes, context invalidation, unavailable service handling.
- Conservative emergency interruption and official-information links.
- Actual M5 recovery intake, deterministic draft, explicit approval, SQLite task updates, resume by case ID, reviewable reassessment, preserved history, and plan download.
- Retrieval-first Qwen explanations in Protect, Respond, Recover and expanded Assistant, with official citations, partial-evidence limits, provider-failure fallback and review-revocation checks. No ungrounded task generator is exposed in the integrated app.
- Evidence screen explaining connected capabilities and remaining integrations.
- Six-step spotlight walkthrough with optional browser narration, Listen/Stop controls, automatic control highlighting, and optional Nebius product explanations.
- Conversational Assistant for product help and validated app operations, with review cards before execution. [Assistant guide](docs/ASSISTANT.md).

## What is intentionally pending

| Owner | Handoff | Current behavior |
| --- | --- | --- |
| M2 | `services/nws_alerts.py` | Integrated Guardian county alerts; PR #2 is ready for review; optional HTTP deployment remains with M2 |
| M3 | `services/knowledge.py`, `services/resources.py` | Reviewed CDC recovery evidence connected; additional phase coverage and resource directory remain pending |
| M4 | `services/emergency.py` | Emergency controls work; conservative fallback only; reviewed rules/golden safety cases pending |
| M5 | Existing `recovery/` | Integrated unchanged from PR #1; source grounding, household persistence and any recovery-policy changes remain with M5/M3 |

[Detailed contracts, TODOs, acceptance checks](docs/INTEGRATION.md). [Design](docs/superpowers/specs/2026-11-02-m1-design.md). The supplied ReadyRelief_Plan.docx remains the requirements authority.

## Storage and configuration

The integrated app defaults to `.local/recovery.sqlite3` (ignored by Git). Override with an absolute `READYRELIEF_DB_PATH`. The standalone M5 `dev_recovery_preview.py` retains its original path behavior. Save your fictional case ID to resume after a browser/server restart on the same machine. Household preferences are session-only. Switching household preferences does not rewrite existing recovery cases.

`.env.example` documents configuration; the application does **not** automatically load `.env` files. For optional AI (also used by the new Assistant):

```powershell
$env:NEBIUS_API_KEY = "your-key"
# Optional for chat/tour: $env:NEBIUS_CHAT_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"
# Optional for M5 planner: $env:NEBIUS_MODEL = "provider-model-id"
.venv/Scripts/python.exe -m streamlit run app.py
```

Never commit keys. Missing/bad provider configuration shows reviewed excerpts with an explicit no-generation notice; saved tasks are unchanged. AI is not invoked by navigation, emergency access, or the default demo.

## Test

```sh
python -m pytest -q
python -m compileall -q app.py domain services ui recovery
```

On Windows, M3 fixtures can exceed the default temporary path length; use a dedicated short path, for example `python -m pytest -q --basetemp="D:/Documents/Code Repos/.t-m1"`. Pytest owns and clears that temporary directory.

The combined suite includes M2/M3 and the original M5 tests plus M1 service contracts, navigation, safety access, mode isolation, approval, persistence/resume, and stale-write checks. [Verification notes](docs/VERIFICATION.md) record the tested environment and limits.

## Team layout

```text
app.py                 single application entry point
ui/                    shared shell, seven screens, product tour, M5 presentation
assets/journey.svg     original local vector illustration (no remote asset dependency)
domain/contracts.py    M1–M4 integration data contracts
services/              M2/M3/M4 adapters, validated assistant planner/executor
recovery/              existing M5 domain, SQLite, planners, reassessment (unchanged)
tests/                 existing M5 + M1 regression tests
.streamlit/config.toml theme and local server defaults
docs/                  integration guide, demo script, design, verification
```

## Deployment

Use a local single-user demo for the contest; run the command above before rehearsing. Keep a backup recording. A hosted Streamlit demo uses `app.py`, Python 3.12, and `requirements.txt`, but **local SQLite may disappear on restart/redeploy**. This has no authentication or private multi-user isolation; case IDs are not access credentials. Do not expose real household data. An external store and access controls require M5/team work before any operational or public-user deployment.

## Scope and honesty

Educational prototype, not an emergency service. Online only. No dispatch, rescue requests, live shelter inventory, push alerts, maps, insurance submission, FEMA eligibility determination, or safety verification. Simulated warnings are never current weather. No-alert responses do not establish safety. Recovery templates are not claimed to be source-grounded. No contest-win or measured-impact claim is made.

## Grounded generation demonstration

Open **Recover → Ask Qwen about reviewed guidance**. Select **flood**, retain **electrical hazards**, then choose **Generate cited explanation**. The reviewed CDC passage may be insufficient for a complete answer; its partial status must stay visible. Open the evidence expander to inspect the exact passage and citation. An unsupported eligibility question produces no model answer. Protect and Respond honor their own evidence phase; recovery evidence is never silently reused for them.

A real, credential-free acceptance record is in [Qwen evidence](docs/evidence/m1-qwen-live-2026-11-03.json). Reproduce it explicitly with `python scripts/verify_grounded_generation.py --live`. This makes paid provider calls using the server environment key; unit tests use clearly labeled doubles. See [current M1 handoff](docs/M1_COMPLETION_HANDOFF.md).
