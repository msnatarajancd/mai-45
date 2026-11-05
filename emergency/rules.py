"""Bounded English phrase rules with local clause qualification.

These navigation heuristics are versioned prototype policy, not a diagnosis or
proof of safety. New wording needs independent evaluation before coverage claims.
"""
from dataclasses import dataclass
import re

from domain.contracts import IncidentType as T

POLICY_VERSION = 'cap04-rules-1.1'


@dataclass(frozen=True)
class Rule:
    code: str
    pattern: str
    types: tuple[T, ...]
    immediate: bool = True


RULES = (
    Rule('current_entrapment', r'\b(?:trapp?ed|traps? (?:us|me|them)|stuck (?:inside|in|on|under)|(?:cannot|can\x27t|unable to) (?:get out|escape|leave (?:the |our |my )?(?:house|home|building|car))|no way out)\b', (T.TRAPPED,)),
    Rule('rising_or_entering_water', r'\b(?:(?:flood)?water(?: level)? (?:is |keeps |has been )?(?:not )?(?:rapidly |quickly |still )?(?:rising|ris+ing|coming (?:in|through)|entering)|rising (?:flood)?water|flooding (?:our|my|the) (?:house|home|car))\b', (T.FLOOD,)),
    Rule('breathing_emergency', r'\b(?:(?:not|barely) breathing|(?:cannot|can\x27t|unable to) breathe|(?:stops?|stopped|stop+ed) breathing|struggling to breathe|choking)\b', (T.MEDICAL,)),
    Rule('unresponsive_person', r'\b(?:unconscious|unresponsive|(?:won\x27t|will not) wake up|(?:cannot|can\x27t) wake (?:him|her|them|up))\b', (T.MEDICAL,)),
    Rule('severe_medical_concern', r'\b(?:chest pain|heart attack|stroke|(?:severe|heavy|uncontrolled) bleeding|bleeding (?:heavily|badly)|(?:need|needs|call|send|require) (?:an? )?ambulance)\b', (T.MEDICAL,)),
    Rule('drowning_person', r'\b(?:drowning|being swept away|swept away by (?:the )?water)\b', (T.MEDICAL, T.FLOOD)),
    Rule('gas_hazard', r'\b(?:smell(?:ing|s)? (?:of )?(?:natural )?gas|gas (?:smell|leak|odor|odour)|(?:natural )?gas (?:is )?leaking)\b', (T.UTILITY_HAZARD,)),
    Rule('active_fire', r'\b(?:on fire|(?:there is|there\x27s) (?:a )?fire|(?:house|home|building|room) (?:is )?burning|smoke (?:is )?(?:filling|coming into))\b', (T.UNKNOWN,)),
    Rule('electrical_hazard', r'\b(?:(?:downed|fallen|live) (?:power |electric(?:al)? )?(?:lines?|wires?)|(?:power |electric(?:al)? )(?:lines?|wires?) (?:is |are |has |have )?(?:down|fallen|sparking)|sparks (?:from|at) (?:the )?(?:outlet|panel))\b', (T.UTILITY_HAZARD,)),
    Rule('explicit_current_danger', r'\b(?:immediate danger|life[- ]threatening|life is in danger|(?:i am|i\x27m|we are|we\x27re) (?:not )?in (?:immediate )?danger)\b', (T.UNKNOWN,)),
    Rule('flood_context', r'\b(?:flood(?:ing|water|s)?|water near|water is near)\b', (T.FLOOD,), False),
    Rule('utility_context', r'\b(?:electrical panel|electrical outlet|electricity|power lines?|gas)\b', (T.UTILITY_HAZARD,), False),
    Rule('medical_context', r'\b(?:medical|ambulance|injur(?:y|ed))\b', (T.MEDICAL,), False),
    Rule('uncertain_breathing', r'\b(?:not sure|don\x27t know|do not know|uncertain) (?:if|whether) (?:\w+ ){0,6}breathing\b', (T.MEDICAL,), False),
    Rule('evacuation_assistance', r'\b(?:evacuat(?:e|ion)|transport(?:ation)?|wheelchair[- ]accessible|accessible (?:ride|vehicle)|need (?:a )?ride|eeap)\b', (T.EVACUATION_SUPPORT,), False),
)

FUTURE = re.compile(r'\b(?:tomorrow|next (?:week|month|year|season)|in (?:a|two|three|\d+) (?:days?|weeks?|months?)|future|planning|plan (?:for|in case)|prepare|preparedness|may need|could need|in case|hypothetical|what if|if (?:i|we|he|she|they|someone|anyone|my|our|a|the|floodwater)|would|should i (?:pack|buy|prepare))\b')
HISTORY = re.compile(r'\b(?:yesterday|last (?:week|month|year|night)|earlier|previously|used to|no longer|(?:was|were|had been)\s+(?:\w+\s+){0,2}(?:trapped|stuck|unconscious|rising|on fire|flooded))\b')
PLANNING = re.compile(r'\b(?:how (?:can|do|should|to)|what (?:should|can)|learn|information|guidance|prepare|planning|plan for|after (?:a |the )?flood|recovery)\b')
NOW = re.compile(r'\b(?:right now|now|currently|at this moment|still)\b')
UNCERTAINTY = re.compile(r'\b(?:not sure|unsure|don\x27t know|do not know|is it (?:safe|dangerous)|might be|may be|possibly|maybe)\b')
NEGATION = re.compile(r'\b(?:not|no|never|without|isn\x27t|aren\x27t|wasn\x27t|weren\x27t|don\x27t|doesn\x27t)\b')


def normalize(text: str) -> str:
    # Whitespace inside a report line is immaterial; line boundaries separate
    # assertions and must survive normalization before clause qualification.
    text = text.casefold().replace('’', "'").replace('‘', "'")
    return '\n'.join(' '.join(line.split()) for line in text.splitlines()).strip()


def clauses(text: str):
    # Separate assertions. A conditional's joined predicates share its scope;
    # contrast or sentence boundaries end that scope. Explicit 'now' overrides
    # inherited context but not an explicit 'what if ... now' in its own clause.
    conditional = False
    separator = ''
    for part in re.split(r'([:;.!?\n]+|\b(?:but|however|yet|and)\b|,)', text):
        part = part.strip()
        if not part:
            continue
        if re.fullmatch(r'[:;.!?\n,]+|but|however|yet|and', part):
            separator = part
            if part != 'and':
                conditional = False
            continue
        inherited = conditional and separator == 'and' and not NOW.search(part)
        yield part, inherited
        conditional = inherited or bool(re.search(r'\b(?:if|in case|hypothetical|would)\b', part))
        separator = ''


def qualification(clause: str, start: int, end: int) -> str | None:
    prefix = clause[:start]
    suffix = clause[end:]
    # 'not sure if' reports uncertainty, not absence or a hypothetical event.
    context = re.sub(r'(?:not sure|don\x27t know|do not know|uncertain) (?:if|whether)', 'uncertain whether', clause)
    if UNCERTAINTY.search(clause) and not FUTURE.search(context) and not HISTORY.search(context):
        return 'uncertain'
    # 'not breathing' and 'cannot breathe' are threat phrases themselves, not
    # negations of a threat. Only the local words before the phrase qualify it.
    local_prefix = ' '.join(prefix.split()[-5:])
    phrase = clause[start:end]
    internal_negation = re.search(r'\bnot\b', phrase) and not phrase.startswith(('not breathing', 'will not wake'))
    if internal_negation or NEGATION.search(local_prefix) or re.match(r'\s+(?:is |are )?not\b', suffix):
        return 'negated'
    # A present-time assertion after older context wins within the same clause.
    present = NOW.search(prefix)
    contextual_prefix = prefix[present.end():] if present else clause
    if FUTURE.search(contextual_prefix):
        return 'future_or_hypothetical'
    if HISTORY.search(contextual_prefix):
        return 'historical'
    return None


def matches(text: str):
    for clause, inherited_conditional in clauses(normalize(text)):
        for rule in RULES:
            for match in re.finditer(rule.pattern, clause):
                qualifier = qualification(clause, match.start(), match.end())
                if qualifier is None and inherited_conditional:
                    qualifier = 'future_or_hypothetical'
                yield rule, clause, qualifier
