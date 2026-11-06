"""Shared navigation and product-guide knowledge; no emergency advice corpus."""
import re
import os
from dataclasses import dataclass
PAGES = {
    'Home': ('home', 'start overview welcome'),
    'Protect': ('shield', 'prepare preparation weather alerts hurricane guardian forecast'),
    'Respond': ('emergency', 'help emergency transportation supplies assistance 911'),
    'Recover': ('checklist', 'recovery plan tasks progress damage resume reassessment'),
    'Recovery Progress': ('monitoring', 'recovery progress dashboard preview specialists milestones'),
    'Household': ('group', 'family profile people mobility pets vehicle preferences area location'),
    'Evidence': ('fact_check', 'sources trust evidence limitations integrations transparency'),
    'Assistant': ('chat', 'ai assistant chat ask copilot commands how walkthrough tour'),
}


@dataclass(frozen=True)
class NavigationItem:
    label: str
    page: str
    icon: str
    group: str | None = None
    focus: str | None = None


def progress_preview_enabled():
    return os.getenv('READYRELIEF_PROGRESS_PREVIEW', '1').strip().casefold() not in {'0', 'false', 'off', 'no', 'disabled'}


def resolve_page(page):
    return 'Recover' if page == 'Recovery Progress' and not progress_preview_enabled() else page


def navigation_items(*, progress_enabled):
    items = []
    for page, (symbol, _) in PAGES.items():
        if page == 'Recovery Progress':
            continue
        items.append(NavigationItem(page, page, symbol))
        if page == 'Recover':
            if progress_enabled:
                items.append(NavigationItem('Recovery Progress · Preview', 'Recovery Progress', 'monitoring', group='Recover'))
            items.extend((
                NavigationItem('My Recovery Plan', 'Recover', 'checklist', group='Recover', focus='Continue my recovery'),
                NavigationItem('Insurance & Documents', 'Recover', 'folder', group='Recover', focus='Prepare for insurance')))
    return tuple(items)


# Exact legacy aliases win before substring matching. Sentinels carry that same
# rule through the existing browser component's regex/keyword interface.
ROUTE_ALIASES = {page.casefold(): page for page in PAGES} | {
    'recovery': 'Recover', 'tasks': 'Recover', 'my recovery plan': 'My Recovery Plan',
    'insurance & documents': 'Insurance & Documents', 'dashboard': 'Recovery Progress'}


def _destination_name(item):
    return item.label if item.focus else item.page


def navigation_target(destination):
    """Resolve a menu/search destination while retaining its existing focus."""
    normalized = navigation_query(destination)
    name = ROUTE_ALIASES.get(normalized, destination)
    return next((item for item in navigation_items(progress_enabled=progress_preview_enabled())
                 if name.casefold() in {item.label.casefold(), item.page.casefold()}), None)


def navigation_search_data(*, progress_enabled=None):
    if progress_enabled is None:
        progress_enabled = progress_preview_enabled()
    active = navigation_items(progress_enabled=progress_enabled)
    names = [_destination_name(item) for item in navigation_items(progress_enabled=True)]
    route_token = lambda name: '__rr_route_' + str(names.index(name)) + '__'
    return {
        'pages': [{'page': _destination_name(item), 'keywords':
                   (item.label if item.focus else PAGES[item.page][1]) + ' ' + route_token(_destination_name(item))}
                  for item in active],
        'normalizers': ROUTE_NORMALIZERS + [[r'^' + re.escape(alias) + r'$', route_token(page)] for alias, page in ROUTE_ALIASES.items()]}
TOUR = [
    ('Home', 'Choose the help you need', 'The three cards open Protect, Respond and Recover. The emergency bar is available on every page. Never place a real emergency call during the demo.', 'Try “Prepare my household” or continue the tour.'),
    ('Household', 'Make the journey yours', 'Enter fictional household preferences, including mobility support, vehicle access and pets. Save household preferences. These are optional and session-only; they never gate emergency access.', 'Look for the household form and “Save household preferences”.'),
    ('Protect', 'Understand the alert mode', 'Choose SIMULATED DEMO and Show simulated alert for the contest story. LIVE CHECK requests county-wide official NWS alerts; failures are labeled unavailable and no alerts is not proof of safety. Switching area or mode clears previous results.', 'Use “Alert mode” and “Check an area”; never present a fixture as current weather.'),
    ('Respond', 'Find the right connection', 'Call 911 and I Can’t Call 911 come first. Optional descriptions use local rules without AI. Choose the current incident area before county links; directory reviews are pending and no pickup is guaranteed. In demo mode, try future transport or rising water. Danger pauses routine work; returning does not clear a saved danger report.', 'Use “Try a fictional scenario” for future transport or rising water. Never activate a real call during a demonstration.'),
    ('Recover', 'Review, accept, then track', 'For a fictional post-storm situation, describe your circumstances and choose Continue to Review. Confirm the supported details and explicitly assess danger; structured intake remains an optional fallback. Read every task, check the review box, and approve. Change a task status and Save progress. Recovery cases and saved progress persist in local SQLite even in SIMULATED DEMO. Keep the case ID to resume after reload on the same machine. Household preferences and chat are session-only. Use Circumstances changed to preview a revision without losing completed work.', 'Your changes are saved locally only after the relevant save or approval control.'),
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
    """Backward-compatible canonical screens; focused UI callers use destinations."""
    return list(dict.fromkeys(item.page for item in search_destinations(query)))


def search_destinations(query):
    data = navigation_search_data()
    normalized = navigation_query(query)
    if normalized in ROUTE_ALIASES:
        destination = ROUTE_ALIASES[normalized]
        target = navigation_target(destination)
        return (target,) if target is not None else ()
    tokens = normalized.split()
    if not tokens:
        return ()
    return tuple(navigation_target(item['page']) for item in data['pages']
                 if all(t in (item['page']+' '+item['keywords']).casefold() for t in tokens))


def chat_routes(query):
    normalized = navigation_query(query)
    if re.match(r'^(how|what|why|where|when|which|who|can|could|would|should|do|does|did|is|are|explain|help)\b', normalized):
        return []
    return [_destination_name(item) for item in search_destinations(query)]
