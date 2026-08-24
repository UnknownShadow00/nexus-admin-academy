"""Intune & Windows 11 endpoint management content (Phase 4B.2).

Populates 5 new TrainingWeek rows (week_number 30-34 -- brand new, never
reusing or renumbering an existing week_number) inside the existing
stage.microsoft_workplace Stage, their lessons/quizzes/guided labs/two live
Service Desk tickets, and shifts TrainingWeek.display_order (only) for 12
existing weeks to open a contiguous slot right after Microsoft 365/Entra
(weeks 25-29). Unlike Phase 4B.1, nothing existing is moved/relocated --
every row this migration creates is new. See
docs/INTUNE_ENDPOINT_MANAGEMENT_CURRICULUM.md for the full research/design
record, including why this required updates to the legacy System B
progression code (progression_service.MODULE_WEEKS, service_desk_progression
.SERVICE_DESK_PACKS) and to the seeded PromotionGate rows for the graduating
role, so this required content cannot be silently skipped by graduation.

Revision ID: 0058_intune_endpoint_management
Revises: 0057_microsoft_workplace_foundations
Create Date: 2026-08-23
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_intune_endpoint_management


revision = "0058_intune_endpoint_management"
down_revision = "0057_microsoft_workplace_foundations"
branch_labels = None
depends_on = None

# upgrade() shifts these week_number -> display_order (see
# training_curriculum_seed._INTUNE_DISPLAY_ORDER_SHIFT); downgrade() reverses
# them back to their pre-Phase-4B.2 (post-Phase-4B.1) values.
_DISPLAY_ORDER_REVERT_TARGETS = {
    10: 18, 11: 19, 12: 20,
    16: 21, 17: 22,
    18: 23, 19: 24, 20: 25,
    21: 26, 22: 27,
    23: 28, 24: 29,
}

_NEW_WEEK_NUMBERS = (30, 31, 32, 33, 34)
_NEW_LEGACY_MODULE_CODES = ("MOD-030", "MOD-031", "MOD-032", "MOD-033", "MOD-034")


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_intune_endpoint_management(session)
    finally:
        session.close()


def downgrade() -> None:
    from app.models.learning import Lesson, Module
    from app.models.lab import LabTemplate
    from app.models.progression import PromotionGate, Role
    from app.models.quiz import Question, Quiz
    from app.models.service_desk import (
        ServiceDeskAssignment,
        ServiceDeskAttempt,
        ServiceDeskAttemptEvent,
        ServiceDeskAttemptGrade,
        ServiceDeskScenario,
        ServiceDeskScenarioVersion,
    )
    from app.models.training import TrainingWeek, TrainingWeekActivity

    session = Session(bind=op.get_bind())
    try:
        new_weeks = session.query(TrainingWeek).filter(TrainingWeek.week_number.in_(_NEW_WEEK_NUMBERS)).all()
        new_week_ids = [week.id for week in new_weeks]
        if new_week_ids:
            session.query(TrainingWeekActivity).filter(TrainingWeekActivity.training_week_id.in_(new_week_ids)).delete(
                synchronize_session=False
            )

        for scenario_key in ("bitlocker-recovery", "offboarding-device-reassignment"):
            scenario = session.query(ServiceDeskScenario).filter_by(stable_key=scenario_key).first()
            if scenario is not None:
                version_ids = [
                    row.id
                    for row in session.query(ServiceDeskScenarioVersion.id)
                    .filter_by(scenario_id=scenario.id)
                    .all()
                ]
                if version_ids:
                    attempt_ids = [
                        row.id
                        for row in session.query(ServiceDeskAttempt.id)
                        .filter(ServiceDeskAttempt.scenario_version_id.in_(version_ids))
                        .all()
                    ]
                    if attempt_ids:
                        session.query(ServiceDeskAttemptGrade).filter(
                            ServiceDeskAttemptGrade.attempt_id.in_(attempt_ids)
                        ).delete(synchronize_session=False)
                        session.query(ServiceDeskAttemptEvent).filter(
                            ServiceDeskAttemptEvent.attempt_id.in_(attempt_ids)
                        ).delete(synchronize_session=False)
                        session.query(ServiceDeskAttempt).filter(ServiceDeskAttempt.id.in_(attempt_ids)).delete(
                            synchronize_session=False
                        )
                    session.query(ServiceDeskAttemptGrade).filter(
                        ServiceDeskAttemptGrade.scenario_version_id.in_(version_ids)
                    ).delete(synchronize_session=False)
                    session.query(ServiceDeskScenarioVersion).filter(
                        ServiceDeskScenarioVersion.id.in_(version_ids)
                    ).delete(synchronize_session=False)
                session.query(ServiceDeskAssignment).filter_by(scenario_id=scenario.id).delete(synchronize_session=False)
                session.delete(scenario)

        new_modules = session.query(Module).filter(Module.code.in_(_NEW_LEGACY_MODULE_CODES)).all()
        new_module_ids = [module.id for module in new_modules]
        if new_module_ids:
            quizzes = session.query(Quiz).filter(Quiz.week_number.in_(_NEW_WEEK_NUMBERS)).all()
            quiz_ids = [quiz.id for quiz in quizzes]
            if quiz_ids:
                session.query(Question).filter(Question.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
                session.query(Quiz).filter(Quiz.id.in_(quiz_ids)).delete(synchronize_session=False)
            session.query(LabTemplate).filter(LabTemplate.week_number.in_(_NEW_WEEK_NUMBERS)).delete(
                synchronize_session=False
            )
            session.query(Lesson).filter(Lesson.module_id.in_(new_module_ids)).delete(synchronize_session=False)
            session.query(Module).filter(Module.id.in_(new_module_ids)).delete(synchronize_session=False)

        for week in new_weeks:
            session.delete(week)

        # Revert the display_order shift for the 12 existing weeks.
        existing_weeks = {
            row.week_number: row
            for row in session.query(TrainingWeek).filter(TrainingWeek.week_number.in_(_DISPLAY_ORDER_REVERT_TARGETS)).all()
        }
        for week_number, original_order in _DISPLAY_ORDER_REVERT_TARGETS.items():
            week = existing_weeks.get(week_number)
            if week is not None:
                week.display_order = original_order

        # Revert the graduation gate additions.
        final_role = session.query(Role).filter_by(name="Junior Infrastructure Administrator").first()
        if final_role is not None:
            lessons_gate = (
                session.query(PromotionGate)
                .filter_by(role_id=final_role.id, requirement_type="min_completed_lessons")
                .first()
            )
            if lessons_gate is not None:
                codes = [
                    code for code in lessons_gate.requirement_config.get("module_codes", [])
                    if code not in _NEW_LEGACY_MODULE_CODES
                ]
                lessons_gate.requirement_config = {
                    **lessons_gate.requirement_config,
                    "module_codes": codes,
                }
            session.query(PromotionGate).filter_by(
                role_id=final_role.id, requirement_type="required_quiz", requirement_config={"week": 33}
            ).delete(synchronize_session=False)
            session.query(PromotionGate).filter_by(
                role_id=final_role.id,
                requirement_type="min_service_desk_passes",
                requirement_config={"pack_key": "endpoint-management", "min_passed": 2},
            ).delete(synchronize_session=False)

        session.commit()
    finally:
        session.close()
