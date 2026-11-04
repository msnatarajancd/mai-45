# UI regression checks

Run `npm ci`, `npx playwright install chromium`, then `npm run test:visual`.
Set READYRELIEF_PYTHON to the Python executable in your virtual environment if needed.
Playwright starts Streamlit when port 8501 is unused; locally it can reuse the running app.
Restart that server after editing imported Python modules.

The committed Windows/Chromium baselines cover bright/dark Home, live search suggestions,
collapsed desktop/tablet navigation, and Protect walkthrough at desktop, tablet and mobile sizes. CI runs on Windows with the
pinned Playwright browser to match the baseline platform. No API keys or live AI are needed.
Tests exercise all six tour targets, Locate control, guide cleanup, retained sidebar collapse,
browser-local sidebar hide/show with content expansion, resizing, readable label sizes, search selection and persistent navigation.

Review intentional changes with `npm run test:visual:update`, inspect every changed PNG,
and commit reviewed baselines. Never update snapshots automatically in CI. Failures upload
expected/actual/difference images and browser traces. Other platforms create their own
platform-specific snapshots; use Windows for comparison against this reviewed baseline.

The native Streamlit UI still requires a server round trip for page changes. Navigation,
theme and tour callbacks update state before rendering, avoiding redundant explicit reruns.
Local warm navigation measured approximately 330–430ms both before and after this change;
this is not a claim of zero-latency routing. Search suggestions and tour location feedback
run in the browser. Grounding checks and recovery approval semantics remain unchanged.


The expanded audit covers all seven screens in both themes at three sizes (42 combinations),
button-label clipping, horizontal overflow, footer reachability, sidebar caption/hover overlap,
chat open/expand/minimize/close, and actual sidebar animation with reduced-motion checks.
Icon-only controls retain accessible names and are excluded from visible-label clipping checks.
The desktop/tablet sidebar uses one toolbar button and a 240ms horizontal transition; reduced
motion disables the transition. No live weather, model generation or recovery writes are used
by these presentation tests. These checks do not certify every possible populated task or chat state.


Header checks verify logo/search visibility after scrolling and sidebar collapse. Tour checks
cover a centered welcome card, a larger step panel, header clearance, and browser voice selection.
David/Mark (male) and Zira (female) were detected on the development Windows machine. Available
voices vary by browser/device; the app lists actual English voices and remembers the user's choice
within the tab. On-device voices are preferred by default, then natural/neural voices. Narration
starts automatically when guided steps begin. Mute persists across steps; a new tour starts with
narration enabled. If autoplay fails, the UI provides an unmute/retry action. Voices are labelled
On-device or Online using the browser's `localService` property. Online voices may send the fixed
tour narration text to the voice provider; no microphone or household data is used. No separate
speech API is configured. Voice orchestration tests use labelled
browser API test doubles, which do not certify perceived voice quality.

The header brand is a keyboard-accessible Home action that preserves the session and clears
navigation search. The branded loading indicator follows Streamlit's actual `running` state,
uses a short reveal delay to avoid flashing on very quick work, and never intercepts clicks.
For a real slow-request check, start `python -m streamlit run tests/fixtures/loading_app.py --server.port=8502`
in another terminal, then run `node tests/loading_browser.cjs`.
The fixture deliberately waits two seconds and makes no external requests.

“Start guided demo” loads the fictional Rivera household and opens a visible welcome panel,
then a three-step Protect → Respond → Recover guide. It shares the narrator and control
highlighting with the six-step product tour. Regression checks cover both demo entry points,
each step, finishing, restarting, and switching back to the product tour. Loading a demo
does not request live alerts, create recovery records, or clear an emergency state.
