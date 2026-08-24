import json

import pytest

from conftest import auth_headers, make_client, make_student
from app.models.lab import LabTemplate
from app.routers.labs import router
from app.services.network_linux_cloud_practical import NETWORK_LINUX_CLOUD_CASES


client = make_client(router)


def _seed_case(db, week_number: int) -> LabTemplate:
    case = NETWORK_LINUX_CLOUD_CASES[week_number]
    lab = LabTemplate(
        title=case["title"],
        description=case["description"],
        lab_type=case["lab_type"],
        difficulty=case["difficulty"],
        week_number=1,
        estimated_minutes=case["estimated_minutes"],
        is_published=True,
        environment_requirements={},
        setup_instructions=case["setup_instructions"],
        success_criteria={
            "evidence_case_workbench": case["workbench"],
            "questions": case["questions"],
        },
        required_evidence={},
        hints={},
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


@pytest.mark.parametrize("week_number", [8, 11, 12, 18, 19, 20, 22])
def test_phase4c2_cases_hide_outcome_and_require_server_verified_plan_and_notes(db, week_number):
    student = make_student(db, f"phase4c2-week-{week_number}")
    lab = _seed_case(db, week_number)
    case = NETWORK_LINUX_CLOUD_CASES[week_number]
    answers = {question["id"]: question["correct"] for question in case["questions"]}
    wrong_answers = {
        question["id"]: [next(option["id"] for option in question["options"] if option["id"] not in question["correct"])]
        for question in case["questions"]
    }
    inspected = case["workbench"]["required_inspections"]

    fetched = client.get(f"/api/labs/{lab.id}", headers=auth_headers(student))
    assert fetched.status_code == 200
    safe = fetched.json()["data"]
    assert "verification" not in safe["success_criteria"]["evidence_case_workbench"]
    assert all("correct" not in question and "explanation" not in question for question in safe["questions"])

    wrong = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": wrong_answers, "inspected_panel_ids": inspected},
        headers=auth_headers(student),
    )
    assert wrong.status_code == 200
    assert wrong.json()["data"] == {
        "ready": False,
        "message": "The selected path did not produce the expected state. Re-open the evidence and revise the unsupported decision.",
    }

    missing_evidence = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": answers, "inspected_panel_ids": inspected[:-1]},
        headers=auth_headers(student),
    )
    assert missing_evidence.status_code == 200
    assert missing_evidence.json()["data"]["ready"] is False

    verified = client.post(
        f"/api/labs/{lab.id}/verify",
        json={"answers": answers, "inspected_panel_ids": inspected},
        headers=auth_headers(student),
    )
    assert verified.status_code == 200
    assert verified.json()["data"]["ready"] is True
    assert verified.json()["data"]["verification"]["fields"]

    notes = {
        "issue": "Recorded incident scope and symptom.",
        "evidence": "Recorded the decisive case evidence.",
        "action": "Selected the narrow approved response.",
        "verification": "Repeated the original path and observed the expected state.",
    }
    for field in case["workbench"].get("additional_note_fields", []):
        notes[field["id"]] = "Named the owner, scope, evidence, and follow-up."
    submitted = client.post(
        f"/api/labs/{lab.id}/submit",
        json={"answers": answers, "notes": json.dumps(notes)},
        headers=auth_headers(student),
    )
    assert submitted.status_code == 200
    assert submitted.json()["data"]["structured_feedback"]["score_pct"] == 100
    assert submitted.json()["data"]["status"] == "submitted"
