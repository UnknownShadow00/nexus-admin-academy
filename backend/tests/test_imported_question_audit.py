from app.models.quiz import Question, Quiz
from app.models.training import TrainingWeek, TrainingWeekActivity
from scripts.audit_imported_question_bank import run_audit


def _quiz(db, *, title, validated=False, required=False, active=True):
    quiz = Quiz(
        title=title,
        week_number=3,
        domain_id="1.0",
        status="published",
        question_count=1,
        source_type="examcompass",
        editorial_status="validated" if validated else "needs_edit",
        answer_keys_validated=validated,
        explanations_complete=validated,
        is_required=required,
        is_active=active,
        show_in_practice_library=validated and not required,
    )
    db.add(quiz)
    db.flush()
    db.add(Question(
        quiz_id=quiz.id,
        question_text=f"{title}: choose one.",
        option_a="Correct answer",
        option_b="Incorrect answer",
        correct_answer="A",
        explanation="The keyed answer is correct.",
    ))
    db.commit()
    return quiz


def test_imported_audit_uses_quiz_source_and_reports_required_usage(db):
    required = _quiz(db, title="Required imported", validated=True, required=True)
    hidden = _quiz(db, title="Unreviewed imported")
    week = TrainingWeek(week_number=3, display_order=3, title="Week 3", learning_goals=[])
    db.add(week)
    db.flush()
    db.add(TrainingWeekActivity(
        stable_id="week-3-required-imported",
        training_week_id=week.id,
        activity_type="quiz",
        content_ref=str(required.id),
        display_order=1,
        is_required=True,
        metadata_json={},
    ))
    db.commit()

    report = run_audit(db)

    assert report["imported"]["all"]["questions"] == 2
    assert report["imported"]["required_curriculum"]["questions"] == 1
    assert report["imported"]["optional_visible"]["questions"] == 0
    by_id = {row["id"]: row for row in report["quizzes"]}
    assert by_id[required.id]["classification"] == "KEEP REQUIRED"
    assert by_id[hidden.id]["classification"] == "HIDE / ARCHIVE"


def test_imported_audit_reports_duplicate_option_as_integrity_risk(db):
    quiz = _quiz(db, title="Duplicate options", validated=True)
    question = quiz.questions[0]
    question.option_b = question.option_a
    db.commit()

    report = run_audit(db)

    assert report["integrity"]["invalid_or_duplicate_option_questions"]
