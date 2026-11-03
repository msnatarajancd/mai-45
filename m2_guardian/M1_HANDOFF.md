# M2 Guardian — handoff to Meenakshi (M1)

Owner: Karthik. Review partner: Thiagu (M4). M3 remains unassigned.
Status: locally implemented/tested; no push or full M1 app integration yet.

## What to integrate

M2 remains an importable Python module. An optional HTTP adapter is now also available; see API_HANDOFF.md for endpoints, authentication and local startup.
Core alert lookup requires only Python's standard library. Streamlit is needed
only for the optional screen. No model key or M3 dependency is needed for alerts.

```python
from m2_guardian import get_alerts, get_alerts_by_point

# Call only on an explicit user action, not on every Streamlit rerun.
if st.button('Check alerts'):
    try:
        result = get_alerts_by_point(latitude, longitude, mode='live')
    except ValueError:
        st.error('Please check the location input.')
    else:
        st.session_state['guardian_result'] = result

# County alternative:
# result = get_alerts('miami_dade', mode='live')
```

The example assumes M1 has already imported Streamlit and obtained validated
location inputs. When selection or mode changes, clear previous results. The M2
preview shows one tested implementation of this behavior.

## Result contract (schema_version 0.1)

| Field | Meaning |
| --- | --- |
| status | `alerts`, `no_alerts`, `unavailable` |
| mode | `live` or `simulated`; always visible in the UI |
| alerts | Original official text plus normalized metadata; empty on failure |
| checked_at | UTC ISO timestamp at lookup start; not the NWS issue time |
| location | Label, `scope` (`point`/`county`), and `point` or `zone` |
| location_id | County/preset ID or `custom_point`; use location data to distinguish coordinates |
| source / endpoint | Official fallback and requested API endpoint (no endpoint in demo mode) |
| notice / error_code | Display-safe notice and machine-readable error category |

Each alert contains `id`, `event`, `headline`, `area`, `sender`, `severity`,
`urgency`, `certainty`, timestamps, `description`, `instruction`, `source_url`,
`geometry`, `affected_zones`, `message_type`, and `simulated`.

See `evaluation/response_examples.json` for all three result shapes. Every example
is explicitly simulated; do not present it as current official conditions.

## UI behavior to retain

- Present official instructions verbatim as plain text.
- Show lookup timestamp, official source and live/demo labels.
- No matches must not imply conditions are safe.
- Unavailable must not silently become no-alerts or a fictional warning.
- Clear results and explanation when the selection/mode changes.
- M4's emergency actions remain accessible regardless of M2 success.
- County results are not address-level predictions; coordinate validity does not
  establish NWS geographic coverage. Don't log precise coordinates unnecessarily.

M1 may use the supplied renderer after its own page configuration:

```python
from m2_guardian.streamlit_demo import render_guardian
render_guardian()  # Official alerts work without M3 or model credentials.
```

This renderer currently includes its own location selector; use the service
functions instead when M1 owns the shared location/profile controls. Keys should
be namespaced if M1 introduces additional widgets with the same labels.

## Guidance integration is a separate step

`render_guardian(retrieve_guidance=m3_adapter, llm_client=client)` accepts optional
adapters. Without them, the alert and classifications are still visible. No
free-form model-generated operational advice is currently displayed. M3 record
schema and review policy are provisional; see README before connecting.

## Local verification

```bash
.venv/bin/python -m pytest tests m2_guardian/tests -q --import-mode=importlib
.venv/bin/python -m m2_guardian.evaluation.run
bash run_m2.sh
```

The combined run has 211 passing tests. The separate proposed M2 acceptance pack
has 12 passing synthetic cases and makes no network or model calls. These are not
claimed to be the team's supplied golden dataset or evidence of real-world safety.
The shared M5 requirements supply pytest for the combined command.

## Remaining team actions

1. Meenakshi adopts the service interface and supported location controls.
2. Thiagu reviews M2 acceptance cases and emergency access in the integrated app.
3. M3 owner supplies reviewed evidence and agrees the retrieval schema.
4. Run the whole Protect → Respond → Recover story after integration; local module
   tests do not establish that the complete application is integrated.


## Optional HTTP interface (latest update)

M2 can now also run as a FastAPI service, using the same connector. See [API_HANDOFF.md](API_HANDOFF.md). Direct imports remain supported; Meenakshi can choose either interface. Nothing has been hosted publicly. The module guidance above still applies to the direct-import path.
