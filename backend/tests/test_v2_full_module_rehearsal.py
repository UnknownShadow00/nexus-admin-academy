"""Authenticated disposable rehearsal of one complete Nexus V2 module.

Playwright covers the rendered navigation, refresh, logout/login, and mobile
shell. This test owns the durable server transitions, including deliberately
failed/retried quiz and Service Desk attempts plus mentor grading.
"""

from app.models.certification import CertificationModule, ModuleAssessment, QuestionV2Meta
from app.models.grading import PendingGrade
from app.models.quiz import Question
from app.models.service_desk import ServiceDeskAssignment
from app.routers import admin_grading, labs, service_desk, v2_curriculum, v2_progress
from app.services.service_desk_realism import fixture_catalog
from app.services.v2_progress_service import record_activity
from app.services.v2_service_desk_onboarding import SERVICE_DESK_ONBOARDING
from conftest import auth_headers, enroll_v2, make_client, make_student
from test_service_desk_attempts import close
from test_service_desk_realism import action, walk
from test_service_desk_realism_v2 import ALL_TRACES
import seed_v2_foundation


MODULE = "module.aplus.core1.ip_configuration"


def _answers(db, questions):
    answers = {}
    for public in questions:
        question = db.get(Question, public["id"])
        meta = db.query(QuestionV2Meta).filter_by(question_id=question.id).one()
        if public["type"] == "short_answer":
            answers[str(question.id)] = meta.acceptable_answers[0]
        elif public["type"] == "free_response":
            concepts = [
                item if isinstance(item, str) else item.get("concept", "")
                for item in (meta.expected_concepts or [])
            ]
            answers[str(question.id)] = ". ".join(filter(None, concepts))
        else:
            answers[str(question.id)] = ",".join(question.all_correct_answers)
    return answers


def _mentor_resolve_pending(client, db, student, *, passed=True):
    for job in db.query(PendingGrade).filter_by(student_id=student.id).all():
        if job.resolved_passed is not None:
            continue
        response = client.post(
            f"/api/admin/grading/{job.id}/override",
            headers={"X-Admin-Key": "rehearsal-admin"},
            json={
                "reason": "Disposable full-module rehearsal decision",
                "score": 1.0 if passed else 0.0,
                "passed": passed,
            },
        )
        assert response.status_code == 200, response.text


def test_authenticated_full_module_rehearsal(db, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "rehearsal-admin")
    seed_v2_foundation.run(db)
    student = make_student(db, username="full-module-rehearsal")
    enroll_v2(monkeypatch, student)
    headers = auth_headers(student)
    client = make_client(
        v2_curriculum.router,
        v2_progress.router,
        labs.router,
        service_desk.router,
        admin_grading.router,
    )

    module = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=headers
    ).json()["data"]
    assert module["continue"]["kind"] in {"lesson", "resource"}

    # Lessons and required external resources use their real authenticated APIs.
    for lesson in module["lessons"]:
        for resource in lesson["resources"]:
            if resource["required"]:
                assert client.post(
                    f"/api/v2/curriculum/modules/{MODULE}/resources/{resource['key']}/activity",
                    headers=headers, json={"opened": True, "completed": True},
                ).status_code == 200
        assert client.post(
            f"/api/v2/curriculum/modules/{MODULE}/lessons/{lesson['key']}/complete",
            headers=headers,
        ).status_code == 200

    module_row = db.query(CertificationModule).filter_by(module_key=MODULE).one()
    assessments = db.query(ModuleAssessment).filter_by(
        certification_module_id=module_row.id, active=True
    ).all()
    knowledge = [
        row for row in assessments
        if row.assessment_role in {"quick_check", "module_quiz"}
    ]
    first_quick_check = next(row for row in knowledge if row.assessment_role == "quick_check")

    # Deliberate Quick Check failure, then a fresh server-selected retry.
    url = f"/api/v2/curriculum/modules/{MODULE}/assessments/{first_quick_check.assessment_key}"
    failed_attempt = client.get(url, headers=headers).json()["data"]
    failed = client.post(
        f"{url}/submit", headers=headers,
        json={"attempt_id": failed_attempt["attempt"]["id"], "answers": {}},
    )
    assert failed.status_code == 200
    _mentor_resolve_pending(client, db, student, passed=False)
    retry = client.post(f"{url}/attempts", headers=headers).json()["data"]
    assert retry["attempt"]["id"] != failed_attempt["attempt"]["id"]

    # Submit every required check correctly. A GET between start and submit is
    # the API equivalent of a browser refresh and must preserve question IDs.
    for assessment in knowledge:
        assessment_url = f"/api/v2/curriculum/modules/{MODULE}/assessments/{assessment.assessment_key}"
        if assessment.id == first_quick_check.id:
            started = retry
        else:
            started = client.get(assessment_url, headers=headers).json()["data"]
        refreshed = client.get(assessment_url, headers=headers).json()["data"]
        assert [q["id"] for q in refreshed["questions"]] == [q["id"] for q in started["questions"]]
        result = client.post(
            f"{assessment_url}/submit", headers=headers,
            json={
                "attempt_id": started["attempt"]["id"],
                "answers": _answers(db, started["questions"]),
            },
        )
        assert result.status_code == 200, result.text
        _mentor_resolve_pending(client, db, student, passed=True)

    practical = next(row for row in assessments if row.assessment_role == "practical")
    lab_params = {
        "v2_module_key": MODULE,
        "v2_assessment_key": practical.assessment_key,
    }
    assert client.post(
        f"/api/labs/{practical.lab_template_id}/start",
        headers=headers, params=lab_params,
    ).status_code in {200, 202}
    assert client.post(
        f"/api/labs/{practical.lab_template_id}/submit",
        headers=headers, params=lab_params,
        json={"notes": "Reviewed ipconfig, gateway, DHCP, DNS, ping, and nslookup evidence.", "answers": {}},
    ).status_code == 200

    ticket = next(row for row in assessments if row.assessment_role == "service_desk")
    for orientation_key in SERVICE_DESK_ONBOARDING:
        orientation = db.query(ModuleAssessment).filter_by(
            assessment_key=orientation_key
        ).one()
        orientation_module = db.get(
            CertificationModule, orientation.certification_module_id
        )
        record_activity(
            db,
            student_id=student.id,
            module_key=orientation_module.module_key,
            activity_type="service_desk",
            ref_key=orientation_key,
            status="passed",
            score=100,
            passed=True,
            commit=True,
        )
    launch = client.post(
        f"/api/v2/curriculum/modules/{MODULE}/service-desk/{ticket.assessment_key}/launch",
        headers=headers,
    )
    assert launch.status_code == 200
    assignment = db.query(ServiceDeskAssignment).filter_by(
        student_id=student.id,
        scenario_id=ticket.service_desk_scenario_id,
        mode="learning",
    ).one()
    first_ticket = client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts", headers=headers
    ).json()
    close(client, student, first_ticket["id"])
    failed_ticket = client.post(
        f"/api/service-desk/attempts/{first_ticket['id']}/complete",
        headers=headers, json={"idempotency_key": "rehearsal-fail"},
    )
    assert failed_ticket.json()["passed"] is False
    second_ticket = client.post(
        f"/api/service-desk/assignments/{assignment.id}/attempts", headers=headers
    ).json()
    assert client.post(
        f"/api/service-desk/attempts/{second_ticket['id']}/hints",
        headers=headers,
        json={"idempotency_key": "rehearsal-hint", "tool": "ticket", "payload": {"step": 1}},
    ).status_code == 201
    ticket_id = "INC2503"
    walk(client, student, second_ticket["id"], ticket_id, ALL_TRACES[ticket_id]["commands"])
    fixture = fixture_catalog()[ticket_id]
    note = action(
        client, student, second_ticket["id"], ticket_id,
        event_type="remote_desktop.add_internal_note",
        payload={
            "ticketId": ticket_id,
            "assetTag": fixture["assetTag"],
            "text": ALL_TRACES[ticket_id]["note"],
        },
        suffix="rehearsal-note",
    )
    assert note.status_code in {200, 201}
    route = fixture.get("escalation")
    if route:
        escalated = action(
            client, student, second_ticket["id"], ticket_id,
            event_type="ticket.escalate",
            payload={
                "ticketId": ticket_id,
                "routeTeam": route["route"],
                "reason": route["reasons"][0],
            },
            suffix="rehearsal-escalate",
        )
        assert escalated.status_code in {200, 201}
    else:
        close(client, student, second_ticket["id"])
    passed_ticket = client.post(
        f"/api/service-desk/attempts/{second_ticket['id']}/complete",
        headers=headers, json={"idempotency_key": "rehearsal-pass"},
    )
    assert passed_ticket.json()["passed"] is True, passed_ticket.json()

    prompts = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=headers
    ).json()["data"]["explain_prompts"]
    for prompt in prompts:
        submitted = client.post(
            f"/api/v2/curriculum/modules/{MODULE}/explain/{prompt['key']}/submit",
            headers=headers,
            json={"answer": "A detailed response in alternate wording that requires mentor review."},
        )
        assert submitted.status_code == 200
        _mentor_resolve_pending(client, db, student, passed=True)

    final = client.get(
        f"/api/v2/curriculum/modules/{MODULE}", headers=headers
    ).json()["data"]
    assert final["progress"]["module_complete"] is True
    assert final["continue"]["kind"] == "complete"
    progress = client.get(
        f"/api/v2/progress/module/{MODULE}", headers=headers
    ).json()["data"]
    assert progress["module_complete"] is True
