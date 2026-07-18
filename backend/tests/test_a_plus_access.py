from conftest import auth_headers, make_client, make_student

from app.models.capstone import CapstoneTemplate
from app.models.cli_lab import CliLab
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabTemplate
from app.models.ticket import Ticket
from app.models.video_watch import VideoWatch
from app.routers.auth import router as auth_router
from app.routers.admin_content import router as admin_content_router
from app.routers.capstones import router as capstones_router
from app.routers.cli_labs import router as cli_labs_router
from app.routers.evidence import router as evidence_router
from app.routers.labs import router as labs_router
from app.routers.tickets import router as tickets_router
from app.routers.study_tracker import router as study_tracker_router


client = make_client(
    auth_router,
    admin_content_router,
    tickets_router,
    labs_router,
    cli_labs_router,
    capstones_router,
    study_tracker_router,
    evidence_router,
)


def _seed_a_plus_catalog(db, count=10):
    videos = []
    for index in range(count):
        video = CurriculumVideo(
            video_key=f"a-plus-{index}",
            section="A+ Core",
            section_order=1,
            title=f"A+ Video {index}",
            exam_code="220-1201" if index % 2 == 0 else "220-1202",
            video_order=index,
            active=True,
        )
        db.add(video)
        videos.append(video)

    # Same section text is not enough: non-A+ exam codes and inactive videos
    # must not change the denominator used by the gate.
    db.add(
        CurriculumVideo(
            video_key="security-plus",
            section="A+ Core",
            section_order=1,
            title="Security+ Video",
            exam_code="SY0-701",
            video_order=count + 1,
            active=True,
        )
    )
    db.add(
        CurriculumVideo(
            video_key="inactive-a-plus",
            section="A+ Core",
            section_order=1,
            title="Inactive A+ Video",
            exam_code="220-1201",
            video_order=count + 2,
            active=False,
        )
    )
    db.commit()
    return videos


def _watch(db, student_id, videos):
    for video in videos:
        db.add(VideoWatch(student_id=student_id, video_key=video.video_key))
    db.commit()


def _seed_hands_on_content(db):
    ticket = Ticket(
        title="Preview ticket",
        description="Troubleshoot a workstation issue.",
        difficulty=1,
        week_number=1,
        hints=["Check the physical connection first."],
    )
    lab = LabTemplate(
        title="Preview lab",
        description="Practice a guided workflow.",
        lab_type="guided",
        difficulty=1,
        week_number=1,
        estimated_minutes=15,
        environment_requirements={},
        setup_instructions="Read the scenario.",
        success_criteria={"tasks": ["Document the result"]},
        required_evidence={},
        hints=[],
        is_published=True,
    )
    cli_lab = CliLab(
        id="a-plus-gated-cli",
        compartment_id="networking",
        vendor_id="cisco-ios",
        title="Preview networking lab",
        difficulty="Beginner",
        est_minutes=5,
        order_index=1,
        content={"scenario": "Inspect a switch.", "objectives": []},
    )
    capstone = CapstoneTemplate(
        title="Preview capstone",
        description="Document an end-to-end troubleshooting scenario.",
        week_number=1,
        is_published=True,
        requirements={"skills": ["Troubleshoot"]},
        deliverables={"items": ["Write-up"]},
        estimated_hours=1,
        rubric={"technical_accuracy": "Accurate"},
    )
    db.add_all([ticket, lab, cli_lab, capstone])
    db.commit()
    for row in (ticket, lab, cli_lab, capstone):
        db.refresh(row)
    return ticket, lab, cli_lab, capstone


def _ticket_payload(student_id):
    return {
        "student_id": student_id,
        "symptom": "The workstation cannot connect.",
        "root_cause": "The network cable is disconnected.",
        "resolution": "Reconnect the cable securely.",
        "verification": "Confirm link and successful connectivity.",
    }


def test_below_threshold_can_browse_but_all_hands_on_mutations_are_blocked(db):
    student = make_student(db)
    videos = _seed_a_plus_catalog(db)
    _watch(db, student.id, videos[:3])
    ticket, lab, cli_lab, capstone = _seed_hands_on_content(db)
    headers = auth_headers(student)

    browse_requests = [
        ("/api/tickets", None),
        (f"/api/tickets/{ticket.id}", None),
        ("/api/labs", None),
        (f"/api/labs/{lab.id}", None),
        ("/api/cli-labs", None),
        (f"/api/cli-labs/{cli_lab.id}", None),
        ("/api/capstones", None),
        (f"/api/capstones/{capstone.id}", None),
    ]
    for path, params in browse_requests:
        response = client.get(path, params=params, headers=headers)
        assert response.status_code == 200, path

    blocked_requests = [
        client.post(
            "/api/tickets/uploads",
            files=[("files", ("ticket.png", b"preview", "image/png"))],
            headers=headers,
        ),
        client.post(f"/api/tickets/{ticket.id}/hint", headers=headers),
        client.post(f"/api/tickets/{ticket.id}/submit", json=_ticket_payload(student.id), headers=headers),
        client.post(
            "/api/evidence/upload",
            data={"ticket_id": ticket.id, "artifact_type": "screenshot"},
            files={"file": ("evidence.png", b"preview", "image/png")},
            headers=headers,
        ),
        client.post(f"/api/labs/{lab.id}/start", headers=headers),
        client.post(f"/api/labs/{lab.id}/submit", json={"notes": "Done"}, headers=headers),
        client.post(
            "/api/labs/999999/evidence",
            data={"artifact_type": "screenshot"},
            files={"file": ("lab.png", b"preview", "image/png")},
            headers=headers,
        ),
        client.post(
            f"/api/cli-labs/{cli_lab.id}/complete",
            json={"commandLog": [], "durationMs": 1000},
            headers=headers,
        ),
        client.post(f"/api/capstones/{capstone.id}/start", headers=headers),
        client.post(f"/api/capstones/{capstone.id}/submit", json={"notes": "Done"}, headers=headers),
    ]
    for response in blocked_requests:
        assert response.status_code == 403
        assert "Complete 40% of A+ Study Tracker" in response.json()["detail"]
        assert "you're at 30%" in response.json()["detail"]


def test_at_threshold_all_hands_on_mutations_keep_existing_behavior(monkeypatch, db):
    student = make_student(db)
    videos = _seed_a_plus_catalog(db)
    _watch(db, student.id, videos[:4])
    ticket, lab, cli_lab, capstone = _seed_hands_on_content(db)
    headers = auth_headers(student)

    async def fake_grade(**_kwargs):
        return {
            "final_score": 8,
            "structure_score": 8,
            "technical_score": 8,
            "communication_score": 8,
            "strengths": ["Clear"],
            "weaknesses": [],
            "feedback": "Good work",
            "anchors": [],
            "checkpoints_met": [],
            "checkpoints_missed": [],
        }

    monkeypatch.setattr("app.routers.tickets.grade_ticket_submission", fake_grade)

    assert client.post(f"/api/tickets/{ticket.id}/hint", headers=headers).status_code == 200
    assert (
        client.post(
            f"/api/tickets/{ticket.id}/submit",
            json=_ticket_payload(student.id),
            headers=headers,
        ).status_code
        == 200
    )
    assert client.post(f"/api/labs/{lab.id}/start", headers=headers).status_code == 200
    assert (
        client.post(
            f"/api/labs/{lab.id}/submit",
            json={"notes": "Completed the lab."},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/cli-labs/{cli_lab.id}/complete",
            json={"commandLog": [], "durationMs": 1000},
            headers=headers,
        ).status_code
        == 200
    )
    assert client.post(f"/api/capstones/{capstone.id}/start", headers=headers).status_code == 200
    assert (
        client.post(
            f"/api/capstones/{capstone.id}/submit",
            json={"notes": "Completed the capstone."},
            headers=headers,
        ).status_code
        == 200
    )


def test_auth_progress_uses_admin_threshold_without_static_cache(monkeypatch, db):
    student = make_student(db, username="dynamic-threshold")
    videos = _seed_a_plus_catalog(db)
    _watch(db, student.id, videos[:3])

    monkeypatch.setenv("ADMIN_API_KEY", "a-plus-settings-test-key")

    first = client.get("/auth/me", headers=auth_headers(student))
    assert first.status_code == 200
    assert first.json()["data"]["a_plus_progress_pct"] == 30
    assert first.json()["data"]["a_plus_unlock_threshold_pct"] == 40
    assert first.json()["data"]["a_plus_unlocked"] is False

    changed = client.patch(
        "/api/admin/settings/a-plus-unlock",
        json={"a_plus_unlock_threshold_pct": 30},
        headers={"X-Admin-Key": "a-plus-settings-test-key"},
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["a_plus_unlock_threshold_pct"] == 30

    second = client.get("/auth/me", headers=auth_headers(student))
    login = client.post(
        "/auth/login",
        json={"username": student.username, "password": "pass123"},
    )
    assert second.status_code == 200
    assert second.json()["data"]["a_plus_unlock_threshold_pct"] == 30
    assert second.json()["data"]["a_plus_unlocked"] is True
    assert login.status_code == 200
    assert login.json()["a_plus_progress_pct"] == 30
    assert login.json()["a_plus_unlock_threshold_pct"] == 30
    assert login.json()["a_plus_unlocked"] is True


def test_watch_response_recalculates_access_for_immediate_frontend_flip(db):
    student = make_student(db, username="watch-flip")
    videos = _seed_a_plus_catalog(db, count=5)
    _watch(db, student.id, videos[:1])

    response = client.post(
        f"/api/study-tracker/{student.id}/watch/{videos[1].video_key}",
        headers=auth_headers(student),
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "watched": True,
        "a_plus_progress_pct": 40,
        "a_plus_unlock_threshold_pct": 40,
        "a_plus_unlocked": True,
    }
