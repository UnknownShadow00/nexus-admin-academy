"""Microsoft 365, Entra & Endpoint Management stage content (Phase 4B.1).

Populates the previously-empty stage.microsoft_workplace Stage with 5 new
TrainingWeek rows (week_number 25-29 -- brand new, never reusing or
renumbering an existing week_number), their lessons/quizzes/guided
labs/Service Desk tickets/capstone, and shifts TrainingWeek.display_order
(only) for 12 existing weeks to open a contiguous slot between Identity &
Access and Network Administration & Infrastructure. Lesson 58 and
LabTemplate 19 are moved (not duplicated) from week 21 into week 26, since
their existing content already covered Entra identity administration more
appropriately than the general cloud-computing module they were teaching
alongside. See docs/MICROSOFT_WORKPLACE_CURRICULUM.md for the full
research/design record, including why this required updates to the legacy
System B progression code (progression_service.MODULE_WEEKS/
derive_current_week, service_desk_progression.SERVICE_DESK_PACKS) and to the
seeded PromotionGate rows for the graduating role, so this required content
cannot be silently skipped by graduation.

Revision ID: 0057_microsoft_workplace_foundations
Revises: 0056_advanced_networking_resequence
Create Date: 2026-08-23
"""

from alembic import op
from sqlalchemy.orm import Session

from app.services.training_curriculum_seed import sync_microsoft_workplace_foundations


revision = "0057_microsoft_workplace_foundations"
down_revision = "0056_advanced_networking_resequence"
branch_labels = None
depends_on = None

# upgrade() shifts these week_number -> display_order (see
# training_curriculum_seed._M365_DISPLAY_ORDER_SHIFT); downgrade() reverses
# them back to their pre-Phase-4B.1 values.
_DISPLAY_ORDER_REVERT_TARGETS = {
    10: 13, 11: 14, 12: 15,
    16: 16, 17: 17,
    18: 18, 19: 19, 20: 20,
    21: 21, 22: 22,
    23: 23, 24: 24,
}

_NEW_WEEK_NUMBERS = (25, 26, 27, 28, 29)
_NEW_LEGACY_MODULE_CODES = ("MOD-025", "MOD-026", "MOD-027", "MOD-028", "MOD-029")
_MOVED_LESSON_ID = 58
_MOVED_LESSON_ORIGINAL_MODULE_CODE = "MOD-021"
_MOVED_LAB_ORIGINAL_UPDATE_TITLE = "Investigate the Entra Identity Ticket"
_MOVED_LAB_ORIGINAL = {
    "title": "Route the Cloud Identity Ticket",
    "week_number": 21,
    "success_criteria": {
        "questions": [
            {
                "id": "signin-log",
                "prompt": "A user can sign into their laptop but not Microsoft 365. What should you inspect first?",
                "context": "The organization synchronizes identities from on-premises AD to Entra ID.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Entra sign-in logs and synchronization state"},
                    {"id": "b", "label": "The laptop display driver"},
                    {"id": "c", "label": "The office printer queue"},
                    {"id": "d", "label": "Reset every authentication method immediately"},
                ],
                "correct": ["a"],
                "explanation": "The split between local and cloud sign-in points to cloud policy, sign-in evidence, or directory synchronization.",
            },
            {
                "id": "mfa-lost-phone",
                "prompt": "A caller says their phone was lost and asks for an MFA reset. What is the first required action?",
                "context": "The caller is in a hurry and can provide their username.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Verify identity using the approved recovery process"},
                    {"id": "b", "label": "Remove MFA based on the username"},
                    {"id": "c", "label": "Give them an administrator's phone number"},
                    {"id": "d", "label": "Disable Conditional Access"},
                ],
                "correct": ["a"],
                "explanation": "An MFA reset changes an account's trust boundary, so identity verification comes first.",
            },
            {
                "id": "responsibility",
                "prompt": "An application service inside an Azure IaaS VM has stopped. Who owns that operating-system fix?",
                "context": "Azure reports that the VM and host platform are healthy.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Your organization, because IaaS customers manage the guest OS"},
                    {"id": "b", "label": "The cloud provider, because every cloud layer is theirs"},
                    {"id": "c", "label": "The user's internet provider"},
                    {"id": "d", "label": "Nobody"},
                ],
                "correct": ["a"],
                "explanation": "In IaaS the provider runs the physical platform, while the customer operates the guest OS and applications.",
            },
        ],
    },
}


def upgrade() -> None:
    session = Session(bind=op.get_bind())
    try:
        sync_microsoft_workplace_foundations(session)
    finally:
        session.close()


def downgrade() -> None:
    from app.models.capstone import CapstoneTemplate
    from app.models.learning import Lesson, Module
    from app.models.lab import LabTemplate
    from app.models.progression import PromotionGate, Role
    from app.models.quiz import Question, Quiz
    from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
    from app.models.training import TrainingWeek, TrainingWeekActivity

    session = Session(bind=op.get_bind())
    try:
        # Restore the moved lesson and lab to their original week/content.
        lesson = session.get(Lesson, _MOVED_LESSON_ID)
        original_module = session.query(Module).filter_by(code=_MOVED_LESSON_ORIGINAL_MODULE_CODE).first()
        if lesson is not None and original_module is not None:
            lesson.module_id = original_module.id
            lesson.lesson_order = 2

        # Looked up by its current (moved) title, not a hardcoded id -- on a
        # fresh install this row was created directly under its final
        # identity (nothing creates "Route the Cloud Identity Ticket" any
        # more), so it never had id 19 to begin with. See the matching
        # comment in sync_microsoft_workplace_foundations.
        lab = session.query(LabTemplate).filter_by(title=_MOVED_LAB_ORIGINAL_UPDATE_TITLE).first()
        moved_lab_id = lab.id if lab is not None else None
        if lab is not None:
            lab.title = _MOVED_LAB_ORIGINAL["title"]
            lab.week_number = _MOVED_LAB_ORIGINAL["week_number"]
            lab.success_criteria = _MOVED_LAB_ORIGINAL["success_criteria"]
        session.flush()

        # Restore week 21's activity ordering to include the lesson/lab again.
        old_week_21 = session.query(TrainingWeek).filter_by(week_number=21).first()
        if old_week_21 is not None and lesson is not None:
            exists = (
                session.query(TrainingWeekActivity)
                .filter_by(training_week_id=old_week_21.id, stable_id=f"week-21-lesson-{lesson.id}")
                .first()
            )
            if exists is None:
                max_order = (
                    session.query(TrainingWeekActivity.display_order)
                    .filter_by(training_week_id=old_week_21.id)
                    .order_by(TrainingWeekActivity.display_order.desc())
                    .first()
                )
                next_order = (max_order[0] if max_order else 0) + 1
                session.add(
                    TrainingWeekActivity(
                        training_week_id=old_week_21.id,
                        stable_id=f"week-21-lesson-{lesson.id}",
                        activity_type="lesson",
                        content_ref=str(lesson.id),
                        display_order=next_order,
                        is_required=False,
                        prerequisite_mode="soft",
                        metadata_json={},
                    )
                )
        if old_week_21 is not None and lab is not None:
            exists = (
                session.query(TrainingWeekActivity)
                .filter_by(training_week_id=old_week_21.id, stable_id=f"week-21-guided_lab-{lab.id}")
                .first()
            )
            if exists is None:
                max_order = (
                    session.query(TrainingWeekActivity.display_order)
                    .filter_by(training_week_id=old_week_21.id)
                    .order_by(TrainingWeekActivity.display_order.desc())
                    .first()
                )
                next_order = (max_order[0] if max_order else 0) + 1
                session.add(
                    TrainingWeekActivity(
                        training_week_id=old_week_21.id,
                        stable_id=f"week-21-guided_lab-{lab.id}",
                        activity_type="guided_lab",
                        content_ref=str(lab.id),
                        display_order=next_order,
                        is_required=True,
                        estimated_minutes=lab.estimated_minutes,
                        prerequisite_mode="soft",
                        metadata_json={},
                    )
                )
        session.flush()

        # Delete new-week activities, then the new weeks/modules/content.
        new_weeks = session.query(TrainingWeek).filter(TrainingWeek.week_number.in_(_NEW_WEEK_NUMBERS)).all()
        new_week_ids = [week.id for week in new_weeks]
        if new_week_ids:
            session.query(TrainingWeekActivity).filter(TrainingWeekActivity.training_week_id.in_(new_week_ids)).delete(
                synchronize_session=False
            )

        for scenario_key in ("m365-entra-auth-method", "m365-signin-conditional-access"):
            scenario = session.query(ServiceDeskScenario).filter_by(stable_key=scenario_key).first()
            if scenario is not None:
                session.query(ServiceDeskScenarioVersion).filter_by(scenario_id=scenario.id).delete(synchronize_session=False)
                session.delete(scenario)

        capstone = session.query(CapstoneTemplate).filter_by(title="Microsoft Workplace Support Shift").first()
        if capstone is not None:
            session.delete(capstone)

        new_modules = session.query(Module).filter(Module.code.in_(_NEW_LEGACY_MODULE_CODES)).all()
        new_module_ids = [module.id for module in new_modules]
        if new_module_ids:
            quizzes = session.query(Quiz).filter(Quiz.week_number.in_(_NEW_WEEK_NUMBERS)).all()
            quiz_ids = [quiz.id for quiz in quizzes]
            if quiz_ids:
                session.query(Question).filter(Question.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
                session.query(Quiz).filter(Quiz.id.in_(quiz_ids)).delete(synchronize_session=False)
            session.query(LabTemplate).filter(
                LabTemplate.week_number.in_(_NEW_WEEK_NUMBERS), LabTemplate.id != (moved_lab_id or -1)
            ).delete(synchronize_session=False)
            session.query(Lesson).filter(Lesson.module_id.in_(new_module_ids), Lesson.id != _MOVED_LESSON_ID).delete(
                synchronize_session=False
            )
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
                lessons_gate.requirement_config = {"module_codes": codes}
            session.query(PromotionGate).filter_by(
                role_id=final_role.id, requirement_type="required_quiz", requirement_config={"week": 27}
            ).delete(synchronize_session=False)
            session.query(PromotionGate).filter_by(
                role_id=final_role.id,
                requirement_type="min_service_desk_passes",
                requirement_config={"pack_key": "microsoft-workplace", "min_passed": 2},
            ).delete(synchronize_session=False)

        session.commit()
    finally:
        session.close()
