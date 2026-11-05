"""Shared navigation and product-guide knowledge; no emergency advice corpus."""
import re
PAGES = {
    'Home': ('home', 'start overview welcome'),
    'Protect': ('shield', 'prepare preparation weather alerts hurricane guardian forecast'),
    'Respond': ('emergency', 'help emergency transportation supplies assistance 911'),
    'Recover': ('checklist', 'recovery plan tasks progress damage resume reassessment'),
    'Household': ('group', 'family profile people mobility pets vehicle preferences area location'),
    'Evidence': ('fact_check', 'sources trust evidence limitations integrations transparency'),
    'Assistant': ('chat', 'ai assistant chat ask copilot commands how walkthrough tour'),
}
TOUR = [
    ('Home', 'Choose the help you need', 'The three cards open Protect, Respond and Recover. The emergency bar is available on every page. Never place a real emergency call during the demo.', 'Try “Prepare my household” or continue the tour.'),
    ('Household', 'Make the journey yours', 'Enter fictional household preferences, including mobility support, vehicle access and pets. Save household preferences. These are optional and session-only; they never gate emergency access.', 'Look for the household form and “Save household preferences”.'),
    ('Protect', 'Understand the alert mode', 'Choose SIMULATED DEMO and Show simulated alert for the contest story. LIVE CHECK requests county-wide official NWS alerts; failures are labeled unavailable and no alerts is not proof of safety. Switching area or mode clears previous results.', 'Use “Alert mode” and “Check an area”; never present a fixture as current weather.'),
    ('Respond', 'Find the right connection', 'Call 911 and I Can’t Call 911 come first. Optional descriptions use local rules without AI. Choose the current incident area before county links; directory reviews are pending and no pickup is guaranteed. In demo mode, try future transport or rising water. Danger pauses routine work; returning does not clear a saved danger report.', 'Use “Try a fictional scenario” for future transport or rising water. Never activate a real call during a demonstration.'),
    ('Recover', 'Review, accept, then track', 'For a fictional post-storm situation, explicitly assess danger, fill the intake, and Create draft plan. Read every task, check the review box, and approve. Change a task status and Save progress. Recovery cases and saved progress persist in local SQLite even in SIMULATED DEMO. Keep the case ID to resume after reload on the same machine. Household preferences and chat are session-only. Use Circumstances changed to preview a revision without losing completed work.', 'Your changes are saved locally only after the relevant save or approval control.'),
    ('Assistant', 'Use your words', 'Ask this assistant to explain a feature, change household preferences, check alerts, show your plan, or prepare a task update. Review its proposed action before confirming. For disaster guidance, expand the chat and use Ask Qwen about reviewed guidance, selecting a hazard and phase. That panel retrieves reviewed passages before generation. The Evidence page explains integration limits.', 'Try “Show my plan” or “Mark my housing task completed”.'),
]
GUIDE = '\n'.join(f'{page}: {title}. {text} {hint}' for page,title,text,hint in TOUR) + '\nEvidence: M2 live county alerts and M3 reviewed CDC recovery retrieval are connected. M1 provides constrained Qwen explanations with citations. CAP-04 local routing and shared interruptions are implemented without AI. Directory publication checks are implemented, but all eight prepared listings await review. Synthetic expectations are proposed, not human-approved safety evidence. M5 recovery is connected. Online only: no offline guarantee, dispatch, transport booking, live shelter capacity, safety certification or benefit eligibility decisions.'


# Shared with the browser suggestions: the route vocabulary and normalization rules
# originate here so chat and the top search cannot maintain different alias lists.
ROUTE_NORMALIZERS = [
    [r'[.!?]+$', ''],
    [r'^(?:(?:can|could|would) you (?:please )?|please )', ''],
    [r'^(?:open|go to|take me to|navigate to|switch to)\s+(?:the\s+)?', ''],
    [r'\s+(?:page|screen|section|workspace)(?:\s+please)?$', ''],
    [r'\s+please$', ''],
]


def navigation_query(query):
    query = query.casefold().strip()
    for pattern, replacement in ROUTE_NORMALIZERS:
        query = re.sub(pattern, replacement, query).strip()
    return query


def search_pages(query):
    tokens = navigation_query(query).split()
    if not tokens:
        return []
    return [page for page, (_, words) in PAGES.items() if all(t in (page+' '+words).casefold() for t in tokens)]


def chat_routes(query):
    normalized = navigation_query(query)
    if re.match(r'^(how|what|why|where|when|which|who|can|could|would|should|do|does|did|is|are|explain|help)\b', normalized):
        return []
    return search_pages(query)
