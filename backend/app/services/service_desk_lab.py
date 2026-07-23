"""Read models and audit helpers for the private Service Desk browser lab."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskAttemptGrade,
    ServiceDeskAuditLog,
    ServiceDeskKnowledgeArticle,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.services.service_desk_definitions import published_definition


def audit(db: Session, *, actor: str, action: str, target_type: str, target_id: str | int, details: dict | None = None) -> None:
    db.add(ServiceDeskAuditLog(actor=actor, action=action, target_type=target_type, target_id=str(target_id), details_json=details or {}))


def latest_versions(db: Session):
    rows = (
        db.query(ServiceDeskScenario, ServiceDeskScenarioVersion)
        .join(ServiceDeskScenarioVersion, ServiceDeskScenarioVersion.scenario_id == ServiceDeskScenario.id)
        .filter(ServiceDeskScenario.status == "active", ServiceDeskScenarioVersion.status == "published", ServiceDeskScenarioVersion.validation_status == "valid")
        .order_by(ServiceDeskScenario.stable_key, ServiceDeskScenarioVersion.version_number.desc())
        .all()
    )
    latest = {}
    for scenario, version in rows:
        latest.setdefault(scenario.id, (scenario, version))
    return list(latest.values())


def _assignment_map(db: Session, student_id: int) -> dict[int, ServiceDeskAssignment]:
    return {row.scenario_id: row for row in db.query(ServiceDeskAssignment).filter(ServiceDeskAssignment.student_id == student_id).all()}


def queue(db: Session, student: Student) -> list[dict]:
    assignments = _assignment_map(db, student.id)
    rows = []
    for scenario, version in latest_versions(db):
        definition = published_definition(version)
        assignment = assignments.get(scenario.id)
        attempts = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.student_id == student.id, ServiceDeskAttempt.scenario_version_id == version.id).order_by(ServiceDeskAttempt.id.desc()).all()
        active = next((item for item in attempts if item.status == "in_progress"), None)
        latest = attempts[0] if attempts else None
        state = "In Progress" if active else "Completed" if latest and latest.passed else "Assigned" if assignment else "Available"
        rows.append({
            "id": scenario.id, "stable_key": scenario.stable_key, "title": scenario.title,
            "ticket_number": definition.student_facts.get("ticket_number"),
            "requester": (definition.student_facts.get("requester") or {}).get("name", "New employee request"),
            "category": scenario.category, "difficulty": scenario.difficulty,
            "priority": definition.student_facts.get("priority", "Normal"), "status": state,
            "mode": active.mode if active else assignment.mode if assignment else "learning",
            "assignment_state": "Required" if assignment and assignment.is_required else "Assigned" if assignment else "Available",
            "attempt_id": active.id if active else None, "passed": bool(latest and latest.passed),
            "due_at": assignment.due_at.isoformat() if assignment and assignment.due_at else None,
        })
    return rows


def overview(db: Session, student: Student) -> dict:
    items = queue(db, student)
    attempts = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.student_id == student.id).order_by(ServiceDeskAttempt.id.desc()).all()
    grades = db.query(ServiceDeskAttemptGrade).join(ServiceDeskAttempt, ServiceDeskAttempt.id == ServiceDeskAttemptGrade.attempt_id).filter(ServiceDeskAttempt.student_id == student.id).all()
    latest = attempts[0] if attempts else None
    active = next((item for item in items if item["attempt_id"]), None)
    recommended = next((item for item in items if item["assignment_state"] == "Required" and not item["passed"]), None) or next((item for item in items if not item["passed"]), None)
    return {
        "active_attempt": active,
        "assigned_scenarios": [item for item in items if item["assignment_state"] != "Available"],
        "available_scenarios": [item for item in items if item["assignment_state"] == "Available"],
        "recommended": recommended,
        "recent_result": None if latest is None else {"attempt_id": latest.id, "score": latest.score, "passed": latest.passed, "mode": latest.mode},
        "scores": {"technical": round(sum(grade.overall_score for grade in grades) / len(grades)) if grades else 0, "process": round(sum(grade.overall_score for grade in grades) / len(grades)) if grades else 0, "documentation": round(sum(grade.overall_score for grade in grades) / len(grades)) if grades else 0},
        "current_mode": active["mode"] if active else "learning",
        "completion_count": len({attempt.scenario_version_id for attempt in attempts if attempt.passed}),
    }


def performance(db: Session, student: Student) -> dict:
    attempts = db.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.student_id == student.id).order_by(ServiceDeskAttempt.id.desc()).all()
    by_version: dict[int, list[ServiceDeskAttempt]] = {}
    for attempt in attempts:
        by_version.setdefault(attempt.scenario_version_id, []).append(attempt)
    rows = []
    for version_id, group in by_version.items():
        version = db.query(ServiceDeskScenarioVersion).filter(ServiceDeskScenarioVersion.id == version_id).one()
        definition = published_definition(version)
        latest = group[0]
        rows.append({"scenario": definition.title, "stable_key": definition.stable_key, "attempts": len(group), "latest_score": latest.score or 0, "best_score": max(item.score or 0 for item in group), "passed": bool(latest.passed), "completed": any(item.passed for item in group), "technical_score": latest.score or 0, "process_score": latest.score or 0, "documentation_score": latest.score or 0, "hints_used": 0, "critical_mistakes": 0, "skills": definition.skill_tags})
    return {"completed_scenarios": sum(1 for item in rows if item["completed"]), "attempt_count": len(attempts), "scenarios": rows}


def public_article(article: ServiceDeskKnowledgeArticle) -> dict:
    return {"id": article.id, "stable_id": article.stable_id, "title": article.title, "category": article.category, "content": article.content, "status": article.status, "skill_tags": article.skill_tags, "created_at": article.created_at.isoformat() if article.created_at else None, "updated_at": article.updated_at.isoformat() if article.updated_at else None}


DEFAULT_ARTICLES = [
    ("identity-verification-basics", "Identity verification basics", "Identity", "Verify an approved identity factor before changing access. Record only that verification was completed, not sensitive values.", ["identity_verification"]),
    ("unlocking-an-account", "Safely unlocking an account", "Identity", "Inspect the intended account after verification. Make the smallest approved change, then document the result.", ["account_lockout"]),
    ("password-reset-safety", "Password-reset best practices", "Identity", "Never request or record a password. Confirm the account, use the simulated reset action, and document the handoff.", ["password_reset"]),
    ("mfa-reset-safety", "MFA reset safety", "Identity", "Reset MFA only after verification and checking the selected account's MFA state.", ["mfa"]),
    ("bitlocker-recovery", "BitLocker recovery procedure", "Endpoint", "Verify the person and device before accessing a recovery key. Do not copy key material into ticket notes.", ["bitlocker"]),
    ("new-employee-checklist", "New employee onboarding checklist", "Onboarding", "Validate the approved request, use the correct account and group, assign the approved device, and document completion.", ["onboarding"]),
    ("resolution-notes", "Writing resolution notes", "Documentation", "State the verification, approved action, and outcome succinctly. Never include passwords, recovery keys, or secret answers.", ["documentation"]),
]


def seed_knowledge_articles(db: Session) -> int:
    created = 0
    for stable_id, title, category, content, tags in DEFAULT_ARTICLES:
        row = db.query(ServiceDeskKnowledgeArticle).filter(ServiceDeskKnowledgeArticle.stable_id == stable_id).first()
        if row is None:
            db.add(ServiceDeskKnowledgeArticle(stable_id=stable_id, title=title, category=category, content=content, status="published", skill_tags=tags))
            created += 1
    return created
