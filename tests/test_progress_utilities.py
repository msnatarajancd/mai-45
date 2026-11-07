from datetime import timedelta


def test_area_available_never_establishes_address_restoration_and_water_is_not_potability():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.utilities import check_utilities
    inputs = load_scenario('chen', 'update')
    inputs.utilities[0].provenance.scope = 'area'
    inputs.utilities[1].potable = None
    result = check_utilities(inputs, now=inputs.as_of)
    items = {item.id: item for item in result.items}
    assert items['electricity'].state.value == 'unknown'
    assert items['water'].state.value == 'yellow'
    assert items['water'].fields['Potability'] == 'Not confirmed'
    assert result.state.value != 'green'


def test_conflicts_stale_unknown_and_not_applicable_have_distinct_states():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.utilities import check_utilities
    inputs = load_scenario('alvarez', 'update')
    result = check_utilities(inputs, now=inputs.as_of)
    water = next(item for item in result.items if item.id == 'water')
    assert water.state.value == 'unknown'
    assert len(water.provenance) == 2
    inputs = load_scenario('baptiste')
    assert check_utilities(inputs, now=inputs.as_of).items[0].state.value == 'unknown'
    inputs = load_scenario('morgan', 'later')
    assert check_utilities(inputs, now=inputs.as_of).items[2].state.value == 'not_applicable'
    assert check_utilities(inputs, now=inputs.as_of).state.value == 'green'


def test_partial_service_yellow_and_stale_reports_never_count_green():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.utilities import check_utilities
    inputs = load_scenario('rivera', 'update')
    assert check_utilities(inputs, now=inputs.as_of).items[0].state.value == 'yellow'
    inputs = load_scenario('chen', 'later')
    for observation in inputs.utilities:
        observation.provenance.valid_until = inputs.as_of - timedelta(seconds=1)
    assert check_utilities(inputs, now=inputs.as_of).state.value == 'unknown'


def test_stale_conflicting_report_is_retained_and_never_silently_certifies_restoration():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.utilities import check_utilities
    inputs = load_scenario('chen', 'later')
    older = inputs.utilities[0].model_copy(deep=True)
    older.status = 'outage'
    older.provenance.observed_at = inputs.as_of - timedelta(days=3)
    older.provenance.valid_until = inputs.as_of - timedelta(days=2)
    inputs.utilities.append(older)
    electricity = check_utilities(inputs, now=inputs.as_of).items[0]
    assert electricity.state.value == 'unknown'
    assert len(electricity.provenance) == 2


def test_confirmed_gas_nonapplicability_does_not_expire_like_restoration_claims():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.models import SourceMode
    from recovery.progress.utilities import check_utilities
    inputs = load_scenario('morgan', 'later')
    inputs.source_mode = SourceMode.SAVED_CASE
    for observation in inputs.utilities:
        observation.provenance.source_mode = SourceMode.SAVED_CASE
        observation.provenance.scope = 'user-reported'
        observation.provenance.valid_until = None
    result = check_utilities(inputs, now=inputs.as_of)
    assert result.items[2].state.value == 'not_applicable'
    assert result.items[0].state.value == 'unknown'
