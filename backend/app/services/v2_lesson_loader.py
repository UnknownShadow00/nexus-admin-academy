"""Idempotent Markdown -> V2 lesson synchroniser (Phase 1B).

Walks ``backend/content/curriculum/**/*.md``. Each file is YAML frontmatter
(between ``---`` fences) + a Markdown body, per ``CURRICULUM_CONTENT_STANDARD``.
Upserts one ``lesson_v2_meta`` row per ``lesson_key`` and syncs its objective
and lesson-to-lesson relationship edges.

Guarantees:

* Re-running makes no duplicate rows (upsert on ``lesson_key``).
* Editing the Markdown body or frontmatter updates the row in place; an
  unchanged file is reported ``unchanged`` (body compared by SHA-256).
* Validation errors name the file and the offending field.
* The legacy ``lessons`` table is never written. A V2 lesson may optionally
  bind to a legacy lesson via ``legacy_lesson_id`` in frontmatter.
* No giant Python constants — the content lives in the ``.md`` files.
"""

from __future__ import annotations

import hashlib
import os

import yaml
from sqlalchemy.orm import Session

from app.models.certification import (
    IMPORTANCE_VALUES,
    LEARNING_RELATIONSHIP_VALUES,
    CertificationModule,
    CertificationObjective,
    CertificationVersion,
    LessonObjective,
    LessonRelationship,
    LessonV2Meta,
    normalize_importance,
)
from app.services.v2_content_loader import ContentValidationError, LoadSummary

_REQUIRED = ("lesson_key", "title", "certification_version", "domain", "module")


def _split_frontmatter(text: str, rel: str) -> tuple[dict, str]:
    if not text.lstrip().startswith("---"):
        raise ContentValidationError(f"{rel}: file must start with a '---' frontmatter block")
    stripped = text.lstrip()
    end = stripped.find("\n---", 3)
    if end == -1:
        raise ContentValidationError(f"{rel}: frontmatter block is not closed with '---'")
    fm_raw = stripped[3:end]
    body = stripped[end + 4 :].lstrip("\n")
    try:
        meta = yaml.safe_load(fm_raw) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - exercised via bad-file test
        raise ContentValidationError(f"{rel}: frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise ContentValidationError(f"{rel}: frontmatter must be a YAML mapping")
    return meta, body


def _validate(meta: dict, rel: str) -> dict:
    for key in _REQUIRED:
        if not str(meta.get(key) or "").strip():
            raise ContentValidationError(f"{rel}: field '{key}' is required")

    importance = normalize_importance(meta.get("importance"))
    if importance is None or importance not in IMPORTANCE_VALUES:
        raise ContentValidationError(
            f"{rel}: field 'importance' must be one of {sorted(IMPORTANCE_VALUES)} "
            f"(got {meta.get('importance')!r})"
        )

    relationship = str(meta.get("learning_relationship") or "").strip().lower()
    if relationship not in LEARNING_RELATIONSHIP_VALUES:
        raise ContentValidationError(
            f"{rel}: field 'learning_relationship' must be one of "
            f"{sorted(LEARNING_RELATIONSHIP_VALUES)} (got {meta.get('learning_relationship')!r})"
        )

    for edge_field in ("builds_on", "review_of"):
        value = meta.get(edge_field)
        if value is not None and not isinstance(value, list):
            raise ContentValidationError(f"{rel}: field '{edge_field}' must be a list of lesson_keys")

    objectives = meta.get("objectives")
    if objectives is not None and not isinstance(objectives, list):
        raise ContentValidationError(f"{rel}: field 'objectives' must be a list of objective codes")

    return {"importance": importance, "learning_relationship": relationship}


def load_lessons(
    db: Session, curriculum_dir: str, *, summary: LoadSummary | None = None
) -> LoadSummary:
    summary = summary or LoadSummary()

    md_files: list[str] = []
    for root, _dirs, files in os.walk(curriculum_dir):
        for name in sorted(files):
            if name.endswith(".md"):
                md_files.append(os.path.join(root, name))
    md_files.sort()

    # Pass 1: upsert every lesson + its objective links.
    pending_edges: list[tuple[str, str, list[str], list[str]]] = []
    for path in md_files:
        rel = os.path.relpath(path, curriculum_dir)
        with open(path, "r", encoding="utf-8") as handle:
            meta, body = _split_frontmatter(handle.read(), rel)
        norm = _validate(meta, rel)

        version = (
            db.query(CertificationVersion)
            .filter(CertificationVersion.version_key == str(meta["certification_version"]))
            .one_or_none()
        )
        if version is None:
            raise ContentValidationError(
                f"{rel}: certification_version '{meta['certification_version']}' is not loaded"
            )
        module = (
            db.query(CertificationModule)
            .filter(CertificationModule.module_key == str(meta["module"]))
            .one_or_none()
        )
        if module is None:
            raise ContentValidationError(f"{rel}: module '{meta['module']}' is not loaded")
        if module.certification_version_id != version.id:
            raise ContentValidationError(
                f"{rel}: module '{meta['module']}' belongs to a different certification version"
            )

        objective_ids: list[int] = []
        for code in meta.get("objectives") or []:
            obj = (
                db.query(CertificationObjective)
                .filter(
                    CertificationObjective.certification_version_id == version.id,
                    CertificationObjective.objective_code == str(code),
                )
                .one_or_none()
            )
            if obj is None:
                raise ContentValidationError(
                    f"{rel}: objective '{code}' does not exist in "
                    f"{meta['certification_version']}"
                )
            objective_ids.append(obj.id)

        legacy_lesson_id = meta.get("legacy_lesson_id")
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        fields = {
            "lesson_id": int(legacy_lesson_id) if legacy_lesson_id else None,
            "certification_version_id": version.id,
            "certification_module_id": module.id,
            "domain_key": str(meta["domain"]),
            "title": str(meta["title"]),
            "summary": meta.get("summary"),
            "importance": norm["importance"],
            "learning_relationship": norm["learning_relationship"],
            "estimated_minutes": _as_int(meta.get("estimated_minutes")),
            "status": str(meta.get("status") or "draft"),
            "content_path": rel.replace(os.sep, "/"),
            "content_body": body,
            "content_hash": content_hash,
            "source_name": meta.get("source_name"),
            "source_url": meta.get("source_url"),
        }
        lesson_key = str(meta["lesson_key"])
        row = (
            db.query(LessonV2Meta)
            .filter(LessonV2Meta.lesson_key == lesson_key)
            .one_or_none()
        )
        if row is None:
            row = LessonV2Meta(lesson_key=lesson_key, **fields)
            db.add(row)
            db.flush()
            summary.record("lesson", "created")
        else:
            summary.record("lesson", "updated" if _apply(row, fields) else "unchanged")

        _sync_lesson_objectives(db, row.id, objective_ids, summary)
        pending_edges.append(
            (
                rel,
                lesson_key,
                [str(k) for k in (meta.get("builds_on") or [])],
                [str(k) for k in (meta.get("review_of") or [])],
            )
        )

    db.flush()

    # Pass 2: relationship edges (targets may be defined in any file).
    key_to_id = {
        row.lesson_key: row.id
        for row in db.query(LessonV2Meta).filter(LessonV2Meta.lesson_key.isnot(None))
    }
    for rel, lesson_key, builds_on, review_of in pending_edges:
        from_id = key_to_id[lesson_key]
        desired: set[tuple[int, str]] = set()
        for edge_type, targets in (("builds_on", builds_on), ("review_of", review_of)):
            for target_key in targets:
                if target_key not in key_to_id:
                    raise ContentValidationError(
                        f"{rel}: '{edge_type}' references unknown lesson_key '{target_key}'"
                    )
                if key_to_id[target_key] == from_id:
                    raise ContentValidationError(
                        f"{rel}: '{edge_type}' cannot reference the lesson itself"
                    )
                desired.add((key_to_id[target_key], edge_type))
        _sync_lesson_relationships(db, from_id, desired, summary)

    db.flush()
    return summary


def _sync_lesson_objectives(db, lesson_meta_id: int, objective_ids: list[int], summary) -> None:
    want = set(objective_ids)
    have = {
        r.objective_id
        for r in db.query(LessonObjective).filter(
            LessonObjective.lesson_v2_meta_id == lesson_meta_id
        )
    }
    for oid in want - have:
        db.add(LessonObjective(lesson_v2_meta_id=lesson_meta_id, objective_id=oid))
        summary.record("lesson_objective", "created")
    for oid in have - want:
        db.query(LessonObjective).filter(
            LessonObjective.lesson_v2_meta_id == lesson_meta_id,
            LessonObjective.objective_id == oid,
        ).delete()
        summary.record("lesson_objective", "updated")


def _sync_lesson_relationships(db, from_id: int, desired: set, summary) -> None:
    have = {
        (r.to_lesson_meta_id, r.relationship_type)
        for r in db.query(LessonRelationship).filter(
            LessonRelationship.from_lesson_meta_id == from_id
        )
    }
    for to_id, edge_type in desired - have:
        db.add(
            LessonRelationship(
                from_lesson_meta_id=from_id,
                to_lesson_meta_id=to_id,
                relationship_type=edge_type,
            )
        )
        summary.record("lesson_relationship", "created")
    for to_id, edge_type in have - desired:
        db.query(LessonRelationship).filter(
            LessonRelationship.from_lesson_meta_id == from_id,
            LessonRelationship.to_lesson_meta_id == to_id,
            LessonRelationship.relationship_type == edge_type,
        ).delete()
        summary.record("lesson_relationship", "updated")


def _apply(row, fields: dict) -> bool:
    changed = False
    for key, value in fields.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    return changed


def _as_int(value):
    if value is None or value == "":
        return None
    return int(value)
