"""Read-only saved facts never acquire synthetic availability or monetary certainty."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest
from recovery.progress.case_reader import load_saved_input
from recovery.progress.models import SourceMode, fingerprint
from test_recovery_records import saved, dump
from test_insurance_workspace import insurance, save, photo


def test_saved_input_is_read_only_unknown_and_stable(saved):
    path, repo, case = saved
    before = dump(path)
    first = load_saved_input(repo, str(case.case_id))
    second = load_saved_input(repo, case.case_id)
    assert first.source_mode is SourceMode.SAVED_CASE
    assert first.as_of == datetime.now(ZoneInfo('America/New_York')).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    assert fingerprint(first) == fingerprint(second)
    assert first.household.total is None and first.household.address is None
    assert not first.providers and not first.housing_sites and first.checklist is None
    assert first.insurance_applicable is None and first.funding.exact_allocation is None
    assert first.funding.received_payment is None
    assert first.insurance_timing is None and first.recovery_timing is None
    assert first.general_preparation_missing
    assert all(u.provenance.scope == 'user_report' and u.provenance.observed_at == case.updated_at for u in first.utilities)
    assert dump(path) == before


def test_counts_conflict_leaves_total_unknown_with_explanation(saved):
    _, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    records.household.adults, records.household.children = 2, 1
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    profile = repo.get_progress_profile(case.case_id).model_copy(update={'total': 5})
    repo.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    result = load_saved_input(repo, case.case_id)
    assert result.household.total is None
    assert any('conflict' in message.lower() for message in result.timing_assumptions)


def test_relevant_records_insurance_and_profile_invalidate_fingerprint(saved):
    _, repo, case = saved
    initial = fingerprint(load_saved_input(repo, case.case_id))
    records = repo.get_recovery_records(case.case_id)
    records.household.adults = 2
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    records_fp = fingerprint(load_saved_input(repo, case.case_id))
    assert records_fp != initial
    snapshot = repo.get_insurance_snapshot(case.case_id)
    snapshot.workspace.profile.insurer_name = 'Fictional Insurer'
    save(repo, snapshot)
    assert fingerprint(load_saved_input(repo, case.case_id)) != records_fp


def test_original_photo_integrity_is_reused_and_only_metadata_leaves_repo(insurance):
    path, repo, case = insurance
    snapshot = repo.get_insurance_snapshot(case.case_id)
    attachment = photo(snapshot)
    save(repo, snapshot, additions=[attachment])
    detached = repo.get_progress_snapshot(case.case_id)
    assert detached.attachment_metadata[0].sha256 == attachment.metadata.sha256
    assert not hasattr(detached.attachment_metadata[0], 'content')
    result = load_saved_input(repo, case.case_id)
    assert result.evidence[0].status == 'saved'
    assert result.checklist is None
    with repo._connection() as connection:
        connection.execute('UPDATE recovery_insurance_attachments SET content=? WHERE case_id=?',
                           (b'corrupt', str(case.case_id)))
    with pytest.raises(ValueError):
        load_saved_input(repo, case.case_id)


@pytest.mark.parametrize('danger', [True, None])
def test_saved_input_safety_is_fail_closed(saved, danger):
    _, repo, case = saved
    changed = case.model_copy(deep=True)
    changed.intake.immediate_danger = danger
    with repo._connection() as connection:
        connection.execute('UPDATE recovery_cases SET case_json=? WHERE case_id=?', (changed.model_dump_json(), str(case.case_id)))
    with pytest.raises(ValueError, match='paused'):
        load_saved_input(repo, case.case_id)


def test_adult_child_sum_requires_explicit_total_confirmation(saved):
    _, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    records.household.adults, records.household.children = 2, 1
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    result = load_saved_input(repo, case.case_id)
    assert result.household.adults == 2 and result.household.children == 1
    assert result.household.total is None


def test_progress_snapshot_is_atomic_during_concurrent_profile_update(saved):
    path, repo, case = saved
    with repo._connection() as connection:
        connection.execute('PRAGMA journal_mode=WAL')
    from recovery.database import SQLiteRecoveryRepository
    concurrent = SQLiteRecoveryRepository(path)
    validate = repo._validate_insurance_snapshot
    changed = False
    def update_after_insurance_read(snapshot):
        nonlocal changed
        validate(snapshot)
        if not changed:
            changed = True
            profile = concurrent.get_progress_profile(case.case_id).model_copy(update={'total': 7})
            concurrent.save_progress_profile(profile, expected_version=0, expected_case=case, explicitly_confirmed=True)
    repo._validate_insurance_snapshot = update_after_insurance_read
    snapshot = repo.get_progress_snapshot(case.case_id)
    assert snapshot.profile.version == 0 and snapshot.profile.total is None
    assert snapshot.revision != concurrent.get_progress_revision(case.case_id)
    assert concurrent.get_progress_profile(case.case_id).total == 7


def test_saved_specialist_payload_excludes_policy_and_claim_references(saved):
    _, repo, case = saved
    snapshot = repo.get_insurance_snapshot(case.case_id)
    snapshot.workspace.profile.policy_reference = 'PRIVATE-POLICY-SECRET'
    snapshot.workspace.profile.claim_reference = 'PRIVATE-CLAIM-SECRET'
    save(repo, snapshot)
    payload = load_saved_input(repo, case.case_id).model_dump_json()
    assert 'PRIVATE-POLICY-SECRET' not in payload
    assert 'PRIVATE-CLAIM-SECRET' not in payload


def test_atomic_snapshot_includes_recorded_journey_metadata(saved):
    _, repo, case = saved
    snapshot = repo.get_progress_snapshot(case.case_id)
    assert list(snapshot.journey_events) == repo.list_journey_events(case.case_id)


@pytest.mark.parametrize(('reported', 'expected'), [
    ('Needed', 'needed'),
    ('Staying with others', 'arranged'),
    ('Temporary lodging', 'arranged'),
    ('Not needed', 'arranged'),
    ('No lodging arranged', 'needed'),
    ('Staying in temporary lodging', 'arranged'),
    ('  TEMPORARY LODGING  ', 'arranged'),
    ('  NEEDED  ', 'needed'),
    ('Unknown', 'unknown'),
])
def test_saved_accommodation_preserves_extractor_and_structured_vocabulary(saved, reported, expected):
    from recovery.progress.housing import check_housing
    _, repo, case = saved
    updated = case.model_copy(deep=True)
    updated.intake.temporary_accommodation_status = reported
    with repo._connection() as connection:
        connection.execute('UPDATE recovery_cases SET case_json=? WHERE case_id=?',
                           (updated.model_dump_json(), str(case.case_id)))
    result = load_saved_input(repo, case.case_id)
    assert result.accommodation_status == expected
    assert result.home_returned is None and result.repairs_complete is None
    housing = check_housing(result, now=datetime.now(timezone.utc))
    assert bool(housing.actions) == (expected in {'needed', 'unknown'})
