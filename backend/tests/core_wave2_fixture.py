"""Minimal real seed content in a disposable database, with V2 disabled."""

from app.models.learning import Lesson, Module
from app.models.quiz import Question, Quiz
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.training_reference_seed import ensure_training_reference_content
from app.services.training_curriculum_seed import reconcile_optional_lesson_requirements
from seed import MODULE_0
from seed_phase_a import MODULES, QUIZZES


def seed_beginner(db):
    ensure_training_reference_content(db)
    for number, spec in enumerate((MODULE_0, MODULES[0])):
        module = Module(code=spec["code"], title=spec["title"], active=True)
        week = TrainingWeek(
            week_number=number,
            display_order=number,
            title=spec["title"],
            requires_previous_week=bool(number),
            learning_goals=[],
        )
        db.add_all([module, week])
        db.flush()
        for index, item in enumerate(spec["lessons"], 1):
            lesson = Lesson(module_id=module.id, **{**item, "status": "published"})
            db.add(lesson)
            db.flush()
            db.add(
                TrainingWeekActivity(
                    training_week_id=week.id,
                    stable_id=f"week-{number}-lesson-{lesson.id}",
                    activity_type="lesson",
                    content_ref=str(lesson.id),
                    display_order=index,
                    is_required=True,
                    estimated_minutes=lesson.estimated_minutes,
                )
            )
        if number == 0:
            quiz = db.get(Quiz, 42)
        else:
            specq = QUIZZES[0]
            quiz = Quiz(
                id=1,
                title=specq["title"],
                week_number=1,
                status="published",
                is_required=True,
                editorial_status="validated",
                answer_keys_validated=True,
                question_count=len(specq["questions"]),
            )
            db.add(quiz)
            db.flush()
            for q in specq["questions"]:
                db.add(Question(quiz_id=quiz.id, **q))
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-quiz-{quiz.id}",
                activity_type="quiz",
                content_ref=str(quiz.id),
                display_order=10,
                is_required=True,
                estimated_minutes=10,
            )
        )
    db.add(
        TrainingWeekActivity(
            training_week_id=week.id,
            stable_id="wave2-optional-video",
            activity_type="video",
            content_ref="166",
            display_order=20,
            is_required=False,
        )
    )
    db.commit()
    reconcile_optional_lesson_requirements(db)
