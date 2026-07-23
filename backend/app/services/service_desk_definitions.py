"""Scenario definition validation, canonicalization, and idempotent publication."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.schemas.service_desk import ScenarioDefinition


_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "service_desk"
_HIDDEN_FIELD_NAMES = {
    "root_cause",
    "expected_action_sequence",
    "hidden_rubric",
    "critical_event_definitions",
    "critical_failure_definitions",
    "instructor_notes",
    "correct_answer",
    "correct_account_id",
    "validation_secret",
}


class ScenarioDefinitionError(ValueError):
    pass


def canonical_definition(definition: ScenarioDefinition | dict) -> dict:
    value = definition.model_dump(mode="json") if isinstance(definition, ScenarioDefinition) else definition
    # Normalize unordered sets before JSON serialization. Pydantic models use a
    # set for supported modes, and a hash must never depend on process hash
    # randomization or set iteration order.
    def normalize(item):
        if isinstance(item, set):
            return sorted(normalize(value) for value in item)
        if isinstance(item, dict):
            return {str(key): normalize(value) for key, value in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(value) for value in item]
        return item

    # JSON round-trip gives every database backend the same primitive payload.
    return json.loads(json.dumps(normalize(value), sort_keys=True, separators=(",", ":")))


def definition_hash(definition: ScenarioDefinition | dict) -> str:
    canonical = canonical_definition(definition)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _find_hidden_key(value, path: str = "") -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            child = f"{path}.{key}" if path else str(key)
            if key in _HIDDEN_FIELD_NAMES:
                return child
            found = _find_hidden_key(nested, child)
            if found:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _find_hidden_key(nested, f"{path}[{index}]")
            if found:
                return found
    return None


def validate_scenario_definition(raw_definition: dict | ScenarioDefinition) -> ScenarioDefinition:
    try:
        definition = (
            raw_definition
            if isinstance(raw_definition, ScenarioDefinition)
            else ScenarioDefinition.model_validate(raw_definition)
        )
    except ValidationError as exc:
        raise ScenarioDefinitionError(str(exc)) from exc

    hidden_in_student_facts = _find_hidden_key(definition.student_facts)
    if hidden_in_student_facts:
        raise ScenarioDefinitionError(
            f"Student facts contain hidden field '{hidden_in_student_facts}'"
        )
    if "critical_failure" in definition.student_visible_state_fields:
        raise ScenarioDefinitionError("Critical failure state cannot be student-visible")
    return definition


def validation_report(raw_definition: dict | ScenarioDefinition) -> dict:
    try:
        definition = validate_scenario_definition(raw_definition)
    except ScenarioDefinitionError as exc:
        return {"valid": False, "errors": [str(exc)]}
    return {
        "valid": True,
        "stable_key": definition.stable_key,
        "version": definition.version,
        "definition_hash": definition_hash(definition),
        "action_count": len(definition.actions),
        "supported_modes": sorted(mode.value for mode in definition.supported_modes),
    }


def load_definition_file(stable_key: str) -> ScenarioDefinition:
    path = _DATA_DIR / f"{stable_key}.json"
    if not path.is_file():
        raise ScenarioDefinitionError(f"Scenario definition file does not exist: {stable_key}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioDefinitionError(f"Scenario definition is not valid JSON: {stable_key}") from exc
    return validate_scenario_definition(raw)


def publish_definition(
    db: Session,
    raw_definition: dict | ScenarioDefinition,
    *,
    published_by: str,
) -> ServiceDeskScenarioVersion:
    """Create a published immutable version or return the matching version.

    A version number is never overwritten. A changed definition must use a new
    version number, preserving every historical attempt's scenario facts.
    """
    definition = validate_scenario_definition(raw_definition)
    # Publication is stricter than shape validation: every immutable published
    # version must have an executable, deterministic completion path.
    from app.services.service_desk_health import run_definition_health

    health = run_definition_health(definition)
    if not health["valid"]:
        raise ScenarioDefinitionError(
            "Scenario cannot be published without a valid completion path: "
            + str(health.get("error", "health validation failed"))
        )
    canonical = canonical_definition(definition)
    checksum = definition_hash(definition)
    scenario = (
        db.query(ServiceDeskScenario)
        .filter(ServiceDeskScenario.stable_key == definition.stable_key)
        .first()
    )
    if scenario is None:
        scenario = ServiceDeskScenario(
            stable_key=definition.stable_key,
            title=definition.title,
            description=definition.description,
            category=definition.category,
            difficulty=definition.difficulty,
            status="active",
            created_by=published_by,
        )
        db.add(scenario)
        db.flush()

    existing = (
        db.query(ServiceDeskScenarioVersion)
        .filter(
            ServiceDeskScenarioVersion.scenario_id == scenario.id,
            ServiceDeskScenarioVersion.version_number == definition.version,
        )
        .first()
    )
    if existing:
        if existing.definition_hash != checksum:
            raise ScenarioDefinitionError(
                "Published scenario versions are immutable; publish a new version number."
            )
        return existing

    version = ServiceDeskScenarioVersion(
        scenario_id=scenario.id,
        version_number=definition.version,
        definition_json=canonical,
        definition_hash=checksum,
        validation_status="valid",
        status="published",
        published_at=datetime.now(timezone.utc),
        published_by=published_by,
    )
    db.add(version)
    db.flush()
    return version


def seed_service_desk_scenarios(db: Session) -> dict:
    """Idempotently publish reviewed Phase 0 definitions; never touch attempts."""
    definition = load_definition_file("locked_user_account")
    version = publish_definition(db, definition, published_by="seed")
    return {"published": 1, "scenario_id": version.scenario_id, "version_id": version.id}


def published_definition(version: ServiceDeskScenarioVersion) -> ScenarioDefinition:
    if version.status != "published" or version.validation_status != "valid":
        raise ScenarioDefinitionError("Scenario version is not published and valid")
    return validate_scenario_definition(version.definition_json)
