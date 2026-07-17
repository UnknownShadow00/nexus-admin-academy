"""Regression tests for TB-01 (boot safety, phantom seeding) and TB-06 (quiz integrity).

Every test here pins a bug that previously existed:
- app crashed at import when OPENROUTER_MODEL was unset
- phantom students (Alex/Jordan/...) were seeded on any empty DB
- single-letter answers to multi-select questions earned full credit
- quiz retakes overwrote the single QuizAttempt row
"""
import importlib

from conftest import auth_headers, make_client, make_student
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.routers.quizzes import router as quizzes_router

client = make_client(quizzes_router)


# ---------------------------------------------------------------- TB-01

def test_ai_service_importable_without_model_env(monkeypatch):
    """ai_service must import cleanly with no AI env vars (old code raised RuntimeError)."""
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    import app.services.ai_service as ai_service
    importlib.reload(ai_service)  # re-run module top-level with the cleared env
    assert ai_service.ai_is_configured() is False
    # restore module state for other tests
    importlib.reload(ai_service)


def test_main_module_has_no_phantom_seeder():
    """seed_students() must be gone from app.main (it polluted cohort stats)."""
    import app.main as main_module
    assert not hasattr(main_module, "seed_students")


def test_ai_base_url_configurable(monkeypatch):
    """TB-07: AI_BASE_URL/AI_MODEL point the service at any OpenAI-compatible endpoint."""
    monkeypatch.setenv("AI_BASE_URL", "http://192.168.0.50:11434/v1")
    monkeypatch.setenv("AI_MODEL", "llama3.1:70b")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    import app.services.ai_service as ai_service
    importlib.reload(ai_service)
    assert ai_service.OPENROUTER_URL == "http://192.168.0.50:11434/v1/chat/completions"
    assert ai_service.OPENROUTER_MODEL == "llama3.1:70b"
    assert ai_service.AI_IS_LOCAL is True
    # local endpoints are configured even without an API key
    assert ai_service.ai_is_configured() is True
    monkeypatch.delenv("AI_BASE_URL")
    monkeypatch.delenv("AI_MODEL")
    importlib.reload(ai_service)


# ---------------------------------------------------------------- TB-06 helpers

def _seed_multi_quiz(db):
    quiz = Quiz(title="Multi Select Quiz", week_number=1, status=QUIZ_STATUS_PUBLISHED)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    q = Question(
        quiz_id=quiz.id,
        question_text="Select ALL correct options.",
        option_a="Right one",
        option_b="Also right",
        option_c="Wrong",
        option_d="Wrong",
        correct_answer="A",
        correct_answers="A,B",
        explanation="A and B are both required.",
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return quiz, q


def _submit(student, quiz, q, answer):
    return client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(q.id): answer}},
        headers=auth_headers(student),
    )


# ---------------------------------------------------------------- TB-06 tests

def test_multi_select_partial_answer_not_full_credit(db):
    """Single letter on a multi-select question must NOT be graded correct."""
    student = make_student(db)
    quiz, q = _seed_multi_quiz(db)
    res = _submit(student, quiz, q, "A")  # partial: missing B
    assert res.status_code == 200
    assert res.json()["data"]["score"] == 0


def test_multi_select_full_answer_any_order(db):
    student = make_student(db)
    quiz, q = _seed_multi_quiz(db)
    res = _submit(student, quiz, q, "b, a")  # order/case/spacing insensitive
    assert res.status_code == 200
    assert res.json()["data"]["score"] == 1


def test_multi_select_empty_answer_incorrect(db):
    student = make_student(db)
    quiz, q = _seed_multi_quiz(db)
    res = _submit(student, quiz, q, "")
    assert res.status_code == 200
    assert res.json()["data"]["score"] == 0


def test_retake_creates_new_attempt_row(db):
    """Every attempt must persist as its own row (previously overwritten)."""
    student = make_student(db)
    quiz, q = _seed_multi_quiz(db)
    r1 = _submit(student, quiz, q, "A")      # wrong, score 0
    r2 = _submit(student, quiz, q, "A,B")    # correct, score 1
    assert r1.status_code == 200 and r2.status_code == 200
    rows = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.student_id == student.id, QuizAttempt.quiz_id == quiz.id)
        .all()
    )
    assert len(rows) == 2
    scores = sorted(r.score for r in rows)
    assert scores == [0, 1]
    # best_score on the newest row reflects history
    assert max(r.best_score or 0 for r in rows) == 1


def test_retake_awards_no_xp(db):
    """XP policy: first attempt only (previously enforced; must survive the rewrite)."""
    student = make_student(db)
    quiz, q = _seed_multi_quiz(db)
    r1 = _submit(student, quiz, q, "A,B")
    r2 = _submit(student, quiz, q, "A,B")
    assert r1.json()["data"]["xp_awarded"] > 0
    assert r2.json()["data"]["xp_awarded"] == 0
    assert r2.json()["data"]["is_first_attempt"] is False
