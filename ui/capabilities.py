"""Shared navigation and product-guide knowledge; no emergency advice corpus."""
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
    ('Protect', 'Understand the alert mode', 'Choose SIMULATED DEMO and Show simulated alert for the contest story. LIVE CHECK currently reports unavailable until M2 connects NWS. Switching area or mode clears previous results.', 'Use “Alert mode” and “Check an area”; never present a fixture as current weather.'),
    ('Respond', 'Find the right connection', 'Choose an assistance category and review official county entry links. These do not guarantee a pickup or shelter availability. Immediate danger pauses the routine journey.', 'Look for “Show assistance options” and the persistent emergency bar.'),
    ('Recover', 'Review, accept, then track', 'For a fictional post-storm situation, explicitly assess danger, fill the intake, and Create draft plan. Read every task, check the review box, and approve. Change a task status and Save progress. Recovery cases and saved progress persist in local SQLite even in SIMULATED DEMO. Keep the case ID to resume after reload on the same machine. Household preferences and chat are session-only. Use Circumstances changed to preview a revision without losing completed work.', 'Your changes are saved locally only after the relevant save or approval control.'),
    ('Assistant', 'Use your words', 'Ask this assistant to explain a feature, change household preferences, check alerts, show your plan, or prepare a task update. Review its proposed action before confirming. The Evidence page explains pending integrations.', 'Try “Show my plan” or “Mark my housing task completed”.'),
]
GUIDE = '\n'.join(f'{page}: {title}. {text} {hint}' for page,title,text,hint in TOUR) + '\nEvidence: M2 alerts, M3 retrieval/directory and M4 reviewed rules remain pending. M5 recovery is connected. No dispatch, real-time shelter inventory, safety assessment or benefit eligibility decisions.'


def search_pages(query):
    tokens = query.casefold().split()
    return [page for page, (_, words) in PAGES.items() if all(t in (page+' '+words).casefold() for t in tokens)]
