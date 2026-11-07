"""Confirmed fictional profile additions remain separate from plans and intake."""
from datetime import date
from decimal import Decimal
import pytest
from pydantic import ValidationError
from recovery.progress.profiles import ProgressProfile
from test_recovery_records import saved, dump


def test_legacy_profile_is_unknown_and_read_only(saved):
    path, repo, case = saved
    before = dump(path)
    profile = repo.get_progress_profile(case.case_id)
    assert profile.version == 0
    assert profile.total is None and profile.housing_budget is None
    assert profile.gas_applicable is None and profile.gas_available is None
    assert dump(path) == before


def test_profile_requires_confirmation_and_cas_without_other_mutation(saved):
    path, repo, case = saved
    before_case, before_plan = repo.get_case(case.case_id), repo.get_active_plan(case.case_id)
    profile = ProgressProfile(case_id=case.case_id, total=4, zip_code='33101', address='123 Fictional Way',
        recovery_started=date(2026, 11, 1), accessibility=True, pets=False, has_vehicle=True,
        housing_budget=Decimal('125.50'), contribution_band='$500–$1,999', gas_applicable=False)
    with pytest.raises(ValueError, match='confirmation'):
        repo.save_progress_profile(profile, expected_version=0, expected_case=case)
    result = repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    assert result.version == 1 and result.updated_at is not None
    assert repo.get_progress_profile(case.case_id) == result
    assert repo.get_case(case.case_id) == before_case and repo.get_active_plan(case.case_id) == before_plan
    with pytest.raises(ValueError, match='[Ss]tale'):
        repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)


@pytest.mark.parametrize('changes', [dict(total=0), dict(total=True), dict(zip_code='ABC'),
    dict(housing_budget='-1'), dict(contribution_band='all the money'),
    dict(gas_applicable=False, gas_available=True)])
def test_invalid_profile_facts_are_rejected(changes, saved):
    with pytest.raises(ValidationError):
        ProgressProfile(case_id=saved[2].case_id, **changes)


@pytest.mark.parametrize('danger', [True, None])
def test_profile_write_pauses_on_safety_change(saved, danger):
    path, repo, case = saved
    profile = repo.get_progress_profile(case.case_id)
    changed = case.model_copy(deep=True)
    changed.intake.immediate_danger = danger
    with repo._connection() as connection:
        connection.execute('UPDATE recovery_cases SET case_json=? WHERE case_id=?',
                           (changed.model_dump_json(), str(case.case_id)))
    with pytest.raises(ValueError, match='safety|danger'):
        repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)


def test_contribution_bands_match_approved_values():
    from recovery.progress.profiles import CONTRIBUTION_BANDS
    assert CONTRIBUTION_BANDS == ('None available', 'Under $500', '$500–$1,999', '$2,000–$4,999',
                                  '$5,000 or more', 'Not sure', 'Prefer not to say')


@pytest.mark.parametrize('band', ['Not sure', 'Prefer not to say', 'None available'])
def test_contribution_uncertainty_decline_and_none_are_preserved_without_exact_cash(saved, band):
    from recovery.progress.case_reader import load_saved_input
    _, repo, case = saved
    profile = ProgressProfile(case_id=case.case_id, contribution_band=band)
    repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    assert repo.get_progress_profile(case.case_id).contribution_band == band
    result = load_saved_input(repo, case.case_id)
    assert result.household.contribution_band == band
    assert result.household.housing_budget is None
    assert result.funding.exact_allocation is None
    assert result.funding.received_payment is None
