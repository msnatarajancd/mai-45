"""Fictional replays must exercise persisted recovery behavior without live services."""
from datetime import date, datetime, time, timedelta, timezone
import json
import socket
import sqlite3
from uuid import uuid4

import pytest
from pydantic import ValidationError

from recovery.database import SQLiteRecoveryRepository
from recovery.models import TaskStatus


def test_six_validated_synthetic_scenarios_have_required_checkpoints():
    from recovery.demo import list_scenarios

    scenarios = list_scenarios()
    assert [s.scenario_id for s in scenarios] == [
        "rivera", "bennett", "patel", "chen", "johnson", "lewis"]
    for scenario in scenarios:
        assert "synthetic" in scenario.label.casefold()
        assert "fictional" in scenario.label.casefold()
        assert scenario.incident_date == date(2026, 10, 1)
        assert scenario.intake.disaster_type in {"Hurricane", "Flood"}
        assert scenario.checkpoint_days == (
            (1, 3, 7) if scenario.scenario_id in {"rivera", "bennett", "patel"}
            else (1, 3, 7, 14, 30))
        assert all("synthetic" in cp.summary.casefold() for cp in scenario.checkpoints)


@pytest.mark.parametrize("scenario_id,days", [
    ("rivera", (1, 3, 7)), ("bennett", (1, 3, 7)), ("patel", (1, 3, 7)),
    ("chen", (1, 3, 7, 14, 30)), ("johnson", (1, 3, 7, 14, 30)),
    ("lewis", (1, 3, 7, 14, 30)),
])
def test_every_checkpoint_replays_real_events_at_simulated_dates(tmp_path, scenario_id, days):
    from recovery.demo import load_checkpoint

    for day in days:
        path = tmp_path / f"{scenario_id}-{day}.sqlite"
        selection = load_checkpoint(path, scenario_id, day)
        repository = SQLiteRecoveryRepository(path)
        case = repository.get_case(selection.case_id)
        assert selection.as_of == date(2026, 10, 1) + timedelta(days=day)
        assert "synthetic" in selection.scenario_label.casefold()
        assert case.intake.immediate_danger is selection.immediate_danger
        events = repository.list_journey_events(selection.case_id)
        assert {event["kind"] for event in events} >= {
            "case_created", "records_confirmed", "plan_approved"}
        assert all(date.fromisoformat(event["occurred_at"][:10]) <= selection.as_of
                   for event in events)
        assert events[0]["occurred_at"].startswith("2026-10-02")
        assert repository.get_recovery_records(selection.case_id).incident_date == date(2026, 10, 1)
        assert repository.get_active_plan(selection.case_id) is not None
        assert (selection.pending_revision_json is not None) == (scenario_id == "bennett" and day == 7)
        if day == 1:
            assert selection.previous_checkpoint_event_cursor is None
        else:
            assert selection.previous_checkpoint_event_cursor in {e["event_id"] for e in events}


def test_explicit_loads_make_isolated_cases_without_overwriting_danger(tmp_path):
    from recovery.demo import load_checkpoint, list_scenarios

    path = tmp_path / "dedicated-demo.sqlite"
    list_scenarios()
    assert not path.exists()
    first = load_checkpoint(path, "lewis", 30)
    repository = SQLiteRecoveryRepository(path)
    before = repository.get_case(first.case_id)
    first_events = repository.list_journey_events(first.case_id)
    second = load_checkpoint(path, "rivera", 1)
    third = load_checkpoint(path, "lewis", 30)
    assert len({first.case_id, second.case_id, third.case_id}) == 3
    assert repository.get_case(first.case_id) == before
    assert repository.list_journey_events(first.case_id) == first_events
    assert first.immediate_danger is True
    assert repository.get_case(second.case_id).intake.immediate_danger is False
    assert first_events[-1]["kind"] == "danger_reported"
    active = repository.get_active_plan(first.case_id)
    with pytest.raises(ValueError, match="danger"):
        repository.update_task_status(active.plan_id, active.proposed_tasks[0].task_id,
                                      TaskStatus.COMPLETED)


def test_unchanged_checkpoint_has_no_new_events_and_keeps_unknowns(tmp_path):
    from recovery.demo import load_checkpoint

    path = tmp_path / "demo.sqlite"
    selection = load_checkpoint(path, "patel", 3)
    repository = SQLiteRecoveryRepository(path)
    events = repository.list_journey_events(selection.case_id)
    assert not [e for e in events if e["event_id"] > selection.previous_checkpoint_event_cursor]
    records = repository.get_recovery_records(selection.case_id)
    assert records.household.adults is None
    assert records.household.children is None
    assert records.household.housing_type is None
    assert records.household.insurer_contact_status == "Unknown"
    assert repository.get_case(selection.case_id).intake.utility_availability["water"] is None


def test_pending_revision_does_not_become_a_recorded_change(tmp_path):
    from recovery.demo import load_checkpoint

    path = tmp_path / "demo.sqlite"
    selection = load_checkpoint(path, "bennett", 7)
    repository = SQLiteRecoveryRepository(path)
    assert selection.pending_change_description
    assert "proposal" in selection.pending_change_description.casefold()
    events = repository.list_journey_events(selection.case_id)
    assert not [e for e in events if e["event_id"] > selection.previous_checkpoint_event_cursor]
    case = repository.get_case(selection.case_id)
    assert "transportation" not in case.intake.household_recovery_needs
    assert len(repository.list_approved_plans(selection.case_id)) == 1


def test_completed_and_blocked_tasks_survive_approved_revisions(tmp_path):
    from recovery.demo import load_checkpoint

    path = tmp_path / "demo.sqlite"
    selection = load_checkpoint(path, "chen", 30)
    repository = SQLiteRecoveryRepository(path)
    plans = repository.list_approved_plans(selection.case_id)
    assert len(plans) >= 2
    final = {t.task_id: t for t in plans[-1].proposed_tasks}
    prior_statuses = {t.task_id: t.status for plan in plans[:-1] for t in plan.proposed_tasks
                      if t.status in {TaskStatus.COMPLETED, TaskStatus.BLOCKED}}
    assert set(prior_statuses.values()) == {TaskStatus.COMPLETED, TaskStatus.BLOCKED}
    assert all(final[task_id].status == status for task_id, status in prior_statuses.items())
    assert repository.list_task_history(selection.case_id)


def test_replay_is_deterministic_without_network_or_model_calls(tmp_path, monkeypatch):
    from recovery.demo import load_checkpoint
    from recovery.dashboard import build_dashboard

    def forbidden(*args, **kwargs):
        pytest.fail("synthetic journey attempted network/model access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    import recovery.ai_planner as ai_planner
    monkeypatch.setattr(ai_planner, "create_ai_draft_plan", forbidden)
    projections = []
    for suffix in ("a", "b"):
        path = tmp_path / f"demo-{suffix}.sqlite"
        selection = load_checkpoint(path, "rivera", 7)
        repository = SQLiteRecoveryRepository(path)
        plan = repository.get_active_plan(selection.case_id)
        events = repository.list_journey_events(selection.case_id)
        view = build_dashboard(repository.get_case(selection.case_id),
                               repository.get_recovery_records(selection.case_id), plan,
                               events, as_of=selection.as_of,
                               since_event_id=selection.previous_checkpoint_event_cursor)
        projections.append(([(e["kind"], e["title"], e["detail"], e["occurred_at"]) for e in events],
                            [(t.title, t.status) for t in plan.proposed_tasks],
                            view.elapsed_days))
    assert projections[0] == projections[1]


def test_invalid_checkpoint_rejected_before_database_creation(tmp_path):
    from recovery.demo import load_checkpoint

    for scenario_id, day in (("missing", 1), ("rivera", 30), ("../rivera", 1), ("rivera", True)):
        path = tmp_path / f"invalid-{day}.sqlite"
        with pytest.raises(ValueError):
            load_checkpoint(path, scenario_id, day)
        assert not path.exists()


def test_fixture_validation_rejects_unlabeled_and_operational_extras():
    from recovery.demo import ScenarioDefinition, list_scenarios

    raw = list_scenarios()[0].model_dump(mode="json")
    for patch in ({"label": "Rivera household"}, {"dispatch_phone": "555-0100"},
                  {"reviewer": "Officially approved"}, {"incident_date": "2027-01-01"}):
        with pytest.raises(ValidationError):
            ScenarioDefinition.model_validate({**raw, **patch})
    text = json.dumps(raw).casefold()
    assert "home is safe" not in text
    assert "recovery complete" not in text


def test_fixture_rejects_nested_operational_fields_and_unsupported_incident():
    from recovery.demo import ScenarioDefinition, list_scenarios

    raw = list_scenarios()[0].model_dump(mode="json")
    for patch in ({"dispatch_phone": "555-0100"}, {"disaster_type": "Official hurricane case"}):
        with pytest.raises(ValidationError):
            ScenarioDefinition.model_validate({**raw, "intake": {**raw["intake"], **patch}})


def test_pending_revision_can_be_explicitly_approved_without_a_pending_milestone(tmp_path):
    from recovery.demo import load_checkpoint
    from recovery.dashboard import build_dashboard
    from recovery.reassessment import ReassessmentPreview

    path = tmp_path / "demo.sqlite"
    selection = load_checkpoint(path, "bennett", 7)
    repository = SQLiteRecoveryRepository(path, clock=lambda: datetime.combine(
        selection.as_of, time(14), timezone.utc))
    events_before = repository.list_journey_events(selection.case_id)
    case = repository.get_case(selection.case_id)
    records = repository.get_recovery_records(selection.case_id)
    plan = repository.get_active_plan(selection.case_id)
    view = build_dashboard(case, records, plan, events_before, as_of=selection.as_of,
                           since_event_id=selection.previous_checkpoint_event_cursor)
    assert view.changes == ()
    assert all("transportation" not in event.detail.casefold() for event in view.timeline)
    assert selection.pending_revision_json is not None
    preview = ReassessmentPreview.model_validate_json(selection.pending_revision_json)
    assert "transportation" in preview.updated_intake.household_recovery_needs
    assert repository.list_journey_events(selection.case_id) == events_before
    repository.approve_reassessment(preview, explicitly_approved=True,
                                     expected_records_version=records.version)
    updated_case = repository.get_case(selection.case_id)
    updated_plan = repository.get_active_plan(selection.case_id)
    assert "transportation" in updated_case.intake.household_recovery_needs
    assert updated_plan.plan_id != plan.plan_id
    assert any(task.planning_key == "transport" for task in updated_plan.proposed_tasks)
    view_after = build_dashboard(updated_case, repository.get_recovery_records(selection.case_id),
                                 updated_plan, repository.list_journey_events(selection.case_id),
                                 as_of=selection.as_of,
                                 since_event_id=selection.previous_checkpoint_event_cursor)
    assert [event.kind for event in view_after.changes] == ["revision_approved"]
    assert not any("pending" in event.title.casefold() for event in view_after.timeline)


@pytest.mark.parametrize("scenario_id", ["rivera", "chen", "johnson"])
def test_agreed_household_stories_preserve_distinct_needs(tmp_path, scenario_id):
    from recovery.demo import load_checkpoint
    from recovery.task_view import current_task_views

    day = 7 if scenario_id == "rivera" else 30
    path = tmp_path / f"{scenario_id}.sqlite"
    selection = load_checkpoint(path, scenario_id, day)
    repository = SQLiteRecoveryRepository(path)
    case = repository.get_case(selection.case_id)
    records = repository.get_recovery_records(selection.case_id)
    plan = repository.get_active_plan(selection.case_id)
    if scenario_id == "rivera":
        assert case.intake.temporary_accommodation_status == "staying with others"
        assert "transportation" in case.intake.household_recovery_needs
        assert records.household.accessibility_needs
        transport = next(view for view in current_task_views(plan)
                         if view.task.planning_key == "transport")
        assert transport.applicable
        assert transport.task.status is not TaskStatus.COMPLETED
    elif scenario_id == "chen":
        assert records.household.insurer_contact_status == "Follow-up requested"
        assert len(records.damage_records) >= 2
        documentation = next(task for task in plan.proposed_tasks if task.planning_key == "damage")
        assert documentation.status is TaskStatus.COMPLETED
        assert any(task.title.startswith("Document newly reported damage:")
                   and task.status is TaskStatus.NOT_STARTED for task in plan.proposed_tasks)
    else:
        assert case.intake.utility_availability == {"electricity": True, "water": True}
        assert "insurance preparation" in case.intake.household_recovery_needs
        assert "transportation" not in case.intake.household_recovery_needs
        historical_keys = {view.task.planning_key for view in current_task_views(plan)
                           if not view.applicable}
        assert "utilities" in historical_keys
        assert "transport" in historical_keys


def test_all_final_checkpoints_are_offline_and_have_no_verified_safety_claim(tmp_path, monkeypatch):
    from recovery.demo import list_scenarios, load_checkpoint
    import recovery.ai_planner as ai_planner

    def forbidden(*args, **kwargs):
        pytest.fail("synthetic journey attempted network/model access")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(ai_planner, "create_ai_draft_plan", forbidden)
    for scenario in list_scenarios():
        path = tmp_path / f"{scenario.scenario_id}.sqlite"
        selection = load_checkpoint(path, scenario.scenario_id, scenario.checkpoint_days[-1])
        repository = SQLiteRecoveryRepository(path)
        recorded = json.dumps(repository.list_journey_events(selection.case_id)).casefold()
        for unsupported_claim in ("home is safe", "household is safe", "recovery complete",
                                  "verified safe", "claim approved", "room booked"):
            assert unsupported_claim not in recorded


def test_resume_checkpoint_preserves_saved_progress_counts_and_timeline_without_writes(tmp_path):
    from recovery.demo import load_checkpoint, resume_checkpoint
    from recovery.dashboard import build_dashboard

    path = tmp_path / 'demo.sqlite'
    selection = load_checkpoint(path, 'rivera', 7)
    repo = SQLiteRecoveryRepository(path, clock=lambda: datetime.combine(selection.as_of, time(18), timezone.utc))
    plan = repo.get_active_plan(selection.case_id)
    task = next(task for task in plan.proposed_tasks if task.planning_key == 'safety')
    repo.update_task_status(plan.plan_id, task.task_id, TaskStatus.COMPLETED,
                            expected_progress_version=plan.progress_version)
    before_plan = repo.get_active_plan(selection.case_id)
    before_events = repo.list_journey_events(selection.case_id)
    before_view = build_dashboard(repo.get_case(selection.case_id), repo.get_recovery_records(selection.case_id),
                                  before_plan, before_events, as_of=selection.as_of)
    before_bytes = path.read_bytes()

    resumed = resume_checkpoint(path, str(selection.case_id))

    assert resumed == selection
    assert path.read_bytes() == before_bytes
    assert repo.get_active_plan(selection.case_id) == before_plan
    assert repo.list_journey_events(selection.case_id) == before_events
    after_view = build_dashboard(repo.get_case(resumed.case_id), repo.get_recovery_records(resumed.case_id),
                                 repo.get_active_plan(resumed.case_id), repo.list_journey_events(resumed.case_id),
                                 as_of=resumed.as_of)
    assert after_view == before_view
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM recovery_cases').fetchone()[0] == 1


def test_resume_retains_matching_pending_preview_and_clears_it_after_actual_approval(tmp_path):
    from recovery.demo import load_checkpoint, resume_checkpoint
    from recovery.reassessment import ReassessmentPreview

    path = tmp_path / 'demo.sqlite'
    selected = load_checkpoint(path, 'bennett', 7)
    before_bytes = path.read_bytes()
    matching = resume_checkpoint(path, selected.case_id)
    assert matching == selected
    assert path.read_bytes() == before_bytes
    repo = SQLiteRecoveryRepository(path, clock=lambda: datetime.combine(selected.as_of, time(18), timezone.utc))
    records = repo.get_recovery_records(selected.case_id)
    repo.approve_reassessment(ReassessmentPreview.model_validate_json(matching.pending_revision_json),
                              explicitly_approved=True, expected_records_version=records.version)
    after_approval_events = repo.list_journey_events(selected.case_id)
    after_approval_bytes = path.read_bytes()

    resumed = resume_checkpoint(path, selected.case_id)

    assert resumed.case_id == selected.case_id
    assert resumed.pending_revision_json is None
    assert resumed.pending_change_description is None
    assert 'transportation' in repo.get_case(selected.case_id).intake.household_recovery_needs
    assert repo.list_journey_events(selected.case_id) == after_approval_events
    assert path.read_bytes() == after_approval_bytes


@pytest.mark.parametrize('change', ['task', 'records', 'danger'])
def test_resume_drops_proposal_stale_against_current_case_plan_or_records(tmp_path, change):
    from recovery.demo import load_checkpoint, resume_checkpoint

    path = tmp_path / 'demo.sqlite'
    selected = load_checkpoint(path, 'bennett', 7)
    repo = SQLiteRecoveryRepository(path)
    if change == 'task':
        plan = repo.get_active_plan(selected.case_id)
        repo.update_task_status(plan.plan_id, plan.proposed_tasks[0].task_id, TaskStatus.IN_PROGRESS,
                                expected_progress_version=plan.progress_version)
    elif change == 'records':
        records = repo.get_recovery_records(selected.case_id)
        records.household.adults = 2
        repo.save_recovery_records(records, expected_version=records.version, explicitly_confirmed=True)
    else:
        repo.report_immediate_danger(selected.case_id)
    before_bytes = path.read_bytes()

    resumed = resume_checkpoint(path, selected.case_id)

    assert resumed.pending_revision_json is None
    assert resumed.pending_change_description is None
    assert resumed.immediate_danger is (change == 'danger')
    assert path.read_bytes() == before_bytes


def test_resume_recomputes_persisted_danger_and_never_clears_it(tmp_path):
    from recovery.demo import load_checkpoint, resume_checkpoint

    path = tmp_path / 'demo.sqlite'
    final = load_checkpoint(path, 'lewis', 30)
    assert resume_checkpoint(path, final.case_id).immediate_danger is True
    earlier = load_checkpoint(path, 'rivera', 3)
    repo = SQLiteRecoveryRepository(path)
    repo.report_immediate_danger(earlier.case_id)
    before = path.read_bytes()
    resumed = resume_checkpoint(path, earlier.case_id)
    assert resumed.immediate_danger is True
    assert repo.get_case(earlier.case_id).intake.immediate_danger is True
    assert path.read_bytes() == before


def test_resume_missing_invalid_or_legacy_case_is_graceful_and_never_creates_storage(tmp_path):
    from recovery.demo import load_checkpoint, resume_checkpoint

    absent = tmp_path / 'absent.sqlite'
    with pytest.raises(ValueError):
        resume_checkpoint(absent, uuid4())
    assert not absent.exists()
    path = tmp_path / 'demo.sqlite'
    selected = load_checkpoint(path, 'rivera', 1)
    for case_id in ('not-a-uuid', uuid4()):
        with pytest.raises(ValueError):
            resume_checkpoint(path, case_id)
    legacy_path = tmp_path / 'legacy.sqlite'
    SQLiteRecoveryRepository(legacy_path)
    before = legacy_path.read_bytes()
    with pytest.raises(ValueError):
        resume_checkpoint(legacy_path, selected.case_id)
    assert legacy_path.read_bytes() == before


@pytest.mark.parametrize('corruption', ['json', 'case_id', 'scenario', 'as_of', 'cursor'])
def test_resume_rejects_invalid_replay_metadata_without_writing(tmp_path, corruption):
    from recovery.demo import load_checkpoint, resume_checkpoint

    path = tmp_path / 'demo.sqlite'
    selected = load_checkpoint(path, 'rivera', 3)
    with sqlite3.connect(path) as connection:
        raw = connection.execute('SELECT selection_json FROM recovery_demo_selections WHERE case_id=?',
                                  (str(selected.case_id),)).fetchone()[0]
        payload = json.loads(raw)
        if corruption == 'case_id':
            payload['case_id'] = str(uuid4())
        elif corruption == 'scenario':
            payload['scenario_id'] = 'not-a-scenario'
        elif corruption == 'as_of':
            payload['as_of'] = '2030-01-01'
        elif corruption == 'cursor':
            payload['previous_checkpoint_event_cursor'] = 999999
        corrupted = 'invalid json' if corruption == 'json' else json.dumps(payload)
        connection.execute('UPDATE recovery_demo_selections SET selection_json=? WHERE case_id=?',
                            (corrupted, str(selected.case_id)))
    before = path.read_bytes()
    with pytest.raises(ValueError):
        resume_checkpoint(path, selected.case_id)
    assert path.read_bytes() == before
