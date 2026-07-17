"""TB-05: deterministic per-student ticket parametrization tests."""
from conftest import auth_headers, make_client, make_student
from app.models.ticket import Ticket
from app.routers.tickets import router as tickets_router
from app.services.ticket_params import resolve_parameters, substitute

client = make_client(tickets_router)

PARAMS = {
    "placeholders": {
        "USERNAME": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
        "DNS_SERVER": ["10.0.0.53", "192.168.9.9", "172.16.0.2", "8.8.4.3", "10.10.10.1"],
    }
}


def _seed_param_ticket(db):
    t = Ticket(
        title="Account lockout: {{USERNAME}}",
        description="User {{USERNAME}} cannot log in. DNS on their PC points to {{DNS_SERVER}}.",
        difficulty=2,
        week_number=3,
        parameters=PARAMS,
        hints=["Check the account status for {{USERNAME}} first."],
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def test_resolver_deterministic():
    v1 = resolve_parameters(PARAMS, student_id=7)
    v2 = resolve_parameters(PARAMS, student_id=7)
    assert v1 == v2  # stable across calls
    assert v1["USERNAME"] == "rpatel"  # 7 % 5 == 2


def test_substitute_leaves_unknown_placeholders():
    assert substitute("Hello {{UNKNOWN}}", {"USERNAME": "x"}) == "Hello {{UNKNOWN}}"


def test_two_students_see_different_scenarios(db):
    s1 = make_student(db)                       # id 1 → index 1
    s2 = make_student(db, username="student2")  # id 2 → index 2
    t = _seed_param_ticket(db)
    d1 = client.get(f"/api/tickets/{t.id}", headers=auth_headers(s1)).json()["data"]
    d2 = client.get(f"/api/tickets/{t.id}", headers=auth_headers(s2)).json()["data"]
    assert "{{" not in d1["description"] and "{{" not in d2["description"]
    assert d1["description"] != d2["description"]
    assert d1["title"] != d2["title"]


def test_hints_substituted(db):
    s1 = make_student(db)
    t = _seed_param_ticket(db)
    r = client.post(f"/api/tickets/{t.id}/hint", headers=auth_headers(s1))
    hint = r.json()["data"]["hints_revealed"][0]
    assert "{{" not in hint
    assert "tnguyen" in hint  # student id 1 → index 1


def test_unparametrized_ticket_unchanged(db):
    s1 = make_student(db)
    t = Ticket(title="Plain ticket", description="No placeholders here.", difficulty=1, week_number=1)
    db.add(t)
    db.commit()
    d = client.get(f"/api/tickets/{t.id}", headers=auth_headers(s1)).json()["data"]
    assert d["title"] == "Plain ticket"
    assert d["description"] == "No placeholders here."
