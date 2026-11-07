"""Authored checkpoint variants must stay isolated, typed and synthetic."""
from copy import deepcopy
from datetime import timedelta

import pytest


def with_catalog(monkeypatch, catalog):
    from recovery.progress import fixtures
    original = fixtures._read
    scenarios = deepcopy(original('scenarios.json'))
    scenarios[0]['checkpoints'][0]['catalog'] = catalog
    monkeypatch.setattr(fixtures, '_read', lambda name: scenarios if name == 'scenarios.json' else original(name))
    return fixtures


def test_checkpoint_catalog_selects_named_rows_and_preserves_capacity_units(monkeypatch):
    fixtures = with_catalog(monkeypatch, {
        'housing_ids': ['school-1', 'hotel-1'], 'provider_ids': ['electrician-1'],
        'housing_overrides': {'hotel-1': {'available_units': 0}},
        'provider_overrides': {'electrician-1': {'availability': 'waiting'}},
    })
    inputs = fixtures.load_scenario('rivera')
    assert [s.id for s in inputs.housing_sites] == ['school-1', 'hotel-1']
    assert inputs.housing_sites[1].available_units == 0
    assert inputs.housing_sites[1].capacity_unit == 'rooms'
    assert inputs.providers[0].availability == 'waiting'
    assert fixtures._read('housing.json')[0]['available_units'] == 2
    assert fixtures._read('providers.json')[0]['availability'] == 'available'
    # Returning to another authored checkpoint never inherits the override.
    assert fixtures.load_scenario('rivera', 'update').housing_sites[0].available_units == 2


def test_empty_catalog_is_not_replaced_with_available_demo_options(monkeypatch):
    fixtures = with_catalog(monkeypatch, {'housing_ids': [], 'provider_ids': []})
    inputs = fixtures.load_scenario('rivera')
    assert inputs.housing_sites == [] and inputs.providers == []


def test_catalog_observation_age_survives_refresh_and_unknown_validity(monkeypatch):
    fixtures = with_catalog(monkeypatch, {'housing_age_hours': 72,
        'housing_validity_hours': 24, 'provider_age_hours': 12, 'provider_validity_hours': None})
    first = fixtures.load_scenario('rivera')
    second = fixtures.load_scenario('rivera')
    provenance = first.housing_sites[0].provenance
    assert provenance.observed_at == first.as_of - timedelta(hours=72)
    assert provenance.valid_until == first.as_of - timedelta(hours=48)
    assert provenance.source_mode.value == 'synthetic'
    assert second.housing_sites[0].provenance == provenance
    assert first.providers[0].provenance.valid_until is None


@pytest.mark.parametrize('catalog', [
    {'housing_ids': ['missing']},
    {'provider_ids': ['electrician-1', 'electrician-1']},
    {'housing_ids': [], 'housing_overrides': {'hotel-1': {'available_units': 5}}},
    {'housing_overrides': {'missing': {'available_units': 1}}},
    {'housing_overrides': {'hotel-1': {'id': 'renamed'}}},
    {'provider_overrides': {'electrician-1': {'provenance': {'source_mode': 'saved_case'}}}},
    {'housing_overrides': {'hotel-1': {'available_units': -1}}},
    {'provider_overrides': {'electrician-1': {'unknown_field': True}}},
    {'housing_age_hours': -1},
    {'unknown_option': True},
])
def test_invalid_catalog_variants_fail_loudly(monkeypatch, catalog):
    fixtures = with_catalog(monkeypatch, catalog)
    with pytest.raises(ValueError):
        fixtures.load_scenario('rivera')
