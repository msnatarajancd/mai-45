# M2 review and M1 integration

Reviewed 2026-11-03 against `origin/feature/m2-guardian` at
`5418de4445864edc6ca68572596c69edb2d80ad9`.
Integrated with a real non-fast-forward merge (`9e857016893508f983537cfd946b5b585c421966`)
into `feature/m1-grounded-integration`; no merge conflicts. No files were copied
between feature branches. This does not change GitHub PR #2 readiness or merge state.

## Application boundary

`services.nws_alerts.get_alerts(location_id, mode)` calls the shared
`GuardianService` directly. It needs no separate server, model, key, or new runtime
dependency. `requirements.txt` already includes the M5 requirements with Pydantic
and Streamlit; Guardian's service uses only the standard library.

The three existing municipality selections use the documented Miami-Dade county
zone, FLC086. Every response explicitly labels county coverage, lack of address-level
prediction, and the distinction between weather alerts and county evacuation orders.
The adapter does not invent geographic precision from city names.

Guardian `no_alerts` maps to M1 `none`; `unavailable` stays unavailable. Neither means
safe conditions. Original descriptions and instructions, official source URLs,
issue/effective/expiry times, sender and area are preserved. A live `checked_at`
is the request-start UTC time, not the warning issue time or successful completion
time. Failed live lookups retain that attempt time. Demo timestamps are fictional;
M1 keeps `checked_at=None` because no live check occurred and labels every demo headline.

## Review findings

The reviewed connector provides a User-Agent, 10-second network timeout, response-size
limit, explicit malformed/paginated-response failure, expiry filtering, cancellation
and supersession handling, official-host source links, and no silent demo fallback.
The direct service and its M1 adapter can be integrated without an HTTP dependency.
The optional API has authentication when configured, strict query validation,
no-store responses and unavailable/503 semantics. It is not deployed by this work.

Remaining coordination/deployment items:

- GitHub API verification on 2026-11-03 found PR #2 open, ready for review (draft=false), unmerged and mergeable_state=clean. This supersedes the older handoff stating it was a draft. No PR metadata or teammate messages were changed.
- The optional HTTP deployment needs its separate requirements, authentication,
  HTTPS, operational controls and hosting review. It is not required by M1's
  direct-import application path.
- The M2 handoff's provisional M3 statements and old test counts predate the merged
  M3 service. M1 should use its reviewed M3 adapter, not wire M2's optional explanation
  callback using the older provisional contract.
- County alerts do not establish current county evacuation orders or address-level
  risk. Those remain separate authoritative sources.
- UI clearing on location/mode change and emergency accessibility must remain in the
  application acceptance checks owned by M1.

## Verification

Executed with the repository `.venv`:

`python -m pytest tests/test_guardian_integration.py tests/test_m1_services.py m2_guardian/tests -q --import-mode=importlib`

Result: **72 passed, 11 skipped, 10 subtests passed**. The 11 optional HTTP tests
explicitly skip because FastAPI/httpx are absent; they are not claimed as passing.
These tests inject official-shaped fixtures to exercise successful alerts, no matches,
network failures and malformed responses, plus demo isolation and county labeling.
The legacy M1 outage test now injects a timeout rather than depending on a real outage.

A separate **real NWS request** through the M1 adapter succeeded at
`2026-11-03T20:38:11.570357+00:00` (lookup start): `status=alerts`, `simulated=false`,
`scope=county`, two alerts returned, source `https://www.weather.gov/`.
This is a historical smoke result, not a claim of current conditions. The no-alert
and outage cases above are injected tests, not real-world no-alert/outage observations.
No Qwen call was made for this integration.
