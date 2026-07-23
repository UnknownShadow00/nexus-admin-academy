from app.models.curriculum_video import CurriculumVideo
from app.models.quiz import EDITORIAL_STATUS_VALIDATED, QUIZ_STATUS_PUBLISHED, Question, Quiz, QuizAttempt
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.routers import study_tracker

from conftest import auth_headers, make_client, make_student


def test_catalog_uses_explicit_mapping_and_shared_score_without_answers(db):
    student = make_student(db, "mapped-catalog-student")
    week = TrainingWeek(
        week_number=1,
        display_order=1,
        title="Basics",
        learning_goals=[],
        is_active=True,
        requires_previous_week=False,
    )
    quiz = Quiz(
        id=20,
        title="Approved Basics Quiz",
        question_count=1,
        week_number=1,
        domain_id="1.0",
        status=QUIZ_STATUS_PUBLISHED,
        editorial_status=EDITORIAL_STATUS_VALIDATED,
        answer_keys_validated=True,
        is_active=True,
    )
    videos = [
        CurriculumVideo(
            id=video_id,
            video_key=f"mapped-{video_id}",
            section="Basics",
            section_order=1,
            title=title,
            video_order=video_id,
            active=True,
        )
        for video_id, title in [(10, "First topic"), (11, "Second topic")]
    ]
    db.add_all([week, quiz, *videos])
    db.flush()
    db.add(Question(
        quiz_id=quiz.id,
        question_text="Hidden question",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_answer="A",
        explanation="Hidden explanation",
    ))
    metadata = {
        "quiz_id": quiz.id,
        "quiz_mapping_basis": "topic_group",
        "quiz_mapping_confidence": "Strong topical",
        "quiz_mapping_evidence": "Reviewed test group.",
    }
    for order, video in enumerate(videos, start=1):
        db.add(TrainingWeekActivity(
            training_week_id=week.id,
            stable_id=f"week-1-video-{video.id}",
            activity_type="video",
            content_ref=str(video.id),
            display_order=order,
            is_required=True,
            metadata_json=metadata,
        ))
    db.add(QuizAttempt(
        student_id=student.id,
        quiz_id=quiz.id,
        answers={"1": "A"},
        results=[],
        score=1,
        best_score=1,
        first_attempt_xp=0,
        xp_awarded=0,
    ))
    db.commit()

    client = make_client(study_tracker.router)
    headers = auth_headers(student)
    curriculum = client.get("/api/study-tracker/curriculum", headers=headers)
    tracker = client.get(f"/api/study-tracker/{student.id}", headers=headers)

    assert curriculum.status_code == 200
    rows = curriculum.json()["data"][0]["videos"]
    assert [row["quiz_id"] for row in rows] == [quiz.id, quiz.id]
    assert all(row["quiz_mapping_basis"] == "topic_group" for row in rows)
    assert "correct_answer" not in curriculum.text
    assert "Hidden explanation" not in curriculum.text
    assert tracker.status_code == 200
    assert tracker.json()["data"]["quiz_scores"][str(quiz.id)]["pct"] == 100


def test_student_cannot_read_another_students_catalog_scores(db):
    student = make_student(db, "catalog-owner")
    other = make_student(db, "catalog-other")
    client = make_client(study_tracker.router)

    response = client.get(f"/api/study-tracker/{student.id}", headers=auth_headers(other))

    assert response.status_code == 403
