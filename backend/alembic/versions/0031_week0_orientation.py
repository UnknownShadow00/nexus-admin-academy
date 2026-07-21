"""Add the Week 0 Nexus orientation lesson and zero-stakes practice storage.

Revision ID: 0031_week0_orientation
Revises: 0030_week_gating_data_fixes
Create Date: 2026-07-21
"""

import sqlalchemy as sa
from alembic import op


revision = "0031_week0_orientation"
down_revision = "0030_week_gating_data_fixes"
branch_labels = None
depends_on = None


ORIENTATION_TITLE = "Welcome to Nexus: Your First Week"
ORIENTATION_SUMMARY = """Nexus is your 24-week practice space for becoming an IT-support technician. You will learn the habits, tools, and communication that help real people when technology gets in their way. You do not need an IT background to begin.

WHAT A WEEK MEANS: each week is a small, guided set of learning and practice. Finish the required items in the order shown, then use optional practice when you want more repetition. You are not expected to know everything before you start.

THE FOUR THINGS YOU WILL SEE:
- A LESSON explains one idea in plain language and gives you a place to save notes.
- A QUIZ is a short checkpoint. It shows what you understand and what to revisit.
- A LAB is a safe place to try a task with guided steps.
- A TICKET is a realistic support request. You explain what you checked, what you did, and how you know it worked.

REQUIRED VS OPTIONAL: required items keep your weekly path moving. Optional practice, review, and certification questions are there when you want extra reps; they do not block your next required step.

EVIDENCE AND REMEDIATION: evidence is a screenshot, command output, or note that shows what happened. Remediation means a focused retry or extra practice after a missed checkpoint — it is coaching, not a punishment.

XP AND YOUR ROLE: XP is a running total of completed learning work. Your Role is a promotion level based on demonstrated readiness and specific gates. XP can show momentum; it does not promote you by itself.

HOW GRADING WORKS: Nexus can use AI to give fast feedback on real ticket work. A mentor may still review it afterward, especially when judgment, safety, or workplace communication matters. NEEDS REVISION means your work is not final yet: read the feedback, improve the missing part, and submit again.

WHEN YOU NEED HELP: ask your mentor or your cohort's agreed help channel. Include the lesson, quiz, lab, or ticket name and what you already tried. That gives people a useful starting point.

YOUR SIMPLE ROUTINE:
1. Open This Week on Home and choose the first item marked Next up.
2. Read the lesson, save a short note, and complete the required quiz or practice.
3. Come back to Home anytime. Your notes, quiz attempts, and submitted work save to your account, and unfinished work stays in This Week.

GUIDED PRACTICE: save one short note below, take the Ticketing Systems Quiz, then write a one-sentence practice response. You may also upload a harmless sample screenshot. This walkthrough is not graded, does not use AI, and does not need mentor review.

WHY THIS MATTERS: good support work is not guessing alone. It is knowing what to do next, recording what happened, asking for help early, and improving one small step at a time."""


def upgrade() -> None:
    op.create_table(
        "student_onboarding_practice",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_student_onboarding_practice"),
    )
    op.create_index(op.f("ix_student_onboarding_practice_id"), "student_onboarding_practice", ["id"], unique=False)
    op.create_index(op.f("ix_student_onboarding_practice_student_id"), "student_onboarding_practice", ["student_id"], unique=False)

    bind = op.get_bind()
    module_id = bind.execute(sa.text("SELECT id FROM modules WHERE code = 'MOD-000'")).scalar()
    if module_id is None:
        return

    # Keep the existing CompTIA lesson intact and place the platform tour first.
    bind.execute(
        sa.text(
            "UPDATE lessons SET lesson_order = 2 "
            "WHERE module_id = :module_id AND title = 'CompTIA 6-Step Process'"
        ),
        {"module_id": module_id},
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO lessons (module_id, title, summary, lesson_order, estimated_minutes, required_notes_template, status)
            SELECT :module_id, :title, :summary, 1, 12, :notes_template, 'published'
             WHERE NOT EXISTS (
                SELECT 1 FROM lessons WHERE module_id = :module_id AND title = :title
             )
            """
        ),
        {
            "module_id": module_id,
            "title": ORIENTATION_TITLE,
            "summary": ORIENTATION_SUMMARY,
            "notes_template": "Write one sentence: What is the first thing you will do when you are unsure what comes next in Nexus?",
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    lesson_id = bind.execute(
        sa.text(
            """
            SELECT lessons.id
              FROM lessons JOIN modules ON modules.id = lessons.module_id
             WHERE modules.code = 'MOD-000' AND lessons.title = :title
            """
        ),
        {"title": ORIENTATION_TITLE},
    ).scalar()
    if lesson_id is not None:
        bind.execute(
            sa.text("DELETE FROM evidence_artifacts WHERE submission_type = 'orientation' AND submission_id = :lesson_id"),
            {"lesson_id": lesson_id},
        )
        bind.execute(sa.text("DELETE FROM lessons WHERE id = :lesson_id"), {"lesson_id": lesson_id})
        bind.execute(
            sa.text(
                "UPDATE lessons SET lesson_order = 1 "
                "WHERE module_id = (SELECT id FROM modules WHERE code = 'MOD-000') "
                "AND title = 'CompTIA 6-Step Process'"
            )
        )
    op.drop_index(op.f("ix_student_onboarding_practice_student_id"), table_name="student_onboarding_practice")
    op.drop_index(op.f("ix_student_onboarding_practice_id"), table_name="student_onboarding_practice")
    op.drop_table("student_onboarding_practice")
