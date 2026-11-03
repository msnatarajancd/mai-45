# Guardian HTTP API — optional M2 deployment boundary

M2 now supports two interfaces over **the same alert logic**:

1. Direct Python imports in the shared app (still supported).
2. HTTP via FastAPI for a separately running service on a laptop, Mac mini or a
   future Replit deployment. No public deployment has been configured.

## Local start (Python 3.12 tested)

From the repository root, with an existing `.venv`:

```bash
.venv/bin/python -m pip install -r requirements-m2-api.txt
bash run_m2_api.sh
```

No Streamlit dependency is required for the HTTP adapter. API runs at
`http://127.0.0.1:8000`; interactive reference is `/docs`, machine-readable schema
is `/openapi.json`, and liveness is `/health`. The UI preview still runs separately
at port 8501 with `bash run_m2.sh`.

## Endpoints

| Request | Meaning |
| --- | --- |
| `GET /health` | Process liveness only; does not check NWS or authentication |
| `GET /v1/alerts?location_id=miami_dade` | Live county lookup |
| `GET /v1/alerts?latitude=25.7617&longitude=-80.1918` | Live point lookup |
| `GET /v1/alerts?mode=simulated&scenario=warning` | Explicitly fictional warning |
| `GET /v1/alerts?mode=simulated&scenario=no_alerts` | Explicitly fictional empty response |
| `GET /v1/alerts?mode=simulated&scenario=unavailable` | Explicitly simulated failure |

Omitting location defaults to Miami-Dade. Use a location ID OR both coordinate
parameters, not both forms. NWS coverage is limited to NWS-served areas. All
non-simulated requests call NWS on demand. No polling, cache or push is introduced.
Unknown/duplicate query parameters, invalid coordinates, unsupported modes and
live requests with a scenario parameter are rejected.

## HTTP semantics

- **200:** valid lookup with `status='alerts'` or `status='no_alerts'`.
- **503:** body retains the normal result contract with `status='unavailable'`,
  including a deliberately simulated outage. Do not replace with an all-clear.
- **422:** invalid or ambiguous request; body contains a validation/error detail.
- **401:** configured API key missing/incorrect.

The result fields match the module contract. Serialization can canonicalize ISO
UTC timestamps, so compare timestamps as instants rather than raw strings. Every
response sends `Cache-Control: no-store`. No wildcard CORS is enabled; M1 Streamlit
should call the service from its Python backend, not put keys into browser code.

## Meenakshi's backend integration

```python
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

base_url = os.environ.get('GUARDIAN_BASE_URL', 'http://127.0.0.1:8000')
query = urlencode({'latitude': 25.7617, 'longitude': -80.1918, 'mode': 'live'})
headers = {}
if os.environ.get('GUARDIAN_API_KEY'):
    headers['X-API-Key'] = os.environ['GUARDIAN_API_KEY']
request = Request(base_url.rstrip('/') + '/v1/alerts?' + query, headers=headers)
try:
    with urlopen(request, timeout=15) as response:
        result = json.load(response)
except HTTPError as error:
    if error.code == 503:
        result = json.load(error)  # Display unavailable notice, not no-alerts.
    else:
        raise  # Map 401/422 to an appropriate application-owned message.
# Also handle connection/timeouts in M1; do not retain old data as current.
```

Only request after user action. Clear old results when location/mode changes;
preserve source, timestamps, official text and live/demo labels in M1's UI.

## Configuration and future hosting

- `GUARDIAN_API_KEY`: optional for local-only tests; guards `/v1/alerts` when set.
- `GUARDIAN_HOST`: launcher defaults to `127.0.0.1`. Non-loopback binding requires
  a nonempty key. No network exposure has been enabled by this implementation.
- `PORT`: local default 8000; can use a hosting platform's provided port later.
- Uvicorn access logs are disabled in the launcher to avoid logging coordinate
  query strings. Hosting proxies and caller logs need separate configuration.

For a future hosting platform with dependencies already installed, the equivalent
command is `python -m uvicorn m2_guardian.api:app --host 0.0.0.0 --port "$PORT" --no-access-log`.
Set a server-side key first and use platform-provided HTTPS. This example is a
future startup command, not a deployed service or a complete production design.
API keys, rate limiting, operational monitoring and hosting privacy/access settings
need review before public exposure. The local launcher's binding check does not
protect alternative launch commands from misconfiguration.

## Verification and remaining work

The HTTP tests use the real adapter with injected upstream fixtures, including
input errors, auth, no-match, outage and simulated modes. Live HTTP smoke checks
verified health, demo warning, simulated outage (503), bad coordinates (422), and
one successful NWS request for public sample Miami coordinates (200). Results are
in `evidence/api_smoke_results.json`.

No HTTP explanation endpoint is exposed yet. M3 retrieval and model-backed
guidance remain a separate integration; none are required for this alert API.
Health is not an upstream availability guarantee. This is still a course prototype.
