"""Accommodation matching over supplied, scoped observations only."""
from datetime import datetime
from decimal import Decimal
from math import ceil

from .models import ActionCandidate, ExecutionState, ProgressInput, ResultItem, SignalState, SourceMode, SpecialistResult


def check_housing(inputs: ProgressInput, *, now: datetime) -> SpecialistResult:
    clock = inputs.as_of if inputs.source_mode == SourceMode.SYNTHETIC else now
    household = inputs.household
    missing = [label for label, value in [('Household total', household.total), ('ZIP or address', household.zip_code or household.address),
               ('Accessibility needs', household.accessibility), ('Pets', household.pets), ('Transport', household.has_vehicle)] if value is None]
    items = []
    for site in inputs.housing_sites:
        if site.provenance.source_mode != inputs.source_mode:
            continue
        if household.county and site.county != household.county:
            continue
        if site.category in ('church', 'school') and site.activated is not True:
            continue
        if household.accessibility is True and site.accessible is False:
            continue
        if household.pets is True and site.accepts_pets is False:
            continue
        if household.has_vehicle is False and site.transport_available is False:
            continue
        units = None
        if household.total is not None:
            if site.capacity_unit == 'spaces':
                units = household.total
            elif site.room_occupancy is not None:
                units = ceil(household.total / site.room_occupancy)
        if units is not None and site.available_units is not None and units > site.available_units:
            continue
        # Multi-room and person-space allocation must explicitly keep a household together.
        if household.total is not None and household.total > 1 and site.can_keep_together is False:
            continue
        price = site.nightly_cost_per_unit * units if site.nightly_cost_per_unit is not None and units is not None else None
        if price is not None and household.housing_budget is not None and price > household.housing_budget:
            continue
        uncertainty = []
        if not (household.zip_code or household.address):
            uncertainty.append('Household location is unconfirmed; area suitability needs confirmation')
        if site.provenance.valid_until is None or clock > site.provenance.valid_until or site.provenance.observed_at > clock:
            uncertainty.append('Availability observation is stale or has no current validity')
        if units is None or site.available_units is None:
            uncertainty.append('Capacity fit is unconfirmed')
        if household.total is None or household.total > 1 and site.can_keep_together is None:
            uncertainty.append('Keeping the household together is unconfirmed')
        for label, required, supported in [('Accessibility', household.accessibility, site.accessible), ('Pets', household.pets, site.accepts_pets)]:
            if required is None or required is True and supported is None:
                uncertainty.append(f'{label} fit is unconfirmed')
        if household.has_vehicle is None or household.has_vehicle is False and site.transport_available is None:
            uncertainty.append('Transport fit is unconfirmed')
        if price is None:
            uncertainty.append('Nightly household cost is unknown')
        elif price > Decimal(0) and household.housing_budget is None:
            uncertainty.append('Housing budget is unknown')
        fields = {'Capacity unit': site.capacity_unit,
                  'Available units': str(site.available_units) if site.available_units is not None else 'Unknown',
                  'Units required': f'{units} {site.capacity_unit}' if units is not None else 'Unknown',
                  'Nightly household cost': f'USD {price:.2f}' if price is not None else 'Unknown',
                  'Household together': {True: 'Supported', False: 'No', None: 'Unknown'}[site.can_keep_together],
                  'Area': site.area,
                  'Distance': f'{site.distance_miles} fictional miles; no route calculated' if site.distance_miles is not None else 'Unknown',
                  'Source': 'Synthetic accommodation example' if inputs.source_mode == SourceMode.SYNTHETIC else site.provenance.source}
        items.append(ResultItem(id=site.id, title=site.name, category=site.category,
                     state=SignalState.UNKNOWN if uncertainty else SignalState.GREEN,
                     summary='Suitability needs confirmation' if uncertainty else 'Matches the supplied household constraints',
                     fields=fields, reasons=uncertainty or ['Capacity, household and declared budget constraints met; no reservation'],
                     provenance=[site.provenance]))
    state, headline = {
        'needed': (SignalState.RED, 'Accommodation still needed'),
        'arranged': (SignalState.GREEN, 'Accommodation reported arranged'),
        'home': (SignalState.GREEN, 'At home, as reported'),
        'unknown': (SignalState.UNKNOWN, 'Current accommodation is unknown'),
    }[inputs.accommodation_status]
    actions = []
    if inputs.accommodation_status in ('needed', 'unknown'):
        actions.append(ActionCandidate(key='housing:confirm-accommodation', title='Confirm a suitable place to stay',
                       reason='Current accommodation is not confirmed. Availability and suitability require confirmation.',
                       tier=1, destination='Recovery Progress'))
    if not inputs.housing_sites or not any(s.provenance.source_mode == inputs.source_mode for s in inputs.housing_sites):
        missing.append('Current accommodation availability source')
    return SpecialistResult(specialist='housing', state=state, headline=headline,
                            summary=f'{len(items)} possible accommodation examples; no booking or guaranteed capacity.' if inputs.source_mode == SourceMode.SYNTHETIC else 'Saved household facts only; accommodation availability has not been verified.',
                            items=items, actions=actions, missing=missing, source_mode=inputs.source_mode,
                            observed_at=clock, execution_state=ExecutionState.NEEDS_INFORMATION if state == SignalState.UNKNOWN else ExecutionState.COMPLETE)
