"""Prepare two isolated legacy-path browser fixtures; never run on production."""

from __future__ import annotations

import sys

from audit_weeks_3_4_journey import _assert_isolated_database, _complete_activity, _required_activities
from app.database import SessionLocal
from app.models.service_desk import ServiceDeskAssignment, ServiceDeskScenario
from app.models.student import Student
from app.services.auth_service import hash_password
from app.services.training_service import build_training_overview


def main() -> None:
    _assert_isolated_database()
    credentials = ((sys.argv[1], sys.argv[2], 1, "locked-user-account"),
                   (sys.argv[3], sys.argv[4], 2, "inc2404"))
    db = SessionLocal()
    try:
        for username, password, target_week, target_key in credentials:
            student = Student(name=f"Phase 0A Week {target_week} Fixture", email=f"{username}@example.invalid",
                              username=username, password_hash=hash_password(password), total_xp=0)
            db.add(student)
            db.commit()
            db.refresh(student)
            for week in range(target_week + 1):
                for activity in _required_activities(db, week):
                    if week == target_week and activity.activity_type == "service_desk_scenario" and activity.content_ref == target_key:
                        continue
                    if week == target_week and target_week == 2 and activity.activity_type == "quiz":
                        continue
                    _complete_activity(db, student, activity)
            for key in ("locked-user-account", "inc2404"):
                scenario = db.query(ServiceDeskScenario).filter_by(stable_key=key).one()
                db.add(ServiceDeskAssignment(student_id=student.id, scenario_id=scenario.id,
                                             mode="simulation", is_required=True, assigned_by="phase0a-e2e"))
            db.commit()
            overview = build_training_overview(db, student)
            assert overview["current_week"]["week_number"] == target_week
            assert overview["next_activity"]["activity_type"] in {"quiz", "service_desk_scenario"}
    finally:
        db.close()


if __name__ == "__main__":
    main()
