"""Pure routing policy; no I/O and no imports from UI, models, or persistence."""
import re

from pydantic import ValidationError

from domain.contracts import IncidentType as T, RouteResult, Urgency as U
from emergency.models import SituationInput
from emergency.rules import POLICY_VERSION, PLANNING, matches, normalize

IMMEDIATE_COPY = 'If you are in immediate danger, call 911. ReadyRelief has not contacted anyone. Use the emergency contact options now.'
UNCERTAIN_COPY = 'Your safety is not established. Call 911 for immediate danger, or use I Can\'t Call 911. You can add details, but they are optional.'
ASSISTANCE_COPY = 'Review official assistance options and their conditions. Current availability is not verified; no service has been booked.'
PLANNING_COPY = 'Review official planning information. This does not establish current safety, enrollment, or transport availability.'


def _result(types, urgency, reasons, *, persist=False, categories=()):
    types = list(dict.fromkeys(types)) or [T.UNKNOWN]
    if len(types) > 1 and T.UNKNOWN in types:
        types.remove(T.UNKNOWN)
    interrupted = urgency in (U.IMMEDIATE, U.UNCERTAIN)
    return RouteResult(route='emergency' if interrupted else 'resources', urgency=urgency,
        incident_types=types, interrupt_routine=interrupted, persist_danger=persist,
        reason_codes=list(dict.fromkeys(reasons)), policy_version=POLICY_VERSION,
        resource_categories=list(categories), guidance_topics=[t.value for t in types if t != T.UNKNOWN],
        message={U.IMMEDIATE: IMMEDIATE_COPY, U.UNCERTAIN: UNCERTAIN_COPY,
                 U.URGENT: ASSISTANCE_COPY, U.ORDINARY: PLANNING_COPY}[urgency])


def evaluate_situation(request: SituationInput) -> RouteResult:
    """Return a bounded navigation decision, never a finding that someone is safe."""
    if not isinstance(request, SituationInput):
        try:
            request = SituationInput.model_validate(request)
        except (ValidationError, TypeError, ValueError):
            return _result([], U.UNCERTAIN, ['malformed_input'])
    text = normalize(request.text)
    found = list(matches(text))
    types = [t for rule, _, _ in found for t in rule.types]
    if request.category:
        types.append(request.category)
    current = [(r, clause) for r, clause, qualifier in found if qualifier in (None, 'uncertain')]
    severe = [(r, clause) for r, clause, qualifier in found if r.immediate and qualifier is None]
    if request.immediate_danger:
        return _result(types, U.IMMEDIATE, ['explicit_danger_report'], persist=True)
    if severe:
        # Asking about the named app control alone is not an incident report.
        severe = [(r, c) for r, c in severe if not (r.code == 'explicit_current_danger' and re.search(r'\b(?:button|control|feature)\b', c))]
    if severe:
        active_types = [t for r, _, qualifier in found if qualifier != 'negated' for t in r.types]
        return _result(active_types, U.IMMEDIATE, [r.code for r, _ in severe], persist=True)
    if request.language.casefold().split('-')[0] != 'en' or (text and not re.search('[a-z]', text)):
        result = _result(types, U.UNCERTAIN, ['unsupported_language'])
        result.message += ' The local phrase rules support English only; this text was not translated.'
        return result
    reasons = [r.code + ':' + qualifier for r, _, qualifier in found if qualifier]
    if any(qualifier == 'uncertain' for _, _, qualifier in found):
        return _result(types, U.UNCERTAIN, reasons + ['uncertain_current_threat'])
    # Resolve current hazard clauses before routing assistance. Planning words
    # in another clause do not qualify a person's present unresolved concern.
    unresolved = [(r, clause) for r, clause in current
                  if r.code != 'evacuation_assistance' and not PLANNING.search(clause)]
    if unresolved:
        codes = {r.code for r, _ in unresolved}
        if {'utility_context', 'flood_context'} <= codes:
            return _result(types, U.UNCERTAIN, ['possible_water_electrical_hazard'])
        return _result(types, U.UNCERTAIN, ['unresolved_hazard_context'])
    transport = T.EVACUATION_SUPPORT in types
    if transport:
        urgent = any(r.code == 'evacuation_assistance' and re.search(r'\b(?:today|now|tonight|urgent|as soon as possible|asap)\b', clause) for r, clause in current)
        return _result(types, U.URGENT if urgent else U.ORDINARY,
                       reasons + ['urgent_evacuation_assistance' if urgent else 'evacuation_planning'],
                       categories=['transportation', 'evacuation_support'])
    if found:
        return _result(types, U.ORDINARY, reasons or ['general_planning_information'])
    if current or request.category not in (None, T.UNKNOWN):
        return _result(types, U.UNCERTAIN, ['unresolved_hazard_context'])
    return _result(types, U.UNCERTAIN, ['unclear_help_request'])


def screen_report(text: str, *, entrypoint: str) -> RouteResult | None:
    """None means no routing match, never a determination of personal safety."""
    try:
        request = SituationInput(text=text, entrypoint=entrypoint)
    except (ValidationError, TypeError, ValueError):
        return _result([], U.UNCERTAIN, ['malformed_input'])
    result = evaluate_situation(request)
    normalized = normalize(text)
    if result.persist_danger:
        return result
    if re.search(r'\b(?:immediate danger) (?:button|control|feature)\b', normalized) and not any(r.code != 'explicit_current_danger' for r, _, _ in matches(normalized)):
        return None
    if any(matches(normalized)):
        return result
    if entrypoint == 'respond' or re.search(r'^(?:help(?: me| us)?|i need help|something is wrong|not sure|i don\x27t know)[.!?]*$', normalized):
        return result
    if re.search(r'\b(?:danger|is (?:my|our|the) (?:home|house) safe|cannot call 911|can\x27t call 911)\b', normalized):
        return result
    return None
