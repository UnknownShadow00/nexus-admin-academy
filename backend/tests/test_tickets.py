from conftest import auth_headers, make_client, make_student
from app.models.ticket import Ticket
from app.routers.tickets import router

client = make_client(router)


def _seed_ticket(db, title="PC won't boot", week_number=1):
    ticket = Ticket(
        title=title,
        description="The PC powers on but does not POST.",
        difficulty=2,
        week_number=week_number,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def test_list_tickets_empty(db):
    student = make_student(db)
    res = client.get("/api/tickets", headers=auth_headers(student))
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_list_tickets_returns_seeded(db):
    student = make_student(db)
    ticket = _seed_ticket(db, title="No display output")
    res = client.get("/api/tickets", headers=auth_headers(student))
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "No display output"
    assert data[0]["id"] == ticket.id


def test_list_tickets_week_filter(db):
    student = make_student(db)
    _seed_ticket(db, title="Week 1 ticket", week_number=1)
    _seed_ticket(db, title="Week 2 ticket", week_number=2)
    res = client.get("/api/tickets?week_number=1", headers=auth_headers(student))
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["title"] == "Week 1 ticket"


def test_list_tickets_unauthenticated(db):
    res = client.get("/api/tickets")
    assert res.status_code == 401
