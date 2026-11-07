# Replit demo deployment

Deploy the existing `app.py`, not a generated replacement app. Python 3.12 is the
tested runtime. One Streamlit process contains M1–M5; Recovery Progress starts its
read-only MCP subprocess internally. The standalone Guardian API is optional and
is not started or exposed by this deployment.

## Project setup

1. Import `https://github.com/msnatarajancd/mai-45` into a Replit Python project.
2. Select the branch containing this deployment preparation (`deploy/replit-demo`
   until merged). Select Python 3.12 in the project's runtime settings; no specific
   unverified Replit module identifier is hardcoded.
3. Install dependencies: `python3 -m pip install -r requirements.txt`.
4. Run `python3 scripts/start_replit.py`. `.replit` supplies this Run command.
5. Confirm one external port: internal 8501 mapped to external 80. If using a
   different PORT, adjust the port mapping to match; default is 8501.

No Node build is required for the runtime; the custom Streamlit components are
embedded in Python. Node and Playwright are development/browser-test tooling.

## Secrets and settings

- `NEBIUS_API_KEY`: optional for deterministic demo, required for AI chat and
  generation. Enter directly in Replit Secrets, never in chat/source control.
- `NEBIUS_CHAT_MODEL`: optional model override for chat/guidance.
- `NEBIUS_MODEL`: optional override for M5's planner client.
- `READYRELIEF_PROGRESS_PREVIEW`: default enabled; set `0` to hide this preview if
  Replit MCP-subprocess verification fails. Report the limitation rather than
  calling a hidden feature verified.
- `PORT`: optional; default 8501. Keep mapping consistent.
- `READYRELIEF_DB_PATH` and `READYRELIEF_PROGRESS_DB_PATH`: optional filesystem
  overrides only, NOT database URLs. Startup defaults to repository-local .local
  SQLite files. They do not establish durable cloud storage.

The app does not load .env automatically. Secrets must be present in the server
and published deployment environment. Check production secrets separately before
publishing; do not assume workspace secrets were copied.

## Publishing proposal

Use one Reserved VM for the first controlled demo, subject to confirming account
entitlement and cost. Build: `python3 -m pip install -r requirements.txt`.
Run: `python3 scripts/start_replit.py`. Bind to 0.0.0.0 with a single public port.
Choose Only you or Workspace only if the account permits; otherwise keep the
preview private until a team access decision is made. A public demo needs explicit
approval with its fictional-data and storage limits understood.

A subscription alone does not establish included deployment capacity or authorize
additional charges. Check the actual machine price/credit estimate before the
final publishing action; obtain an agreed spending cap if new charges apply.

## Demo limitations

The app has no authentication or private multi-user record isolation. Use synthetic
households and test attachments only. Case IDs are not access credentials. Never
reuse a local real-user database in the published artifact.

SQLite stores recovery cases, task history, progress and insurance attachments.
Do not promise continuity across restarts, redeploys or replicas. Reserved VM does
not by itself make filesystem writes durable. Replit-managed SQL requires actual
repository/schema adaptation; setting DATABASE_URL alone will not convert SQLite.
Session-only household/chat state can reset on reconnect or restart.

The committed reviewed-source corpus can be bundled as read-only deployment data.
Review/acquisition changes should happen through the source-review workflow and
be republished; do not invent new approval records during deployment.

## Verification before sharing

- Home loads, emergency actions remain visible, and all navigation works.
- Run a simulated Guardian alert; confirm its simulation label.
- Explicitly test one live NWS lookup; outages stay unavailable.
- Start a fictional recovery case, approve a plan, update a task, resume by ID.
- Run Recovery Progress: verify actual local MCP tools, not just a rendered page.
- Try optional AI with the server key; missing/failed credentials remain explicit.
- Exercise photograph validation and export with synthetic test files.
- Check desktop/mobile rendering and persistent Streamlit browser connection.
- Verify HTTPS, access settings and recorded limitations before sharing the URL.

Local verification is not Replit verification. Record restart/redeployment results
on the actual platform; do not claim durable persistence from a local test.

## Local check of the same launcher

From a configured local environment:

```sh
PORT=8512 READYRELIEF_BIND_ADDRESS=127.0.0.1 .venv/bin/python scripts/start_replit.py
```

This lets the main app run alongside the older Guardian preview at port 8501.
Stop with Ctrl+C. Replit uses `python3` from its project environment; no local Mac
`.venv` or absolute Mac paths are imported.

## References

- https://docs.replit.com/features/project-setup/configuration
- https://docs.replit.com/features/project-setup/ports
- https://docs.replit.com/learn/projects-and-artifacts/replit-deployments
- https://docs.replit.com/core-concepts/project-editor/app-setup/secrets
