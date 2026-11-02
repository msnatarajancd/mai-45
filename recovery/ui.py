import os
import sqlite3
from pathlib import Path
from uuid import UUID

import streamlit as st

from .assessment import RecoveryIntakeNotPermitted, start_recovery_case
from .database import SQLiteRecoveryRepository
from .demo_planner import create_demo_draft_plan
from .models import PlanStatus, RecoveryIntake, RecoveryPlan, TaskStatus


def get_recovery_database_path(
    database_path: str | Path | None = None,
) -> Path:
    configured_path = database_path or os.environ.get("READYRELIEF_DB_PATH")
    path = (
        Path(configured_path).expanduser()
        if configured_path
        else Path.home() / ".readyrelief" / "recovery_preview.sqlite3"
    ).resolve()

    shared_clone = Path(__file__).resolve().parents[1] / "mai-45"
    try:
        path.relative_to(shared_clone.resolve())
    except ValueError:
        return path
    raise ValueError("The preview database must be outside the mai-45 shared clone")


def _utility_value(selection: str) -> bool | None:
    return {"Available": True, "Unavailable": False, "Unknown": None}[selection]


def _render_emergency_controls() -> None:
    st.markdown("### Emergency assistance")
    call_column, alternative_column, danger_column = st.columns(3)
    with call_column:
        st.link_button("Call 911", "tel:911", use_container_width=True)
    with alternative_column:
        if st.button("I Can't Call 911", use_container_width=True):
            st.session_state["show_alternative_emergency_help"] = True
    with danger_column:
        if st.button("Report immediate danger", use_container_width=True):
            st.session_state["emergency_interrupt"] = True
            st.rerun()

    if st.session_state.get("show_alternative_emergency_help", False):
        st.warning(
            "This demo cannot contact responders. Text-to-911 availability varies "
            "by location; use an emergency contact option available where you are."
        )


def _render_emergency_interrupt() -> None:
    st.error(
        "Emergency handoff: routine recovery actions are paused. "
        "This demo has not contacted or dispatched emergency responders."
    )
    st.info(
        "Call 911 if you can. If you cannot, use an emergency contact option "
        "available where you are. Text-to-911 availability varies by location."
    )
    if st.button("Return to recovery demo", key="dismiss_emergency_interrupt"):
        st.session_state["emergency_interrupt"] = False
        st.rerun()
    st.stop()


def _set_page(page: str) -> None:
    st.session_state["recovery_page"] = page


def _render_welcome() -> None:
    st.title("ReadyRelief - Recovery Copilot")
    st.caption("SIMULATED DEMO | Local single-user preview; not a public service")
    st.write(
        "Recovery Copilot helps organize recovery needs and track progress. "
        "Do not enter real personal or sensitive information."
    )
    if st.button("Start Recovery Assessment", type="primary"):
        _set_page("assessment")
        st.rerun()
    if st.button("Resume Existing Recovery"):
        _set_page("resume")
        st.rerun()


def _render_assessment(repository: SQLiteRecoveryRepository) -> None:
    st.header("Recovery Assessment")
    with st.form("recovery_assessment"):
        disaster_type = st.selectbox(
            "Disaster type", ["Hurricane", "Flood", "Wildfire"]
        )
        housing_condition = st.selectbox(
            "Housing condition",
            ["Minor reported damage", "Major reported damage", "No damage reported"],
        )
        electricity = st.selectbox(
            "Electricity availability", ["Unknown", "Available", "Unavailable"]
        )
        water = st.selectbox(
            "Water availability", ["Unknown", "Available", "Unavailable"]
        )
        accommodation = st.selectbox(
            "Temporary accommodation status",
            ["Staying in temporary lodging", "Staying with others", "No lodging arranged"],
        )
        needs = st.multiselect(
            "Household recovery needs",
            [
                "Temporary housing",
                "Water and household supplies",
                "Transportation",
                "Damage documentation",
            ],
            default=["Temporary housing", "Water and household supplies"],
        )
        danger_selection = st.selectbox(
            "Immediate danger assessment",
            [
                "Choose an assessment",
                "No immediate danger reported",
                "Immediate danger reported",
            ],
        )
        submitted = st.form_submit_button("Continue")

    if not submitted:
        return

    danger_value = {
        "No immediate danger reported": False,
        "Immediate danger reported": True,
    }.get(danger_selection)
    intake = RecoveryIntake(
        disaster_type=disaster_type,
        housing_condition=housing_condition,
        utility_availability={
            "electricity": _utility_value(electricity),
            "water": _utility_value(water),
        },
        temporary_accommodation_status=accommodation,
        immediate_danger=danger_value,
        household_recovery_needs=needs,
    )
    try:
        case = start_recovery_case(intake, repository)
    except RecoveryIntakeNotPermitted as error:
        if error.assessment.outcome.value == "EMERGENCY_HANDOFF":
            st.session_state["emergency_interrupt"] = True
            st.rerun()
        st.error("Select an explicit danger assessment before continuing. No case was saved.")
        return
    except sqlite3.Error as error:
        st.error(f"The recovery case could not be saved: {error}")
        return

    st.session_state["case_id"] = str(case.case_id)
    _set_page("planning")
    st.rerun()


def _get_current_case(repository: SQLiteRecoveryRepository):
    case_id = st.session_state.get("case_id")
    if not case_id:
        return None
    try:
        return repository.get_case(UUID(case_id))
    except ValueError:
        return None


def _render_planning(repository: SQLiteRecoveryRepository) -> None:
    case = _get_current_case(repository)
    if case is None:
        st.error("Recovery case not found. Resume with a valid saved case ID.")
        if st.button("Return to welcome"):
            _set_page("welcome")
            st.rerun()
        return

    if case.intake.immediate_danger is True:
        st.session_state["emergency_interrupt"] = True
        st.rerun()
    if case.intake.immediate_danger is None:
        st.error("Planning is paused until immediate danger has been explicitly assessed.")
        return

    st.header("Draft Recovery Plan")
    st.code(str(case.case_id))
    from .ai_planner import AIPlanningError, create_ai_draft_plan
    from .llm_client import NebiusClient, PlanningClientError

    mode = st.radio("Initial planner", ["SIMULATED DEMO", "AI-assisted (experimental)"])
    st.caption(f"Planner: {mode}")
    st.info("Local simulated application. Plans require household review and explicit approval; not official guidance.")
    draft_key = f"draft_plan_json:{case.case_id}:{mode}"
    if mode == "AI-assisted (experimental)":
        st.warning("UNGROUNDED EXPERIMENTAL AI OUTPUT. No verified guidance is connected. Only general organization and review steps are permitted.")
        st.caption("Generating sends the fictional intake to Nebius. Do not use real personal or sensitive information.")
        if st.button("Generate AI Draft Plan"):
            st.session_state.pop(draft_key, None)
            try:
                with st.spinner("Generating a draft for review..."):
                    draft = create_ai_draft_plan(case, [], NebiusClient())
                latest_case = repository.get_case(case.case_id)
                if latest_case is not None and latest_case.intake.immediate_danger is True:
                    st.session_state["emergency_interrupt"] = True
                    st.rerun()
                if latest_case != case:
                    st.error("Recovery circumstances changed during generation. No draft was retained; review the current assessment before retrying.")
                else:
                    st.session_state[draft_key] = draft.model_dump_json()
            except PlanningClientError:
                st.error("AI client configuration is invalid. No draft was created; you may explicitly choose SIMULATED DEMO.")
            except RecoveryIntakeNotPermitted:
                st.error("Planning is paused until immediate danger has been assessed.")
            except AIPlanningError as error:
                st.error(str(error))
        if draft_key not in st.session_state:
            return
    try:
        if draft_key not in st.session_state:
            draft_plan = create_demo_draft_plan(case)
            st.session_state[draft_key] = draft_plan.model_dump_json()
        plan = RecoveryPlan.model_validate_json(st.session_state[draft_key])
    except RecoveryIntakeNotPermitted:
        st.error("Planning is paused until immediate danger has been assessed.")
        return

    if plan.planning_disclosure:
        st.warning(plan.planning_disclosure)
    for task in plan.proposed_tasks:
        with st.expander(f"{task.title} - {task.priority.value}"):
            st.write(task.description)
            st.write(f"**Priority:** {task.priority.value}")
            st.write(f"**Reason:** {task.reason_for_recommendation}")
            _render_task_evidence(task)

    saved_plan_id = str(plan.plan_id) if repository.get_plan(plan.plan_id) else None
    save_column, approve_column = st.columns(2)
    with save_column:
        if st.button("Save Draft Plan", disabled=saved_plan_id == str(plan.plan_id)):
            try:
                repository.save_draft_plan(plan)
                st.session_state[f"saved_draft_id:{case.case_id}"] = str(plan.plan_id)
                st.success("Draft saved. It is not active until explicitly approved.")
                st.rerun()
            except sqlite3.Error as error:
                st.error(f"The draft could not be saved: {error}")
    with approve_column:
        if st.button("Approve Recovery Plan", type="primary"):
            try:
                if saved_plan_id != str(plan.plan_id):
                    repository.save_draft_plan(plan)
                repository.approve_plan(plan.plan_id)
                st.session_state["initial_plan_notice"] = "Recovery plan saved and explicitly approved. It is now the active plan."
                _set_page("dashboard")
                st.rerun()
            except (sqlite3.Error, ValueError) as error:
                st.error(f"The plan could not be approved: {error}")


def _render_dashboard(repository: SQLiteRecoveryRepository) -> None:
    case = _get_current_case(repository)
    if case is None:
        st.error("Recovery case not found. Resume with a valid saved case ID.")
        return
    plan = repository.get_active_plan(case.case_id)
    st.header("Recovery Dashboard")
    approval_notice = st.session_state.pop("initial_plan_notice", None)
    if approval_notice:
        st.success(approval_notice)
    notice = st.session_state.pop("revision_notice", None)
    if notice:
        st.success(notice)
    st.write("Recovery case ID")
    st.code(str(case.case_id))
    if plan is None:
        st.info("There is no active plan for this recovery case.")
        if st.button("Create a Demo Draft Plan"):
            _set_page("planning")
            st.rerun()
        return

    st.write("Active recovery plan")
    st.code(str(plan.plan_id))
    st.caption("Planner: AI-assisted (experimental)" if plan.planning_disclosure else "Planner: SIMULATED DEMO (deterministic templates)")
    if plan.planning_disclosure:
        st.warning(plan.planning_disclosure)
    with st.expander("Previous approved plans (historical reference)"):
        for historical in repository.list_approved_plans(case.case_id):
            if historical.plan_id != plan.plan_id:
                st.write(f"Previous approved plan: {historical.plan_id}")
                for task in historical.proposed_tasks:
                    st.write(f"{task.title} - {task.status.value}")
    _render_reassessment(repository, case, plan)
    rendered_version_key = f"rendered_progress:{plan.plan_id}"
    rendered_version = st.session_state.get(rendered_version_key, plan.progress_version)
    for task in plan.proposed_tasks:
        with st.expander(f"{task.title} - {task.status.value}"):
            st.write(task.description)
            st.write(f"**Priority:** {task.priority.value}")
            st.write(f"**Reason:** {task.reason_for_recommendation}")
            _render_task_evidence(task)
            status_options = list(TaskStatus)
            current_index = status_options.index(task.status)
            form_key = f"task-status-form:{plan.plan_id}:{task.task_id}"
            with st.form(form_key):
                new_status = st.selectbox(
                    "Task status",
                    status_options,
                    index=current_index,
                    format_func=lambda status: status.value,
                    key=f"task-status:{plan.plan_id}:{task.task_id}:{plan.progress_version}",
                )
                submitted = st.form_submit_button("Save task status")
            if submitted:
                try:
                    repository.update_task_status(
                        plan.plan_id, task.task_id, new_status,
                        expected_progress_version=rendered_version,
                    )
                    st.session_state["task_update_notice"] = (
                        f"Saved {task.title} as {new_status.value}."
                    )
                    st.rerun()
                except (sqlite3.Error, ValueError) as error:
                    st.error(f"Task status could not be saved: {error}")

    st.session_state[rendered_version_key] = plan.progress_version
    notice = st.session_state.pop("task_update_notice", None)
    if notice:
        st.success(notice)


def _render_resume(repository: SQLiteRecoveryRepository) -> None:
    st.header("Resume Recovery")
    with st.form("resume_recovery"):
        case_id_text = st.text_input("Fictional recovery case ID")
        submitted = st.form_submit_button("Resume Recovery")
    if not submitted:
        return

    try:
        case_id = UUID(case_id_text.strip())
    except ValueError:
        st.error("Enter a valid case UUID.")
        return

    try:
        case = repository.get_case(case_id)
        if case is None:
            st.error("No recovery case was found for that ID.")
            return
        st.session_state["case_id"] = str(case.case_id)
        _set_page("dashboard" if repository.get_active_plan(case_id) else "planning")
        st.rerun()
    except sqlite3.Error as error:
        st.error(f"The recovery case could not be retrieved: {error}")


def render_recovery_copilot(
    database_path: str | Path | None = None,
) -> None:
    """Render the reusable Recovery Copilot preview inside a Streamlit app."""
    st.caption("SIMULATED DEMO | Local single-user preview; not official safety verification")
    _render_emergency_controls()
    if st.session_state.get("emergency_interrupt", False):
        # Emergency controls and handoff remain available even if persistence fails.
        for key in list(st.session_state):
            if key.startswith("reassessment_preview:"):
                del st.session_state[key]
        if st.session_state.get("case_id"):
            try:
                path = get_recovery_database_path(database_path)
                if path.exists():
                    SQLiteRecoveryRepository(path).report_immediate_danger(UUID(st.session_state["case_id"]))
            except (OSError, sqlite3.Error, ValueError):
                st.warning("The danger report could not be saved across sessions. Emergency assistance controls remain available.")
        _render_emergency_interrupt()

    try:
        resolved_database_path = get_recovery_database_path(database_path)
        resolved_database_path.parent.mkdir(parents=True, exist_ok=True)
        repository = SQLiteRecoveryRepository(resolved_database_path)
    except (OSError, sqlite3.Error, ValueError) as error:
        st.error(f"The local recovery database is unavailable: {error}")
        return

    page = st.session_state.get("recovery_page", "welcome")
    try:
        if page == "welcome":
            _render_welcome()
        elif page == "assessment":
            _render_assessment(repository)
        elif page == "planning":
            _render_planning(repository)
        elif page == "dashboard":
            _render_dashboard(repository)
        elif page == "resume":
            _render_resume(repository)
        else:
            st.session_state["recovery_page"] = "welcome"
            _render_welcome()
    except sqlite3.Error as error:
        st.error(f"A recovery database operation failed: {error}")

def _render_reassessment(repository, case, plan) -> None:
    from .reassessment import ReassessmentPreview, preview_reassessment
    from .assessment import RecoveryAssessmentOutcome

    with st.expander("Report changes / preview reassessment"):
        preview_key = f"reassessment_preview:{case.case_id}"
        st.caption("Review a proposed revision. The current plan stays active until you explicitly approve.")
        danger = st.selectbox("Current immediate danger assessment", [
            "Choose an assessment", "No immediate danger reported", "Immediate danger reported"],
            key=f"reassessment_danger:{plan.plan_id}")
        if danger == "Immediate danger reported":
            st.session_state.pop(preview_key, None)
            st.session_state["emergency_interrupt"] = True
            st.rerun()
        with st.form(f"reassessment:{plan.plan_id}"):
            disaster = st.text_input("Updated disaster type", value=case.intake.disaster_type)
            housing = st.text_input("Updated housing condition", value=case.intake.housing_condition)
            accommodation = st.text_input("Updated accommodation", value=case.intake.temporary_accommodation_status)
            utilities = {}
            choices = ["Unknown", "Available", "Unavailable"]
            for name in sorted(case.intake.utility_availability.keys() | {"electricity", "water"}):
                initial = {None: "Unknown", True: "Available", False: "Unavailable"}[case.intake.utility_availability.get(name)]
                utilities[name] = _utility_value(st.selectbox(
                    f"Updated {name} availability", choices, index=choices.index(initial)))
            needs = st.text_area("Updated household needs (one per line)", value="\n".join(case.intake.household_recovery_needs))
            submitted = st.form_submit_button("Preview proposed revision")
        if submitted:
            st.session_state.pop(preview_key, None)
            try:
                updated = RecoveryIntake(
                    disaster_type=disaster, housing_condition=housing,
                    temporary_accommodation_status=accommodation,
                    utility_availability=utilities,
                    household_recovery_needs=[n.strip() for n in needs.splitlines() if n.strip()],
                    immediate_danger={"No immediate danger reported": False,
                                      "Immediate danger reported": True}.get(danger),
                )
                preview = preview_reassessment(case, plan, updated)
            except ValueError as error:
                st.error(f"Reassessment could not be previewed: {error}")
                return
            if preview.outcome is RecoveryAssessmentOutcome.EMERGENCY_HANDOFF:
                st.session_state["emergency_interrupt"] = True
                st.rerun()
            if preview.outcome is RecoveryAssessmentOutcome.DANGER_NOT_ASSESSED:
                st.error("Explicitly assess current immediate danger before reassessment.")
                return
            st.session_state[preview_key] = preview.model_dump_json()
        if preview_key not in st.session_state:
            return
        preview = ReassessmentPreview.model_validate_json(st.session_state[preview_key])
        st.markdown("**Previous reported circumstances**")
        st.json(preview.previous_case.intake.model_dump(mode="json"))
        st.markdown("**Updated reported circumstances**")
        st.json(preview.updated_intake.model_dump(mode="json"))
        st.info("Proposed draft for review only. No revision has been saved or approved.")
        if not preview.changed_circumstances:
            st.write("No changed circumstances detected.")
        for change in preview.changed_circumstances:
            st.write(change.explanation)
        for label, recommendations in (
            ("Tasks remaining relevant", preview.relevant_tasks),
            ("New recommended tasks", preview.new_tasks),
            ("Tasks potentially no longer relevant", preview.potentially_irrelevant_tasks),
            ("Previously completed tasks", preview.completed_tasks),
        ):
            st.markdown(f"**{label}**")
            if not recommendations:
                st.write("None")
            for recommendation in recommendations:
                st.write(f"{recommendation.task.title} ({recommendation.task.status.value}): {recommendation.explanation}")

        if st.button("Keep Current Plan"):
            st.session_state.pop(preview_key, None)
            st.session_state["revision_notice"] = "Current plan kept. No revision was saved."
            st.rerun()
        if st.button("Approve Revised Recovery Plan", type="primary"):
            if danger != "No immediate danger reported":
                st.error("Explicitly assess current immediate danger before approval.")
                return
            try:
                repository.approve_reassessment(preview, explicitly_approved=True)
            except RecoveryIntakeNotPermitted as error:
                if error.assessment.outcome is RecoveryAssessmentOutcome.EMERGENCY_HANDOFF:
                    st.session_state["emergency_interrupt"] = True
                    st.rerun()
                st.error("Explicitly assess immediate danger before approval.")
            except (ValueError, sqlite3.Error) as error:
                st.error(f"Revision was not saved: {error}")
            else:
                st.session_state.pop(preview_key, None)
                st.session_state["revision_notice"] = "Revised recovery plan saved and approved. It is now the active plan."
                st.rerun()


def _render_task_evidence(task) -> None:
    if task.source_reference is None:
        st.caption("Evidence: no verified source reference; not verified official guidance.")
    else:
        st.caption(f"Evidence reference: {task.source_reference}. Source applicability and support require review; not official safety verification.")
