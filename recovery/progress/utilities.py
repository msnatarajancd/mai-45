"""Keep service, evidence freshness, address scope and potability separate."""
from datetime import datetime

from .models import ActionCandidate, ExecutionState, ProgressInput, ResultItem, SignalState, SourceMode, SpecialistResult


def check_utilities(inputs: ProgressInput, *, now: datetime) -> SpecialistResult:
    clock = inputs.as_of if inputs.source_mode == SourceMode.SYNTHETIC else now
    items, actions, missing = [], [], []
    for service in ('electricity', 'water', 'gas'):
        observations = [o for o in inputs.utilities if o.service == service and o.provenance.source_mode == inputs.source_mode]
        fresh = [o for o in observations if o.provenance.observed_at <= clock and o.provenance.valid_until is not None and clock <= o.provenance.valid_until]
        address = [o for o in fresh if o.provenance.scope in ('address', 'household', 'user-reported address')]
        statuses = {o.status for o in address}
        reasons = [f'{o.provider}: {o.status}; {o.provenance.scope}. {o.note}' for o in observations]
        if not observations:
            state, summary = SignalState.UNKNOWN, 'No current observation supplied'
        elif service == 'gas' and {o.status for o in observations} == {'not_applicable'}:
            state, summary = SignalState.NOT_APPLICABLE, 'Gas is not used by this household, as explicitly reported'
        elif len(fresh) != len(observations):
            state, summary = SignalState.UNKNOWN, 'One or more observations are stale or have no current validity'
        elif len(statuses) > 1 or service == 'water' and len({o.potable for o in address if o.potable is not None}) > 1:
            state, summary = SignalState.UNKNOWN, 'Conflicting reports; restoration is unconfirmed'
        elif not address:
            state, summary = SignalState.UNKNOWN, 'No fresh address-level report; area information cannot confirm restoration'
        elif 'unknown' in statuses:
            state, summary = SignalState.UNKNOWN, 'Service is unconfirmed'
        elif 'not_applicable' in statuses:
            state, summary = (SignalState.NOT_APPLICABLE, 'Gas is not used by this household') if service == 'gas' else (SignalState.UNKNOWN, 'Applicability needs confirmation')
        elif 'outage' in statuses:
            state, summary = SignalState.RED, 'Address-level interruption reported'
        elif 'partial' in statuses:
            state, summary = SignalState.YELLOW, 'Partial service reported'
        elif service == 'water' and not all(o.potable is True for o in address):
            state, summary = SignalState.YELLOW, 'Water available; drinking safety is not confirmed'
        else:
            state, summary = SignalState.GREEN, 'Address-level service available, as reported'
        fields = {'Provider': ', '.join(dict.fromkeys(o.provider for o in observations)) or 'Unknown',
                  'Scope': ', '.join(dict.fromkeys(o.provenance.scope for o in observations)) or 'Unknown',
                  'Source': 'Synthetic utility observations' if inputs.source_mode == SourceMode.SYNTHETIC else 'Saved/user-reported observations; no live verification'}
        if service == 'water':
            fields['Potability'] = 'Reported potable' if address and all(o.potable is True for o in address) else 'Reported not potable' if any(o.potable is False for o in address) else 'Not confirmed'
        items.append(ResultItem(id=service, title=service.title(), category='utility', state=state, summary=summary,
                                fields=fields, reasons=reasons or ['No supplied service observation'], provenance=[o.provenance for o in observations]))
        if state in (SignalState.UNKNOWN, SignalState.RED, SignalState.YELLOW):
            missing.append(f'Current {service} restoration/potability confirmation' if service == 'water' else f'Current {service} address report')
            actions.append(ActionCandidate(key=f'utilities:{service}', title=f'Confirm {service} and essential needs',
                           reason=summary, tier=1 if state == SignalState.RED else 2, destination='My Recovery Plan'))
    applicable = [item.state for item in items if item.state != SignalState.NOT_APPLICABLE]
    state = (SignalState.RED if SignalState.RED in applicable else SignalState.UNKNOWN if SignalState.UNKNOWN in applicable
             else SignalState.YELLOW if SignalState.YELLOW in applicable else SignalState.GREEN)
    return SpecialistResult(specialist='utilities', state=state,
                            headline={SignalState.RED: 'Essential service interruption reported', SignalState.UNKNOWN: 'Some utility status is unconfirmed', SignalState.YELLOW: 'Service is partial or needs confirmation', SignalState.GREEN: 'Named utility conditions are met'}[state],
                            summary='Electricity, water and gas are assessed separately. Service availability does not establish home safety.',
                            items=items, actions=actions, missing=missing, source_mode=inputs.source_mode, observed_at=clock,
                            execution_state=ExecutionState.NEEDS_INFORMATION if state == SignalState.UNKNOWN else ExecutionState.COMPLETE)
