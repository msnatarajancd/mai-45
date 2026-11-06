from datetime import timedelta
from decimal import Decimal
import pytest


def test_expected_and_approved_payment_do_not_reduce_cash_gap():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.insurance import assess_funding
    inputs = load_scenario('alvarez', 'update')
    result = assess_funding(inputs, now=inputs.as_of)
    assert result.available_allocation == Decimal('500')
    assert result.exact_gap == Decimal('6500')
    assert result.state.value == 'red'
    inputs.funding.received_payment = inputs.funding.approved_payment
    assert assess_funding(inputs, now=inputs.as_of).exact_gap == Decimal('6500')  # no explicit new allocation


@pytest.mark.parametrize('mutation', ['band', 'stale', 'stage', 'currency', 'future', 'saved'])
def test_inexact_stale_cross_stage_and_saved_case_facts_never_produce_exact_gap(mutation):
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.insurance import assess_funding
    from recovery.progress.models import SourceMode
    inputs = load_scenario('alvarez')
    if mutation == 'band':
        inputs.funding.exact_allocation = None
    elif mutation == 'stale':
        inputs.funding.estimated_cost.valid_until = inputs.as_of - timedelta(seconds=1)
    elif mutation == 'stage':
        inputs.funding.exact_allocation.stage_id = 'different-stage'
    elif mutation == 'currency':
        inputs.funding.exact_allocation.currency = 'EUR'
    elif mutation == 'future':
        inputs.funding.exact_allocation.observed_at = inputs.as_of + timedelta(days=1)
    else:
        inputs.source_mode = SourceMode.SAVED_CASE
    assert assess_funding(inputs, now=inputs.as_of).exact_gap is None


def test_spent_money_is_not_available_or_double_counted_as_future_cost():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.insurance import assess_funding
    inputs = load_scenario('chen', 'update')
    result = assess_funding(inputs, now=inputs.as_of)
    assert result.available_allocation == Decimal('500')
    assert result.remaining_cost == Decimal('500')
    assert result.exact_gap == 0
