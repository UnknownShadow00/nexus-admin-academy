from datetime import date

from conftest import auth_headers, make_client, make_student

from app.models.quiz import (
    EDITORIAL_STATUS_VALIDATED,
    QUIZ_STATUS_PUBLISHED,
    Question,
    Quiz,
)
from app.models.flashcard import FlashcardReview
from app.models.xp_ledger import XPLedger
from app.routers.admin_quiz import router as admin_quiz_router
from app.routers.flashcards import router as flashcards_router
from app.routers.quizzes import router as quizzes_router

client = make_client(quizzes_router, flashcards_router, admin_quiz_router)


def _seed_quiz(db, title="Help Desk Basics", week_number=1):
    quiz = Quiz(
        title=title,
        week_number=week_number,
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def _seed_multi_select_question(db, quiz_id):
    question = Question(
        quiz_id=quiz_id,
        question_text="Which basic information is required? (Select 3 answers)",
        option_a="User information",
        option_b="Expected resolution date",
        option_c="Device information",
        option_d="Escalation levels required",
        option_e="Problem description",
        option_f=None,
        option_g=None,
        option_h=None,
        correct_answer="A",
        correct_answers="A,C,E",
        explanation="Tickets need requester, device, and problem details up front.",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def _seed_single_choice_question(db, quiz_id):
    question = Question(
        quiz_id=quiz_id,
        question_text="What port does HTTPS use?",
        option_a="443",
        option_b="80",
        option_c="21",
        option_d="25",
        correct_answer="A",
        explanation="HTTPS uses TCP port 443.",
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def test_multi_select_partial_answer_is_wrong_and_creates_flashcard(db):
    student = make_student(db)
    quiz = _seed_quiz(db)
    question = _seed_multi_select_question(db, quiz.id)

    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "A"}},
        headers=auth_headers(student),
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["score"] == 0
    assert body["results"][0]["is_correct"] is False
    assert body["results"][0]["correct_answers"] == ["A", "C", "E"]

    card = (
        db.query(FlashcardReview)
        .filter_by(student_id=student.id, question_id=question.id)
        .first()
    )
    assert card is not None
    assert card.last_wrong_answer == "A"


def test_multi_select_extra_answer_is_wrong(db):
    student = make_student(db)
    quiz = _seed_quiz(db)
    question = _seed_multi_select_question(db, quiz.id)

    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "A,C,E,B"}},
        headers=auth_headers(student),
    )
    assert res.json()["data"]["results"][0]["is_correct"] is False


def test_multi_select_order_independent_exact_match_is_correct(db):
    student = make_student(db)
    quiz = _seed_quiz(db)
    question = _seed_multi_select_question(db, quiz.id)

    res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "E,A,C"}},
        headers=auth_headers(student),
    )
    body = res.json()["data"]
    assert body["results"][0]["is_correct"] is True
    assert body["score"] == 1

    # No flashcard should be created for a correct answer.
    assert (
        db.query(FlashcardReview)
        .filter_by(student_id=student.id, question_id=question.id)
        .first()
        is None
    )


def test_daily_review_card_hides_blank_options_and_shows_all_correct_answers(db):
    student = make_student(db)
    quiz = _seed_quiz(db)
    question = _seed_multi_select_question(db, quiz.id)

    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "A"}},
        headers=auth_headers(student),
    )

    res = client.get("/api/flashcards/due", headers=auth_headers(student))
    assert res.status_code == 200
    cards = res.json()["data"]
    assert len(cards) == 1
    card = cards[0]

    # F, G, H were NULL in the DB and must never be rendered.
    assert set(card["options"].keys()) == {"A", "B", "C", "D", "E"}
    assert "F" not in card["options"]
    assert "G" not in card["options"]
    assert "H" not in card["options"]

    # All three correct answers must be present, not just the legacy single letter.
    assert card["correct_answers"] == ["A", "C", "E"]
    assert card["is_multi_select"] is True
    assert card["last_wrong_answer"] == "A"
    assert card["explanation"]
    assert card["quiz_title"] == "Help Desk Basics"


def test_rating_flashcard_does_not_change_quiz_score_or_award_xp(db):
    student = make_student(db)
    quiz = _seed_quiz(db)
    question = _seed_single_choice_question(db, quiz.id)

    submit_res = client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": student.id, "answers": {str(question.id): "B"}},
        headers=auth_headers(student),
    )
    original_score = submit_res.json()["data"]["score"]
    xp_entries_before = db.query(XPLedger).filter_by(student_id=student.id).count()

    due = client.get("/api/flashcards/due", headers=auth_headers(student)).json()[
        "data"
    ]
    card_id = due[0]["id"]

    rate_res = client.post(
        f"/api/flashcards/{card_id}/rate",
        json={"rating": 3},
        headers=auth_headers(student),
    )
    assert rate_res.status_code == 200

    xp_entries_after = db.query(XPLedger).filter_by(student_id=student.id).count()
    assert xp_entries_after == xp_entries_before

    review_res = client.get(
        f"/api/quizzes/{quiz.id}/review/{student.id}", headers=auth_headers(student)
    )
    assert review_res.json()["data"]["score"] == original_score


def test_review_state_distinguishes_fresh_due_and_clear(db):
    fresh = make_student(db, username="fresh-review")
    fresh_body = client.get("/api/flashcards/due", headers=auth_headers(fresh)).json()
    assert fresh_body["review_state"] == "fresh"
    assert fresh_body["due_count"] == 0
    assert fresh_body["priorities"] == []

    quiz = _seed_quiz(db, title="DHCP and APIPA Quiz")
    question = _seed_single_choice_question(db, quiz.id)
    question.question_text = "What does a 169.254 address suggest about DHCP?"
    question.tags = ["networking.ipv4.dhcp.03"]
    db.commit()
    client.post(
        f"/api/quizzes/{quiz.id}/submit",
        json={"student_id": fresh.id, "answers": {str(question.id): "B"}},
        headers=auth_headers(fresh),
    )

    due_body = client.get("/api/flashcards/due", headers=auth_headers(fresh)).json()
    assert due_body["review_state"] == "due"
    assert due_body["due_count"] == 1
    assert due_body["priority_count"] == 1
    assert len(due_body["priorities"]) == 1
    assert due_body["priorities"][0]["concept_name"] == "DHCP and APIPA"
    assert "missed" in due_body["priorities"][0]["reason"].lower()
    assert due_body["priorities"][0]["review_url"]

    card_id = due_body["data"][0]["id"]
    client.post(
        f"/api/flashcards/{card_id}/rate",
        json={"rating": 3},
        headers=auth_headers(fresh),
    )
    clear_body = client.get("/api/flashcards/due", headers=auth_headers(fresh)).json()
    assert clear_body["review_state"] == "clear"
    assert clear_body["due_count"] == 0


def test_review_priorities_are_deterministic_and_limited_to_three(db):
    student = make_student(db, username="priority-review")
    quiz = _seed_quiz(db, title="Support Concepts Quiz")
    questions = []
    prompts = [
        "Ticket concept one",
        "Ticket concept two",
        "What does a 169.254 address suggest about DHCP?",
        "What should you check in a printer queue?",
        "What does DNS resolve?",
    ]
    for index, prompt in enumerate(prompts):
        question = Question(
            quiz_id=quiz.id,
            question_text=prompt,
            option_a="Correct",
            option_b="Wrong",
            correct_answer="A",
            explanation="Use the ticket workflow.",
            tags=[f"internal.ticket.{index}"],
        )
        db.add(question)
        questions.append(question)
    db.flush()
    for index, question in enumerate(questions):
        db.add(
            FlashcardReview(
                student_id=student.id,
                question_id=question.id,
                due_date=date.today(),
                review_count=index,
                last_rating=1 if index else None,
                last_wrong_answer="B",
            )
        )
    db.commit()

    body = client.get("/api/flashcards/due", headers=auth_headers(student)).json()

    assert body["due_count"] == 5
    assert body["priority_count"] == 3
    assert len(body["priorities"]) == 3
    assert [row["question_id"] for row in body["priorities"]] == [
        questions[0].id,
        questions[2].id,
        questions[3].id,
    ]
    assert len({row["concept_name"] for row in body["priorities"]}) == 3
    assert all("internal." not in row["concept_name"] for row in body["priorities"])
