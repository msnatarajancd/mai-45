from datetime import timedelta
from decimal import Decimal


def test_hotel_capacity_uses_rooms_and_prices_all_required_rooms():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    inputs = load_scenario('chen')
    inputs.accommodation_status = 'needed'
    inputs.household.total = 4
    inputs.household.housing_budget = Decimal('150')
    site = inputs.housing_sites[0]
    site.accepts_pets = True
    inputs.housing_sites = [site]
    assert check_housing(inputs, now=inputs.as_of).items == []  # 2 rooms cost $190
    inputs.household.housing_budget = Decimal('200')
    result = check_housing(inputs, now=inputs.as_of)
    assert result.items[0].fields['Units required'] == '2 rooms'
    assert result.items[0].fields['Nightly household cost'] == 'USD 190.00'
    assert result.state.value == 'red'  # still needs accommodation
    site.available_units = 1
    assert check_housing(inputs, now=inputs.as_of).items == []


def test_known_access_pet_and_transport_constraints_exclude_matches():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    inputs = load_scenario('baptiste')
    site = inputs.housing_sites[4]
    site.available_units = 8
    site.can_keep_together = True
    site.accepts_pets = True
    inputs.housing_sites = [site]
    assert not check_housing(inputs, now=inputs.as_of).items  # inaccessible
    site.accessible = True
    inputs.household.pets = True
    site.accepts_pets = False
    assert not check_housing(inputs, now=inputs.as_of).items
    site.accepts_pets = True
    inputs.household.has_vehicle = False
    assert not check_housing(inputs, now=inputs.as_of).items
    site.transport_available = True
    assert check_housing(inputs, now=inputs.as_of).items


def test_unknown_capacity_stale_reports_and_unactivated_sites_are_not_guaranteed():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    inputs = load_scenario('williams')
    inputs.housing_sites = [inputs.housing_sites[5]]
    result = check_housing(inputs, now=inputs.as_of)
    assert result.items[0].state.value == 'unknown'
    assert 'Household total' in result.missing
    inputs.housing_sites[0].activated = False
    assert not check_housing(inputs, now=inputs.as_of).items
    inputs = load_scenario('chen')
    inputs.housing_sites = [inputs.housing_sites[0]]
    inputs.housing_sites[0].provenance.valid_until = inputs.as_of - timedelta(hours=1)
    assert check_housing(inputs, now=inputs.as_of).items[0].state.value == 'unknown'


def test_saved_case_never_uses_supplied_synthetic_catalog_as_real_availability():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.models import SourceMode
    from recovery.progress.housing import check_housing
    inputs = load_scenario('chen')
    inputs.source_mode = SourceMode.SAVED_CASE
    assert not check_housing(inputs, now=inputs.as_of).items


def test_missing_location_keeps_categories_visible_with_uncertain_suitability():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.housing import check_housing
    inputs = load_scenario('chen')
    inputs.household.zip_code = inputs.household.address = None
    inputs.housing_sites = [inputs.housing_sites[0]]
    item = check_housing(inputs, now=inputs.as_of).items[0]
    assert item.state.value == 'unknown'
    assert any('location' in reason.lower() for reason in item.reasons)
