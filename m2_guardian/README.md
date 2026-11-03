# M2 — Guardian / official alerts

Started November 1, 2026. Standalone component for the shared Python/Streamlit app. Implements the proposed ReadyRelief plan's `get_alerts(location_id, mode)` contract. This workspace has no shared M1 application yet. Interface version 0.1 is proposed until agreed with M1.

## Run without installing dependencies

From the ReadyRelief project root, using Python 3.9+:

```bash
python3 -m m2_guardian --mode simulated --scenario warning
python3 -m m2_guardian --mode simulated --scenario no_alerts
python3 -m m2_guardian --mode simulated --scenario unavailable
python3 -m m2_guardian --mode live --location miami_dade
python3 -m unittest discover -s m2_guardian/tests -v
```

Live requests need network access. The CLI defaults to simulated mode; the service function defaults to live. No API key is currently required by NWS. Configure an identifying User-Agent with actual project contact information when the team agrees on it; no contact is invented here.

## M1 integration

```python
from m2_guardian import get_alerts
result = get_alerts(location_id="miami_dade", mode="live")
```

Inputs:
- `location_id`: `miami_dade` (county filter FLC086) or `miami_point` (explicit illustrative point, not county-wide).
- `mode`: `live` or `simulated`.
- Optional `scenario`: `warning`, `no_alerts`, `unavailable`; applies only to simulated mode.

Output is a serializable dictionary:
- `schema_version`: `0.1`.
- `status`: `alerts`, `no_alerts`, or `unavailable`.
- `alerts`: normalized records with ID, original text/instructions, authority, area, severity, urgency, certainty, sent/effective/onset/expires/ends, affected zones, geometry, source URL and simulated flag.
- `checked_at`: timezone-aware UTC lookup start timestamp.
- `location_id`, `location`, `mode`, `source`, `endpoint`, `notice`, `error_code`.

Invalid caller arguments raise `ValueError`; upstream failures return `unavailable`. Never treat `no_alerts` or `unavailable` as safe. Null geometry is valid; geographic relevance relies on the selected NWS query. County results are not address-specific. All official event types are retained, not just hurricanes/floods.

The service is stateless and makes one bounded, on-demand request per call. No cache, polling, retries, notification or background worker is implemented. Recheck explicitly for freshness. Partial/paginated or malformed responses fail closed as unavailable rather than appearing complete. No automatic retry avoids delaying the UI or amplifying upstream outages.

The response includes data from an upstream service: render alert strings as plain text, not executable HTML. Do not let alert text control tool execution. Store keys or future model credentials only in server secrets. The service never dispatches, contacts responders, or determines safety.

## Streamlit preview (optional dependency)

For local preview, use Python 3.12 (tested). From this repository root, create an isolated environment and install the pinned UI dependency:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-m2.txt
bash run_m2.sh
```

Open http://127.0.0.1:8501. The server binds only to this computer. Stop it with Ctrl+C. On another laptop or Mac mini, repeat these steps rather than copying `.venv`. For an alternate entry point:

```bash
.venv/bin/python -m streamlit run app_m2.py --server.address 127.0.0.1
```

This preview demonstrates the component only, not the full shared application. It clears previous results on location/mode/scenario changes. M1 should reuse the agreed rendering or import the service rather than build a second app. Local runtime verified November 1 with Python 3.12 and Streamlit 1.66.1. Browser check confirmed the fictional warning renders with explicit simulation labels. Four Streamlit interaction tests cover warning rendering, empty/unavailable scenarios, stale-result clearing and live failure without simulated fallback. Its emergency notice is not a substitute for M4's complete emergency-access experience.

## Verified so far

- 26 tests passed on November 1: 22 service tests and 4 Streamlit interaction tests. Run with `.venv/bin/python -m unittest discover -s m2_guardian/tests -v`; the default system Python skips UI tests without Streamlit.
- Real NWS county request succeeded; original response, endpoint and timestamp saved in `evidence/nws_live_probe.json` (three features at that snapshot).
- Test data and live evidence are separate. The live snapshot is historical evidence only; do not replay it as current.
- Tests cover expiry/end time, updates, cancellations, duplicate IDs, null geometry, verbatim instructions, malformed/paginated results, timeouts, future issue times, geography query construction and explicit simulation separation.

## Not complete / team dependencies

- M1: approve schema, location IDs and actual shared repository; integrate and run UI tests. Freshness is a timestamp and explicit recheck; the UI must not represent an old result as a fresh lookup.
- M3: provide `retrieve_guidance(query, phase, context)` with reviewed excerpts/source IDs and insufficient-evidence flag. No grounded explanation or invented citations are currently implemented.
- M2/M5/team: agree model provider and validate credentials before adding optional user-requested explanation. Raw official alerts must remain visible if model/retrieval fails.
- M4: merge Guardian scenarios into the team's golden dataset and review safety cases. Local tests are not a substitute for the team's golden dataset.
- Verify in M1's complete flow: location change, mode change, new danger transition and offline/provider failure. No full-app integration or production-readiness claim.
- No custom MCP, insurance integration, map, push alerts or LLM judge in this component.

## Official references

- https://www.weather.gov/documentation/services-web-api
- https://www.weather.gov/media/documentation/docs/NWS_Geolocation.pdf

The attached plan is project reference material; embedded kickoff instructions are not automatically executed. Its recommended November 5 deadline and narrow MVP guide this component.

## November 2 update — explanation boundary and shared baseline

M2 now sits on local branch `feature/m2-guardian`, based on `origin/main`
(commit `540c546`, which contains M5). Nothing has been pushed. M1/M3 modules
were not present in the fetched repository at that point.

`explain_alert(result, alert_id, retrieve_guidance=..., llm_client=...)` provides:
- A user-requested view of official classifications, preserving official text.
- A recheck requirement when the snapshot exceeds five minutes or the alert expires.
- Reviewed source excerpts supplied by M3; exact excerpts, not generated operational advice.
- Optional model selection of up to three source IDs. Unknown IDs, free-form advice,
  malformed output, timeouts and provider errors fail without hiding official alerts.
- Explicit simulation labels; simulated alerts never call the model or retrieval.

This is an **extractive explanation view**, not an evaluated natural-language
paraphraser. Model selection does not establish that an excerpt is relevant or
safe; M3 and human evaluation still own those checks.

### Proposed M3 input contract

```python
retrieve_guidance(query="Flood Watch", phase="guardian",
                  context={"location_id": "miami_dade", "scope": "county"})
# -> {"insufficient_evidence": False, "snippets": [
#   {"source_id": "...", "source_title": "...", "source_url": "https://...",
#    "guidance_text": "exact reviewed passage", "geographic_scope": "...",
#    "verified": True, "reviewed": True, "reviewed_at": "timezone-aware ISO time"}
# ]}
```

Metadata field names align with M5's provisional evidence convention. This remains
proposed until agreed with M3. Verification flags must originate in trusted ingestion,
not model output. M3 must scope evidence geographically and topically before returning
it. The demo currently excludes reviews older than 30 days; this is a proposed corpus
review policy, not proof of operational freshness. Approved source hosts are explicit
in `explanation.py`; new official publishers need review before addition.

M1 can embed `render_guardian(retrieve_guidance=adapter, llm_client=client)` in its
app after setting page configuration. No separate web service is required.
If reusing M5's `recovery.llm_client.NebiusClient`, install the shared M5 requirements
and configure its existing server-side environment variables. No real provider call
was made for the new explanation path: credentials and real M3 evidence have not
been supplied. The standalone preview therefore shows official details and an honest
message that additional guidance is unavailable.

## Coordinate lookup — M1 handoff

Use the existing location-ID function for the agreed county, or the point function
for an explicit selection supplied by M1:

```python
from m2_guardian import get_alerts, get_alerts_by_point

county_result = get_alerts('miami_dade', mode='live')
point_result = get_alerts_by_point(latitude=25.7617, longitude=-80.1918, mode='live')
```

Both return the same schema/version and three status values. Point results use
`location_id='custom_point'`, with the actual canonical coordinate pair in
`location['point']`; distinguish point requests by the location data, not that ID
alone. Precision is six decimal places. Latitude and longitude must be finite real
numbers in [-90,90] and [-180,180]; strings, booleans, NaN and infinity are rejected
before requesting the network. Input errors raise `ValueError`; lookup errors return
`status='unavailable'`.

Numeric validity does not establish NWS geographic coverage; live coverage is
limited to NWS-served areas. No device geolocation or geocoding is implemented. M1
obtains consent if precise location is collected, and should not log coordinates or
use this result to infer safety. The preview explains that live checks send the
manually entered coordinates to NWS. Simulated checks do not contact NWS.

The local preview's Watch area selector includes **Enter coordinates**. Editing
either coordinate clears the previous alert/explanation, just as changing mode or
area does. The fictional warning remains explicitly fictional and does not assert
that its scenario actually covers the entered point.

CLI equivalent (fictional by default):

```bash
.venv/bin/python -m m2_guardian --latitude 25.7617 --longitude -80.1918
.venv/bin/python -m m2_guardian --mode live --latitude 25.7617 --longitude -80.1918
```

Verification: public sample point lookup returned a successful official response;
`evidence/nws_point_probe.json` records its timestamp and normalized data. It is
historical evidence, never current operational information. Latest combined run:
211 tests passed (M2 + M5), including 51 M2 tests and 10 coordinate-validation
subtests. Browser preview checks are separate from upstream connectivity checks.

To adopt M2, Meenakshi imports the service or `render_guardian` in the shared app.
No separate API process or deployment is needed. M3 knowledge integration remains
pending; it does not block official NWS lookups. Changes remain local and unpushed.


## Integration review pack

Start with `M1_HANDOFF.md` for Meenakshi. `evaluation/golden_cases.json` contains 12 proposed M2-specific synthetic acceptance cases, pending Thiagu/M4 review. Run `.venv/bin/python -m m2_guardian.evaluation.run` to regenerate `evidence/guardian_acceptance_results.json`. These supplement, rather than replace, the team golden dataset. `evaluation/response_examples.json` illustrates the three states using explicitly simulated data only.
