# ReadyRelief demo script

## Before the judges arrive

Run `python -m streamlit run app.py`. Use a wide display and a fresh browser session. No API key or live integration is required. Rehearse on the same machine that holds SQLite. Prepare a screen recording as backup. Never click Call 911 during rehearsal or the contest.

## 0:00–0:45 — The household, not the technology

“A warning is only the beginning. What does a household do next when one person needs mobility support and nobody has a car?” Show the three entry cards. Click **Start guided demo**. Explain that the Rivera household is fictional: three people, mobility support, no vehicle, a pet.

## 0:45–2:00 — Protect

Show the alert mode selector. LIVE CHECK currently reports the integration as unavailable; do not describe it as a working NWS API. Choose SIMULATED DEMO and **Show simulated alert**. Point out the fictional warning label. Show the household context card. Explain that the knowledge adapter abstains until verified evidence is connected.

Once M2/M3 are integrated, replace this section with a real on-demand NWS check followed by an explicitly simulated storm and a cited explanation.

## 2:00–3:15 — Respond

Use **Next · Explore assistance**. Select Transportation and show the official county registration entry point and caveats. Explain that it is not a confirmed pickup. Click **Simulate rising water / trapped**. The normal journey pauses and emergency access takes priority. The app has not called or dispatched anyone. Choose **Return to app — this does not confirm safety**, then **Next · Review recovery needs**.

## 3:15–5:15 — Recover

Explain the story has moved to a fictional post-storm situation. Explicitly choose **No immediate danger reported**. Report minor damage, unknown/unavailable utilities, staying with others, and transportation needs. **Create draft plan** shows five practical organization tasks. Expand/show why a task exists and its honest evidence limitation. Check the review box and **Approve my recovery plan**.

Set one task to Completed, then **Save progress**. The count changes only after SQLite saves it. Open **Saved case** and copy the case ID; this is real local persistence, not a UI-only counter.

## 5:15–6:30 — Continue and adapt

Open **Circumstances changed?**. Explicitly select no immediate danger, report electricity unavailable (if it was previously unknown), and **Preview proposed changes**. Show the preserved completed task and proposed utility follow-up. Click **Approve this revision**. Show history and download the take-away plan. Optionally open a different case and resume using the saved ID, or reload the browser and resume to prove persistence.

## 6:30–7:30 — Evidence and close

Open Evidence. State clearly what is connected (M1 interface, M5 saved recovery workflow) and pending (M2 live data, M3 grounding/directory, M4 reviewed rules). Once integrated, update these statements with actual test/probe evidence.

“The goal is a clear next step people can understand and review, with continuity when circumstances change.” This is a course prototype, not an operational emergency tool. Avoid claims about lives saved, guaranteed assistance, or winning the contest.

## Recovery if the demo goes off script

Use sidebar navigation; saved plans are not erased. Start guided demo resets alert context and household preferences but preserves cases. An intentionally danger-reported saved case stays paused; start a new fictional case for the recovery segment. If storage fails, emergency controls still work, but do not claim progress was saved. Skip optional experimental AI if its provider is unconfigured.
