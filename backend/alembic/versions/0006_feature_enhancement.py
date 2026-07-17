"""feature enhancement package schema

Revision ID: 0006_feature_enhancement
Revises: 0005_ai_rate_limits
Create Date: 2026-02-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_feature_enhancement"
down_revision = "0005_ai_rate_limits"
branch_labels = None
depends_on = None


WINDOWS_COMMANDS = [
    ("ipconfig", "Displays all current TCP/IP network configuration values", "ipconfig [/all | /release | /renew | /flushdns]", "ipconfig /all\nipconfig /flushdns", "networking", "windows"),
    ("ping", "Tests network connectivity to another host", "ping [-t] [-n count] target", "ping google.com\nping -t 8.8.8.8", "networking", "windows"),
    ("netstat", "Displays active TCP connections and listening ports", "netstat [-a] [-n] [-o] [-b]", "netstat -ano", "networking", "windows"),
    ("nslookup", "Queries DNS for domain and IP mapping", "nslookup domain [dns-server]", "nslookup google.com", "networking", "windows"),
    ("tracert", "Traces route packets take to destination", "tracert target", "tracert google.com", "networking", "windows"),
    ("sfc", "System File Checker scan and repair", "sfc /scannow", "sfc /scannow", "system", "windows"),
    ("chkdsk", "Checks disk and reports status", "chkdsk [drive:] [/f] [/r]", "chkdsk C: /f /r", "system", "windows"),
    ("Get-Service", "PowerShell: lists services", "Get-Service [-Name] <string>", "Get-Service -Name 'Win*'", "powershell", "windows"),
    ("Get-Process", "PowerShell: lists running processes", "Get-Process [-Name] <string>", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10", "powershell", "windows"),
    ("net user", "Manages local user accounts", "net user [username] [password] [/add | /delete]", "net user john P@ssw0rd /add", "active_directory", "windows"),
]

OBJECTIVES = [
    ("1.0", "1.1", "Install and configure laptop hardware and components", '["RAM types","Storage types","Wireless cards"]'),
    ("2.0", "2.3", "Troubleshoot network connectivity issues", '["DNS","DHCP","IP configuration"]'),
    ("3.0", "3.5", "Troubleshoot Windows OS issues", '["Safe mode","SFC","Event viewer"]'),
    ("4.0", "4.1", "Implement security best practices", '["Least privilege","MFA","Patch management"]'),
]


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    cols_ticket = _get_columns("tickets")
    if "category" not in cols_ticket:
        op.add_column("tickets", sa.Column("category", sa.String(length=100), nullable=True))
    if "objective_ids" not in cols_ticket:
        op.add_column("tickets", sa.Column("objective_ids", sa.JSON(), nullable=True))

    cols_submission = _get_columns("ticket_submissions")
    if "started_at" not in cols_submission:
        op.add_column("ticket_submissions", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    if "duration_minutes" not in cols_submission:
        op.add_column("ticket_submissions", sa.Column("duration_minutes", sa.Integer(), nullable=True))

    op.execute("UPDATE tickets SET category = COALESCE(category, 'general')")
    op.execute("UPDATE tickets SET objective_ids = '[]' WHERE objective_ids IS NULL")

    op.create_table(
        "login_streaks",
        sa.Column("student_id", sa.Integer(), primary_key=True),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_login", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "command_reference",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("command", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("syntax", sa.Text(), nullable=True),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("os", sa.String(length=20), nullable=False, server_default="windows"),
    )
    op.create_index("idx_command_search", "command_reference", ["command", "description"])

    op.create_table(
        "comptia_objectives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("domain", sa.String(length=10), nullable=False),
        sa.Column("objective_number", sa.String(length=10), nullable=False),
        sa.Column("objective_text", sa.Text(), nullable=False),
        sa.Column("subtopics", sa.Text(), nullable=True),
    )

    op.create_table(
        "student_objective_progress",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("objective_id", sa.Integer(), nullable=False),
        sa.Column("mastery_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_practiced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["objective_id"], ["comptia_objectives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_id", "objective_id"),
    )

    for cmd in WINDOWS_COMMANDS:
        op.execute(
            sa.text(
                """
                INSERT INTO command_reference (command, description, syntax, example, category, os)
                VALUES (:command, :description, :syntax, :example, :category, :os)
                """
            ).bindparams(
                command=cmd[0], description=cmd[1], syntax=cmd[2], example=cmd[3], category=cmd[4], os=cmd[5]
            )
        )

    for obj in OBJECTIVES:
        op.execute(
            sa.text(
                """
                INSERT INTO comptia_objectives (domain, objective_number, objective_text, subtopics)
                VALUES (:domain, :objective_number, :objective_text, :subtopics)
                """
            ).bindparams(domain=obj[0], objective_number=obj[1], objective_text=obj[2], subtopics=obj[3])
        )


def downgrade() -> None:
    op.drop_table("student_objective_progress")
    op.drop_table("comptia_objectives")
    op.drop_index("idx_command_search", table_name="command_reference")
    op.drop_table("command_reference")
    op.drop_table("login_streaks")

    cols_submission = _get_columns("ticket_submissions")
    if "duration_minutes" in cols_submission:
        op.drop_column("ticket_submissions", "duration_minutes")
    if "started_at" in cols_submission:
        op.drop_column("ticket_submissions", "started_at")

    cols_ticket = _get_columns("tickets")
    if "objective_ids" in cols_ticket:
        op.drop_column("tickets", "objective_ids")
    if "category" in cols_ticket:
        op.drop_column("tickets", "category")
