from app.config import load_env
from app.models.quiz import (
    EDITORIAL_STATUS_UNREVIEWED,
    QUIZ_PURPOSE_CERTIFICATION,
    QUIZ_PURPOSE_GATE,
    QUIZ_PURPOSE_PRACTICE,
    QUIZ_PURPOSE_REMEDIATION,
    QUIZ_PURPOSE_REQUIRED,
    Question,
    Quiz,
    QuizAssignment,
    QuizAttempt,
)
from app.routers.admin_quiz import router as admin_quiz_router
from app.routers.quizzes import router as quizzes_router
from app.services.quiz_progression import (
    is_quiz_passed,
    required_quizzes_for_week,
)
from conftest import auth_headers, make_client, make_student
from seed_quiz_organization import rebalance_seed_answer_positions


student_client = make_client(quizzes_router)
admin_client = make_client(admin_quiz_router)


def _quiz(db, *, title, purpose, week=1, required=False, checklist=False, validated=True):
    quiz = Quiz(
        title=title,
        week_number=week,
        domain_id="1.0",
        status="published",
        question_count=1,
        quiz_purpose=purpose,
        is_required=required,
        show_in_weekly_checklist=checklist,
        show_in_practice_library=not required,
        editorial_status="validated" if validated else EDITORIAL_STATUS_UNREVIEWED,
        source_type="seed" if validated else "examcompass",
        answer_keys_validated=validated,
        explanations_complete=validated,
        is_active=True,
    )
    db.add(quiz)
    db.flush()
    db.add(
        Question(
            quiz_id=quiz.id,
            question_text="Choose the correct answer.",
            option_a="Correct",
            option_b="Wrong",
            option_c="Wrong",
            option_d="Wrong",
            correct_answer="A",
            explanation="A is correct.",
        )
    )
    db.commit()
    db.refresh(quiz)
    return quiz


def test_required_quiz_blocks_until_passed(db):
    student = make_student(db)
    required = _quiz(
        db,
        title="Required",
        purpose=QUIZ_PURPOSE_REQUIRED,
        required=True,
        checklist=True,
    )

    assert required_quizzes_for_week(db, 1) == [required]
    assert not is_quiz_passed(db, student.id, required)

    db.add(QuizAttempt(student_id=student.id, quiz_id=required.id, answers={}, score=0, xp_awarded=0))
    db.commit()
    assert not is_quiz_passed(db, student.id, required)

    db.add(QuizAttempt(student_id=student.id, quiz_id=required.id, answers={}, score=1, xp_awarded=0))
    db.commit()
    assert is_quiz_passed(db, student.id, required)


def test_optional_and_certification_quizzes_never_block_week(db):
    _quiz(db, title="Practice", purpose=QUIZ_PURPOSE_PRACTICE)
    _quiz(db, title="Certification", purpose=QUIZ_PURPOSE_CERTIFICATION)

    assert required_quizzes_for_week(db, 1) == []


def test_remediation_only_appears_when_assigned_or_triggered(db):
    student = make_student(db)
    remediation = _quiz(db, title="Remediation", purpose=QUIZ_PURPOSE_REMEDIATION)

    response = student_client.get("/api/quizzes", headers=auth_headers(student))
    assert response.status_code == 200
    assert remediation.id not in {row["id"] for row in response.json()["data"]}

    db.add(QuizAssignment(student_id=student.id, quiz_id=remediation.id, reason="mentor_assignment"))
    db.commit()
    response = student_client.get("/api/quizzes", headers=auth_headers(student))
    assert remediation.id in {row["id"] for row in response.json()["data"]}


def test_gate_only_blocks_its_assigned_week(db):
    gate = _quiz(
        db,
        title="Week 4 Gate",
        purpose=QUIZ_PURPOSE_GATE,
        week=4,
        required=True,
        checklist=True,
    )

    assert required_quizzes_for_week(db, 3) == []
    assert required_quizzes_for_week(db, 4) == [gate]
    assert required_quizzes_for_week(db, 5) == []


def _admin_headers(monkeypatch):
    load_env.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "password")
    monkeypatch.setenv("ADMIN_API_KEY", "quiz-org-test-key")
    load_env()
    return {"X-Admin-Key": "quiz-org-test-key"}


def test_admin_quiz_list_paginates_searches_and_filters_all_rows(db, monkeypatch):
    for index in range(104):
        _quiz(
            db,
            title=f"Bank {index:03d}",
            purpose=QUIZ_PURPOSE_CERTIFICATION if index % 2 else QUIZ_PURPOSE_PRACTICE,
            week=(index % 24) + 1,
        )

    headers = _admin_headers(monkeypatch)
    first = admin_client.get("/api/admin/quizzes?page=1&per_page=50", headers=headers)
    third = admin_client.get("/api/admin/quizzes?page=3&per_page=50", headers=headers)
    filtered = admin_client.get(
        "/api/admin/quizzes?search=Bank%20103&purpose=certification", headers=headers
    )

    assert first.status_code == 200 and first.json()["total"] == 104
    assert len(first.json()["data"]) == 50
    assert len(third.json()["data"]) == 4
    assert [row["title"] for row in filtered.json()["data"]] == ["Bank 103"]


def test_unvalidated_import_cannot_be_marked_required(db, monkeypatch):
    imported = _quiz(
        db,
        title="Unvalidated Import",
        purpose=QUIZ_PURPOSE_CERTIFICATION,
        validated=False,
    )
    response = admin_client.patch(
        f"/api/admin/quizzes/{imported.id}",
        json={"is_required": True, "show_in_weekly_checklist": True},
        headers=_admin_headers(monkeypatch),
    )

    assert response.status_code == 409
    assert "validated answer keys" in response.json()["detail"].lower()


def test_unvalidated_quiz_cannot_be_put_in_student_practice_library(db, monkeypatch):
    imported = _quiz(db, title="Unvalidated practice", purpose=QUIZ_PURPOSE_PRACTICE, validated=False)
    response = admin_client.patch(
        f"/api/admin/quizzes/{imported.id}",
        json={"show_in_practice_library": True},
        headers=_admin_headers(monkeypatch),
    )

    assert response.status_code == 409
    assert "student visibility" in response.json()["detail"].lower()


def test_editorial_queue_prioritizes_practice_and_exposes_review_fields(db, monkeypatch):
    practice = _quiz(db, title="Practice first", purpose=QUIZ_PURPOSE_PRACTICE, validated=False)
    remediation = _quiz(db, title="Remediation second", purpose=QUIZ_PURPOSE_REMEDIATION, validated=False)
    _quiz(db, title="Validated", purpose=QUIZ_PURPOSE_PRACTICE, validated=True)

    response = admin_client.get("/api/admin/quizzes/editorial-queue", headers=_admin_headers(monkeypatch))

    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["id"] for row in rows] == [practice.id, remediation.id]
    assert set(rows[0]) >= {
        "title", "quiz_purpose", "recommended_week", "question_count",
        "missing_explanations", "answer_keys_validated", "quality_score",
        "source_type", "editorial_status",
    }


def test_seed_answer_rebalance_preserves_grading_and_is_idempotent(db):
    quiz = _quiz(db, title="Seed Position Test", purpose=QUIZ_PURPOSE_REQUIRED, required=True, checklist=True)
    question = quiz.questions[0]
    question.question_text = "Stable prompt used to choose a deterministic answer position"
    question.option_a = "Wrong A"
    question.option_b = "Correct text"
    question.option_c = "Wrong C"
    question.option_d = "Wrong D"
    question.correct_answer = "B"
    quiz.source_type = "seed"
    db.commit()

    rebalance_seed_answer_positions(db)
    db.flush()
    first = (question.option_a, question.option_b, question.option_c, question.option_d, question.correct_answer)
    assert getattr(question, f"option_{question.correct_answer.lower()}") == "Correct text"

    rebalance_seed_answer_positions(db)
    db.flush()
    second = (question.option_a, question.option_b, question.option_c, question.option_d, question.correct_answer)
    assert second == first
