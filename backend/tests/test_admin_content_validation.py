from app.config import load_env
from app.models.quiz import Question, Quiz
from app.routers.admin_content import router as admin_content_router
from app.routers.admin_quiz import router as admin_quiz_router
from conftest import make_client


client = make_client(admin_content_router, admin_quiz_router)


def _headers(monkeypatch):
    load_env.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "password")
    monkeypatch.setenv("ADMIN_API_KEY", "validation-test-key")
    load_env()
    return {"X-Admin-Key": "validation-test-key"}


def test_invalid_admin_payloads_return_422(monkeypatch):
    headers = _headers(monkeypatch)

    missing_required = client.post("/api/admin/modules", json={"code": "MOD-100"}, headers=headers)
    invalid_lab = client.post(
        "/api/admin/labs/templates",
        json={"title": "Bad Lab", "difficulty": 6, "week_number": 25},
        headers=headers,
    )
    unrestricted_field = client.post(
        "/api/admin/commands",
        json={"command": "ipconfig", "description": "Show IP", "is_admin": True},
        headers=headers,
    )

    assert missing_required.status_code == 422
    assert invalid_lab.status_code == 422
    assert unrestricted_field.status_code == 422


def test_existing_admin_form_formats_still_create_content(monkeypatch):
    headers = _headers(monkeypatch)
    module = client.post(
        "/api/admin/modules",
        json={"code": "MOD-100", "title": "Validated Module", "module_order": 100, "unlock_threshold": 70},
        headers=headers,
    )
    lesson = client.post(
        "/api/admin/lessons",
        json={"module_id": module.json()["data"]["module_id"], "title": "Validated Lesson", "lesson_order": 1, "summary": "", "video_url": "", "outcomes": []},
        headers=headers,
    )
    lab = client.post(
        "/api/admin/labs/templates",
        json={
            "title": "Validated Lab",
            "description": None,
            "lab_type": "windows",
            "difficulty": 2,
            "week_number": 10,
            "is_published": False,
            "success_criteria": {},
            "required_evidence": {},
            "hints": {},
            "environment_requirements": {},
        },
        headers=headers,
    )
    capstone = client.post(
        "/api/admin/capstones/templates",
        json={"title": "Validated Capstone", "week_number": 24, "requirements": {}, "deliverables": {}, "rubric": {}},
        headers=headers,
    )
    command = client.post(
        "/api/admin/commands",
        json={"command": "ipconfig", "description": "Show IP configuration", "syntax": "ipconfig /all", "category": "Windows", "example": "ipconfig"},
        headers=headers,
    )

    for response in (module, lesson, lab, capstone, command):
        assert response.status_code == 200, response.text


def test_quiz_import_schema_accepts_existing_csv_shape(monkeypatch):
    headers = _headers(monkeypatch)
    response = client.post(
        "/api/admin/quiz/scrape-save",
        json={
            "title": "Imported Quiz",
            "source_url": "csv_import",
            "week_number": 3,
            "lesson_id": None,
            "domain_id": "1.0",
            "questions": [
                {
                    "question_text": "Which command shows IP configuration?",
                    "option_a": "ipconfig",
                    "option_b": "dir",
                    "option_c": "copy",
                    "option_d": "del",
                    "correct_answer": "A",
                    "explanation": "ipconfig displays interface addressing.",
                }
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["question_count"] == 1


def test_examcompass_scrape_save_flags_invalid_question_without_rejecting_batch(monkeypatch, db):
    headers = _headers(monkeypatch)
    response = client.post(
        "/api/admin/quiz/scrape-save",
        json={
            "title": "Flagged Import",
            "source_url": "https://examcompass.com/quiz",
            "week_number": 3,
            "questions": [
                {
                    "question_text": "Good question",
                    "option_a": "Right",
                    "option_b": "Wrong",
                    "correct_answer": "A",
                    "explanation": "A is right.",
                },
                {
                    # Only one non-blank option — the validator rejects this,
                    # but the import must still save it (flagged) rather than
                    # silently dropping a previously-accepted ExamCompass row.
                    "question_text": "Bad question",
                    "option_a": "Only option",
                    "correct_answer": "A",
                },
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["question_count"] == 2
    assert body["flagged_for_review_count"] == 1

    # Imported content is stored for editorial review, never activated merely
    # because the transport succeeded.
    assert db.get(Quiz, body["quiz_id"]).is_active is False

    questions = db.query(Question).filter(Question.quiz_id == body["quiz_id"]).order_by(Question.id).all()
    assert questions[0].flagged_for_review is False
    assert questions[1].flagged_for_review is True
    assert questions[1].flag_reason


def test_bookmarklet_import_preserves_multiselect_and_flags_select_n_mismatch(monkeypatch, db):
    headers = _headers(monkeypatch)
    response = client.post(
        "/api/admin/quiz/bookmarklet-import",
        json={
            "title": "Bookmarklet Import",
            "source_url": "https://examcompass.com/quiz",
            "week_number": 3,
            "questions": [
                {
                    "question_text": "Which apply? (Select 2 answers)",
                    "option_a": "Right one",
                    "option_b": "Right two",
                    "option_c": "Wrong",
                    "correct_answer": "A",
                    "all_correct_answers": ["A", "B"],
                    "explanation": "A and B are both correct.",
                },
                {
                    "question_text": "Which apply? (Select 2 answers)",
                    "option_a": "Only one stored",
                    "option_b": "Wrong",
                    "option_c": "Wrong",
                    "correct_answer": "A",
                    "all_correct_answers": [],
                    "explanation": "",
                },
            ],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["flagged_for_review_count"] == 1

    questions = db.query(Question).filter(Question.quiz_id == body["quiz_id"]).order_by(Question.id).all()
    assert questions[0].correct_answers == "A,B"
    assert questions[0].all_correct_answers == ["A", "B"]
    assert questions[0].flagged_for_review is False
    assert questions[1].flagged_for_review is True
    assert "Select 2" in questions[1].flag_reason
    assert db.get(Quiz, body["quiz_id"]).is_active is False


def test_examcompass_import_flags_duplicate_options_for_review(monkeypatch, db):
    headers = _headers(monkeypatch)
    response = client.post(
        "/api/admin/quiz/scrape-save",
        json={
            "title": "Duplicate option import",
            "source_url": "https://examcompass.com/quiz",
            "week_number": 3,
            "questions": [{
                "question_text": "Which value is correct?",
                "option_a": "Same",
                "option_b": "Same",
                "correct_answer": "A",
            }],
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["flagged_for_review_count"] == 1
    question = db.query(Question).filter(Question.quiz_id == body["quiz_id"]).one()
    assert question.flagged_for_review is True
    assert "duplicate text" in question.flag_reason.lower()
