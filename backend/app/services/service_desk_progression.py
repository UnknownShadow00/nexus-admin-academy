from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.service_desk import (
    ServiceDeskAssignment,
    ServiceDeskAttempt,
    ServiceDeskScenario,
    ServiceDeskScenarioVersion,
)
from app.models.student import Student
from app.services.progression_service import derive_current_week


@dataclass(frozen=True)
class ServiceDeskPack:
    key: str
    name: str
    scenario_keys: tuple[str, ...]
    required_week: int
    required_prior_passes: int


# Pack order is the progression order. Keys intentionally point only to
# scenarios with complete simulation fixtures and server grading objectives.
SERVICE_DESK_PACKS = (
    ServiceDeskPack(
        key="starter-support",
        name="Starter Support",
        scenario_keys=("inc2405", "inc2404", "inc2403", "inc2502"),
        required_week=0,
        required_prior_passes=0,
    ),
    ServiceDeskPack(
        key="desktop-support",
        name="Desktop Support",
        scenario_keys=("inc2408", "inc2501", "inc2509", "inc2504"),
        required_week=3,
        required_prior_passes=2,
    ),
    ServiceDeskPack(
        key="accounts-access",
        name="Accounts & Access",
        scenario_keys=("inc2401", "inc2505", "inc2510", "inc2507"),
        required_week=6,
        required_prior_passes=2,
    ),
    ServiceDeskPack(
        key="networking",
        name="Networking",
        scenario_keys=("inc2406", "inc2407", "inc2503", "inc2402"),
        required_week=8,
        required_prior_passes=2,
    ),
    ServiceDeskPack(
        key="advanced-troubleshooting",
        name="Advanced Troubleshooting",
        scenario_keys=("inc2506", "inc2508"),
        required_week=10,
        required_prior_passes=3,
    ),
)

PACK_BY_SCENARIO = {
    scenario_key: pack
    for pack in SERVICE_DESK_PACKS
    for scenario_key in pack.scenario_keys
}
PACK_INDEX = {pack.key: index for index, pack in enumerate(SERVICE_DESK_PACKS)}


def difficulty_presentation(value: int | None) -> tuple[str, str]:
    level = max(1, min(3, int(value or 1)))
    label = {1: "Beginner", 2: "Intermediate", 3: "Advanced"}[level]
    return label, "★" * level


def _passed_scenario_keys(db: Session, student_id: int) -> set[str]:
    return {
        stable_key
        for (stable_key,) in (
            db.query(ServiceDeskScenario.stable_key)
            .join(
                ServiceDeskScenarioVersion,
                ServiceDeskScenarioVersion.scenario_id == ServiceDeskScenario.id,
            )
            .join(
                ServiceDeskAttempt,
                ServiceDeskAttempt.scenario_version_id == ServiceDeskScenarioVersion.id,
            )
            .filter(
                ServiceDeskAttempt.student_id == student_id,
                ServiceDeskAttempt.passed.is_(True),
            )
            .distinct()
            .all()
        )
    }


def build_service_desk_progression(db: Session, student: Student) -> dict:
    current_week = (
        max(pack.required_week for pack in SERVICE_DESK_PACKS)
        if student.is_mentor
        else derive_current_week(student.id, db)
    )
    passed_keys = _passed_scenario_keys(db, student.id)
    assigned_managed_keys = {
        stable_key
        for (stable_key,) in db.query(ServiceDeskScenario.stable_key)
        .join(
            ServiceDeskAssignment,
            ServiceDeskAssignment.scenario_id == ServiceDeskScenario.id,
        )
        .filter(
            ServiceDeskAssignment.student_id == student.id,
            ServiceDeskScenario.stable_key.in_(set(PACK_BY_SCENARIO)),
        )
        .all()
    }
    # The seed-owned catalog always includes the complete starter pack. A
    # smaller instructor-created assignment set is an explicit assignment and
    # remains available even when its normal pack has not been reached.
    direct_assignment_override_keys = (
        assigned_managed_keys
        if not set(SERVICE_DESK_PACKS[0].scenario_keys).issubset(assigned_managed_keys)
        else set()
    )
    passed_by_pack = {
        pack.key: len(set(pack.scenario_keys) & passed_keys)
        for pack in SERVICE_DESK_PACKS
    }
    unlocked_pack_keys = {SERVICE_DESK_PACKS[0].key}

    for index, pack in enumerate(SERVICE_DESK_PACKS[1:], start=1):
        prior_pack = SERVICE_DESK_PACKS[index - 1]
        if (
            prior_pack.key in unlocked_pack_keys
            and current_week >= pack.required_week
            and passed_by_pack[prior_pack.key] >= pack.required_prior_passes
        ):
            unlocked_pack_keys.add(pack.key)
        else:
            break

    active_pack = max(
        (pack for pack in SERVICE_DESK_PACKS if pack.key in unlocked_pack_keys),
        key=lambda pack: PACK_INDEX[pack.key],
    )
    next_pack = next(
        (pack for pack in SERVICE_DESK_PACKS if pack.key not in unlocked_pack_keys),
        None,
    )
    next_pack_data = None
    if next_pack:
        prior_pack = SERVICE_DESK_PACKS[PACK_INDEX[next_pack.key] - 1]
        requirements = []
        if current_week < next_pack.required_week:
            requirements.append(f"reach Week {next_pack.required_week}")
        if passed_by_pack[prior_pack.key] < next_pack.required_prior_passes:
            requirements.append(
                f"complete {next_pack.required_prior_passes} "
                f"{prior_pack.name} cases successfully"
            )
        if not requirements:
            requirements.append("finish the current case-pack requirements")
        reason = requirements[0][0].upper() + requirements[0][1:]
        if len(requirements) == 2:
            first = requirements[0][0].upper() + requirements[0][1:]
            reason = f"{first} and {requirements[1]}"
        next_pack_data = {
            "key": next_pack.key,
            "name": next_pack.name,
            "required_week": next_pack.required_week,
            "required_passes": next_pack.required_prior_passes,
            "source_pack_name": prior_pack.name,
            "source_pack_passes": passed_by_pack[prior_pack.key],
            "reason": f"{reason}.",
        }

    return {
        "current_week": current_week,
        "passed_keys": passed_keys,
        "passed_by_pack": passed_by_pack,
        "direct_assignment_override_keys": direct_assignment_override_keys,
        "unlocked_pack_keys": unlocked_pack_keys,
        "active_pack": active_pack,
        "next_pack": next_pack_data,
    }


def scenario_access(progression: dict, stable_key: str) -> dict:
    normalized = stable_key.lower()
    pack = PACK_BY_SCENARIO.get(normalized)
    if pack is None:
        # Admin-authored/test scenarios outside the managed catalog keep their
        # existing assignment behavior. They still require student ownership.
        return {
            "managed": False,
            "unlocked": True,
            "queue_type": "assigned",
            "pack_key": "custom",
            "pack_name": "Assigned by instructor",
            "pack_order": len(SERVICE_DESK_PACKS),
        }

    assigned_override = normalized in progression["direct_assignment_override_keys"]
    unlocked = pack.key in progression["unlocked_pack_keys"] or assigned_override
    passed = normalized in progression["passed_keys"]
    queue_type = (
        "assigned"
        if unlocked
        and (pack.key == progression["active_pack"].key or assigned_override)
        and not passed
        else "practice"
    )
    return {
        "managed": True,
        "unlocked": unlocked,
        "queue_type": queue_type,
        "pack_key": pack.key,
        "pack_name": pack.name,
        "pack_order": PACK_INDEX[pack.key],
    }


def require_scenario_unlocked(
    db: Session, student: Student, scenario: ServiceDeskScenario
) -> dict:
    progression = build_service_desk_progression(db, student)
    access = scenario_access(progression, scenario.stable_key)
    if access["unlocked"]:
        return access

    pack = PACK_BY_SCENARIO[scenario.stable_key.lower()]
    next_pack = progression["next_pack"]
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "success": False,
            "code": "SERVICE_DESK_PACK_LOCKED",
            "error": (
                next_pack["reason"]
                if next_pack and next_pack["key"] == pack.key
                else f"Complete the earlier Service Desk case packs before {pack.name}."
            ),
            "data": {
                "pack": pack.name,
                "required_week": pack.required_week,
                "current_week": progression["current_week"],
                "next_action_route": "/training",
            },
        },
    )
