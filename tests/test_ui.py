import sqlite3
from pathlib import Path
from uuid import UUID

import pytest
from streamlit.testing.v1 import AppTest

from recovery.database import SQLiteRecoveryRepository
from recovery.models import PlanStatus, TaskStatus
from recovery.ui import get_recovery_database_path


def test_database_path_defaults_outside_shared_clone(tmp_path: Path) -> None:
    path = get_recovery_database_path(tmp_path / "preview.sqlite3")

    assert path == (tmp_path / "preview.sqlite3").resolve()


def test_database_path_rejects_shared_clone_location() -> None:
    shared_clone = Path(__file__).resolve().parents[1] / "mai-45"

    with pytest.raises(ValueError, match="outside the mai-45"):
        get_recovery_database_path(shared_clone / "preview.sqlite3")


def test_emergency_controls_are_visible_on_welcome_screen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_path = Path(__file__).resolve().parents[1] / "dev_recovery_preview.py"
    database_path = tmp_path / "preview.sqlite3"
    monkeypatch.setenv("READYRELIEF_DB_PATH", str(database_path))
    app = AppTest.from_file(str(app_path), default_timeout=10)
    app.run()

    assert "Call 911" in [button.label for button in app.get("link_button")]
    assert "I Can't Call 911" in [button.label for button in app.button]
    assert "Report immediate danger" in [button.label for button in app.button]
    assert "SIMULATED DEMO" in app.caption[0].value


def test_new_danger_interrupts_normal_ui_flow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_path = Path(__file__).resolve().parents[1] / "dev_recovery_preview.py"
    monkeypatch.setenv("READYRELIEF_DB_PATH", str(tmp_path / "preview.sqlite3"))
    app = AppTest.from_file(str(app_path), default_timeout=10)
    app.run()

    next(button for button in app.button if button.label == "Report immediate danger").click().run()

    assert any("routine recovery actions are paused" in item.value for item in app.error)
    assert any("has not contacted or dispatched" in item.value for item in app.error)
    assert "Call 911" in [button.label for button in app.get("link_button")]


@pytest.mark.parametrize(
    ("danger_selection", "expected_message"),
    [
        ("Choose an assessment", "Select an explicit danger assessment"),
        ("Immediate danger reported", "Emergency handoff"),
    ],
)
def test_assessment_danger_blocks_case_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    danger_selection: str,
    expected_message: str,
) -> None:
    app_path = Path(__file__).resolve().parents[1] / "dev_recovery_preview.py"
    database_path = tmp_path / "preview.sqlite3"
    monkeypatch.setenv("READYRELIEF_DB_PATH", str(database_path))
    app = AppTest.from_file(str(app_path), default_timeout=10).run()
    next(button for button in app.button if button.label == "Start Recovery Assessment").click().run()
    if danger_selection != "Choose an assessment":
        next(
            selectbox
            for selectbox in app.selectbox
            if selectbox.label == "Immediate danger assessment"
        ).select(danger_selection)
    next(button for button in app.button if button.label == "Continue").click().run()

    assert any(expected_message in item.value for item in app.error)
    with sqlite3.connect(database_path) as connection:
        case_count = connection.execute(
            "SELECT COUNT(*) FROM recovery_cases"
        ).fetchone()[0]
    assert case_count == 0


def test_alternative_emergency_control_explains_local_availability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_path = Path(__file__).resolve().parents[1] / "dev_recovery_preview.py"
    monkeypatch.setenv("READYRELIEF_DB_PATH", str(tmp_path / "preview.sqlite3"))
    app = AppTest.from_file(str(app_path), default_timeout=10)
    app.run()

    next(button for button in app.button if button.label == "I Can't Call 911").click().run()

    assert any(
        "Text-to-911 availability varies by location" in item.value
        for item in app.warning
    )


def test_ui_saves_draft_approves_updates_and_resumes_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_path = Path(__file__).resolve().parents[1] / "dev_recovery_preview.py"
    database_path = tmp_path / "preview.sqlite3"
    monkeypatch.setenv("READYRELIEF_DB_PATH", str(database_path))
    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    next(button for button in app.button if button.label == "Start Recovery Assessment").click().run()
    next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "Immediate danger assessment"
    ).select("No immediate danger reported")
    next(button for button in app.button if button.label == "Continue").click().run()

    assert any("Draft Recovery Plan" in item.value for item in app.header), [
        item.value for item in app.error
    ]
    with sqlite3.connect(database_path) as connection:
        case_id = UUID(
            connection.execute("SELECT case_id FROM recovery_cases").fetchone()[0]
        )
    next(button for button in app.button if button.label == "Save Draft Plan").click().run()

    repository = SQLiteRecoveryRepository(database_path)
    assert repository.get_active_plan(case_id) is None
    with sqlite3.connect(database_path) as connection:
        plan_id = UUID(
            connection.execute(
                "SELECT plan_id FROM recovery_plans WHERE case_id = ?",
                (str(case_id),),
            ).fetchone()[0]
        )
    assert repository.get_plan(plan_id).approval_status is PlanStatus.DRAFT

    next(button for button in app.button if button.label == "Approve Recovery Plan").click().run()
    active_plan = repository.get_active_plan(case_id)
    assert active_plan is not None
    assert active_plan.approval_status is PlanStatus.APPROVED

    first_task = active_plan.proposed_tasks[0]
    next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "Task status"
    ).select(TaskStatus.COMPLETED)
    next(button for button in app.button if button.label == "Save task status").click().run()

    resumed_app = AppTest.from_file(str(app_path), default_timeout=10).run()
    next(button for button in resumed_app.button if button.label == "Resume Existing Recovery").click().run()
    next(
        item
        for item in resumed_app.text_input
        if item.label == "Fictional recovery case ID"
    ).set_value(str(case_id))
    next(button for button in resumed_app.button if button.label == "Resume Recovery").click().run()

    resumed_repository = SQLiteRecoveryRepository(database_path)
    resumed_plan = resumed_repository.get_active_plan(case_id)
    assert resumed_plan is not None
    assert next(task for task in resumed_plan.proposed_tasks if task.task_id == first_task.task_id).status is TaskStatus.COMPLETED
    assert any("COMPLETED" in item.label for item in resumed_app.expander)

    next(
        button
        for button in resumed_app.button
        if button.label == "Report immediate danger"
    ).click().run()
    assert any("routine recovery actions are paused" in item.value for item in resumed_app.error)
    assert resumed_repository.get_active_plan(case_id).proposed_tasks[0].status is TaskStatus.COMPLETED