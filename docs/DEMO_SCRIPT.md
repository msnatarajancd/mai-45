# ReadyRelief demo script

## Before presenting

Start the app with the [local setup commands](../README.md#run-locally). Use fictional data, a fresh browser session, and the same machine that holds SQLite. No API key is needed for the main demonstration. Keep a backup recording and prepare a separate fresh browser session for the recovery segment. Never click **Call 911** or trigger a real phone/message handler during rehearsal or presentation.

The main sequence is future assistance → simulated current danger → cannot-call information → a separate fictional recovery case. All eight directory listings currently await review, so show pending/no-match states and official entry links honestly. Do not substitute a synthetic verified service card.

## 0:00–0:45 — Introduce the household

“A warning is only the beginning. What does a household do next when someone needs mobility support and there is no vehicle?” Show the Home entry cards and choose **Start guided demo**. Explain that the household and simulated warning are fictional. Optional household preferences never gate emergency access.

## 0:45–1:45 — Protect

Choose **SIMULATED DEMO** and **Show simulated alert**. Point out the visible simulation label and county-level context. Live NWS checks are integrated and user initiated, but do not rely on a live request for the presentation. An unavailable response stays unavailable; no alerts does not prove safety.

Explain that approved CDC excerpts cover selected recovery topics. Protect cannot silently reuse recovery-only evidence, and a missing reviewed match produces abstention rather than generated advice.

## 1:45–3:00 — Plan assistance in Respond

Open Respond, headed **I Need Help Now**. Show **Call 911** first and **I Can't Call 911** second without activating a phone link. The form and current-area selector are optional.

In **Try a fictional scenario**, select **SIMULATED DEMO · Accessible transport next week** and choose **Load fictional scenario**. Explain that this fixture explicitly supplies fictional Miami-Dade incident context; an ordinary user's saved area is not silently treated as current location. The same local evaluator used for manual input routes this as ordinary planning.

Show the pending/no-reviewed-match notice and official EEAP information/registration links. If demonstrating the optional event context, choose **Hurricane** explicitly; the prepared EEAP evidence has that scope and cannot be matched by inventing a hazard. Listings remain unpublished until source, passage, and separate directory review are complete. Read current registration timing directly with the county; the app has not enrolled anyone or booked a pickup.

Optionally load **Accessible transport today** to contrast urgent assistance with future planning. Urgency does not establish service availability.

## 3:00–4:15 — Current danger and cannot-call access

Load **SIMULATED DEMO · Rising water and trapped parent**. The input is “My father is trapped and water is rising.” The local policy identifies flood and entrapment with immediate urgency and interrupts routine work without an AI turn. The simulated label must remain visible.

Point to the two contact actions. Explain that `tel:911` asks a supported device to open a dialer only after a user click. The visible number and desktop fallback remain available. The app has not connected a call, dispatched anyone, or confirmed a rescue.

Choose **I Can't Call 911**. Show optional communication needs and the incident-area-dependent official information links. Select **No usable connection** to show that the app cannot restore connectivity or guarantee delivery. County links do not verify local device coverage. With an unknown area, the app does not assume Miami-Dade texting support. The separate fictional **Cannot speak safely** scenario opens this pathway through its explicit communication context.

A new danger report pauses routine proposals and recovery work. Saving danger is best effort; storage failure cannot hide the contact actions. **Return to app — this does not confirm safety** only leaves the view. It does not clear a saved danger flag.

## 4:15–6:00 — Separate fictional recovery scene

Switch to the prepared fresh browser session and open Recover to create a new fictional case. Do not reuse a danger-reported case or describe the return button as safety clearance.

Explicitly choose **No immediate danger reported** for this different fictional situation. Enter minor damage, unknown/unavailable utilities, staying with others, and transport needs. Choose **Create draft plan**, inspect its tasks and evidence limitation, check the review box, and choose **Approve my recovery plan**.

Set one task to Completed and choose **Save progress**. The count changes after SQLite saves it. Open **Saved case** and retain the case ID to demonstrate real local persistence. These organization templates are not a source-grounded emergency response plan.

## 6:00–7:00 — Reassess and show boundaries

In **Circumstances changed?**, explicitly report no immediate danger for this fictional scene, change one circumstance, and choose **Preview proposed changes**. Show preserved completed work, review the proposal, then choose **Approve this revision**. Show history or download the plan.

Open Evidence. State what is connected: county alerts, reviewed CDC recovery excerpts, optional constrained generation, local CAP-04 routing/interruption, directory publication checks, and M5 persistence. State what remains pending: all eight directory approvals and broader reviewed coverage. Synthetic expectations are proposed checks, not human safety certification.

Close with the practical outcome: a clear next contact option and continuity for reviewed recovery work. This online-only course prototype does not provide automated dispatch, pickup guarantees, live capacity, or confirmed external outcomes.

## If a dependency fails

Use the top navigation; saved plans are not erased by navigation. Starting the guided demo changes fictional context but preserves recovery cases and danger state. Use a separate fictional case after a danger scene.

If AI is unavailable, keep the deterministic sequence and reviewed-excerpt fallback. If the directory or its review gate fails, show the unavailable/pending state and official entry links. If storage fails, do not claim a save; emergency access remains visible while the web app is available. Loss of the server/browser connection has no offline continuity guarantee.

## Optional assistant and grounded-generation segment

Search `tasks` in the top toolbar, then open **Ask ReadyRelief**. With configured AI, request a fictional household change and show its preview before **Confirm action**. A navigation request such as “open Recover” navigates directly; it does not create a data-changing approval card. Keep this segment optional.

In a separate recovery scene, expand **Ask Qwen about reviewed guidance**, select **flood**, and request **electrical hazards**. Choose **Generate cited explanation** only when the provider is configured. Show the real-model label, partial-evidence notice, exact approved CDC passage, and citation. It is not permission to reenter or operate equipment. An unsupported FEMA eligibility question must produce no generated answer.

Historical real-provider evidence is in `docs/evidence/m1-qwen-live-2026-11-03.json`; tests use labeled doubles. Explanations do not write task state. The coordinated [verification record](VERIFICATION.md) contains current checks; do not present a test count as a real-world reliability measure.
