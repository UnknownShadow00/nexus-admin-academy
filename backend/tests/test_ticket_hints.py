"""TB-04: ticket hint ladder + XP penalty tests.

AI grading is mocked (no live provider in this environment — stated per the
project's honesty rules); penalty math and reveal mechanics are exercised
against real DB rows through the real endpoints.
"""
from unittest.mock import AsyncMock, patch

from conftest import auth_headers, make_client, make_student
from app.models.ticket import Ticket, TicketSubmission
from app.routers.tickets import hint_multiplier, router as tickets_router

client = make_client(tickets_router)


# ------------------------------------------------------------ penalty math

def test_hint_multiplier_ladder():
    assert hint_multiplier(0) == 1.0
    assert hint_multiplier(1) == 0.95
    assert hint_multiplier(2) == 0.90
    assert hint_multiplier(3) == 0.80
    assert hint_multiplier(4) == 0.65
    # beyond ladder length clamps to deepest penalty, floored at 40%
    assert hint_multiplier(9) == 0.65


# ------------------------------------------------------------ fixtures

def _seed_ticket(db, hints=None):
    t = Ticket(
        title="DNS resolution failing",
        description="User cannot browse.",
        difficulty=2,
        week_number=1,
        hints=hints if hints is not None else [
            "Focus on name resolution, not connectivity.",
            "Compare ping by IP vs ping by hostname.",
            "Check the configured DNS server with ipconfig /all.",
            "The DNS server address is wrong — correct it and flush the cache.",
        ],
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# ------------------------------------------------------------ reveal endpoint

def test_hint_reveal_progression(db):
    student = make_student(db)
    t = _seed_ticket(db)
    r1 = client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student))
    assert r1.status_code == 200
    d1 = r1.json()["data"]
    assert d1["hints_used"] == 1
    assert len(d1["hints_revealed"]) == 1
    assert d1["current_xp_multiplier"] == 0.95
    assert d1["next_hint_xp_penalty_percent"] == 10  # cost shown BEFORE next reveal

    r2 = client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student))
    d2 = r2.json()["data"]
    assert d2["hints_used"] == 2
    assert d2["hints_revealed"][-1].startswith("Compare ping")


def test_hint_exhaustion_rejected(db):
    student = make_student(db)
    t = _seed_ticket(db, hints=["only hint"])
    assert client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student)).status_code == 200
    r = client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student))
    assert r.status_code == 400
    assert "already revealed" in r.json()["detail"]


def test_hintless_ticket_404(db):
    student = make_student(db)
    t = _seed_ticket(db, hints=[])
    r = client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student))
    assert r.status_code == 404


def test_hints_isolated_per_student(db):
    """Two students' reveals must not bleed into each other (isolation check)."""
    s1, s2 = make_student(db), make_student(db, username="student2")
    t = _seed_ticket(db)
    client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(s1))
    client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(s1))
    r = client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(s2))
    assert r.json()["data"]["hints_used"] == 1  # s2 starts fresh


# ------------------------------------------------------------ XP penalty applied

_MOCK_GRADE = {
    "final_score": 8,
    "structure_score": 8,
    "technical_score": 8,
    "communication_score": 8,
    "strengths": [],
    "weaknesses": [],
    "feedback": "mocked",
}


def _submit_payload(student):
    return {
        "student_id": student.id,
        "symptom": "User cannot browse; ping by IP works, by hostname fails.",
        "root_cause": "Workstation configured with an incorrect DNS server address.",
        "resolution": "Corrected the DNS server setting and flushed the resolver cache.",
        "verification": "nslookup resolves and browsing verified working with the user.",
        "commands_used": "ping, ipconfig /all, nslookup, ipconfig /flushdns",
    }


def test_xp_reduced_after_hints(db):
    student = make_student(db)
    t = _seed_ticket(db)
    # reveal two hints (multiplier 0.90), then submit with mocked grading
    client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student))
    client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(student))
    with patch("app.routers.tickets.grade_ticket_submission", new=AsyncMock(return_value=_MOCK_GRADE)), \
         patch("app.routers.tickets.grade_ticket_with_answer_key", new=AsyncMock(return_value=_MOCK_GRADE)):
        r = client.post(f"/api/tickets/{t.id}/submit", json=_submit_payload(student), headers=auth_headers(student))
    assert r.status_code == 200, r.text
    # base 8*10=80, solo multiplier 1.0, hint multiplier 0.90 → 72
    assert r.json()["data"]["xp_awarded"] == 72
    sub = db.query(TicketSubmission).filter_by(student_id=student.id, ticket_id=t.id).first()
    assert sub.hints_used == 2


def test_xp_unreduced_without_hints(db):
    student = make_student(db)
    t = _seed_ticket(db)
    with patch("app.routers.tickets.grade_ticket_submission", new=AsyncMock(return_value=_MOCK_GRADE)), \
         patch("app.routers.tickets.grade_ticket_with_answer_key", new=AsyncMock(return_value=_MOCK_GRADE)):
        r = client.post(f"/api/tickets/{t.id}/submit", json=_submit_payload(student), headers=auth_headers(student))
    assert r.status_code == 200, r.text
    assert r.json()["data"]["xp_awarded"] == 80
