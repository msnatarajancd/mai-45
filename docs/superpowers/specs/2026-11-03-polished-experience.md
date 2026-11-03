# Polished application and spoken walkthrough

User direction: modern iPhone/iPad-inspired visual quality, compact spacing, intuitive navigation, icon appearance controls, and spoken walkthroughs that highlight the controls being discussed.

Retain the existing Streamlit workflows, reviewed evidence boundaries, emergency access and approval semantics. Use a coherent slate/teal palette with semantic bright/dark colors, softer surfaces, compact navigation groups, icon toolbar controls, native mobile navigation and a responsive home journey card. Remove the oversized SVG illustration with overflowing labels from the home view. Use real workflow descriptions rather than invented preparedness scores.

Walkthrough is opt-in and nonblocking: a floating guide, six actual control targets, browser speech synthesis after a Listen gesture, Stop, Show me where, Previous/Next/End, written fallback, reduced-motion scrolling, target clearance above the guide, and explicit cleanup on updates/unmount/emergency. Optional AI explanation remains distinct from browser narration. No forms are automatically submitted and no task state is written by the guide.

Verification: existing application tests, theme/navigation and tour state tests; JavaScript lifecycle regression; desktop/mobile screenshot inspection; browser-instrumented narration, cleanup and target-overlap checks; native browser voice availability and fallback checks. No real emergency calls or live provider calls are needed for this presentation change.
