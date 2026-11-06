"""Preparation and next-stage funding are independent, explainable checks."""
from datetime import datetime
from decimal import Decimal

from .models import (ActionCandidate, ExecutionState, Model, MoneyFact, ProgressInput,
                     ResultItem, SignalState, SourceMode, SpecialistResult)


class FundingAssessment(Model):
    state: SignalState
    available_allocation: Decimal | None = None
    remaining_cost: Decimal | None = None
    exact_gap: Decimal | None = None
    reasons: list[str]


def _current(fact: MoneyFact | None, stage: str | None, clock: datetime) -> bool:
    return bool(fact is not None and stage is not None and fact.stage_id == stage and fact.currency == 'USD'
                and fact.observed_at <= clock and fact.valid_until is not None and clock <= fact.valid_until)


def assess_funding(inputs: ProgressInput, *, now: datetime) -> FundingAssessment:
    """Calculate only from current exact stage facts, never a contribution band.

    Stage cost/allocation are totals; recorded spend reduces both outstanding
    stage cost and the remaining allocation once. Payments do not implicitly
    increase an allocation, even when received.
    """
    clock = inputs.as_of if inputs.source_mode == SourceMode.SYNTHETIC else now
    funding = inputs.funding
    if inputs.source_mode != SourceMode.SYNTHETIC:
        return FundingAssessment(state=SignalState.UNKNOWN, reasons=['Saved-case stage costs and allocations are not collected in this release'])
    if not (_current(funding.estimated_cost, funding.stage_id, clock) and _current(funding.exact_allocation, funding.stage_id, clock)):
        return FundingAssessment(state=SignalState.UNKNOWN, reasons=['A current exact USD cost and explicit allocation for the same stage are needed',
                                 'Contribution bands, expected payments and approved payments do not establish cash available'])
    spent = Decimal(0)
    if funding.spent_from_allocation is not None:
        if not _current(funding.spent_from_allocation, funding.stage_id, clock):
            return FundingAssessment(state=SignalState.UNKNOWN, reasons=['Spent allocation is stale, in another currency or for a different stage'])
        spent = funding.spent_from_allocation.amount
    remaining = max(Decimal(0), funding.estimated_cost.amount - spent)
    available = max(Decimal(0), funding.exact_allocation.amount - spent)
    gap = max(Decimal(0), remaining - available)
    reasons = ['Uses only the explicit allocation remaining after recorded spend',
               'Expected, approved and received-but-unallocated payments are shown separately and never added to available funds']
    if spent > funding.exact_allocation.amount:
        reasons.append('Recorded spend exceeds the declared allocation; no remaining allocation assumed')
    return FundingAssessment(state=SignalState.RED if gap > 0 else SignalState.GREEN,
                             available_allocation=available, remaining_cost=remaining, exact_gap=gap, reasons=reasons)


def check_insurance_and_funding(inputs: ProgressInput, *, now: datetime) -> SpecialistResult:
    clock = inputs.as_of if inputs.source_mode == SourceMode.SYNTHETIC else now
    items, missing, actions = [], [], []
    checklist = inputs.checklist if inputs.source_mode == SourceMode.SYNTHETIC else None
    if inputs.insurance_applicable is False:
        prep_state, prep_summary = SignalState.NOT_APPLICABLE, 'No insurance reported; household funding still applies'
    elif inputs.insurance_applicable is None or checklist is None or checklist.id != inputs.checklist_id:
        prep_state, prep_summary = SignalState.UNKNOWN, 'Selected checklist suitability is unknown'
        missing.extend(inputs.general_preparation_missing)
        missing.append('A selected verified preparation checklist')
    else:
        requirement_states = []
        for requirement in checklist.requirements:
            linked = [e for e in inputs.evidence if requirement.id in e.requirement_ids]
            statuses = {e.status for e in linked}
            if not requirement.applicable or statuses == {'not_applicable'}:
                state = SignalState.NOT_APPLICABLE
            elif 'saved' in statuses:
                state = SignalState.GREEN
            elif 'reported_available' in statuses:
                state = SignalState.YELLOW
            elif 'not_collected' in statuses or 'unavailable' in statuses or not linked:
                state = SignalState.RED
            else:
                state = SignalState.UNKNOWN
            requirement_states.append(state)
            items.append(ResultItem(id=f'requirement:{requirement.id}', title=requirement.title, category='preparation requirement',
                                    state=state, summary=', '.join(sorted(statuses)) or 'not collected',
                                    fields={'Evidence links': ', '.join(e.id for e in linked) or 'None'},
                                    reasons=['Only explicit requirement-to-evidence links are used; no document-content interpretation']))
            if state not in (SignalState.GREEN, SignalState.NOT_APPLICABLE):
                missing.append(requirement.title)
        applicable = [s for s in requirement_states if s != SignalState.NOT_APPLICABLE]
        prep_state = (SignalState.RED if SignalState.RED in applicable else SignalState.UNKNOWN if SignalState.UNKNOWN in applicable
                      else SignalState.YELLOW if SignalState.YELLOW in applicable else SignalState.GREEN)
        prep_summary = 'Applicable checklist evidence is saved; this is preparation only, not approval' if prep_state == SignalState.GREEN else 'Some applicable preparation evidence is missing or unconfirmed'
    items.insert(0, ResultItem(id='preparation', title='Preparation', category='insurance', state=prep_state, summary=prep_summary,
                              fields={'Checklist': checklist.label if checklist else 'Suitability unknown',
                                      'Scope': 'Fictional selected checklist' if checklist else 'General saved preparation omissions only'},
                              reasons=['Packet readiness does not establish coverage, acceptance or approval']))
    if prep_state in (SignalState.RED, SignalState.YELLOW, SignalState.UNKNOWN):
        actions.append(ActionCandidate(key='insurance:prepare-evidence', title='Review missing preparation information',
                       reason=prep_summary, tier=2, destination='Insurance & Documents'))
    funding = assess_funding(inputs, now=now)
    amount_label = lambda value: f'USD {value:.2f}' if value is not None else 'Unknown'
    funding_fields = {'Next stage': inputs.funding.stage_label or 'Unknown',
                      'Contribution band': inputs.household.contribution_band or 'Not supplied',
                      'Remaining stage cost': amount_label(funding.remaining_cost),
                      'Available allocation': amount_label(funding.available_allocation),
                      'Exact stage gap': amount_label(funding.exact_gap),
                      'Source': 'Explicit synthetic financial facts' if inputs.source_mode == SourceMode.SYNTHETIC else 'User-reported contribution band; exact ledger not collected'}
    funding_summary = ('A funding gap blocks the next stage' if funding.state == SignalState.RED else
                       'Declared allocation covers the remaining named stage cost' if funding.state == SignalState.GREEN else
                       'Not enough information about funds available for the next stage')
    items.append(ResultItem(id='funding', title='Funding for the next stage', category='funding', state=funding.state,
                            summary=funding_summary, fields=funding_fields, reasons=funding.reasons))
    if funding.state != SignalState.GREEN and inputs.repairs_complete is not True:
        actions.append(ActionCandidate(key='funding:confirm-next-stage', title='Confirm funds for the next repair stage',
                       reason=funding_summary + '; future reimbursement is not available cash.', tier=2,
                       destination='My Recovery Plan', dependencies=['Confirm next-stage scope and available allocation']))
    if funding.state == SignalState.UNKNOWN:
        missing.append('Current stage cost and available allocation')
    if inputs.insurance_applicable is False:
        payment_state, payment_summary = SignalState.NOT_APPLICABLE, 'No insurance payment track'
    elif inputs.source_mode == SourceMode.SAVED_CASE:
        payment_state, payment_summary = SignalState.UNKNOWN, 'Insurance decisions and payment events are not collected here'
    elif _current(inputs.funding.received_payment, inputs.funding.stage_id, clock):
        payment_state, payment_summary = SignalState.GREEN, 'Payment received in the fictional record; allocation remains separate'
    elif inputs.funding.expected_payment or inputs.funding.approved_payment or inputs.funding.decision in ('approved', 'pending'):
        payment_state, payment_summary = SignalState.YELLOW, 'Decision or payment pending; money has not been recorded received'
    else:
        payment_state, payment_summary = SignalState.UNKNOWN, 'Decision and receipt of money are unconfirmed'
    payment_fields = {'Decision': inputs.funding.decision if inputs.source_mode == SourceMode.SYNTHETIC else 'Unknown'}
    for label, fact in [('Expected', inputs.funding.expected_payment), ('Approved', inputs.funding.approved_payment), ('Received', inputs.funding.received_payment)]:
        payment_fields[label] = f'{fact.currency} {fact.amount:.2f}; {fact.stage_id}; recorded {fact.observed_at.date()}' if fact and inputs.source_mode == SourceMode.SYNTHETIC else 'Not recorded'
    items.append(ResultItem(id='insurance-payment', title='Insurance decision & receipt', category='insurance', state=payment_state,
                            summary=payment_summary, fields=payment_fields,
                            reasons=['An approved payment is separate from receipt, available allocation and completed repairs']))
    if payment_state == SignalState.YELLOW and inputs.repairs_complete is True:
        actions.append(ActionCandidate(key='insurance:follow-payment', title='Review pending insurance reimbursement',
                       reason='Reported repairs are complete; payment is still unresolved.', tier=3, destination='Insurance & Documents'))
    states = [s for s in (prep_state, funding.state, payment_state) if s != SignalState.NOT_APPLICABLE]
    state = (SignalState.RED if SignalState.RED in states else SignalState.UNKNOWN if SignalState.UNKNOWN in states
             else SignalState.YELLOW if SignalState.YELLOW in states else SignalState.GREEN)
    return SpecialistResult(specialist='insurance', state=state, headline='Preparation and funding need separate checks',
                            summary='Evidence readiness, decisions, received money and next-stage allocation are distinct facts.',
                            items=items, actions=actions, missing=missing, source_mode=inputs.source_mode, observed_at=clock,
                            execution_state=ExecutionState.NEEDS_INFORMATION if state == SignalState.UNKNOWN else ExecutionState.COMPLETE)
