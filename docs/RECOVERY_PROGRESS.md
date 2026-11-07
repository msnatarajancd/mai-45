# Recovery Progress preview

Recovery Progress is a separate screen under **Recover**. Existing assessment, plan approval, tasks, reassessment, insurance inventory, attachments and exports remain the editing workflows.

## Run and explore

Install `requirements.txt`, run `python -m streamlit run app.py`, then open **Recovery Progress · Preview**. Select a household/checkpoint and click **Refresh checks**. Entry, navigation, details and browser reload never automatically start a check.

The **24 fictional households** each have `initial`, `update` and `later` checkpoints: **72 authored states** in total. The original Rivera, Chen, Alvarez, Baptiste, Morgan and Williams stories remain, alongside 18 stories covering large families, pets/transport budgets, full housing, accessibility, area-only and conflicting utility reports, water potability, stale observations, uninsured recovery, payment/allocation differences, currency/stage mismatches, linked evidence, provider responses and setbacks. Data includes **48 accommodation sites** (12 per category), **60 repair providers** (12 per trade) and **8 neutral fictional preparation checklists**. All identities, addresses, prices, ratings, capacities, responses and timing are synthetic.

Use the [demo walkthrough](RECOVERY_PROGRESS_DEMO_GUIDE.md) for short presentation routes, all household/checkpoint expectations, and MCP examples. A printable copy is available in [PDF](../output/pdf/ReadyRelief_Recovery_Progress_Demo_Guide.pdf). After updating fixtures, select **Refresh checks**; previously saved observations can correctly appear outdated until refreshed. Do not delete your saved Recovery database to prepare a demo.

`READYRELIEF_PROGRESS_PREVIEW=0` disables the preview. `READYRELIEF_PROGRESS_DB_PATH` sets its separate result database; default `.local/recovery-progress.sqlite3`, or a `-progress.sqlite3` sibling of an explicit `READYRELIEF_DB_PATH`. Runtime databases are ignored by Git.

## Architecture

Streamlit → LangGraph → official MCP Python client → local stdio Recovery MCP server → deterministic specialists → validated results → Next Best Action → dashboard.

Housing runs first; Utilities, Insurance & Funding and Rebuild run in parallel; Next Best Action follows. This is actual graph execution and MCP communication. It is not LLM reasoning or live provider verification. No API key, vector database or paid search service is required. The preview pins LangGraph 1.2.20 and official MCP Python SDK 2.3.0 in `requirements-progress.txt`. Tracing is disabled for this local workflow and provider credentials are not passed to its subprocess.

Execution state is separate from domain status: a completed check can report an outage. Synthetic latency is explicitly simulated. Results are tied to the input fingerprint, source mode, context and emergency epoch; changed context or danger invalidates late results. Failed checks do not make old observations current.

The latest attempt survives a browser reload. An abandoned in-flight attempt is shown as interrupted and needs a manual refresh. After a partial failure in the same household context, source and checkpoint, earlier successful details remain available under **Earlier successful observation — outdated**, retaining their original observation time. Switching checkpoints does not carry those details into the new checkpoint. A failed check says **No new observation** and contributes no old recommendation to the current ranking.

## Use from another MCP host

The server command is `python -m recovery.progress.mcp_server`, using the interpreter where requirements are installed. Example compatible-host configuration (replace paths; enclosing formats can vary):

```json
{
  "mcpServers": {
    "readyrelief-recovery": {
      "command": "/absolute/path/to/mai-45/.venv/bin/python",
      "args": ["-m", "recovery.progress.mcp_server"],
      "env": {"PYTHONPATH": "/absolute/path/to/mai-45"}
    }
  }
}
```

Read-only tools: `find_temporary_housing`, `check_utility_health`, `assess_insurance_readiness`, `assess_funding_gap`, `search_repair_providers`. Insurance and funding share one assessment so the business rules remain consistent. The server calls the same functions in `recovery/progress/` as the app's domain layer.

Call a tool with `{"scenario_id":"rivera","checkpoint_id":"initial"}`. The graph alternatively supplies a complete typed `payload`, including confirmed saved-case projections or checkpoint-scoped simulated updates. Choose one mechanism, not both. Responses include source mode, context key, input fingerprint and structured results. No tool reads arbitrary files, writes accepted cases, reserves housing, sends messages or submits claims.

Useful tool examples include `santos/update` (whole-household capacity), `garcia/update` (water supply versus potability), `singh/update` (received money without allocation), `wilson/initial` (unlinked evidence), and `davis/update` (a replacement provider quote). `campbell/update` intentionally fails the utility check. Williams checkpoints and `fernandez/update` pause routine tools because safety is unconfirmed or danger is reported; these are expected rejections, not successful checks.

The authoring-only `catalog` object in a checkpoint can select housing/provider IDs, override supplied fields, and set observation age and validity. Empty selections remain empty. Unknown IDs, duplicate selections, identity/provenance changes and invalid typed values are rejected. Source catalog rows never mutate. `demo_scenarios.json` carries the presenter notes and checked expected signals, execution states and primary actions.

Run `python -m scripts.verify_recovery_demo_data` to exercise all five tools across all 72 checkpoints through the actual local stdio MCP boundary. Its report distinguishes ordinary results from expected safety and simulated-service rejections.

## Saved fictional cases and limitations

Existing Recover offers an optional, reviewed profile: confirmed total, ZIP/full fictional address, recovery-start date, accessibility/pets/transport, nightly housing budget, broad repair contribution and gas applicability/report. A known adults/children sum is not silently promoted to a confirmed total. Profile saves do not alter accepted tasks. The overview masks the address.

The dashboard reads a consistent case/records/plan/insurance/profile aggregate and uses a cheap revision check while polling, rather than repeatedly reading photos. Missing saved-case availability, provider/checklist suitability and financial events remain unknown. This local prototype still requests fictional information only.

Hotel rooms and shelter spaces retain their units. Water availability is not potability. Area reports do not establish address restoration. Evidence preparation is not insurer approval. Expected/approved-but-unpaid funds are not cash; broad contribution bands cannot establish an exact funding gap. Home and funding milestones are separate. Synthetic timing is illustrative; saved cases display **Not enough information**.

## Checks

Run `python -m pytest -q`, `node tests/search_suggestions.mjs`, `node tests/tour_lifecycle.mjs` and `npm run test:visual -- tests/visual/progress.spec.cjs`. Runtime tests exercise the actual stdio MCP boundary and LangGraph. Browser checks cover refresh, details, stale context, themes and responsive layout. Existing screenshot baselines target Windows; do not blindly replace them with macOS renders.

Verified after the synthetic-data expansion on November 6, 2026: **1,283 Python tests passed**, 11 skipped, 10 subtests passed (`python -m pytest -q --ignore=artifacts`); **12 Progress browser checks passed** across desktop, tablet and mobile. All 72 checkpoints were exercised through **360 actual stdio MCP calls**: 339 successful results and 21 expected safety/service rejections. Compilation and whitespace checks passed. Existing Windows screenshot-baseline comparisons were not run on this Mac. The 18-page demo guide was rendered and visually inspected.
