# Search, walkthrough and conversational operations

## Find a screen

Use **Search menu** in the top toolbar. It matches names and keywords: tasks → Recover, weather → Protect, mobility → Household, chat → Assistant. Search never hides the emergency controls above the current screen. Clear the input to restore all seven entries.

## Learn the app

Choose **Show me around** in the sidebar. The guide visits Home, Household, Protect, Respond, Recover and Assistant. Each step explains the actual controls and why they exist. Use Previous step, Next step or End tour. If you navigate elsewhere, Take me to this step restores the relevant page. You can restart the tour at any time.

**Explain this step with AI** sends a product-help request and fictional session context to Nebius. It does not send recovery records, change settings, advance the tour, or approve anything. The basic walkthrough is local and works without an API key.

## Ask ReadyRelief

Choose **Assistant** or the **Ask ReadyRelief** button on any ordinary screen. Modes:

- **Nebius AI:** natural-language explanations and structured action proposals. Requires the server's NEBIUS_API_KEY. Uses NEBIUS_CHAT_MODEL, then NEBIUS_MODEL, otherwise Qwen/Qwen3-235B-A22B-Instruct-2507 (the school-planning reference app's model).
- **Local guide · no AI:** explicit commands such as `start tour`, `start demo`, `check alerts`, `show my plan` and `open Recover`. This is labeled deterministic fallback, not simulated AI.

Example prompts:

- “How do I save my progress?” → product explanation, no action.
- “Change my fictional household to four people and no vehicle.” → reviewable preference update.
- “Switch to Homestead and keep simulated mode.” → area/mode proposal; old alert results clear.
- “Check alerts.” → uses the existing adapter; never invents live weather.
- “Show my plan.” → displays actual saved tasks in chat.
- “Mark my housing task completed.” → proposes an update to the matched active task; asks for clarification when ambiguous.
- “Resume case <fictional UUID>.” → opens an existing local case.
- “Create a flood recovery draft: minor damage, water unknown, electricity unavailable, staying with others, transportation and temporary housing needed.” → reviewable intake; a human no-immediate-danger checkbox is required before creating a fictional case.
- “Approve this draft.” → displays every draft task and requires a separate review checkbox plus confirmation.
- “Electricity is now unavailable; reassess my plan and keep the other needs.” → prepares a revision for review in Recover; it does not approve the revision.

Every proposed operation has a separate Confirm action / Cancel action card. Actual execution results are labeled **Application result · not AI**. Starting another message discards an older pending proposal. Clearing conversation removes chat and pending proposals, not recovery records.

## Boundaries

One validated action per turn; no model-generated code, SQL, HTTP endpoints, shell commands or unrestricted tools. A saved task update is bound to the exact plan ID/progress version in the reviewed proposal. Changes to household/area/case/plan invalidate stale proposals; the SQLite layer atomically rejects intervening task writes and inactive plans. Replays are rejected.

The assistant is for product help and bounded operations, not emergency or medical advice. Conservative danger phrases bypass Nebius and open existing emergency controls. This is a fallback pattern check, not M4's completed safety classifier. Routine recovery writes remain blocked for pending or saved danger reports. Product questions about the immediate-danger button do not themselves create danger reports.

Messages, recent conversation (last six entries) and the current fictional household/recovery context are sent to Nebius only when submitting an AI request. The app retains at most 30 chat entries in the browser session. No private cross-device history or login is provided. Credentials stay in server environment variables; no keys are copied from other repositories or committed. This reuses M5's bounded transport and adds validated structured-action parsing inspired by the school-planning app, without introducing its full agent framework.

Provider timeouts, unavailable credentials and malformed outputs leave application state unchanged. No unapproved operation is automatically substituted. M2 live alerts, M3 source grounding/directory, and M4 reviewed rules remain pending exactly as before.

## Verification

Unit tests cover schema rejection, how-to vs operation requests, danger bypass, confirmation requirements, replay rejection, stale context, real task writes, explicit intake approval and a concurrent write occurring between snapshot comparison and execution. AppTest covers menu search/empty results, tour transitions, local navigation proposals and AI-profile confirmation. Live fictional Nebius checks verified product explanation, household changes and context changes without executing returned proposals. See VERIFICATION.md for the combined suite and browser evidence.

## Chat and appearance

Open **Ask ReadyRelief** at the bottom right of any regular screen. **Expand chat** opens the full assistant screen; **Minimize chat** returns to the previous screen. Closing and reopening the bubble preserves the conversation, assistant mode and pending confirmation for the browser session. Use **Bright / Dark** in the top toolbar to change appearance. The responsive layout uses the available screen width.
