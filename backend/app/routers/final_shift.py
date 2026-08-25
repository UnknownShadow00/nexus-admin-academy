"""Phase 4C.3 Final Support Shift — a small, purpose-built controller for the
Week 23/24 incident-queue exercise. It does not introduce a second general
grading engine: scoring logic lives in app/services/final_shift_grading.py
and follows the same "recompute from stored definition + logged actions"
approach as service_desk_grading.compute_grade. Ownership is always resolved
from the authenticated student, never from a client-supplied run id, so one
student can never read or mutate another's attempt.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lab import LabRun, LabTemplate
from app.models.student import Student
from app.schemas.final_shift import (
    FinalShiftHandoffRequest,
    IncidentActionRequest,
)
from app.services.activity_service import log_activity, mark_student_active
from app.services.auth_service import get_current_student
from app.services.final_shift_grading import compute_final_shift_grade
from app.services.progression_service import require_week_reached
from app.utils.responses import ok

router = APIRouter(prefix="/api/final-shift", tags=["final-shift"])

FINAL_SHIFT_VERSION = "4c3"


def _get_case_lab(db: Session, lab_id: int) -> LabTemplate:
    lab = db.query(LabTemplate).filter(LabTemplate.id == lab_id, LabTemplate.is_published.is_(True)).first()
    if not lab or lab.lab_type != "structured_final_shift":
        raise HTTPException(status_code=404, detail="Final shift not found")
    return lab


def _case(lab: LabTemplate) -> dict:
    criteria = lab.success_criteria or {}
    case = criteria.get("final_shift")
    if not case:
        raise HTTPException(status_code=500, detail="Final shift is not configured")
    return {"final_shift": case, "lab_id": lab.id}


def _incidents_by_key(case: dict) -> dict[str, dict]:
    return {incident["key"]: incident for incident in case["final_shift"]["incidents"]}


def _student_safe_incident(incident: dict, state: dict) -> dict:
    return {
        "key": incident["key"],
        "requester": incident["requester"],
        "reported_at": incident["reported_at"],
        "complaint": incident["complaint"],
        "impact_clue": incident["impact_clue"],
        "skill_area": incident["skill_area"],
        "panels": incident["panels"],
        "required_inspections": incident["required_inspections"],
        "diagnosis_options": incident["diagnosis"]["options"],
        "actions": [{"id": action["id"], "label": action["label"]} for action in incident["actions"]],
        "requires_user_update": incident["requires_user_update"],
        "requires_escalation": incident["requires_escalation"],
        "state": {
            "inspected_panel_ids": state.get("inspected_panel_ids", []),
            "diagnosis_answer": state.get("diagnosis_answer"),
            "action_choice": state.get("action_choice"),
            "unsafe_action_attempted": bool(state.get("unsafe_action_attempted")),
            "documentation": state.get("documentation", {}),
            "status": state.get("status", "not_started"),
            "verification": state.get("revealed_verification"),
        },
    }


def _latest_run(db: Session, lab_id: int, student_id: int) -> LabRun | None:
    return (
        db.query(LabRun)
        .filter(LabRun.lab_template_id == lab_id, LabRun.student_id == student_id)
        .order_by(LabRun.created_at.desc(), LabRun.id.desc())
        .first()
    )
_EMPTY_FEEDBACK = {"final_shift_version": FINAL_SHIFT_VERSION, "queue_order": [], "incidents": {}, "handoff": {}}


def _active_run(db: Session, lab_id: int, student_id: int) -> LabRun | None:
    """The run to act on: the latest one, unless it was already submitted (a
    submitted run is history; further actions require starting a fresh one)."""
    run = _latest_run(db, lab_id, student_id)
    if run is None or run.status == "submitted":
        return None
    return run


@router.get("/{lab_id}")
def get_final_shift(
    lab_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_case_lab(db, lab_id)
    require_week_reached(db, current_student, lab.week_number)
    case = _case(lab)
    run = _active_run(db, lab.id, current_student.id)
    feedback = (run.structured_feedback if run else None) or _EMPTY_FEEDBACK
    incidents = [
        _student_safe_incident(incident, (feedback.get("incidents") or {}).get(incident["key"], {}))
        for incident in case["final_shift"]["incidents"]
    ]
    return ok(
        {
            "lab_id": lab.id,
            "title": lab.title,
            "guidance_level": case["final_shift"]["guidance_level"],
            "queue_intro": case["final_shift"]["queue_intro"],
            "guidance_notes": case["final_shift"].get("guidance_notes", []),
            "handoff_fields": case["final_shift"]["handoff_fields"],
            "run_id": run.id if run else None,
            "status": run.status if run else "not_started",
            "queue_order": feedback.get("queue_order", []),
            "handoff": feedback.get("handoff", {}),
            "grading": feedback.get("grading"),
            "incidents": incidents,
        }
    )


@router.post("/{lab_id}/start")
def start_final_shift(
    lab_id: int,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_case_lab(db, lab_id)
    require_week_reached(db, current_student, lab.week_number)
    run = _active_run(db, lab.id, current_student.id)
    now = datetime.now(UTC)
    if run is None:
        run = LabRun(
            lab_template_id=lab.id,
            student_id=current_student.id,
            status="in_progress",
            started_at=now,
            structured_feedback=dict(_EMPTY_FEEDBACK, incidents={}, queue_order=[], handoff={}),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        mark_student_active(db, current_student.id)
        log_activity(db, current_student.id, "lab_started", lab.title, "Final shift started")
    return ok({"run_id": run.id, "status": run.status})


def _require_active_run(db: Session, lab: LabTemplate, student_id: int) -> LabRun:
    run = _active_run(db, lab.id, student_id)
    if run is None:
        raise HTTPException(status_code=400, detail="Start the final shift before working an incident")
    return run


@router.post("/{lab_id}/incidents/{incident_key}/open")
def open_incident(
    lab_id: int,
    incident_key: str,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_case_lab(db, lab_id)
    require_week_reached(db, current_student, lab.week_number)
    case = _case(lab)
    incidents = _incidents_by_key(case)
    if incident_key not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    run = _require_active_run(db, lab, current_student.id)
    feedback = dict(run.structured_feedback or _EMPTY_FEEDBACK)
    queue_order = list(feedback.get("queue_order", []))
    if incident_key not in queue_order:
        queue_order.append(incident_key)
        feedback["queue_order"] = queue_order
        run.structured_feedback = feedback
        db.commit()
    return ok({"queue_order": feedback.get("queue_order", [])})


@router.post("/{lab_id}/incidents/{incident_key}/attempt")
def attempt_incident(
    lab_id: int,
    incident_key: str,
    payload: IncidentActionRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_case_lab(db, lab_id)
    require_week_reached(db, current_student, lab.week_number)
    case = _case(lab)
    incidents = _incidents_by_key(case)
    incident = incidents.get(incident_key)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    run = _require_active_run(db, lab, current_student.id)
    feedback = dict(run.structured_feedback or _EMPTY_FEEDBACK)
    if incident_key not in feedback.get("queue_order", []):
        raise HTTPException(status_code=409, detail="Open this incident from the queue before working it")

    actions_by_id = {action["id"]: action for action in incident["actions"]}
    chosen_action = actions_by_id.get(payload.action_choice) if payload.action_choice else None
    unsafe_this_attempt = bool(chosen_action and not chosen_action["safe"])

    all_incidents_state = dict(feedback.get("incidents", {}))
    prior_state = dict(all_incidents_state.get(incident_key, {}))

    inspections_ok = set(incident["required_inspections"]).issubset(set(payload.inspected_panel_ids))
    diagnosis_ok = payload.diagnosis_answer == incident["diagnosis"]["correct"]
    action_ok = chosen_action is not None and chosen_action["safe"] and payload.action_choice == incident["correct_action_id"]
    ready = inspections_ok and diagnosis_ok and action_ok

    new_state = {
        "inspected_panel_ids": sorted(set(payload.inspected_panel_ids)),
        "diagnosis_answer": payload.diagnosis_answer,
        "action_choice": payload.action_choice,
        "unsafe_action_attempted": bool(prior_state.get("unsafe_action_attempted")) or unsafe_this_attempt,
        "documentation": {**prior_state.get("documentation", {}), **payload.documentation},
    }
    if ready:
        new_state["status"] = "escalated" if incident["requires_escalation"] else "resolved"
        new_state["revealed_verification"] = incident["verification"]
    else:
        new_state["status"] = "investigating"
        new_state["revealed_verification"] = None

    all_incidents_state[incident_key] = new_state
    feedback["incidents"] = all_incidents_state
    run.structured_feedback = feedback
    if run.started_at is None:
        run.started_at = datetime.now(UTC)
    db.commit()

    message = "The plan is verified. The after-state is confirmed below." if ready else (
        "That plan was not accepted. Unsafe actions never produce a simulated success — re-open the evidence and revise."
        if unsafe_this_attempt
        else "Not ready yet: inspect the remaining evidence or reconsider the diagnosis before choosing an action."
    )
    return ok({"ready": ready, "status": new_state["status"], "verification": new_state["revealed_verification"], "message": message})


@router.post("/{lab_id}/handoff")
def submit_handoff(
    lab_id: int,
    payload: FinalShiftHandoffRequest,
    db: Session = Depends(get_db),
    current_student: Student = Depends(get_current_student),
):
    lab = _get_case_lab(db, lab_id)
    require_week_reached(db, current_student, lab.week_number)
    case = _case(lab)
    run = _require_active_run(db, lab, current_student.id)
    feedback = dict(run.structured_feedback or _EMPTY_FEEDBACK)

    incident_states = feedback.get("incidents", {})
    incidents = case["final_shift"]["incidents"]
    unfinished = [
        incident["key"]
        for incident in incidents
        if incident_states.get(incident["key"], {}).get("status") not in {"resolved", "escalated"}
    ]
    if unfinished:
        raise HTTPException(
            status_code=409,
            detail=f"These incidents still need a verified resolution or escalation: {', '.join(unfinished)}",
        )

    feedback["handoff"] = {
        "resolved": payload.resolved.strip(),
        "escalated": payload.escalated.strip(),
        "watch_items": payload.watch_items.strip(),
    }
    feedback["final_shift_version"] = FINAL_SHIFT_VERSION
    grade = compute_final_shift_grade(case, feedback)
    feedback["grading"] = grade

    now = datetime.now(UTC)
    run.structured_feedback = feedback
    run.status = "submitted"
    run.submitted_at = now
    run.verified_at = now
    run.final_score = grade["overall_score"]
    db.commit()
    db.refresh(run)
    mark_student_active(db, current_student.id)
    log_activity(db, current_student.id, "lab_submitted", lab.title, "Final shift submitted")
    return ok({"run_id": run.id, "status": run.status, "grading": grade})
