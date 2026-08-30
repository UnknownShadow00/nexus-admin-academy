"""Objective-coverage reporting for a V2 certification version (Phase 1B).

"Covered" = the objective has at least one V2 lesson mapped to it via
``lesson_objectives``. Multiple lessons mapping the same objective do not
inflate coverage (coverage counts DISTINCT objectives). Each certification
version is scored in isolation — objectives, lessons, and questions are all
filtered to the version.

This is the backend for a future admin coverage report; no UI is built here.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.certification import (
    CertificationObjective,
    CertificationVersion,
    LessonObjective,
    LessonV2Meta,
    QuestionV2Meta,
)


def _resolve_version(db: Session, version: "int | str") -> CertificationVersion:
    query = db.query(CertificationVersion)
    if isinstance(version, int):
        row = query.filter(CertificationVersion.id == version).one_or_none()
    else:
        row = query.filter(CertificationVersion.version_key == str(version)).one_or_none()
    if row is None:
        raise ValueError(f"certification version {version!r} not found")
    return row


def certification_version_coverage(db: Session, version: "int | str") -> dict:
    """Return lesson coverage (authoritative) plus question coverage (extra)."""
    ver = _resolve_version(db, version)

    objectives = (
        db.query(CertificationObjective)
        .filter(
            CertificationObjective.certification_version_id == ver.id,
            CertificationObjective.active.is_(True),
        )
        .order_by(CertificationObjective.display_order, CertificationObjective.objective_code)
        .all()
    )
    total = len(objectives)

    # DISTINCT objective_ids that have >= 1 lesson mapping — via lesson_v2_meta
    # rows that themselves belong to this version (defence in depth).
    lesson_covered_ids = {
        row[0]
        for row in db.query(func.distinct(LessonObjective.objective_id))
        .join(LessonV2Meta, LessonObjective.lesson_v2_meta_id == LessonV2Meta.id)
        .join(CertificationObjective, LessonObjective.objective_id == CertificationObjective.id)
        .filter(CertificationObjective.certification_version_id == ver.id)
        .all()
    }

    # Question coverage: an objective_code recorded on a question_v2_meta row
    # that is tied to this version (by resolved FK, else by version string).
    question_covered_codes = {
        row[0]
        for row in db.query(func.distinct(QuestionV2Meta.objective_code))
        .filter(
            QuestionV2Meta.objective_code.isnot(None),
            (QuestionV2Meta.certification_version_id == ver.id)
            | (QuestionV2Meta.certification_version == ver.version_key),
        )
        .all()
        if row[0]
    }

    covered = []
    uncovered = []
    for obj in objectives:
        entry = {
            "objective_code": obj.objective_code,
            "objective_text": obj.objective_text,
            "domain_key": obj.domain_key,
            "has_lesson": obj.id in lesson_covered_ids,
            "has_question": obj.objective_code in question_covered_codes,
        }
        (covered if entry["has_lesson"] else uncovered).append(entry)

    covered_count = len(covered)
    coverage_percent = round(100.0 * covered_count / total, 1) if total else 0.0

    by_domain: dict[str, dict] = {}
    for obj in objectives:
        bucket = by_domain.setdefault(
            obj.domain_key or "?", {"total": 0, "covered": 0}
        )
        bucket["total"] += 1
        if obj.id in lesson_covered_ids:
            bucket["covered"] += 1
    for bucket in by_domain.values():
        bucket["coverage_percent"] = (
            round(100.0 * bucket["covered"] / bucket["total"], 1) if bucket["total"] else 0.0
        )

    return {
        "certification_version": ver.version_key,
        "certification_version_id": ver.id,
        "total_objectives": total,
        "covered_objectives": covered_count,
        "uncovered_objectives": total - covered_count,
        "coverage_percent": coverage_percent,
        "question_covered_objectives": sum(
            1 for o in objectives if o.objective_code in question_covered_codes
        ),
        "uncovered": uncovered,
        "covered": covered,
        "by_domain": by_domain,
    }


def uncovered_objectives(db: Session, version: "int | str") -> list[dict]:
    """Convenience: just the objectives with no lesson mapping."""
    return certification_version_coverage(db, version)["uncovered"]
