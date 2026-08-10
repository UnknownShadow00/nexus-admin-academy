from app.models.quiz import Question, Quiz
from scripts.check_nexus_question_quality import check
from app.services.seed_question_sync import sync_seed_questions


def _quiz(db, *, required=True):
    quiz = Quiz(
        title="Authored quality gate", week_number=1, status="published",
        source_type="seed", is_required=required,
    )
    db.add(quiz)
    db.flush()
    return quiz


def test_quality_guard_fails_invalid_required_authored_question(db):
    quiz = _quiz(db)
    db.add(Question(
        quiz_id=quiz.id, seed_key="nexus-authored:quality:01", question_text="Pick one.",
        option_a="A", option_b="B", correct_answer="A", explanation="",
    ))
    db.commit()

    failures, warnings = check(db)

    assert failures


def test_quality_guard_warns_but_does_not_fail_for_editorial_length_signal(db):
    quiz = _quiz(db, required=False)
    for ordinal in range(4):
        db.add(Question(
            quiz_id=quiz.id, seed_key=f"nexus-authored:quality:{ordinal:02d}",
            question_text=f"Question {ordinal}", option_a="A", option_b="A much longer correct answer",
            option_c="C", option_d="D", correct_answer="B", explanation="Reviewed.",
        ))
    db.commit()

    failures, warnings = check(db)

    assert failures == []
    assert any("concentration" in warning for warning in warnings)
    assert any("uniquely-longest" in warning for warning in warnings)


def test_authored_seed_sync_updates_question_in_place_without_losing_identity(db):
    quiz = _quiz(db, required=False)
    original = {
        "question_text": "Original authored prompt",
        "option_a": "Correct option",
        "option_b": "Wrong option",
        "option_c": "Another wrong option",
        "option_d": "Final wrong option",
        "correct_answer": "A",
        "correct_answers": None,
        "explanation": "Original explanation.",
    }
    sync_seed_questions(db, quiz, [original])
    db.commit()
    question_id = quiz.questions[0].id

    revised = {**original, "question_text": "Revised authored prompt", "explanation": "Revised explanation."}
    sync_seed_questions(db, quiz, [revised])
    db.commit()
    questions = db.query(Question).filter(Question.quiz_id == quiz.id).all()

    assert len(questions) == 1
    assert questions[0].id == question_id
    assert questions[0].seed_key == "nexus-authored:authored-quality-gate:01"
    assert questions[0].question_text == "Revised authored prompt"
