"""Explicit, validated loader for small V2 pilot interaction manifests."""

from __future__ import annotations

import os

import yaml
from sqlalchemy.orm import Session

from app.models.certification import CertificationModule, LessonV2Meta
from app.models.v2_evidence import V2EvidenceRequirement
from app.models.v2_interaction import V2InteractionDefinition
from app.services.v2_interaction_service import InteractionValidationError, validate_definition


DEFAULT_PILOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "content", "interactions", "pilot-v2-interactions.yaml",
)


def load_interactions(db: Session, path: str = DEFAULT_PILOT_PATH, *, commit: bool = False) -> dict:
    """Publish validated versions; existing authored versions are never rewritten."""
    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("interactions"), list):
        raise InteractionValidationError(f"{path}: interactions must be a list")
    docs = document["interactions"]
    keys = set()
    published = set()
    for index, doc in enumerate(docs):
        try:
            validate_definition(doc)
        except InteractionValidationError as exc:
            raise InteractionValidationError(f"{path}: interactions[{index}]: {exc}") from exc
        identity = (doc["key"], doc["version"])
        if identity in keys:
            raise InteractionValidationError(f"{path}: duplicate version {identity}")
        keys.add(identity)
        if doc.get("status", "draft") == "published":
            if doc["key"] in published:
                raise InteractionValidationError(f"{path}: multiple published versions of {doc['key']}")
            published.add(doc["key"])
    created = retired = unchanged = 0
    for doc in docs:
        module = db.query(CertificationModule).filter_by(module_key=doc["module_key"], active=True).one_or_none()
        if module is None:
            raise InteractionValidationError(f"{path}: module {doc['module_key']} is unavailable")
        other_module = db.query(V2InteractionDefinition).filter(
            V2InteractionDefinition.interaction_key == doc["key"],
            V2InteractionDefinition.module_id != module.id,
        ).first()
        if other_module is not None:
            raise InteractionValidationError(f"{path}: interaction {doc['key']} cannot move to another module")
        lesson = None
        if doc.get("lesson_key"):
            lesson = db.query(LessonV2Meta).filter_by(
                lesson_key=doc["lesson_key"], certification_module_id=module.id,
            ).one_or_none()
            if lesson is None or lesson.status not in {"ready", "published"}:
                raise InteractionValidationError(f"{path}: lesson {doc['lesson_key']} is unavailable")
        existing = db.query(V2InteractionDefinition).filter_by(interaction_key=doc["key"], version=doc["version"]).one_or_none()
        fixed = {
            "interaction_type": doc["type"], "module_id": module.id,
            "lesson_id": lesson.id if lesson else None, "title": doc["title"],
            "instructions": doc["instructions"], "config": doc["config"],
            "required": doc.get("required", False),
            "display_order": doc.get("display_order", 0),
            "pass_percent": doc.get("pass_percent", 100),
        }
        status = doc.get("status", "draft")
        if existing:
            if any(getattr(existing, field) != value for field, value in fixed.items()):
                raise InteractionValidationError(f"{path}: version {doc['key']} v{doc['version']} changed; author a new version")
            if existing.status == "retired" and status != "retired":
                raise InteractionValidationError(f"{path}: retired versions cannot be reopened")
            if existing.status != status:
                existing.status = status
            else:
                unchanged += 1
        else:
            existing = V2InteractionDefinition(
                interaction_key=doc["key"], version=doc["version"], status=status, **fixed,
            )
            db.add(existing)
            created += 1
        if status == "published":
            older = db.query(V2InteractionDefinition).filter(
                V2InteractionDefinition.interaction_key == doc["key"],
                V2InteractionDefinition.version != doc["version"],
                V2InteractionDefinition.status == "published",
            ).all()
            for old in older:
                old.status = "retired"
                retired += 1
            requirement = db.query(V2EvidenceRequirement).filter_by(
                module_id=module.id, evidence_type="interaction", ref_key=doc["key"],
            ).one_or_none()
            if requirement is None:
                requirement = V2EvidenceRequirement(
                    module_id=module.id, evidence_type="interaction", ref_key=doc["key"],
                )
                db.add(requirement)
            requirement.is_required = doc.get("required", False)
            requirement.active = True
        elif doc["key"] not in published and db.query(V2InteractionDefinition).filter_by(
            interaction_key=doc["key"], module_id=module.id, status="published",
        ).first() is None:
            requirement = db.query(V2EvidenceRequirement).filter_by(
                module_id=module.id, evidence_type="interaction", ref_key=doc["key"],
            ).one_or_none()
            if requirement:
                requirement.active = False
    db.flush()
    if commit:
        db.commit()
    return {"created": created, "retired": retired, "unchanged": unchanged}
