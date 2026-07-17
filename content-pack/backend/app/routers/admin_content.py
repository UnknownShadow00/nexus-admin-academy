import logging
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.ai_usage_log import AIUsageLog
from app.models.capstone import CapstoneRun, CapstoneTemplate
from app.models.command_reference import CommandReference
from app.models.evidence import EvidenceArtifact
from app.models.incident import Incident, IncidentParticipant, IncidentTicket, RCASubmission, RootCause
from app.models.lab import LabRun, LabTemplate
from app.models.learning import Lesson, Module
from app.models.progression import MethodologyFramework, PromotionGate, Role
from app.models.quiz import Quiz, QuizAttempt
from app.models.resource import Resource
from app.models.student import Student
from app.models.ticket import Ticket
from app.schemas.resource import ResourceCreateRequest
from app.services.admin_auth import verify_admin
from app.services.ai_service import ai_health_test
from app.utils.responses import ok

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_admin)])
logger = logging.getLogger(__name__)



@router.post("/resources")
def create_resource(payload: ResourceCreateRequest, db: Session = Depends(get_db)):
    resource = Resource(
        title=payload.title,
        url=str(payload.url),
        resource_type=payload.resource_type,
        week_number=payload.week_number,
        category=payload.category,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return ok({"resource_id": resource.id})

@router.delete("/resources/{resource_id}")
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    db.delete(resource)
    db.commit()
    return ok({"deleted": True})

@router.get("/ai-test")
async def ai_test(db: Session = Depends(get_db)):
    try:
        result = await ai_health_test(db, user_id=0)
        return {"success": True, **result}
    except HTTPException as exc:
        return {"success": False, "error": exc.detail}
    except Exception as exc:
        logger.exception("ai_test_failed")
        return {"success": False, "error": str(exc)}

@router.get("/ai-usage")
def get_ai_usage_stats(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    daily_cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    monthly_cutoff = now - timedelta(days=30)

    daily = db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0)).filter(AIUsageLog.created_at > daily_cutoff).scalar() or 0
    monthly = db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0)).filter(AIUsageLog.created_at > monthly_cutoff).scalar() or 0
    total = db.query(func.coalesce(func.sum(AIUsageLog.cost_estimate), 0)).scalar() or 0

    breakdown_rows = (
        db.query(
            AIUsageLog.feature.label("feature"),
            func.count(AIUsageLog.id).label("call_count"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AIUsageLog.cost_estimate), 0).label("total_cost"),
            func.coalesce(func.avg(AIUsageLog.cost_estimate), 0).label("avg_cost_per_call"),
        )
        .group_by(AIUsageLog.feature)
        .order_by(func.sum(AIUsageLog.cost_estimate).desc())
        .all()
    )

    recent = db.query(AIUsageLog).order_by(AIUsageLog.created_at.desc()).limit(20).all()

    return ok(
        {
            "summary": {
                "daily_cost": float(Decimal(str(daily))),
                "monthly_cost": float(Decimal(str(monthly))),
                "total_cost": float(Decimal(str(total))),
            },
            "breakdown": [
                {
                    "feature": row.feature,
                    "calls": int(row.call_count),
                    "tokens": int(row.total_tokens or 0),
                    "cost": float(Decimal(str(row.total_cost or 0))),
                    "avg_per_call": float(Decimal(str(row.avg_cost_per_call or 0))),
                }
                for row in breakdown_rows
            ],
            "recent_calls": [
                {
                    "feature": row.feature,
                    "model": row.model,
                    "tokens": row.total_tokens,
                    "cost": float(Decimal(str(row.cost_estimate))),
                    "timestamp": row.created_at.isoformat() if row.created_at else None,
                }
                for row in recent
            ],
        }
    )

@router.get("/modules")
def list_modules(db: Session = Depends(get_db)):
    rows = db.query(Module).order_by(Module.module_order.asc().nullslast(), Module.id.asc()).all()
    return ok(
        [
            {
                "id": row.id,
                "code": row.code,
                "title": row.title,
                "description": row.description,
                "target_role": row.target_role,
                "difficulty_band": row.difficulty_band,
                "estimated_hours": row.estimated_hours,
                "prerequisite_module_id": row.prerequisite_module_id,
                "unlock_threshold": row.unlock_threshold,
                "module_order": row.module_order,
                "active": row.active,
            }
            for row in rows
        ]
    )

@router.post("/modules")
def create_module(payload: dict, db: Session = Depends(get_db)):
    row = Module(
        code=payload.get("code"),
        title=payload.get("title"),
        description=payload.get("description"),
        target_role=payload.get("target_role"),
        difficulty_band=payload.get("difficulty_band"),
        estimated_hours=payload.get("estimated_hours"),
        prerequisite_module_id=payload.get("prerequisite_module_id"),
        unlock_threshold=payload.get("unlock_threshold", 70),
        module_order=payload.get("module_order"),
        active=payload.get("active", True),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"module_id": row.id})

@router.put("/modules/{module_id}")
def update_module(module_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(Module).filter(Module.id == module_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Module not found")
    for field in [
        "code",
        "title",
        "description",
        "target_role",
        "difficulty_band",
        "estimated_hours",
        "prerequisite_module_id",
        "unlock_threshold",
        "module_order",
        "active",
    ]:
        if field in payload:
            setattr(row, field, payload[field])
    db.commit()
    return ok({"module_id": row.id})

@router.get("/lessons")
def list_lessons(module_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Lesson)
    if module_id is not None:
        q = q.filter(Lesson.module_id == module_id)
    rows = q.order_by(Lesson.module_id.asc(), Lesson.lesson_order.asc()).all()
    return ok(
        [
            {
                "id": row.id,
                "module_id": row.module_id,
                "title": row.title,
                "video_url": row.video_url,
                "summary": row.summary,
                "lesson_order": row.lesson_order,
                "outcomes": row.outcomes,
                "estimated_minutes": row.estimated_minutes,
                "required_notes_template": row.required_notes_template,
                "status": row.status,
            }
            for row in rows
        ]
    )

@router.post("/lessons")
def create_lesson(payload: dict, db: Session = Depends(get_db)):
    row = Lesson(
        module_id=payload.get("module_id"),
        title=payload.get("title"),
        video_url=payload.get("video_url"),
        summary=payload.get("summary"),
        lesson_order=payload.get("lesson_order"),
        outcomes=payload.get("outcomes") or [],
        estimated_minutes=payload.get("estimated_minutes"),
        required_notes_template=payload.get("required_notes_template"),
        status=payload.get("status", "draft"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"lesson_id": row.id})

@router.put("/lessons/{lesson_id}")
def update_lesson(lesson_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")

    for field in [
        "module_id",
        "title",
        "video_url",
        "summary",
        "lesson_order",
        "outcomes",
        "estimated_minutes",
        "required_notes_template",
        "status",
    ]:
        if field in payload:
            setattr(row, field, payload[field])
    db.commit()
    return ok({"lesson_id": row.id})

@router.put("/tickets/{ticket_id}/answer-key")
def update_ticket_answer_key(ticket_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for field in [
        "root_cause",
        "root_cause_type",
        "required_checkpoints",
        "required_evidence",
        "scoring_anchors",
        "model_answer",
        "lesson_id",
        "domain_id",
    ]:
        if field in payload:
            setattr(row, field, payload[field])
    db.commit()
    return ok({"ticket_id": row.id})

@router.get("/evidence")
def list_evidence(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(EvidenceArtifact)
    if status:
        q = q.filter(EvidenceArtifact.validation_status == status)
    rows = q.order_by(EvidenceArtifact.uploaded_at.desc()).limit(200).all()
    return ok(
        [
            {
                "id": row.id,
                "submission_type": row.submission_type,
                "submission_id": row.submission_id,
                "artifact_type": row.artifact_type,
                "storage_key": row.storage_key,
                "validation_status": row.validation_status,
                "validation_notes": row.validation_notes,
                "uploaded_at": row.uploaded_at,
            }
            for row in rows
        ]
    )

@router.put("/evidence/{artifact_id}")
def review_evidence(artifact_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(EvidenceArtifact).filter(EvidenceArtifact.id == artifact_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if "validation_status" in payload:
        row.validation_status = payload["validation_status"]
    if "validation_notes" in payload:
        row.validation_notes = payload["validation_notes"]
    row.validated_at = datetime.utcnow()
    row.validated_by = payload.get("validated_by")
    db.commit()
    return ok({"artifact_id": row.id})

@router.get("/methodology/frameworks")
def list_methodology_frameworks(db: Session = Depends(get_db)):
    rows = db.query(MethodologyFramework).order_by(MethodologyFramework.id.asc()).all()
    return ok(
        [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "steps": row.steps,
                "required_for_role": row.required_for_role,
            }
            for row in rows
        ]
    )

@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    rows = db.query(Role).order_by(Role.rank_order.asc()).all()
    return ok([{"id": r.id, "name": r.name, "rank_order": r.rank_order, "description": r.description} for r in rows])

@router.get("/promotion-gates")
def list_promotion_gates(role_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(PromotionGate)
    if role_id:
        q = q.filter(PromotionGate.role_id == role_id)
    rows = q.order_by(PromotionGate.role_id.asc(), PromotionGate.id.asc()).all()
    return ok(
        [
            {
                "id": row.id,
                "role_id": row.role_id,
                "requirement_type": row.requirement_type,
                "requirement_config": row.requirement_config,
                "effective_from": row.effective_from,
                "effective_to": row.effective_to,
            }
            for row in rows
        ]
    )

@router.get("/labs/templates")
def list_lab_templates(lesson_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(LabTemplate)
    if lesson_id is not None:
        q = q.filter(LabTemplate.lesson_id == lesson_id)
    rows = q.order_by(LabTemplate.created_at.desc()).all()
    return ok(
        [
            {
                "id": r.id,
                "lesson_id": r.lesson_id,
                "title": r.title,
                "description": r.description,
                "lab_type": r.lab_type,
                "difficulty": r.difficulty,
                "week_number": r.week_number,
                "estimated_minutes": r.estimated_minutes,
                "is_published": r.is_published,
                "proxmox_template_vmid": r.proxmox_template_vmid,
                "environment_requirements": r.environment_requirements,
                "setup_instructions": r.setup_instructions,
                "break_script": r.break_script,
                "success_criteria": r.success_criteria,
                "required_evidence": r.required_evidence,
                "hints": r.hints,
                "model_solution": r.model_solution,
            }
            for r in rows
        ]
    )

@router.post("/labs/templates")
def create_lab_template(payload: dict, db: Session = Depends(get_db)):
    row = LabTemplate(
        lesson_id=payload.get("lesson_id"),
        title=payload.get("title"),
        description=payload.get("description"),
        lab_type=payload.get("lab_type"),
        difficulty=payload.get("difficulty", 1),
        week_number=payload.get("week_number", 1),
        estimated_minutes=payload.get("estimated_minutes"),
        is_published=payload.get("is_published", True),
        proxmox_template_vmid=payload.get("proxmox_template_vmid"),
        environment_requirements=payload.get("environment_requirements") or {},
        setup_instructions=payload.get("setup_instructions"),
        break_script=payload.get("break_script"),
        success_criteria=payload.get("success_criteria") or {},
        required_evidence=payload.get("required_evidence") or {},
        hints=payload.get("hints") or {},
        model_solution=payload.get("model_solution"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"lab_template_id": row.id})

@router.put("/labs/templates/{template_id}")
def update_lab_template(template_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(LabTemplate).filter(LabTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lab template not found")

    for field in [
        "lesson_id",
        "title",
        "description",
        "lab_type",
        "difficulty",
        "week_number",
        "estimated_minutes",
        "is_published",
        "proxmox_template_vmid",
        "environment_requirements",
        "setup_instructions",
        "break_script",
        "success_criteria",
        "required_evidence",
        "hints",
        "model_solution",
    ]:
        if field in payload:
            setattr(row, field, payload[field])

    db.commit()
    return ok({"lab_template_id": row.id})

@router.delete("/labs/templates/{template_id}")
def delete_lab_template(template_id: int, db: Session = Depends(get_db)):
    row = db.query(LabTemplate).filter(LabTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lab template not found")

    db.delete(row)
    db.commit()
    return ok({"deleted": True})

@router.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    rows = db.query(Incident).order_by(Incident.created_at.desc()).all()
    return ok(
        [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "incident_type": r.incident_type,
                "severity": r.severity,
                "impacted_services": r.impacted_services,
                "rca_required": r.rca_required,
                "root_cause_id": r.root_cause_id,
            }
            for r in rows
        ]
    )

@router.post("/incidents")
def create_incident(payload: dict, db: Session = Depends(get_db)):
    root_cause_id = payload.get("root_cause_id")
    if not root_cause_id and payload.get("root_cause"):
        rc = RootCause(
            service_area=payload["root_cause"].get("service_area"),
            cause_type=payload["root_cause"].get("cause_type"),
            description=payload["root_cause"].get("description"),
            break_method=payload["root_cause"].get("break_method"),
            fix_method=payload["root_cause"].get("fix_method"),
            validation_steps=payload["root_cause"].get("validation_steps"),
        )
        db.add(rc)
        db.flush()
        root_cause_id = rc.id

    row = Incident(
        title=payload.get("title"),
        description=payload.get("description"),
        incident_type=payload.get("incident_type"),
        impacted_services=payload.get("impacted_services") or [],
        root_cause_id=root_cause_id,
        start_time=payload.get("start_time"),
        end_time=payload.get("end_time"),
        rca_required=payload.get("rca_required", True),
        severity=payload.get("severity"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"incident_id": row.id})

@router.post("/incidents/{incident_id}/tickets")
def link_incident_ticket(incident_id: int, payload: dict, db: Session = Depends(get_db)):
    row = IncidentTicket(
        incident_id=incident_id,
        ticket_id=payload.get("ticket_id"),
        symptom_role=payload.get("symptom_role"),
        dependency_order=payload.get("dependency_order"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"incident_ticket_id": row.id})

@router.get("/capstones/templates")
def list_capstone_templates(db: Session = Depends(get_db)):
    rows = db.query(CapstoneTemplate).order_by(CapstoneTemplate.created_at.desc()).all()
    return ok(
        [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "role_level": r.role_level,
                "week_number": r.week_number,
                "is_published": r.is_published,
                "requirements": r.requirements,
                "deliverables": r.deliverables,
                "estimated_hours": r.estimated_hours,
                "rubric": r.rubric,
            }
            for r in rows
        ]
    )

@router.post("/capstones/templates")
def create_capstone_template(payload: dict, db: Session = Depends(get_db)):
    row = CapstoneTemplate(
        title=payload.get("title"),
        description=payload.get("description"),
        role_level=payload.get("role_level"),
        week_number=payload.get("week_number"),
        is_published=payload.get("is_published", False),
        requirements=payload.get("requirements") or {},
        deliverables=payload.get("deliverables") or {},
        estimated_hours=payload.get("estimated_hours"),
        rubric=payload.get("rubric") or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"capstone_template_id": row.id})

@router.put("/capstones/templates/{template_id}")
def update_capstone_template(template_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(CapstoneTemplate).filter(CapstoneTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Capstone template not found")

    for field in [
        "title",
        "description",
        "role_level",
        "week_number",
        "is_published",
        "requirements",
        "deliverables",
        "estimated_hours",
        "rubric",
    ]:
        if field in payload:
            setattr(row, field, payload[field])

    db.commit()
    db.refresh(row)
    return ok(
        {
            "capstone_template_id": row.id,
            "week_number": row.week_number,
            "is_published": row.is_published,
        }
    )

@router.delete("/capstones/templates/{template_id}")
def delete_capstone_template(template_id: int, db: Session = Depends(get_db)):
    row = db.query(CapstoneTemplate).filter(CapstoneTemplate.id == template_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Capstone template not found")

    db.delete(row)
    db.commit()
    return ok({"deleted": True})

@router.get("/ops/summary")
def operations_summary(db: Session = Depends(get_db)):
    return ok(
        {
            "lab_templates": db.query(func.count(LabTemplate.id)).scalar() or 0,
            "lab_runs": db.query(func.count(LabRun.id)).scalar() or 0,
            "incidents": db.query(func.count(Incident.id)).scalar() or 0,
            "incident_participants": db.query(func.count(IncidentParticipant.id)).scalar() or 0,
            "rca_submissions": db.query(func.count(RCASubmission.id)).scalar() or 0,
            "capstone_templates": db.query(func.count(CapstoneTemplate.id)).scalar() or 0,
            "capstone_runs": db.query(func.count(CapstoneRun.id)).scalar() or 0,
        }
    )

@router.get("/commands")
def list_commands(db: Session = Depends(get_db)):
    rows = db.query(CommandReference).order_by(CommandReference.command.asc()).all()
    return ok(
        [
            {
                "id": r.id,
                "command": r.command,
                "description": r.description,
                "syntax": r.syntax,
                "example": r.example,
                "category": r.category,
                "os": r.os,
            }
            for r in rows
        ]
    )

@router.post("/commands")
def create_command(payload: dict, db: Session = Depends(get_db)):
    row = CommandReference(
        command=payload.get("command"),
        description=payload.get("description"),
        syntax=payload.get("syntax"),
        example=payload.get("example"),
        category=payload.get("category"),
        os=payload.get("os", "windows"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"command_id": row.id})

@router.put("/commands/{command_id}")
def update_command(command_id: int, payload: dict, db: Session = Depends(get_db)):
    row = db.query(CommandReference).filter(CommandReference.id == command_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Command not found")
    for field in ["command", "description", "syntax", "example", "category", "os"]:
        if field in payload:
            setattr(row, field, payload[field])
    db.commit()
    return ok({"command_id": row.id})

@router.delete("/commands/{command_id}")
def delete_command(command_id: int, db: Session = Depends(get_db)):
    row = db.query(CommandReference).filter(CommandReference.id == command_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Command not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": True})


@router.get("/quiz-attempts/flagged")
def get_flagged_attempts(db: Session = Depends(get_db)):
    attempts = db.query(QuizAttempt).filter(QuizAttempt.time_per_question.isnot(None)).all()
    result = []
    for attempt in attempts:
        tpq = attempt.time_per_question or {}
        if not tpq:
            continue
        values = [value for value in tpq.values() if isinstance(value, (int, float))]
        if not values:
            continue
        avg = sum(values) / len(values)
        if avg >= 8:
            continue
        student = db.query(Student).filter(Student.id == attempt.student_id).first()
        quiz = db.query(Quiz).filter(Quiz.id == attempt.quiz_id).first()
        result.append(
            {
                "attempt_id": attempt.id,
                "student_id": attempt.student_id,
                "student_name": getattr(student, "full_name", None) or student.name if student else "Unknown",
                "quiz_id": attempt.quiz_id,
                "quiz_title": quiz.title if quiz else "Unknown",
                "score": attempt.score,
                "avg_seconds_per_question": round(avg, 1),
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
            }
        )
    result.sort(key=lambda x: x["avg_seconds_per_question"])
    return ok(result, total=len(result), page=1, per_page=len(result) or 1)


@router.delete("/vms/cleanup")
def cleanup_idle_vms(idle_hours: int = 2, db: Session = Depends(get_db)):
    from datetime import timezone
    from app.models.vm_assignment import VmAssignment
    from app.services import proxmox_service, guacamole_service

    cutoff = datetime.now(timezone.utc) - timedelta(hours=idle_hours)
    idle = (
        db.query(VmAssignment)
        .filter(VmAssignment.status != "destroyed", VmAssignment.created_at < cutoff)
        .all()
    )

    destroyed = []
    errors = []
    for assignment in idle:
        try:
            proxmox_service.destroy_vm(assignment.vmid)
        except Exception as exc:
            logger.warning("Cleanup: failed to destroy VM %s: %s", assignment.vmid, exc)
            assignment.status = "failed"
            errors.append({"vmid": assignment.vmid, "error": str(exc)})
            continue

        if assignment.guac_conn_id:
            try:
                guacamole_service.delete_connection(assignment.guac_conn_id)
            except Exception as exc:
                logger.warning("Cleanup: failed to delete connection %s: %s", assignment.guac_conn_id, exc)

        assignment.status = "destroyed"
        assignment.destroyed_at = datetime.now(timezone.utc)
        destroyed.append(assignment.vmid)

    db.commit()
    return ok({"destroyed": destroyed, "errors": errors})
