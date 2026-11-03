# Searchable navigation and ReadyRelief assistant

Requested extension to M1: searchable left navigation, a contextual WalkMe-style product tour, and conversational operations using Nebius like the school-planning application.

Approach: retain Streamlit and reuse M5's bounded Nebius transport. A local capability guide anchors explanations. A discriminated Pydantic action schema permits only known app operations; no model-generated code, URLs, SQL or arbitrary tool execution. One action per turn keeps previews understandable. No multi-agent framework or external walkthrough SDK is needed.

Search matches screen names and synonyms, never hides global emergency controls, and has a clear empty state. A six-step tour has back/next/exit, points to actual controls and follows the relevant page. AI explanations are optional and never replace deterministic steps.

Chat uses fictional page/household/current-case context plus bounded conversation history. Text and context go to Nebius only on submit, with explicit disclosure. Missing credentials/provider failures leave state unchanged. A labeled local mode offers navigation/help when AI is unavailable; it is never described as AI.

Supported actions: navigate, start tour/demo, change area/mode, edit household, check alerts, show/resume recovery, create a draft, approve a reviewed draft, update a task, and preview a reassessment. Saved writes require user confirmation; draft/reassessment require a human no-immediate-danger confirmation. A reassessment revision is approved through the existing review screen, preserving the original M5 approval checks. Proposals bind the source case/plan/progress snapshot; case switches and concurrent updates invalidate them. Repeated clicks do not repeat a mutation. Danger indications bypass the provider and pause routine operations.

Implement with tests first: navigation synonyms/empty results; schema rejection; provider failures; prompt-injection cannot introduce tools; no implicit writes; stale context and progress rejection; danger bypass; tour transitions; AppTest search/chat confirmation; full existing suite and a small fictional live Nebius smoke test. Changes remain on the existing M1 branch.
