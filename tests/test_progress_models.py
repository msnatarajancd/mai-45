from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError


def test_unknown_household_facts_stay_unknown_and_negative_money_is_rejected():
    from recovery.progress.models import HouseholdContext
    household = HouseholdContext(label='Unconfirmed')
    assert household.total is None and household.has_vehicle is None
    assert household.housing_budget is None and household.pets is None
    with pytest.raises(ValidationError):
        HouseholdContext(label='Example', housing_budget=Decimal('-1'))


def test_fingerprint_binds_source_checkpoint_and_household_facts():
    from recovery.progress.models import ProgressInput, HouseholdContext, SourceMode, fingerprint
    inputs = ProgressInput(context_key='case-1', source_mode=SourceMode.SAVED_CASE,
                           as_of=datetime(2026, 10, 1, tzinfo=timezone.utc), household=HouseholdContext(label='Example'))
    assert fingerprint(inputs) == fingerprint(inputs.model_copy(deep=True))
    changed = inputs.model_copy(update={'household': inputs.household.model_copy(update={'total': 2})})
    assert fingerprint(inputs) != fingerprint(changed)
    with pytest.raises(ValidationError):
        ProgressInput(context_key='bad', source_mode=SourceMode.SAVED_CASE,
                      as_of=datetime(2026, 10, 1), household=HouseholdContext(label='Example'))


def test_money_rejects_nonfinite_amounts_and_utilities_can_be_partial():
    from recovery.progress.models import MoneyFact, UtilityObservation, Provenance, SourceMode
    stamp = datetime(2026, 10, 1, tzinfo=timezone.utc)
    for amount in ['NaN', 'Infinity']:
        with pytest.raises(ValidationError):
            MoneyFact(amount=amount, stage_id='roof', observed_at=stamp)
    partial = UtilityObservation(service='electricity', status='partial', provider='Example',
                                 provenance=Provenance(source_mode=SourceMode.SAVED_CASE, source='User report', observed_at=stamp))
    assert partial.status == 'partial'
