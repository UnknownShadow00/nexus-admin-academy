"""Authoring validation, learner views, and deterministic V2 interaction grading."""

from __future__ import annotations

import copy
import json
import random
import re
from datetime import datetime, timezone

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.orm import Session

from app.models.certification import CertificationModule, LessonV2Meta
from app.models.v2_evidence import V2EvidenceRecord, V2EvidenceRequirement
from app.models.v2_interaction import INTERACTION_TYPES, V2InteractionAttempt, V2InteractionDefinition
from app.services.v2_progress_service import record_trusted_evidence


class InteractionValidationError(ValueError):
    """Invalid authoring or learner response, with a safe public message."""


class InteractionUnavailable(ValueError):
    """An interaction is outside the requested published module."""


class InteractionStale(ValueError):
    """The displayed definition is no longer the published version."""


MAX_TYPED_ANSWER_LENGTH = 500
MAX_INTERACTION_RESPONSE_LENGTH = 4096


def _require_response_fits(response: dict) -> None:
    if len(json.dumps(response)) > MAX_INTERACTION_RESPONSE_LENGTH:
        raise InteractionValidationError("authored answer IDs exceed the submission size limit")


def _nonempty(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InteractionValidationError(f"{field} must be nonempty text")
    return value.strip()


def _choices(config: dict, *, field: str = "choices") -> list[dict]:
    choices = config.get(field)
    if not isinstance(choices, list) or len(choices) < 2:
        raise InteractionValidationError(f"{field} needs at least two choices")
    ids = []
    for choice in choices:
        if not isinstance(choice, dict):
            raise InteractionValidationError(f"{field} entries must be objects")
        ids.append(_nonempty(choice.get("id"), f"{field}.id"))
        _nonempty(choice.get("label"), f"{field}.label")
    if len(set(ids)) != len(ids):
        raise InteractionValidationError(f"{field} IDs must be unique")
    return choices


def validate_definition(doc: dict) -> dict:
    """Reject broken or ambiguous authoring before a definition is published."""
    if not isinstance(doc, dict):
        raise InteractionValidationError("interaction must be an object")
    key = _nonempty(doc.get("key"), "key")
    if len(key) > 160 or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", key):
        raise InteractionValidationError("key must be a stable lowercase identifier")
    version = doc.get("version")
    if type(version) is not int or version < 1:
        raise InteractionValidationError("version must be a positive integer")
    kind = doc.get("type")
    if kind not in INTERACTION_TYPES:
        raise InteractionValidationError("unknown interaction type")
    _nonempty(doc.get("module_key"), "module_key")
    if doc.get("lesson_key") is not None:
        _nonempty(doc["lesson_key"], "lesson_key")
    if len(_nonempty(doc.get("title"), "title")) > 200:
        raise InteractionValidationError("title must be 200 characters or fewer")
    _nonempty(doc.get("instructions"), "instructions")
    status = doc.get("status", "draft")
    if status not in {"draft", "published", "retired"}:
        raise InteractionValidationError("status must be draft, published, or retired")
    if type(doc.get("required", False)) is not bool:
        raise InteractionValidationError("required must be true or false")
    pass_percent = doc.get("pass_percent", 100)
    if type(pass_percent) is not int or not 1 <= pass_percent <= 100:
        raise InteractionValidationError("pass_percent must be 1 through 100")
    if type(doc.get("display_order", 0)) is not int:
        raise InteractionValidationError("display_order must be an integer")
    config = doc.get("config")
    if not isinstance(config, dict):
        raise InteractionValidationError("config must be an object")
    _nonempty(config.get("explanation"), "config.explanation")
    if type(config.get("reveal_correct", False)) is not bool:
        raise InteractionValidationError("config.reveal_correct must be true or false")
    if kind == "matching":
        pairs = config.get("pairs")
        if not isinstance(pairs, list) or len(pairs) < 2:
            raise InteractionValidationError("matching needs at least two pairs")
        left_ids, right_ids = [], []
        for pair in pairs:
            if not isinstance(pair, dict):
                raise InteractionValidationError("matching pairs must be objects")
            left_ids.append(_nonempty(pair.get("id"), "pair.id"))
            right_ids.append(_nonempty(pair.get("right_id"), "pair.right_id"))
            _nonempty(pair.get("left"), "pair.left")
            _nonempty(pair.get("right"), "pair.right")
        if len(set(left_ids)) != len(left_ids) or len(set(right_ids)) != len(right_ids):
            raise InteractionValidationError("matching IDs must be unique")
        _require_response_fits({"matches": {pair["id"]: pair["right_id"] for pair in pairs}})
    elif kind == "ordering":
        steps = config.get("steps")
        if not isinstance(steps, list) or len(steps) < 2:
            raise InteractionValidationError("ordering needs at least two steps")
        ids = []
        for step in steps:
            if not isinstance(step, dict):
                raise InteractionValidationError("ordering steps must be objects")
            ids.append(_nonempty(step.get("id"), "step.id"))
            _nonempty(step.get("text"), "step.text")
        if len(set(ids)) != len(ids):
            raise InteractionValidationError("ordering step IDs must be unique")
        _require_response_fits({"order": ids})
    elif kind == "typed_answer":
        _nonempty(config.get("question"), "config.question")
        answers = config.get("accepted_answers")
        if not isinstance(answers, list) or not answers:
            raise InteractionValidationError("typed answer needs accepted answers")
        for answer in answers:
            _nonempty(answer, "accepted answer")
            if len(" ".join(answer.strip().split())) > MAX_TYPED_ANSWER_LENGTH:
                raise InteractionValidationError("accepted answer exceeds the typed answer length limit")
            _require_response_fits({"answer": " ".join(answer.strip().split())})
        if type(config.get("case_sensitive", False)) is not bool:
            raise InteractionValidationError("case_sensitive must be true or false")
    else:
        choices = _choices(config)
        correct = _nonempty(config.get("correct_choice_id"), "correct_choice_id")
        if correct not in {choice["id"] for choice in choices}:
            raise InteractionValidationError("correct choice must exist")
        for choice in choices:
            _require_response_fits({"choice_id": choice["id"]})
        if kind == "image_identification":
            image_url = _nonempty(config.get("image_url"), "image_url")
            if not image_url.startswith("/v2-interactions/") or ".." in image_url:
                raise InteractionValidationError("image_url must use a local interaction asset")
            _nonempty(config.get("image_alt"), "image_alt")
            _nonempty(config.get("question"), "question")
        elif kind == "command_output":
            for field in ("command", "output", "question"):
                _nonempty(config.get(field), field)
        elif kind == "safe_action":
            _nonempty(config.get("scenario"), "scenario")
            if type(config.get("safety_critical", False)) is not bool:
                raise InteractionValidationError("safety_critical must be true or false")
    return doc


def _public_content(definition: V2InteractionDefinition) -> dict:
    config = definition.config
    kind = definition.interaction_type
    if kind == "matching":
        left = [{"id": pair["id"], "text": pair["left"]} for pair in config["pairs"]]
        right = [{"id": pair["right_id"], "text": pair["right"]} for pair in config["pairs"]]
        random.SystemRandom().shuffle(right)
        return {"left": left, "right": right}
    if kind == "ordering":
        steps = [{"id": step["id"], "text": step["text"]} for step in config["steps"]]
        random.SystemRandom().shuffle(steps)
        return {"steps": steps}
    if kind == "typed_answer":
        return {"question": config["question"]}
    content = {"choices": [{"id": choice["id"], "label": choice["label"]} for choice in config["choices"]]}
    if kind == "image_identification":
        content.update(image_url=config["image_url"], image_alt=config["image_alt"], question=config["question"])
    elif kind == "command_output":
        content.update(command=config["command"], output=config["output"], question=config["question"])
    else:
        content.update(scenario=config["scenario"], safety_critical=config.get("safety_critical", False))
    return content


def _definition_view(definition: V2InteractionDefinition, lesson_key: str | None = None) -> dict:
    return {
        "key": definition.interaction_key, "version": definition.version,
        "version_id": definition.id,
        "type": definition.interaction_type, "title": definition.title,
        "instructions": definition.instructions, "required": definition.required,
        "lesson_key": lesson_key,
        "content": _public_content(definition),
    }


def _published(db: Session, module_key: str, interaction_key: str | None = None, lesson_key: str | None = None):
    query = db.query(V2InteractionDefinition).join(CertificationModule).outerjoin(
        LessonV2Meta, V2InteractionDefinition.lesson_id == LessonV2Meta.id,
    ).filter(
        CertificationModule.module_key == module_key,
        CertificationModule.active.is_(True),
        V2InteractionDefinition.status == "published",
        or_(
            V2InteractionDefinition.lesson_id.is_(None),
            LessonV2Meta.status.in_(("ready", "published")),
        ),
    )
    if interaction_key is not None:
        query = query.filter(V2InteractionDefinition.interaction_key == interaction_key)
    if lesson_key is not None:
        query = query.filter(
            LessonV2Meta.lesson_key == lesson_key,
        )
    return query.order_by(V2InteractionDefinition.display_order, V2InteractionDefinition.id).all()


def lock_interaction_module(db: Session, module_key: str) -> None:
    """Serialize publication and submissions for a V2 module until commit."""
    if db.get_bind().dialect.name == "sqlite":
        # SQLite ignores FOR UPDATE. A no-op write takes its transaction-wide
        # writer lock before reading the published interaction version.
        matched = db.execute(text(
            "UPDATE certification_modules SET id = id WHERE module_key = :key AND active = 1"
        ), {"key": module_key}).rowcount
        if not matched:
            raise InteractionUnavailable("This interaction module is not available.")
    else:
        module_id = db.query(CertificationModule.id).filter_by(
            module_key=module_key, active=True,
        ).with_for_update().scalar()
        if module_id is None:
            raise InteractionUnavailable("This interaction module is not available.")


def interaction_list(db: Session, student_id: int, module_key: str, lesson_key: str | None = None) -> list[dict]:
    definitions = _published(db, module_key, lesson_key=lesson_key)
    lesson_ids = {row.lesson_id for row in definitions if row.lesson_id is not None}
    lesson_keys = dict(db.query(LessonV2Meta.id, LessonV2Meta.lesson_key).filter(
        LessonV2Meta.id.in_(lesson_ids),
    ).all()) if lesson_ids else {}
    progress = _progress_summaries(db, student_id, definitions)
    return [{
        "interaction": _definition_view(row, lesson_keys.get(row.lesson_id)),
        "progress": progress[row.interaction_key],
    } for row in definitions]


def _attempt_view(row: V2InteractionAttempt) -> dict:
    return {
        "id": row.id, "version": row.version, "attempt_number": row.attempt_number,
        "response": row.response_snapshot, "result": row.result_snapshot,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


RECENT_ATTEMPT_LIMIT = 5


def _empty_progress() -> dict:
    return {
        "status": "not_started", "attempt_count": 0, "passed": False,
        "best_score": None, "best_result": None,
        "latest_attempt_at": None, "latest_result": None,
    }


def _progress_summaries(db: Session, student_id: int, definitions: list[V2InteractionDefinition]) -> dict[str, dict]:
    """One bounded-result query for all requested interactions, regardless of retries."""
    progress = {row.interaction_key: _empty_progress() for row in definitions}
    if not progress:
        return progress
    attempt = V2InteractionAttempt
    ranked = select(
        attempt.interaction_key.label("interaction_key"),
        attempt.score.label("score"),
        attempt.result_snapshot.label("result_snapshot"),
        attempt.created_at.label("created_at"),
        func.count().over(partition_by=attempt.interaction_key).label("attempt_count"),
        func.max(case((attempt.passed.is_(True), 1), else_=0)).over(
            partition_by=attempt.interaction_key,
        ).label("passed_any"),
        func.row_number().over(
            partition_by=attempt.interaction_key,
            order_by=(attempt.score.desc(), attempt.attempt_number.asc()),
        ).label("best_rank"),
        func.row_number().over(
            partition_by=attempt.interaction_key,
            order_by=attempt.attempt_number.desc(),
        ).label("latest_rank"),
    ).where(
        attempt.student_id == student_id,
        attempt.interaction_key.in_(progress),
    ).subquery()
    rows = db.execute(select(ranked).where(or_(
        ranked.c.best_rank == 1, ranked.c.latest_rank == 1,
    ))).mappings()
    for row in rows:
        item = progress[row["interaction_key"]]
        item["attempt_count"] = row["attempt_count"]
        item["passed"] = bool(row["passed_any"])
        item["status"] = "passed" if item["passed"] else "in_progress"
        if row["best_rank"] == 1:
            item["best_score"] = row["score"]
            item["best_result"] = row["result_snapshot"]
        if row["latest_rank"] == 1:
            item["latest_attempt_at"] = row["created_at"].isoformat()
            item["latest_result"] = row["result_snapshot"]
    required_keys = {row.interaction_key for row in definitions if row.required}
    if required_keys:
        satisfied_keys = {
            key for (key,) in db.query(V2EvidenceRequirement.ref_key).join(
                V2EvidenceRecord, V2EvidenceRecord.requirement_id == V2EvidenceRequirement.id,
            ).filter(
                V2EvidenceRequirement.module_id == definitions[0].module_id,
                V2EvidenceRequirement.evidence_type == "interaction",
                V2EvidenceRequirement.ref_key.in_(required_keys),
                V2EvidenceRequirement.active.is_(True),
                V2EvidenceRequirement.is_required.is_(True),
                V2EvidenceRecord.student_id == student_id,
            )
        }
        for key in required_keys:
            item = progress[key]
            item["passed"] = key in satisfied_keys
            item["status"] = "passed" if item["passed"] else "in_progress" if item["attempt_count"] else "not_started"
    return progress


def _progress(db: Session, student_id: int, definition: V2InteractionDefinition) -> dict:
    key = definition.interaction_key
    progress = _progress_summaries(db, student_id, [definition])[key]
    recent = db.query(V2InteractionAttempt).filter_by(
        student_id=student_id, interaction_key=key,
    ).order_by(V2InteractionAttempt.attempt_number.desc()).limit(RECENT_ATTEMPT_LIMIT).all()
    progress["recent_attempts"] = [_attempt_view(row) for row in recent]
    return progress


def interaction_view(db: Session, student_id: int, module_key: str, key: str) -> dict:
    definitions = _published(db, module_key, interaction_key=key)
    if len(definitions) != 1:
        raise InteractionUnavailable("This interaction is not available.")
    row = definitions[0]
    return {
        "interaction": _definition_view(
            row, db.get(LessonV2Meta, row.lesson_id).lesson_key if row.lesson_id else None,
        ),
        "progress": _progress(db, student_id, row),
    }


def _response_keys(response: dict, expected: str) -> None:
    if not isinstance(response, dict) or set(response) != {expected}:
        raise InteractionValidationError("Response contains invalid fields")


def _normalized(value: str, *, case_sensitive: bool) -> str:
    text = " ".join(value.strip().split())
    return text if case_sensitive else text.casefold()


def _grade(definition: V2InteractionDefinition, response: dict) -> tuple[int, bool, dict]:
    config = definition.config
    kind = definition.interaction_type
    correct_answer = None
    if kind == "matching":
        _response_keys(response, "matches")
        matches = response["matches"]
        expected = {pair["id"]: pair["right_id"] for pair in config["pairs"]}
        if not isinstance(matches, dict) or set(matches) != set(expected) or any(type(value) is not str for value in matches.values()) or len(set(matches.values())) != len(matches) or not set(matches.values()) <= set(expected.values()):
            raise InteractionValidationError("Select one unique match for each item")
        score = round(100 * sum(matches[left] == right for left, right in expected.items()) / len(expected))
        correct_answer = [f"{pair['left']} → {pair['right']}" for pair in config["pairs"]]
    elif kind == "ordering":
        _response_keys(response, "order")
        order = response["order"]
        expected = [step["id"] for step in config["steps"]]
        if not isinstance(order, list) or len(order) != len(expected) or any(type(item) is not str for item in order) or set(order) != set(expected):
            raise InteractionValidationError("Order every step exactly once")
        score = round(100 * sum(given == correct for given, correct in zip(order, expected)) / len(expected))
        correct_answer = [step["text"] for step in config["steps"]]
    elif kind == "typed_answer":
        _response_keys(response, "answer")
        answer = response["answer"]
        if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_TYPED_ANSWER_LENGTH:
            raise InteractionValidationError("Enter a short answer")
        case_sensitive = config.get("case_sensitive", False)
        accepted = {_normalized(item, case_sensitive=case_sensitive) for item in config["accepted_answers"]}
        score = 100 if _normalized(answer, case_sensitive=case_sensitive) in accepted else 0
        correct_answer = config["accepted_answers"][0]
    else:
        _response_keys(response, "choice_id")
        choice = response["choice_id"]
        choice_ids = {item["id"] for item in config["choices"]}
        if type(choice) is not str or choice not in choice_ids:
            raise InteractionValidationError("Choose one of the available answers")
        score = 100 if choice == config["correct_choice_id"] else 0
        correct_answer = next(item["label"] for item in config["choices"] if item["id"] == config["correct_choice_id"])
    passed = score >= definition.pass_percent
    correct = score == 100
    result = {
        "passed": passed, "correct": correct, "score": score,
        "feedback": ("Correct. " if correct else "Passed with some mistakes. " if passed else "Not quite. ") + config["explanation"],
        "correct_answer": correct_answer if config.get("reveal_correct", False) else None,
        "next_action": "Return to the module for your next step" if passed else "Try again",
    }
    return score, passed, result


def submit_interaction(db: Session, student_id: int, module_key: str, key: str, version_id: int, response: dict) -> dict:
    lock_interaction_module(db, module_key)
    definitions = _published(db, module_key, interaction_key=key)
    if len(definitions) != 1:
        raise InteractionUnavailable("This interaction is not available.")
    definition = definitions[0]
    if definition.id != version_id:
        raise InteractionStale("This interaction changed. Reload it before submitting your answer.")
    score, passed, result = _grade(definition, response)
    attempt_number = (db.query(func.max(V2InteractionAttempt.attempt_number)).filter_by(student_id=student_id, interaction_key=key).scalar() or 0) + 1
    attempt = V2InteractionAttempt(
        student_id=student_id, definition_id=definition.id,
        interaction_key=key, version=definition.version,
        attempt_number=attempt_number,
        definition_snapshot={
            "key": key, "version": definition.version, "type": definition.interaction_type,
            "title": definition.title, "instructions": definition.instructions,
            "module_key": module_key, "config": copy.deepcopy(definition.config),
            "pass_percent": definition.pass_percent, "required": definition.required,
        },
        response_snapshot=copy.deepcopy(response), result_snapshot=copy.deepcopy(result),
        score=score, passed=passed, created_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    db.flush()
    if passed and definition.required:
        requirement = db.query(V2EvidenceRequirement).filter_by(
            module_id=definition.module_id, evidence_type="interaction", ref_key=key,
            active=True, is_required=True,
        ).one_or_none()
        if requirement is None:
            raise InteractionValidationError("Required interaction evidence is not configured")
        record_trusted_evidence(db, student_id=student_id, requirement_id=requirement.id, source_ref=f"v2-interaction-attempt:{attempt.id}")
    db.commit()
    return {
        "interaction": _definition_view(
            definition, db.get(LessonV2Meta, definition.lesson_id).lesson_key if definition.lesson_id else None,
        ),
        "progress": _progress(db, student_id, definition),
        "submission_result": {"attempt_id": attempt.id, **result},
    }
