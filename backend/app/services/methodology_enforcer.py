from sqlalchemy.orm import Session

from app.models.progression import MethodologyFramework, StudentMethodologyProgress
from app.models.student import Student


def can_access_tickets(student_id: int, db: Session) -> dict:
    student = db.query(Student).filter(Student.id == student_id).first()
    role_id = student.current_role_id if student and student.current_role_id else 1

    required_frameworks = (
        db.query(MethodologyFramework)
        .filter((MethodologyFramework.required_for_role.is_(None)) | (MethodologyFramework.required_for_role <= role_id))
        .all()
    )

    missing_frameworks = []
    for framework in required_frameworks:
        progress = (
            db.query(StudentMethodologyProgress)
            .filter(
                StudentMethodologyProgress.student_id == student_id,
                StudentMethodologyProgress.framework_id == framework.id,
            )
            .first()
        )
        if not progress or not progress.completed or not progress.practice_passed:
            missing_frameworks.append(framework.name)

    return {"allowed": len(missing_frameworks) == 0, "missing_frameworks": missing_frameworks}

