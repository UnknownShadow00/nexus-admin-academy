from app.models.squad_activity import SquadActivity
from app.models.student import Student
from app.routers.admin_students import router as admin_students_router
from app.routers.students import router as students_router
from app.services.admin_auth import verify_admin
from conftest import auth_headers, make_client


student_client = make_client(students_router)
admin_client = make_client(admin_students_router)
admin_client.app.dependency_overrides[verify_admin] = lambda: True


def _student(name: str, username: str, *, is_mentor: bool, total_xp: int) -> Student:
    return Student(
        name=name,
        email=f"{username}@test.local",
        username=username,
        is_mentor=is_mentor,
        total_xp=total_xp,
    )


def test_student_squad_dashboard_hides_mentor_activity_and_roster_entry(db):
    student = _student("Real Student", "real-student", is_mentor=False, total_xp=100)
    mentor = _student("Mentor Account", "mentor-account", is_mentor=True, total_xp=9999)
    db.add_all([student, mentor])
    db.commit()

    student_activity = SquadActivity(
        student_id=student.id,
        activity_type="lab_started",
        title="Student Lab",
        detail="Student activity remains visible",
    )
    mentor_activity = SquadActivity(
        student_id=mentor.id,
        activity_type="lab_started",
        title="Mentor account-management action",
        detail="Private account-management-only detail",
    )
    db.add_all([student_activity, mentor_activity])
    db.commit()
    student_activity_id = student_activity.id
    student_id = student.id
    headers = auth_headers(student)
    db.close()

    response = student_client.get("/api/squad/dashboard", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert [row["id"] for row in data["activity_feed"]] == [student_activity_id]
    assert [row["student_id"] for row in data["members"]] == [student_id]
    assert "Private account-management-only detail" not in str(data["activity_feed"])


def test_admin_squad_activity_still_includes_mentor_activity(db):
    student = _student("Real Student", "real-student", is_mentor=False, total_xp=100)
    mentor = _student("Mentor Account", "mentor-account", is_mentor=True, total_xp=9999)
    db.add_all([student, mentor])
    db.commit()

    mentor_activity = SquadActivity(
        student_id=mentor.id,
        activity_type="lab_started",
        title="Mentor Lab",
        detail="Visible to admin only",
    )
    db.add(mentor_activity)
    db.commit()
    mentor_activity_id = mentor_activity.id
    db.close()

    response = admin_client.get("/api/admin/squad/activity")

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [mentor_activity_id]
