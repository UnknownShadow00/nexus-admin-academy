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
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.curriculum_structure import module_for_week
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
        scenario_keys=(
            "locked-user-account",
            "password-reset",
            "mfa-reset",
            "inc2404",
        ),
        required_week=1,
        required_prior_passes=0,
    ),
    ServiceDeskPack(
        key="desktop-support",
        name="Desktop Support",
        scenario_keys=("inc2408", "inc2501", "inc2403", "inc2502", "inc2509"),
        required_week=3,
        required_prior_passes=2,
    ),
    ServiceDeskPack(
        key="accounts-access",
        name="Accounts & Access",
        scenario_keys=("inc2401", "inc2405", "inc2505", "inc2507"),
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
        scenario_keys=("inc2504", "inc2506", "inc2508", "inc2510"),
        required_week=10,
        required_prior_passes=3,
    ),
    # Phase 4B.1. required_week=26 is a new week_number (Entra Users, Groups
    # & Access), never a renumbering of an existing week. It sits after
    # every other pack's required_week so it unlocks once the rest of the
    # legacy-numbered curriculum (weeks 0-24) is done -- see
    # docs/MICROSOFT_WORKPLACE_CURRICULUM.md "Dual progression systems" for
    # why that stagger against the Learning Path's earlier display position
    # is intentional, not a bug.
    #
    # Only two scenario_keys: server-side grading in service_desk_objectives.py
    # only has evidence vocabulary for directory/account-state actions
    # (directory.inspect_account, .reset_mfa, .verify_identity, etc.) -- there
    # is no mailbox/OneDrive/SharePoint tool surface, and no "forbidden
    # action" primitive to penalize an unsafe shortcut (e.g. resetting MFA on
    # a suspicious prompt instead of escalating). Those topics are guided_lab
    # evidence-interpretation exercises instead (see
    # docs/MICROSOFT_WORKPLACE_CURRICULUM.md "Practical environment
    # strategy") rather than live simulation tickets the grader cannot
    # actually evaluate.
    ServiceDeskPack(
        key="microsoft-workplace",
        name="Microsoft Workplace Support",
        scenario_keys=(
            "m365-entra-auth-method",
            "m365-signin-conditional-access",
        ),
        required_week=26,
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
                ServiceDeskAttempt.experience_mode == "assessment",
            )
            .distinct()
            .all()
        )
    }


def _guided_scenario_keys(db: Session, student_id: int) -> set[str]:
    return {
        stable_key
        for (stable_key,) in (
            db.query(ServiceDeskScenario.stable_key)
            .join(ServiceDeskScenarioVersion)
            .join(ServiceDeskAttempt)
            .filter(
                ServiceDeskAttempt.student_id == student_id,
                ServiceDeskAttempt.passed.is_(True),
                ServiceDeskAttempt.experience_mode == "guided",
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
    guided_completed_keys = _guided_scenario_keys(db, student.id)
    managed_assignments = (
        db.query(
            ServiceDeskScenario.stable_key,
            ServiceDeskAssignment.assigned_by,
        )
        .join(
            ServiceDeskAssignment,
            ServiceDeskAssignment.scenario_id == ServiceDeskScenario.id,
        )
        .filter(
            ServiceDeskAssignment.student_id == student.id,
            ServiceDeskScenario.stable_key.in_(set(PACK_BY_SCENARIO)),
        )
        .all()
    )
    # Seed and account-creation rows are catalog inventory. Any other owner is
    # an intentional instructor assignment for that exact case only.
    catalog_owners = {"seed", "student-create", "migration-0047"}
    direct_assignment_override_keys = {
        stable_key
        for stable_key, assigned_by in managed_assignments
        if assigned_by and assigned_by not in catalog_owners
    }
    in_progress_keys = {
        stable_key
        for (stable_key,) in db.query(ServiceDeskScenario.stable_key)
        .join(
            ServiceDeskScenarioVersion,
            ServiceDeskScenarioVersion.scenario_id == ServiceDeskScenario.id,
        )
        .join(
            ServiceDeskAttempt,
            ServiceDeskAttempt.scenario_version_id == ServiceDeskScenarioVersion.id,
        )
        .filter(
            ServiceDeskAttempt.student_id == student.id,
            ServiceDeskAttempt.status == "in_progress",
        )
        .distinct()
        .all()
    }
    curriculum_rows = (
        db.query(TrainingWeek.week_number, TrainingWeekActivity.content_ref)
        .join(
            TrainingWeekActivity,
            TrainingWeekActivity.training_week_id == TrainingWeek.id,
        )
        .filter(
            TrainingWeekActivity.activity_type == "service_desk_scenario",
            TrainingWeekActivity.is_required.is_(True),
            TrainingWeek.week_number <= current_week,
        )
        .all()
    )
    # A required weekly case is an exact curriculum assignment. It can be
    # started when that week is reached without unlocking the case's pack.
    curriculum_unlocked_keys = {stable_key for _, stable_key in curriculum_rows}
    curriculum_current_keys = {
        stable_key
        for week_number, stable_key in curriculum_rows
        if week_number == current_week
    }
    passed_by_pack = {
        pack.key: len(set(pack.scenario_keys) & passed_keys)
        for pack in SERVICE_DESK_PACKS
    }
    unlocked_pack_keys = set()

    starter_pack = SERVICE_DESK_PACKS[0]
    if student.is_mentor or current_week >= starter_pack.required_week:
        unlocked_pack_keys.add(starter_pack.key)

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

    active_pack = (
        max(
            (pack for pack in SERVICE_DESK_PACKS if pack.key in unlocked_pack_keys),
            key=lambda pack: PACK_INDEX[pack.key],
        )
        if unlocked_pack_keys
        else None
    )
    next_pack = next(
        (pack for pack in SERVICE_DESK_PACKS if pack.key not in unlocked_pack_keys),
        None,
    )
    next_pack_data = None
    if next_pack:
        next_index = PACK_INDEX[next_pack.key]
        prior_pack = SERVICE_DESK_PACKS[next_index - 1] if next_index else None
        week_met = current_week >= next_pack.required_week
        pass_count = passed_by_pack[prior_pack.key] if prior_pack else 0
        passes_met = pass_count >= next_pack.required_prior_passes
        # The first pack becomes available after orientation; later packs use
        # the module at their historical numeric progression threshold.
        required_module = module_for_week(0 if next_index == 0 else next_pack.required_week)
        required_module_title = (
            required_module.title if required_module else "the required training module"
        )
        if next_index == 0:
            reason = "Complete Nexus Orientation to begin your first Service Desk shift."
        else:
            pending = []
            if not week_met:
                pending.append(f"reach {required_module_title}")
            if not passes_met:
                remaining = next_pack.required_prior_passes - pass_count
                pending.append(
                    f"successfully resolve {remaining} more {prior_pack.name} "
                    f"case{'s' if remaining != 1 else ''}"
                )
            reason = "To unlock, " + " and ".join(pending) + "."
        next_pack_data = {
            "key": next_pack.key,
            "name": next_pack.name,
            "required_week": next_pack.required_week,
            "required_module_id": required_module.stable_id if required_module else None,
            "required_module_title": required_module_title,
            "required_passes": next_pack.required_prior_passes,
            "source_pack_name": prior_pack.name if prior_pack else None,
            "source_pack_passes": pass_count,
            "reason": reason,
            "requirements": {
                "week": {
                    "label": (
                        "Complete Nexus Orientation"
                        if next_index == 0
                        else f"Reach {required_module_title}"
                    ),
                    "met": week_met,
                },
                "passes": None
                if prior_pack is None
                else {
                    "label": (
                        f"Successfully resolve {next_pack.required_prior_passes} "
                        f"{prior_pack.name} cases"
                    ),
                    "met": passes_met,
                    "completed": pass_count,
                    "required": next_pack.required_prior_passes,
                },
            },
        }

    assigned_keys = (
        set(direct_assignment_override_keys)
        | set(in_progress_keys)
        | (curriculum_current_keys - passed_keys)
    )
    if active_pack:
        active_candidates = [
            key
            for key in active_pack.scenario_keys
            if key not in passed_keys
            and key not in assigned_keys
            and (key not in guided_completed_keys or key in curriculum_unlocked_keys)
        ]
        assigned_keys.update(active_candidates[: max(0, 4 - len(assigned_keys))])

    return {
        "current_week": current_week,
        "passed_keys": passed_keys,
        "guided_completed_keys": guided_completed_keys,
        "passed_by_pack": passed_by_pack,
        "direct_assignment_override_keys": direct_assignment_override_keys,
        "curriculum_unlocked_keys": curriculum_unlocked_keys,
        "curriculum_current_keys": curriculum_current_keys,
        "in_progress_keys": in_progress_keys,
        "assigned_keys": assigned_keys,
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
            "experience_mode": "assessment",
            "guided_completed": False,
            "required_this_week": False,
            "pack_key": "custom",
            "pack_name": "Assigned by instructor",
            "pack_order": len(SERVICE_DESK_PACKS),
        }

    assigned_override = normalized in progression["direct_assignment_override_keys"]
    curriculum_unlocked = normalized in progression["curriculum_unlocked_keys"]
    unlocked = (
        pack.key in progression["unlocked_pack_keys"]
        or assigned_override
        or curriculum_unlocked
    )
    passed = normalized in progression["passed_keys"]
    if passed:
        queue_type = "practice"
    elif assigned_override:
        queue_type = "assigned"
    elif normalized in progression["assigned_keys"]:
        queue_type = "assigned"
    else:
        queue_type = "earlier"
    return {
        "managed": True,
        "unlocked": unlocked,
        "queue_type": queue_type,
        "pack_key": pack.key,
        "pack_name": pack.name,
        "pack_order": PACK_INDEX[pack.key],
        "experience_mode": (
            "practice"
            if passed
            else "assessment"
            if (
                normalized in progression["curriculum_unlocked_keys"]
                or assigned_override
            )
            else "guided"
        ),
        "guided_completed": normalized in progression["guided_completed_keys"],
        "required_this_week": normalized in progression["curriculum_current_keys"],
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
