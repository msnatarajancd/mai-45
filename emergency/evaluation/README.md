# CAP-04 proposed synthetic acceptance data

All fixtures are fictional. `expectation_status: PROPOSED` and `human_reviewed: false` are deliberate: these datasets have not received human safety approval and are not official guidance, service evidence, or verified operational contacts.

The 24 golden cases were hand-authored by an independent fixture agent from the CAP-04 request and implementation plan before inspecting the emergency rule/service implementation. The initial golden file was frozen before the first evaluation. The 48 development cases are separate wording and context checks. Golden expectations must be reviewed as requirements; do not rewrite them merely to match a classifier result. The development typo example was clarified to treat “I am traped” as a current entrapment report because its intended meaning is clear.

Run from the repository root:

```sh
python -m emergency.evaluation.run --dataset golden --output artifacts/cap04-evaluation.json
python -m emergency.evaluation.run --dataset development --output artifacts/cap04-development.json
```

The command writes every case's proposed expectation and actual decision, type/urgency/routing/safety accuracy, critical misses, forbidden claim matches, attempted provider/network calls, dataset version, and observed policy versions. A mandatory mismatch or failed I/O guard exits with status 1. Invalid dataset/schema input fails rather than substituting demo data.

Each record has a unique ID, explicit synthetic classification, a strict `SituationInput`, expected incident types/urgency/route/interruption/persistence, mandatory status, and forbidden external outcomes. Matching incident types is order-independent. Immediate expected cases count as critical misses when the decision does not preserve immediate urgency, emergency routing, interruption, and danger persistence. Safety accuracy measures interruption/persistence expectations and absence of forbidden claims or external calls. Type correctness and critical misses are separate metrics.

The evaluation calls `emergency.service.evaluate_situation(SituationInput(...))` directly. Runtime guards reject and count the application's `NebiusClient.complete` provider boundary and standard Python socket, HTTP-connect, and URL-open boundaries. Separate blocked probes verify the guards before evaluation; these self-test probes are excluded from policy call counts. No credentials are needed. This is a bounded regression guard for the application, not an operating-system sandbox or proof about arbitrary native libraries. Forbidden-claim checks are bounded phrase patterns, not general semantic entailment.

The synthetic demo loader lives in `emergency/demo.py`. Its UI-facing payload contains only an ID, a visible simulated label, and input; it never imports these expectations. Live mode is rejected before fixture files are read. Profiles cannot establish current incident location or household presence. The nine failure-state records describe test setup and acceptance behavior; loading one does not inject a live outage. Integration and UI tests must implement the applicable fault at its real boundary.

Passing this small proposed synthetic suite demonstrates the tested prototype behavior only. It does not establish clinical, rescue, or real-world classification reliability, official approval, connectivity, delivery, dispatch, enrollment, availability, transport booking, or rescue.
