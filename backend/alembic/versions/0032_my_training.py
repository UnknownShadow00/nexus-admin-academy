"""Add the guided My Training weekly curriculum.

Revision ID: 0032_my_training
Revises: 0031_week0_orientation
Create Date: 2026-07-22
"""

from collections import defaultdict

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0032_my_training"
down_revision = "0031_week0_orientation"
branch_labels = None
depends_on = None


WEEKS = [
    (0, "Welcome to Nexus", "Learn how Nexus works and practice the support workflow without pressure.", 60, ["Find your way around Nexus", "Use the six-step troubleshooting process"]),
    (1, "IT Support and Ticket Basics", "Learn how support work is recorded, communicated, and completed.", 180, ["Write a useful ticket", "Communicate clearly with a user", "Recognize common support requests"]),
    (2, "Computer Hardware", "Build a beginner-friendly mental model of the parts inside a computer.", 300, ["Identify core PC components", "Explain storage, memory, CPU, power, and firmware symptoms"]),
    (3, "Windows Fundamentals", "Use Windows accounts, settings, and diagnostic tools as a support technician.", 300, ["Navigate Windows support tools", "Use basic Windows diagnostics"]),
    (4, "Working the Queue", "Prioritize work, support mobile devices and printers, and communicate next steps.", 270, ["Prioritize by impact", "Support common peripherals", "Use professional support communication"]),
    (5, "Windows and Hardware Troubleshooting", "Apply a structured process to startup, application, storage, and device problems.", 300, ["Troubleshoot common Windows failures", "Recognize hardware failure symptoms"]),
    (6, "Accounts and Permissions", "Handle account lifecycle, file access, and escalation safely.", 210, ["Distinguish account and permission issues", "Escalate access requests safely"]),
    (7, "Endpoint Security", "Recognize endpoint threats and support users through safe response steps.", 300, ["Recognize malware and phishing", "Use endpoint protection tools safely"]),
    (8, "Client Networking", "Follow a repeatable client-side network troubleshooting path.", 300, ["Check connectivity from the client", "Use common Windows network tools"]),
    (9, "IP Addressing and Packet Flow", "Reason about IP addresses, subnets, ARP, and local packet delivery.", 240, ["Read IPv4 settings", "Explain basic packet flow"]),
    (10, "Switching and VLAN Basics", "Learn cables, ports, VLANs, and the first Cisco CLI workflows.", 300, ["Identify network media", "Verify switch ports and VLANs"]),
    (11, "Routing and Network Services", "Connect VLANs and understand DHCP, DNS, routing, and related services.", 270, ["Explain core network services", "Troubleshoot service reachability"]),
    (12, "Secure Network Administration", "Troubleshoot network access while preserving secure administration.", 240, ["Use a structured network troubleshooting process", "Recognize wireless and SOHO security controls"]),
    (13, "Active Directory Foundations", "Support domains, organizational units, users, and groups.", 240, ["Explain Active Directory structure", "Handle common domain account requests"]),
    (14, "Domain Operations and File Services", "Support domain joins, computer accounts, and group-based file access.", 210, ["Troubleshoot a domain join", "Use groups for file access"]),
    (15, "Group Policy", "Understand Group Policy processing and investigate settings that do not apply.", 210, ["Explain Group Policy scope", "Use gpresult and RSoP evidence"]),
    (16, "Server Networking and PowerShell", "Use server DNS, DHCP, and PowerShell for safe administration.", 240, ["Investigate DNS and DHCP services", "Use PowerShell for repeatable checks"]),
    (17, "Server Operations and Recovery", "Work with logs, services, backups, patching, and remote administration.", 270, ["Investigate server operations", "Verify a real restore"]),
    (18, "Linux Fundamentals", "Navigate Linux and work safely with files, permissions, packages, and SSH.", 240, ["Navigate the Linux filesystem", "Manage permissions and SSH basics"]),
    (19, "Linux Services and Troubleshooting", "Investigate Linux services, logs, networking, DNS, and scheduled jobs.", 240, ["Use systemd and journalctl", "Troubleshoot Linux networking"]),
    (20, "Linux Production and Security", "Support web services, firewalls, backups, monitoring, and common security threats.", 300, ["Triage a production Linux service", "Recognize and reduce common security risks"]),
    (21, "Cloud Concepts and Identity", "Understand cloud service models and support cloud identity.", 210, ["Compare cloud service models", "Support Entra ID identity tasks"]),
    (22, "Azure Infrastructure", "Support Azure virtual machines, network security groups, and storage.", 240, ["Investigate Azure VM access", "Reason about cloud storage access"]),
    (23, "Integrated Operations", "Work a mixed queue and communicate clearly during incidents.", 240, ["Prioritize mixed support work", "Write a useful incident update"]),
    (24, "Capstone Readiness", "Bring the full support workflow together for the final role-gated capstone.", 300, ["Demonstrate integrated troubleshooting", "Verify capstone readiness"]),
]


VIDEO_WEEKS = {
    0: [182, 166, 168],
    1: [167, 176, 177],
    2: list(range(19, 21)) + list(range(30, 45)),
    3: list(range(108, 121)) + [131],
    4: list(range(1, 6)) + list(range(45, 53)) + [62, 169, 175, 180, 181],
    5: list(range(57, 61)) + list(range(125, 128)) + list(range(162, 166)),
    6: [139],
    7: [133, 134, 137, 138, 143, 144, 156, 157, 158],
    8: [6, 7, 8, 16, 17, 18, 61, 121, 122, 123, 124],
    9: [14, 15],
    10: [12, 13] + list(range(21, 30)),
    11: [9, 10, 11],
    12: [141, 142, 160],
    13: [140],
    15: [135, 136],
    16: [178, 179],
    17: [170],
    18: [128, 129, 130],
    20: list(range(145, 156)) + [159, 161],
    21: list(range(53, 57)) + [132],
    23: [174],
    24: [171, 172, 173],
}


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "training_weeks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("learning_goals", _json_type(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("requires_previous_week", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("week_number >= 0", name="ck_training_weeks_number_nonnegative"),
        sa.CheckConstraint("display_order >= 0", name="ck_training_weeks_order_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_number", name="uq_training_weeks_week_number"),
    )
    op.create_index("ix_training_weeks_display_order", "training_weeks", ["display_order"], unique=False)
    op.create_index("ix_training_weeks_is_active", "training_weeks", ["is_active"], unique=False)
    op.create_table(
        "training_week_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("training_week_id", sa.Integer(), nullable=False),
        sa.Column("stable_id", sa.String(length=160), nullable=False),
        sa.Column("activity_type", sa.String(length=32), nullable=False),
        sa.Column("content_ref", sa.String(length=160), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_required", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("prerequisite_activity_id", sa.Integer(), nullable=True),
        sa.Column("prerequisite_mode", sa.String(length=12), server_default="soft", nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("display_order >= 0", name="ck_training_activities_order_nonnegative"),
        sa.CheckConstraint("estimated_minutes IS NULL OR estimated_minutes >= 0", name="ck_training_activities_minutes_nonnegative"),
        sa.CheckConstraint("prerequisite_mode IN ('soft', 'hard')", name="ck_training_activities_prerequisite_mode"),
        sa.CheckConstraint("activity_type IN ('video','quiz','lesson','guided_lab','networking_lab','support_ticket','command_exercise','terminal_exercise','review','capstone')", name="ck_training_activities_type"),
        sa.ForeignKeyConstraint(["prerequisite_activity_id"], ["training_week_activities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["training_week_id"], ["training_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stable_id", name="uq_training_week_activities_stable_id"),
        sa.UniqueConstraint("training_week_id", "display_order", name="uq_training_week_activity_order"),
    )
    op.create_index("ix_training_week_activities_training_week_id", "training_week_activities", ["training_week_id"], unique=False)
    op.create_index("ix_training_week_activities_activity_type", "training_week_activities", ["activity_type"], unique=False)

    bind = op.get_bind()
    week_table = sa.table(
        "training_weeks",
        sa.column("week_number", sa.Integer), sa.column("display_order", sa.Integer),
        sa.column("title", sa.String), sa.column("description", sa.Text),
        sa.column("learning_goals", _json_type()), sa.column("estimated_minutes", sa.Integer),
        sa.column("is_active", sa.Boolean), sa.column("requires_previous_week", sa.Boolean),
    )
    bind.execute(
        week_table.insert(),
        [
            {"week_number": number, "display_order": number, "title": title, "description": description,
             "learning_goals": goals, "estimated_minutes": minutes, "is_active": True,
             "requires_previous_week": number > 0}
            for number, title, description, minutes, goals in WEEKS
        ],
    )
    week_ids = dict(bind.execute(sa.text("SELECT week_number, id FROM training_weeks")).all())
    orders = defaultdict(int)
    activities = []

    def add(week, kind, ref, required, minutes=None, suffix=None):
        orders[week] += 1
        activities.append({
            "training_week_id": week_ids[week], "stable_id": suffix or f"week-{week}-{kind}-{ref}",
            "activity_type": kind, "content_ref": str(ref), "display_order": orders[week],
            "is_required": required, "estimated_minutes": minutes, "prerequisite_mode": "soft", "metadata_json": {},
        })

    # Existing learning-path lessons remain the weekly foundation. Module order 0
    # maps to Week 0; module orders 2..25 map to Weeks 1..24.
    lesson_rows = bind.execute(sa.text(
        "SELECT l.id, l.estimated_minutes, m.module_order FROM lessons l JOIN modules m ON m.id=l.module_id "
        "WHERE l.status='published' AND (m.module_order=0 OR m.module_order BETWEEN 2 AND 25) "
        "ORDER BY m.module_order, l.lesson_order"
    )).all()
    for lesson_id, minutes, module_order in lesson_rows:
        add(0 if module_order == 0 else module_order - 1, "lesson", lesson_id, True, minutes)

    video_relevance = dict(bind.execute(sa.text("SELECT id, job_relevance FROM curriculum_videos WHERE active = :active"), {"active": True}).all())
    for week, video_ids in VIDEO_WEEKS.items():
        for video_id in video_ids:
            if video_id in video_relevance:
                # The existing job-relevance review is the evidence-backed way
                # to keep the beginner path focused. Know-it and awareness
                # videos stay assigned for review but do not gate progression.
                add(week, "video", video_id, video_relevance[video_id] == "job_critical")

    # Only editorially approved, answer-key-validated quizzes are exposed. Existing
    # required flags decide whether an attempt must pass to unlock the next week.
    quiz_rows = bind.execute(sa.text(
        "SELECT id, week_number, is_required FROM quizzes WHERE is_active = :active AND status='published' "
        "AND editorial_status='validated' AND answer_keys_validated = :active AND week_number BETWEEN 0 AND 24 "
        "ORDER BY week_number, id"
    ), {"active": True}).all()
    for quiz_id, week, required in quiz_rows:
        add(week, "quiz", quiz_id, bool(required), 15)

    lab_rows = bind.execute(sa.text(
        "SELECT id, week_number, estimated_minutes FROM lab_templates WHERE is_published = :active AND week_number BETWEEN 0 AND 24 ORDER BY week_number, id"
    ), {"active": True}).all()
    for lab_id, week, minutes in lab_rows:
        add(week, "guided_lab", lab_id, True, minutes)

    # One representative ticket is required per week; extra real tickets remain
    # optional practice. No ticket content is copied into the weekly tables.
    ticket_rows = bind.execute(sa.text("SELECT id, week_number FROM tickets WHERE week_number BETWEEN 0 AND 24 ORDER BY week_number, id")).all()
    first_ticket = set()
    for ticket_id, week in ticket_rows:
        required = week not in first_ticket
        add(week, "support_ticket", ticket_id, required, 30)
        first_ticket.add(week)

    cli_week = {
        "meet-cli-001": 1,
        "dev-nf-encap-001": 9,
        "dev-nf-checkpoint-001": 9,
        "dev-sw-act-01": 10,
        "dev-sw-act-04": 10,
        "dev-sw-act-09": 10,
        "dev-sw-act-14": 10,
        "dev-sw-act-18": 10,
        "dev-sw-act-23": 11,
        "exam-first-switch": 11,
        "exam-ssh": 12,
    }
    cli_rows = bind.execute(sa.text("SELECT id, est_minutes FROM cli_lab ORDER BY compartment_id, order_index")).all()
    for lab_id, minutes in cli_rows:
        if lab_id in cli_week:
            add(cli_week[lab_id], "networking_lab", lab_id, False, minutes)

    capstone_rows = bind.execute(sa.text("SELECT id, week_number, estimated_hours FROM capstone_templates WHERE is_published = :active AND week_number BETWEEN 0 AND 24 ORDER BY week_number, id"), {"active": True}).all()
    for capstone_id, week, hours in capstone_rows:
        add(week, "capstone", capstone_id, False, (hours or 2) * 60)

    # Keep an approved quiz immediately after its exactly linked video. Quiz
    # links are title-based in the existing curriculum, so only exact database
    # matches are reordered; no relationship is inferred from similar titles.
    exact_links = dict(bind.execute(sa.text(
        "SELECT q.id, MIN(v.id) FROM quizzes q JOIN curriculum_videos v ON v.quiz_title=q.title "
        "WHERE q.is_active = :active AND q.status='published' AND q.editorial_status='validated' "
        "AND q.answer_keys_validated = :active AND v.active = :active GROUP BY q.id"
    ), {"active": True}).all())
    for week in week_ids:
        week_rows = [item for item in activities if item["training_week_id"] == week_ids[week]]
        for quiz_id, video_id in exact_links.items():
            quiz_row = next((item for item in week_rows if item["activity_type"] == "quiz" and item["content_ref"] == str(quiz_id)), None)
            video_row = next((item for item in week_rows if item["activity_type"] == "video" and item["content_ref"] == str(video_id)), None)
            if quiz_row and video_row:
                week_rows.remove(quiz_row)
                week_rows.insert(week_rows.index(video_row) + 1, quiz_row)
        for order, item in enumerate(week_rows, start=1):
            item["display_order"] = order

    activity_table = sa.table(
        "training_week_activities",
        sa.column("training_week_id", sa.Integer), sa.column("stable_id", sa.String),
        sa.column("activity_type", sa.String), sa.column("content_ref", sa.String),
        sa.column("display_order", sa.Integer), sa.column("is_required", sa.Boolean),
        sa.column("estimated_minutes", sa.Integer), sa.column("prerequisite_mode", sa.String),
        sa.column("metadata_json", _json_type()),
    )
    if activities:
        bind.execute(activity_table.insert(), activities)


def downgrade() -> None:
    op.drop_index("ix_training_week_activities_activity_type", table_name="training_week_activities")
    op.drop_index("ix_training_week_activities_training_week_id", table_name="training_week_activities")
    op.drop_table("training_week_activities")
    op.drop_index("ix_training_weeks_is_active", table_name="training_weeks")
    op.drop_index("ix_training_weeks_display_order", table_name="training_weeks")
    op.drop_table("training_weeks")
