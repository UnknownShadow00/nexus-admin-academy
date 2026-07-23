from app.models.curriculum_video import CurriculumVideo
from app.models.quiz import Quiz
from app.services.training_reference_seed import ensure_training_reference_content


def test_reviewed_training_reference_seed_is_complete_and_idempotent(db):
    first = ensure_training_reference_content(db)
    db.commit()
    second = ensure_training_reference_content(db)
    db.commit()

    assert first == {"videos": 75, "quizzes": 3}
    assert second == {"videos": 0, "quizzes": 0}
    assert db.query(CurriculumVideo).filter(CurriculumVideo.id.between(108, 182)).count() == 75
    quizzes = db.query(Quiz).filter(Quiz.id.in_([42, 48, 78])).all()
    assert {quiz.title for quiz in quizzes} == {
        "Ticketing Systems Quiz",
        "Incident Response Quiz",
        "Core PC Hardware Troubleshooting Quiz",
    }
    assert {quiz.id: len(quiz.questions) for quiz in quizzes} == {42: 4, 48: 4, 78: 19}
