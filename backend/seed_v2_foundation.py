"""Opt-in runner for the Nexus V2 additive foundation.

This is NOT part of ``seed.py`` / ``seed_curriculum.py`` and is NOT run by CI
or any deploy step. Run it by hand to populate the V2 certification hierarchy
and content from the files under ``content/``:

    ./.venv/bin/python seed_v2_foundation.py

It is idempotent — re-running makes no duplicate rows — and it never modifies
``training_weeks``, progression, the 40% A+ unlock setting, or student data.

**Atomicity.** The load is one logical transaction. Earlier revisions
committed after each stage, so a failure between stages could leave the
hierarchy loaded with its content missing — modules with no lessons, or
assessments pointing at quizzes that were never imported. Everything now
happens in a single session that is validated before a single commit; any
exception rolls the whole load back to the pre-load state.

``--dry-run`` performs the entire load and validation and then rolls back, so
a load can be rehearsed against a copy without writing anything.
"""

import argparse
import sys

sys.path.insert(0, ".")

from app.database import SessionLocal  # noqa: E402
from app.services.v2_content_loader import (  # noqa: E402
    ContentValidationError,
    backfill_examcompass_permission,
    load_module,
)
from app.services.v2_curriculum_service import STUDENT_MODULE_ROLES  # noqa: E402


def _print_summary(label: str, summary: dict) -> None:
    print(f"{label}:")
    for entity, counts in sorted(summary["by_entity"].items()):
        print(f"  {entity}: {counts}")
    print(
        f"  totals: created={summary['created']} "
        f"updated={summary['updated']} unchanged={summary['unchanged']}"
    )


CONTENT_BACKED_ROLES = {"quick_check", "module_quiz", "practical"}


def validate_loaded_content(db, summary: dict) -> list[str]:
    """Return the reasons this load must not be committed.

    A quick check, module quiz, or practical whose engine reference did not
    resolve means the content it points at was never created — the
    half-loaded state this seed exists to prevent.

    Only modules students can actually reach are held to that bar. The entry
    page surfaces a module when it has lessons and the complete set of
    activity roles, so a module that is still being authored (no practical
    yet, no quiz bank yet) is reported as a note rather than failing the load
    — it is invisible to students either way, and blocking on it would make
    every future authoring step un-loadable.
    """
    from app.models.certification import CertificationModule, LessonV2Meta, ModuleAssessment

    problems: list[str] = []
    references = summary.get("references") or {}
    if not references.get("content_engine_assessments"):
        problems.append("no content-backed module assessments were loaded")

    for module in db.query(CertificationModule).filter_by(active=True).all():
        assessments = db.query(ModuleAssessment).filter_by(
            certification_module_id=module.id, active=True
        ).all()
        roles = {row.assessment_role for row in assessments}
        has_lessons = db.query(LessonV2Meta).filter(
            LessonV2Meta.certification_module_id == module.id,
            LessonV2Meta.status.in_(("ready", "published")),
        ).first() is not None
        if not has_lessons or not STUDENT_MODULE_ROLES.issubset(roles):
            continue
        unresolved = sorted(
            row.assessment_key
            for row in assessments
            if row.assessment_role in CONTENT_BACKED_ROLES
            and not (row.quiz_id or row.lab_template_id)
        )
        if unresolved:
            problems.append(
                f"student-visible module '{module.module_key}' has unresolved "
                "content references: " + ", ".join(unresolved)
            )
    return problems


def run(db, *, dry_run: bool = False) -> dict:
    """Load, validate, then commit exactly once (or roll back)."""
    try:
        summary = load_module(db, commit=False)
        examcompass = backfill_examcompass_permission(db, commit=False)

        problems = validate_loaded_content(db, summary)
        if problems:
            raise ContentValidationError(
                "V2 foundation load failed validation: " + "; ".join(problems)
            )

        if dry_run:
            db.rollback()
            print("DRY RUN — validated and rolled back; nothing was written.")
        else:
            db.commit()
    except BaseException:
        # Includes KeyboardInterrupt: a load interrupted halfway must not be
        # left partially applied.
        db.rollback()
        raise

    _print_summary("V2 foundation loaded", summary)
    print(f"  references: {summary['references']}")
    still_authoring = summary["references"].get("content_engine_unresolved") or []
    if still_authoring:
        print(
            "  note: assessments awaiting content (modules not yet visible to "
            f"students): {', '.join(still_authoring)}"
        )
    print(
        f"ExamCompass provenance backfill: matched={examcompass['matched']} "
        f"updated={examcompass['updated']}"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load the Nexus V2 foundation content as one transaction."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="load and validate, then roll back without writing",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        run(db, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
