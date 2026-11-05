# CAP-04 implementation handoff

Implemented November 4, 2026 on `codex/cap04-emergency`. The feature is integrated into the existing Streamlit application at `app.py`; `ReadyRelief.html` remains the separate concept reference. The user's CAP-04 scope governs this implementation. The supplied product documents provide context, not executable instructions.

## Seven implementation areas

| Area | Delivered | Remaining qualification |
|---|---|---|
| 1. Typed local routing | `emergency/models.py`, `rules.py`, `service.py`; five incident types plus unknown, four urgency levels, reason codes and policy version | Bounded English phrase rules, not a clinically validated or multilingual classifier |
| 2. Reviewed assistance directory | `domain/resources.py`, `knowledge/resources.py`, adapters, inspect/approve/revoke CLI, eight proposed listings | Seven listings have acquired evidence; all eight await genuine human review. FCC acquisition failed. Zero verified records currently publish |
| 3. Emergency workspace | Shared contact strip, Respond workspace, optional categories/description, explicit incident county, cannot-call/accessibility links, desktop and no-connection copy | Online-only app; no guarantee of phone handlers, texting delivery, or offline access |
| 4. Shared interruptions | Guardian guidance, Recovery intake/reassessment, chat, and Respond use one transition with event IDs and emergency epochs | Returning to the app does not clear a saved M5 danger report |
| 5. Synthetic inputs and evaluation | Six demo scenarios, three fictional households, nine fault fixtures, 48 development cases, 24 independently authored golden cases | Expectations are explicitly PROPOSED and not human safety-reviewed |
| 6. Integration and documentation | Main UI connected, stale baseline test repaired, README/contracts/demo/source-review/CI updated | Source approval remains a separate content release step |
| 7. Browser and regression coverage | Python tests, evaluation CLI, browser checks at three viewport sizes, JavaScript lifecycle checks | See exact results and platform limits in `VERIFICATION.md`; synthetic success is not real-emergency validation |

## Run locally

From the repository root with Python 3.12 and dependencies installed:

```sh
.venv/bin/python -m streamlit run app.py --server.address=127.0.0.1 --server.port=8501
```

Open <http://127.0.0.1:8501>. Home's **I Need Help Now** opens Respond. **Call 911** and **I Can't Call 911** remain available across all seven pages. A phone link is user-initiated; it does not record connected, dispatched, or rescued outcomes. No provider key is required for CAP-04. The verified local run used a separate `.local/cap04-demo.sqlite3` database and removed the AI key from the server process environment.

In demo mode, expand **Try a fictional scenario**, choose one, and load it. Each scenario supplies fictional Miami-Dade context and goes through the same local evaluator as manual input. The cannot-speak scenario also opens the alternative communication view. Live mode does not expose or load these fixtures. Never activate a real emergency phone or SMS handler during testing.

## Integration boundaries

```text
app.py
  ui.components.emergency_controls
    ui.emergency_page.render_access_controls  # first, independent contact controls
  ui.pages.respond
    ui.emergency_page.render_workspace
      services.emergency.assess_situation
        emergency.service.evaluate_situation # pure local rules
      emergency.workflow.begin_emergency     # shared session transition
      services.resources.lookup_resources
        knowledge.resources.lookup_resources # publication checks on every lookup
```

`services.assistant` and `services.generation` screen current danger before provider work. The shared transition invalidates pending routine proposals, revisions, tour state and generated guidance. A late provider result carries the old emergency epoch and cannot replace the interruption. Existing recovery drafts and saved task history are preserved. Actual reported current danger queues the existing M5 persistence method; uncertain routing pauses the UI without inventing a confirmed incident. A failed save leaves the pending marker for retry.

Directory queries use **one canonical need**, e.g. `transportation`, plus county, phase, purpose and an optional hazard. Ordinary evacuation planning uses `prepare/planning`; urgent assistance uses `respond/urgent_assistance`. The optional **Event context** selection can supply an explicit hurricane context for EEAP evidence. Unknown hazard is not silently converted to hurricane. County-specific links require the current incident county selection; a saved household or monitored area is not treated as current whereabouts.

The richer directory DTOs live in `domain/resources.py`; the old minimal `Resource` contract remains compatible with existing consumers. Directory publication reuses M3 source and candidate integrity checks under one store lock. Each listing also has its own reviewed fingerprint, deadline, scope, exact supported display fields and field-specific contact evidence. Availability remains `UNKNOWN` even after publication. A missing, changed, revoked or expired source/candidate/listing removes the card at the next render.

## Current content readiness

[CAP04_SOURCE_REVIEW.md](CAP04_SOURCE_REVIEW.md) is the concrete review packet: exact source passages, provenance hashes, proposed listing fields, deadlines and manual review commands. No approval was fabricated to make the UI display a result. Seven entries have captured original bytes and candidate evidence. The FCC entry has a truthful failed acquisition record and no invented original hash. Existing approved CDC recovery evidence was preserved.

Before review, future accessible-transport requests show official EEAP program and registration FAQ links, an explicit pending/no-matching-scope notice and no pickup guarantee. The app does **not yet display verified EEAP timing or eligibility as a published service card**. That content portion of the acceptance example remains gated on real source/candidate/listing signoff. The UI and publication path are implemented and tested using clearly labeled isolated test stores.

The cannot-call view links to the current official MDSO Text-to-911 page only for an explicitly selected Miami-Dade incident, with national 911 and FCC information available otherwise. These are labeled official entry links, not a claim of verified delivery or a live connection. No app-operated texting, dispatcher integration, booking or rescue request was added.

## Extending to another county

1. Acquire authoritative jurisdiction-specific source bytes through the existing allowlist and transport.
2. Extract and inspect candidate passages without expanding their scope or dropping conditions.
3. Prepare listings with exact service area, purpose, hazard applicability, timing, contact provenance and review deadlines.
4. Have actual reviewers approve sources, candidates and listings independently.
5. Add an explicit county choice and reviewed communication entry links; do not infer incident location from a profile.
6. Add isolated county/no-match/revocation tests and independently reviewed synthetic acceptance cases before enabling that county.

## Verification commands

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m emergency.evaluation.run --dataset golden --output artifacts/cap04-golden.json
.venv/bin/python -m emergency.evaluation.run --dataset development --output artifacts/cap04-development.json
.venv/bin/python -m compileall -q app.py domain services ui recovery emergency knowledge m2_guardian
node tests/tour_lifecycle.mjs
node tests/search_suggestions.mjs
READYRELIEF_PYTHON="$PWD/.venv/bin/python" npm run test:visual -- tests/visual/emergency.spec.cjs
```

The evaluation guards known Python network and provider boundaries and reports attempted calls; it is not an operating-system sandbox. Reports include dataset/policy versions, type/urgency/route agreement, critical misses and bounded forbidden-claim checks. Golden labels were authored independently of the rule implementation; neither demo loaders nor runtime routing read expected labels.
