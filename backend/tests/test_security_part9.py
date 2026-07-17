"""Part 9 security audit — regression tests.

Each test pins a fixed vulnerability:
- unbounded evidence uploads (disk-fill DoS)
- evidence artifacts linkable across students (IDOR)
- 'Bearer <anything>' passing allow_admin_or_student
- deterministic, never-expiring admin session cookie
- quiz answers/explanations leaking before submission
"""
import io
import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from conftest import auth_headers, make_client, make_student
from app.models.evidence import EvidenceArtifact
from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
from app.models.ticket import Ticket
from app.routers.evidence import router as evidence_router
from app.routers.quizzes import router as quizzes_router
from app.routers.tickets import router as tickets_router

evidence_client = make_client(evidence_router)
tickets_client = make_client(tickets_router)
quiz_client = make_client(quizzes_router)


def _seed_ticket(db):
    t = Ticket(title="Evidence target", description="d", difficulty=1, week_number=1)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _png_upload(size_bytes):
    return {"file": ("shot.png", io.BytesIO(b"\x89PNG" + b"0" * size_bytes), "image/png")}


# ------------------------------------------------------------ upload limits

def test_upload_size_cap_413(db, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/nexus-test-uploads")
    import app.routers.evidence as ev
    monkeypatch.setattr(ev, "MAX_UPLOAD_BYTES", 1024)  # 1 KB cap for the test
    student = make_student(db)
    ticket = _seed_ticket(db)
    r = evidence_client.post(
        "/api/evidence/upload",
        files=_png_upload(4096),
        data={"ticket_id": str(ticket.id), "artifact_type": "screenshot"},
        headers=auth_headers(student),
    )
    assert r.status_code == 413


def test_upload_bad_extension_rejected(db, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/nexus-test-uploads")
    student = make_student(db)
    ticket = _seed_ticket(db)
    r = evidence_client.post(
        "/api/evidence/upload",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        data={"ticket_id": str(ticket.id), "artifact_type": "screenshot"},
        headers=auth_headers(student),
    )
    assert r.status_code == 400


def test_upload_stamps_ownership(db, monkeypatch):
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/nexus-test-uploads")
    student = make_student(db)
    ticket = _seed_ticket(db)
    r = evidence_client.post(
        "/api/evidence/upload",
        files=_png_upload(64),
        data={"ticket_id": str(ticket.id), "artifact_type": "screenshot"},
        headers=auth_headers(student),
    )
    assert r.status_code == 200, r.text
    row = db.query(EvidenceArtifact).get(r.json()["data"]["artifact_id"])
    assert row.student_id == student.id


# ------------------------------------------------------------ evidence IDOR

def _submit_payload(student, before_id=None):
    return {
        "student_id": student.id,
        "symptom": "Websites fail by name; IP ping works fine today.",
        "root_cause": "Incorrect DNS server configured on the NIC.",
        "resolution": "Corrected the DNS server and flushed the cache.",
        "verification": "nslookup resolves; browsing confirmed with the user.",
        "before_screenshot_id": before_id,
    }


def test_cannot_link_another_students_evidence(db):
    s1 = make_student(db)
    s2 = make_student(db, username="student2")
    ticket = _seed_ticket(db)
    theirs = EvidenceArtifact(
        student_id=s1.id, submission_type="ticket", submission_id=ticket.id,
        artifact_type="screenshot", storage_key="x.png",
    )
    db.add(theirs)
    db.commit()
    r = tickets_client.post(
        f"/api/tickets/{ticket.id}/submit",
        json=_submit_payload(s2, before_id=theirs.id),
        headers=auth_headers(s2),
    )
    assert r.status_code == 403
    assert "not yours" in r.json()["detail"]


def test_legacy_unowned_evidence_not_linkable(db):
    """Pre-fix artifacts (student_id NULL) cannot be claimed by anyone."""
    s1 = make_student(db)
    ticket = _seed_ticket(db)
    legacy = EvidenceArtifact(
        student_id=None, submission_type="ticket", submission_id=ticket.id,
        artifact_type="screenshot", storage_key="old.png",
    )
    db.add(legacy)
    db.commit()
    r = tickets_client.post(
        f"/api/tickets/{ticket.id}/submit",
        json=_submit_payload(s1, before_id=legacy.id),
        headers=auth_headers(s1),
    )
    assert r.status_code == 403


# ------------------------------------------------------------ auth hardening

def _admin_env(monkeypatch):
    from app.config import load_env
    load_env.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "shadowgarden")
    monkeypatch.setenv("ADMIN_PASSWORD", "IloveIT")
    monkeypatch.setenv("ADMIN_API_KEY", "unit-test-api-key")
    load_env()


def test_bearer_garbage_rejected(db, monkeypatch):
    """allow_admin_or_student previously passed ANY Bearer string."""
    _admin_env(monkeypatch)
    from app.services.admin_auth import allow_admin_or_student
    app = FastAPI()

    @app.get("/guarded", dependencies=[Depends(allow_admin_or_student)])
    def guarded():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/guarded", headers={"Authorization": "Bearer total-garbage"})
    assert r.status_code == 401


def test_valid_student_jwt_still_passes(db, monkeypatch):
    _admin_env(monkeypatch)
    from app.services.admin_auth import allow_admin_or_student
    student = make_student(db)
    app = FastAPI()

    @app.get("/guarded", dependencies=[Depends(allow_admin_or_student)])
    def guarded():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/guarded", headers=auth_headers(student))
    assert r.status_code == 200


def test_legacy_deterministic_admin_cookie_rejected(monkeypatch):
    """sha256(password + constant) cookies must no longer authenticate."""
    _admin_env(monkeypatch)
    from hashlib import sha256
    from app.services.admin_auth import verify_admin
    app = FastAPI()

    @app.get("/adm", dependencies=[Depends(verify_admin)])
    def adm():
        return {"ok": True}

    client = TestClient(app)
    legacy = sha256("IloveIT:nexus-admin-session:v1".encode()).hexdigest()
    r = client.get("/adm", cookies={"admin_session": legacy})
    assert r.status_code == 403


def test_random_admin_session_roundtrip(monkeypatch):
    """Login issues a working random session; logout revokes it server-side."""
    _admin_env(monkeypatch)
    from app.routers.admin_session import router as session_router
    from app.services.admin_auth import verify_admin
    app = FastAPI()
    app.include_router(session_router)

    @app.get("/adm", dependencies=[Depends(verify_admin)])
    def adm():
        return {"ok": True}

    client = TestClient(app)
    login = client.post("/api/admin/session/login",
                        json={"username": "shadowgarden", "password": "IloveIT"})
    assert login.status_code == 200
    assert client.get("/adm").status_code == 200
    cookie_value = client.cookies.get("admin_session")
    client.post("/api/admin/session/logout")
    # replaying the revoked cookie must fail even though the value was valid once
    replay = TestClient(app)
    r = replay.get("/adm", cookies={"admin_session": cookie_value})
    assert r.status_code == 403


# ------------------------------------------------------------ answer leakage

def test_quiz_get_leaks_no_answers(db):
    student = make_student(db)
    quiz = Quiz(title="LeakCheck", week_number=1, status=QUIZ_STATUS_PUBLISHED)
    db.add(quiz)
    db.flush()
    db.add(Question(quiz_id=quiz.id, question_text="Q?", option_a="a", option_b="b",
                    option_c="c", option_d="d", correct_answer="A",
                    explanation="the secret why"))
    db.commit()
    r = quiz_client.get(f"/api/quizzes/{quiz.id}", headers=auth_headers(student))
    body = r.text
    assert "correct_answer" not in body
    assert "the secret why" not in body


def test_ticket_get_leaks_no_model_answer(db):
    student = make_student(db)
    t = Ticket(title="LeakCheck T", description="d", difficulty=1, week_number=1,
               root_cause="SECRET ROOT CAUSE", model_answer="SECRET MODEL ANSWER",
               scoring_anchors={"root_cause": "2 = SECRET ANCHOR"})
    db.add(t)
    db.commit()
    r = tickets_client.get(f"/api/tickets/{t.id}", headers=auth_headers(student))
    assert "SECRET" not in r.text
