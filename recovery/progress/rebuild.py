"""Fictional provider matching; no contact, acceptance or booking side effects."""
from datetime import datetime

from .insurance import assess_funding
from .models import ActionCandidate, ExecutionState, ProgressInput, ResultItem, SignalState, SourceMode, SpecialistResult

_TRANSITIONS = {
    None: ['shortlisted'],
    'shortlisted': ['enquiry_recorded'],
    'enquiry_recorded': ['awaiting_reply'],
    'awaiting_reply': ['quote_received', 'declined'],
    'quote_received': ['quote_accepted', 'declined'],
    'quote_accepted': ['work_committed'],
    'declined': [],
    'work_committed': [],
}


def allowed_provider_events(current_state: str | None) -> list[str]:
    """Return forward simulation transitions, never dispatch real work."""
    return list(_TRANSITIONS.get(current_state, []))


def check_rebuild(inputs: ProgressInput, *, now: datetime) -> SpecialistResult:
    clock = inputs.as_of if inputs.source_mode == SourceMode.SYNTHETIC else now
    if 'rebuild' in inputs.specialist_failures:
        return SpecialistResult(specialist='rebuild', state=SignalState.UNKNOWN, headline="Couldn't update providers",
                                summary='This synthetic checkpoint explicitly simulates an unavailable provider check.',
                                source_mode=inputs.source_mode, observed_at=clock, execution_state=ExecutionState.FAILED,
                                missing=['Current provider response'])
    funding = assess_funding(inputs, now=now)
    interactions = {i.provider_id: i for i in inputs.interactions}
    items, actions, missing = [], [], []
    for provider in inputs.providers:
        if provider.provenance.source_mode != inputs.source_mode or provider.trade not in inputs.needed_trades:
            continue
        if inputs.household.county and provider.county != inputs.household.county:
            continue
        if inputs.household.area and inputs.household.area not in provider.areas:
            continue
        if inputs.household.accessibility is True and provider.accessible_service is False:
            continue
        interaction = interactions.get(provider.id)
        fresh = provider.provenance.observed_at <= clock and provider.provenance.valid_until is not None and clock <= provider.provenance.valid_until
        reasons = ['Fictional service area and trade match; no message, acceptance or appointment has been sent']
        if interaction is not None and interaction.state == 'declined':
            state, summary = SignalState.NOT_APPLICABLE, 'Provider declined in the simulated record'
        elif not fresh:
            state, summary = SignalState.UNKNOWN, 'Provider observation is stale'
        elif interaction is not None:
            state = SignalState.GREEN if interaction.state == 'work_committed' else SignalState.YELLOW
            summary = {'shortlisted': 'Shortlisted only', 'enquiry_recorded': 'Enquiry recorded; no real message sent',
                       'awaiting_reply': 'Awaiting a simulated reply', 'quote_received': 'Quote received; not accepted or scheduled',
                       'quote_accepted': 'Quote accepted in the simulation; work not yet committed',
                       'work_committed': 'Work commitment recorded in the simulation; repairs not thereby completed'}[interaction.state]
        elif provider.availability == 'available':
            state, summary = SignalState.GREEN, 'Availability listed in the fictional catalog; no appointment confirmed'
        elif provider.availability in ('waiting', 'unavailable'):
            state, summary = SignalState.YELLOW, 'Provider waiting or unavailable in the fictional catalog'
        else:
            state, summary = SignalState.UNKNOWN, 'Provider availability is unknown'
        fields = {'Trade': provider.trade, 'Area': ', '.join(provider.areas),
                  'Rating': f'{provider.rating}/5 ({provider.review_count} fictional reviews)' if provider.rating is not None and provider.review_count is not None else 'Unrated',
                  'Availability': provider.availability, 'Interaction': interaction.state if interaction else 'none',
                  'Source': 'Synthetic provider; no real contact destination' if inputs.source_mode == SourceMode.SYNTHETIC else provider.provenance.source}
        if interaction and interaction.quote:
            quote = interaction.quote
            fields['Quote'] = f'{quote.currency} {quote.amount:.2f}; {quote.stage_id}; recorded {quote.observed_at.date()}'
            reasons.append('A quote does not imply acceptance, funding or scheduled work')
        if inputs.household.accessibility is True and provider.accessible_service is None:
            reasons.append('Accessibility support needs confirmation')
            if state == SignalState.GREEN:
                state = SignalState.UNKNOWN
        items.append(ResultItem(id=provider.id, title=provider.name, category=provider.trade, state=state,
                                summary=summary, fields=fields, reasons=reasons, provenance=[provider.provenance]))
        if state == SignalState.NOT_APPLICABLE or interaction and interaction.state == 'work_committed' or inputs.repairs_complete is True:
            continue
        action_title = ('Review the simulated quote' if interaction and interaction.state == 'quote_received' else
                        'Follow up on the simulated provider response' if interaction else 'Review a fictional repair provider')
        actions.append(ActionCandidate(key=f'rebuild:{provider.id}', title=action_title,
                       reason=f'{provider.trade}: {summary}. Availability and affordability require confirmation.',
                       tier=3, destination='Recovery Progress',
                       dependencies=[] if funding.state == SignalState.GREEN else ['Confirm next-stage scope and funding before any work commitment']))
    if inputs.repairs_complete is True:
        state, headline = SignalState.GREEN, 'Repairs reported complete'
    elif not inputs.needed_trades:
        state, headline = SignalState.UNKNOWN, 'Repair scope is unconfirmed'
        missing.append('Needed repair trades')
    elif not items or all(item.state in (SignalState.UNKNOWN, SignalState.NOT_APPLICABLE) for item in items):
        state, headline = SignalState.UNKNOWN, 'No current matching provider observations'
        missing.append('Current providers for the household repair scope')
    else:
        committed = {p.trade for p in inputs.providers if (interactions.get(p.id) is not None and interactions[p.id].state == 'work_committed'
                     and any(item.id == p.id and item.state == SignalState.GREEN for item in items))}
        state = SignalState.GREEN if set(inputs.needed_trades).issubset(committed) else SignalState.YELLOW
        headline = 'Work commitments recorded' if state == SignalState.GREEN else 'Repair arrangements are in progress'
    return SpecialistResult(specialist='rebuild', state=state, headline=headline,
                            summary='Provider availability, quotes, accepted quotes, commitments and completed repairs are separate stages.',
                            items=items, actions=actions, missing=missing, source_mode=inputs.source_mode, observed_at=clock,
                            execution_state=ExecutionState.NEEDS_INFORMATION if state == SignalState.UNKNOWN else ExecutionState.COMPLETE)
