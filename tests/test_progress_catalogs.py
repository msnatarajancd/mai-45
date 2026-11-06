"""Guard the authored catalogs and their useful demonstration boundaries."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

import pytest

from recovery.progress.housing import check_housing
from recovery.progress.models import (
    ChecklistProfile, HousingSite, ProgressInput, RepairProvider,
)
from recovery.progress.rebuild import check_rebuild


DATA = Path(__file__).resolve().parents[1] / 'recovery' / 'progress' / 'data'
AREAS = {'Bay demo area', 'Palmetto demo area', 'Coral demo area'}
HOUSING = {
    'hotel': 'hotel', 'church': 'church', 'school': 'school',
    'official-shelter': 'official shelter',
}
TRADES = {
    'electrician': 'Electrician', 'contractor': 'Contractor',
    'plumber': 'Plumber', 'roofer': 'Roofer', 'pool-specialist': 'Pool specialist',
}
CHECKLIST_REQUIREMENTS = {
    'sample-e': ['displacement_record', 'temporary_stay_receipts', 'photos'],
    'sample-f': ['inspection_summary', 'scope', 'quote', 'photos'],
    'sample-g': ['inventory', 'ownership', 'repair_progress', 'photos'],
    'sample-h': ['damage_summary', 'scope', 'receipts', 'payment_record'],
}


def _rows(filename):
    return json.loads((DATA / filename).read_text(encoding='utf-8'))


def _inputs():
    observed = datetime(2026, 8, 3, 12, tzinfo=timezone.utc)
    provenance = {
        'source_mode': 'synthetic', 'source': 'Fictional catalog test',
        'observed_at': observed, 'valid_until': observed + timedelta(days=1),
    }
    return ProgressInput(
        context_key='synthetic:catalog-test', source_mode='synthetic', as_of=observed,
        household={
            'label': 'Fictional catalog-test household', 'total': 4,
            'zip_code': '00000', 'county': 'Miami-Dade', 'area': 'Bay demo area',
            'accessibility': True, 'pets': True, 'has_vehicle': False,
            'housing_budget': 200,
        },
        accommodation_status='needed', needed_trades=['Electrician'],
        housing_sites=[dict(row, provenance=provenance) for row in _rows('housing.json')],
        providers=[dict(row, provenance=provenance) for row in _rows('providers.json')],
    )


@pytest.mark.parametrize('filename,prefixes,category_key,model', [
    ('housing.json', HOUSING, 'category', HousingSite),
    ('providers.json', TRADES, 'trade', RepairProvider),
])
def test_catalogs_have_twelve_valid_unique_records_per_category_and_keep_original_order(
    filename, prefixes, category_key, model,
):
    rows = _rows(filename)
    assert Counter(row[category_key] for row in rows) == {
        category: 12 for category in prefixes.values()
    }
    assert len({row['id'] for row in rows}) == len(rows)
    assert {row['id'] for row in rows} == {
        f'{prefix}-{number}' for prefix in prefixes for number in range(1, 13)
    }
    assert [row['id'] for row in rows[:len(prefixes) * 3]] == [
        f'{prefix}-{number}' for prefix in prefixes for number in range(1, 4)
    ]
    inputs = _inputs()
    records = inputs.housing_sites if filename == 'housing.json' else inputs.providers
    assert all(isinstance(record, model) for record in records)
    for row in rows:
        assert row['name'].startswith(('Demo ', 'Fictional '))
        assert row['county'] == 'Miami-Dade'
        assert 'provenance' not in row  # The loader binds each checkpoint observation.
        assert not re.search(r'https?://|www\.|@|\b\d{3}[-. ]\d{3}[-. ]\d{4}\b', json.dumps(row))
        areas = {row['area']} if 'area' in row else set(row['areas'])
        assert areas and areas <= AREAS


@pytest.mark.parametrize('category', HOUSING.values())
def test_each_housing_category_covers_capacity_and_household_constraints(category):
    rows = [row for row in _rows('housing.json') if row['category'] == category]
    assert {row['capacity_unit'] for row in rows} == ({'rooms'} if category == 'hotel' else {'spaces'})
    assert any(row['available_units'] == 0 for row in rows)
    assert any(row['available_units'] is None for row in rows)
    assert any((row['available_units'] or 0) >= 2 for row in rows)
    for field in ['can_keep_together', 'accessible', 'accepts_pets', 'transport_available']:
        assert {row[field] for row in rows} == {True, False, None}
        assert all(row[field] is None or type(row[field]) is bool for row in rows)
    assert all(row['available_units'] is None or type(row['available_units']) is int for row in rows)
    if category in {'church', 'school'}:
        assert {row['activated'] for row in rows} >= {True, False}
    if category == 'hotel':
        assert all(row['room_occupancy'] is not None and row['room_occupancy'] > 0 for row in rows)
        assert len({row['nightly_cost_per_unit'] for row in rows}) >= 5
    else:
        assert all(row['room_occupancy'] is None and row['nightly_cost_per_unit'] == 0 for row in rows)


@pytest.mark.parametrize('prefix', HOUSING)
def test_full_unknown_and_large_family_catalog_rows_produce_distinct_matches(prefix):
    inputs = _inputs()
    inputs.household.total = 8
    inputs.housing_sites = [site for site in inputs.housing_sites if site.id in {
        f'{prefix}-4', f'{prefix}-5', f'{prefix}-6',
    }]
    result = check_housing(inputs, now=inputs.as_of)
    items = {item.id: item for item in result.items}
    assert f'{prefix}-4' not in items  # Known full sites cannot suggest a vacancy.
    assert items[f'{prefix}-5'].state.value == 'unknown'
    assert 'Capacity fit is unconfirmed' in items[f'{prefix}-5'].reasons
    assert items[f'{prefix}-6'].state.value == 'green'
    assert result.state.value == 'red'  # A suitable listing never arranges accommodation.
    if prefix == 'hotel':
        assert items['hotel-6'].fields['Units required'] == '2 rooms'
        assert items['hotel-6'].fields['Nightly household cost'] == 'USD 90.00'
    else:
        assert items[f'{prefix}-6'].fields['Units required'] == '8 spaces'


@pytest.mark.parametrize('prefix', HOUSING)
def test_new_catalog_options_exercise_access_pets_transport_and_family_exclusions(prefix):
    inputs = _inputs()
    inputs.housing_sites = [site for site in inputs.housing_sites if site.id in {
        f'{prefix}-{number}' for number in range(7, 12)
    }]
    result = check_housing(inputs, now=inputs.as_of)
    assert [item.id for item in result.items] == [f'{prefix}-7']
    assert result.items[0].state.value == 'green'


def test_unactivated_community_locations_are_excluded_and_hotel_costs_use_household_total():
    inputs = _inputs()
    inputs.housing_sites = [site for site in inputs.housing_sites if site.id in {
        'church-12', 'school-12', 'hotel-7', 'hotel-12',
    }]
    inputs.household.housing_budget = 60
    result = check_housing(inputs, now=inputs.as_of)
    assert [item.id for item in result.items] == ['hotel-7']
    assert result.items[0].fields['Nightly household cost'] == 'USD 60.00'


@pytest.mark.parametrize('trade', TRADES.values())
def test_every_trade_has_rated_unrated_and_all_availability_and_accessibility_variants(trade):
    rows = [row for row in _rows('providers.json') if row['trade'] == trade]
    assert {row['availability'] for row in rows} == {'available', 'waiting', 'unavailable', 'unknown'}
    assert {row['accessible_service'] for row in rows} == {True, False, None}
    assert any(row['rating'] is None and row['review_count'] is None for row in rows)
    assert any(row['rating'] is not None and row['review_count'] > 0 for row in rows)
    assert any(len(row['areas']) > 1 for row in rows)
    assert set().union(*(set(row['areas']) for row in rows)) == AREAS
    for row in rows:
        assert len(row['areas']) == len(set(row['areas']))
        assert (row['rating'] is None) == (row['review_count'] is None)
        assert row['review_count'] is None or type(row['review_count']) is int
        assert row['accessible_service'] is None or type(row['accessible_service']) is bool


def test_new_provider_rows_distinguish_unavailable_waiting_unrated_and_known_access_mismatch():
    inputs = _inputs()
    inputs.providers = [provider for provider in inputs.providers if provider.id in {
        'electrician-4', 'electrician-5', 'electrician-7', 'electrician-9',
    }]
    result = check_rebuild(inputs, now=inputs.as_of)
    items = {item.id: item for item in result.items}
    assert set(items) == {'electrician-4', 'electrician-5', 'electrician-7'}
    assert items['electrician-4'].fields['Availability'] == 'unavailable'
    assert items['electrician-5'].fields['Availability'] == 'waiting'
    assert items['electrician-4'].state.value == items['electrician-5'].state.value == 'yellow'
    assert items['electrician-7'].state.value == 'green'
    assert items['electrician-7'].fields['Rating'] == 'Unrated'
    assert result.state.value == 'yellow'  # Availability is not a work commitment.


def test_eight_neutral_checklists_have_unique_stable_requirement_links():
    profiles = [ChecklistProfile.model_validate(row) for row in _rows('checklists.json')]
    assert [profile.id for profile in profiles] == [f'sample-{letter}' for letter in 'abcdefgh']
    for profile in profiles:
        identifiers = [requirement.id for requirement in profile.requirements]
        assert identifiers and len(set(identifiers)) == len(identifiers)
        assert all(re.fullmatch('[a-z]+(?:_[a-z]+)*', identifier) for identifier in identifiers)
        assert all(requirement.title and requirement.applicable for requirement in profile.requirements)
        if profile.id in CHECKLIST_REQUIREMENTS:
            assert identifiers == CHECKLIST_REQUIREMENTS[profile.id]
            assert 'fictional' in profile.description.lower()
            assert 'insurer' not in profile.label.lower()
