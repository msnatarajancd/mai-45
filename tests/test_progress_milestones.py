def _results(inputs):
    from recovery.progress.housing import check_housing
    from recovery.progress.utilities import check_utilities
    from recovery.progress.insurance import check_insurance_and_funding
    from recovery.progress.rebuild import check_rebuild
    return tuple(check(inputs,now=inputs.as_of) for check in (check_housing,check_utilities,check_insurance_and_funding,check_rebuild))


def test_home_and_funding_tracks_can_diverge_without_global_percentage():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.milestones import build_milestones
    inputs=load_scenario('chen','later')
    view=build_milestones(inputs,_results(inputs))
    assert view.elapsed_days == 22
    assert next(m for m in view.home if m.title=='Returned home').state.value=='green'
    assert next(m for m in view.home if m.title=='Repairs completed').state.value=='green'
    assert next(m for m in view.funding if m.title=='Insurance funds received').state.value=='yellow'
    assert 'Illustrative' in view.recovery_range


def test_saved_case_ranges_unknown_and_return_home_not_inferred_from_utilities():
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.models import SourceMode
    from recovery.progress.milestones import build_milestones
    inputs=load_scenario('rivera','later')
    inputs.source_mode=SourceMode.SAVED_CASE
    inputs.recovery_started=None
    inputs.home_returned=None
    view=build_milestones(inputs,_results(inputs))
    assert view.elapsed_days is None and 'unknown' in view.elapsed_label.lower()
    assert view.insurance_range == view.recovery_range == 'Not enough information'
    assert next(m for m in view.home if m.title=='Returned home').state.value=='unknown'


def test_no_insurance_excludes_only_insurance_milestones_and_future_start_is_unknown():
    from datetime import timedelta
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.milestones import build_milestones
    inputs=load_scenario('morgan')
    inputs.recovery_started=inputs.as_of.date()+timedelta(days=1)
    view=build_milestones(inputs,_results(inputs))
    assert view.elapsed_days is None
    assert next(m for m in view.funding if m.title=='Insurance decision').state.value=='not_applicable'
    assert next(m for m in view.funding if m.title=='Funding for next stage').state.value!='not_applicable'


def test_elapsed_days_uses_household_new_york_calendar_not_utc_midnight():
    from datetime import date, datetime, timezone
    from recovery.progress.fixtures import load_scenario
    from recovery.progress.milestones import build_milestones
    inputs=load_scenario('chen')
    inputs.recovery_started=date(2026,10,1)
    inputs.as_of=datetime(2026,10,3,1,tzinfo=timezone.utc)  # Oct 2 evening in Miami
    assert build_milestones(inputs,()).elapsed_days == 1
