"""Idempotently populate weekly references after normal content seeding.

Production upgrades receive these rows in migration 0032. A brand-new database
runs migrations before the ordinary seed scripts have created content, so
``seed_curriculum.py`` calls this synchronizer after its final commit. Existing
weekly configuration is never overwritten.
"""

from collections import defaultdict

from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from app.models.capstone import CapstoneTemplate
from app.models.cli_lab import CliLab
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabTemplate
from app.models.learning import Lesson, Module
from app.models.quiz import Quiz
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.training_quiz_mapping import OPTIONAL_LESSON_IDS, mapping_metadata, video_is_required


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

CLI_WEEKS = {
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

# Stable Service Desk keys are deliberately independent of legacy Ticket IDs.
# Keep this compact mapping near the weekly seed so required curriculum never
# falls back to the retired support_ticket product.
SERVICE_DESK_WEEKS = {
    1: "locked-user-account",
    2: "inc2404",
    3: "password-reset",
    4: "mfa-reset",
    5: "inc2502",
    6: "inc2505",
    7: "inc2508",
    8: "inc2407",
    14: "inc2510",
}

ORIENTATION_LESSON_TITLE = "Welcome to Nexus: Your First Week"
ORIENTATION_QUIZ_TITLE = "Ticketing Systems Quiz"


HARDWARE_IDENTIFICATION_QUESTIONS = [
    {
        "id": "cpu-socket",
        "prompt": "Which component must match the motherboard socket before an Intel desktop CPU can be installed?",
        "context": "The board is labelled LGA1700 and the technician has an Intel Core processor specified for LGA1700.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The CPU socket and its mounting pattern"},
            {"id": "b", "label": "A 288-pin DIMM slot"},
            {"id": "c", "label": "An M.2 Key M connector"},
            {"id": "d", "label": "A PCIe x16 expansion slot"},
        ],
        "correct": ["a"],
        "explanation": "Desktop processors are keyed to a specific socket family. An LGA1700 processor requires an LGA1700 motherboard socket; DIMM, M.2, and PCIe slots serve other components.",
    },
    {
        "id": "dimm-generation",
        "prompt": "Which memory module belongs in this slot?",
        "context": "The motherboard manual calls the memory sockets 'DDR5 DIMM' and the slot key is positioned for DDR5.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "A DDR4 desktop DIMM"},
            {"id": "b", "label": "A DDR5 desktop DIMM"},
            {"id": "c", "label": "A DDR4 SO-DIMM"},
            {"id": "d", "label": "An M.2 NVMe SSD"},
        ],
        "correct": ["b"],
        "explanation": "DDR4 and DDR5 DIMMs have differently placed keys and are not interchangeable. A DDR5-labelled desktop DIMM slot accepts a DDR5 desktop DIMM, not a SO-DIMM or storage device.",
    },
    {
        "id": "storage-interface",
        "prompt": "Which drive is the correct match for the connector shown?",
        "context": "The board has a short M.2 Key M socket marked 'PCIe 4.0 x4 / NVMe'. There is no 2.5-inch drive bay involved.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "An M.2 NVMe SSD"},
            {"id": "b", "label": "A 2.5-inch SATA SSD with separate SATA data and power cables"},
            {"id": "c", "label": "A 3.5-inch SATA hard drive"},
            {"id": "d", "label": "A PCIe x1 network adapter"},
        ],
        "correct": ["a"],
        "explanation": "An M.2 Key M connector marked for PCIe/NVMe is intended for an M.2 NVMe drive. SATA 2.5-inch and 3.5-inch drives use separate SATA data and power connections.",
    },
    {
        "id": "pcie-slot-size",
        "prompt": "Which slot should be selected for a full-height graphics card that needs a PCIe x16 electrical connection?",
        "context": "The motherboard has one long PCIe x16 slot and several short PCIe x1 slots. The graphics card uses a full-length x16 edge connector.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Any short PCIe x1 slot"},
            {"id": "b", "label": "The long PCIe x16 slot"},
            {"id": "c", "label": "A DDR5 DIMM slot"},
            {"id": "d", "label": "The M.2 Key M socket"},
        ],
        "correct": ["b"],
        "explanation": "A full-length graphics card is installed in the long PCIe x16 slot. A physical x1 slot is too short for the card, while DIMM and M.2 sockets are not expansion-card slots.",
    },
    {
        "id": "psu-connectors",
        "prompt": "Which PSU connector powers the motherboard itself?",
        "context": "A new ATX motherboard needs its main board-power connection. Other components include a SATA SSD and a PCIe graphics card.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "24-pin ATX motherboard power connector"},
            {"id": "b", "label": "15-pin SATA power connector"},
            {"id": "c", "label": "6+2-pin PCIe auxiliary power connector"},
            {"id": "d", "label": "SATA data cable"},
        ],
        "correct": ["a"],
        "explanation": "The 24-pin ATX connector is the main power feed for an ATX motherboard. SATA power feeds drives, PCIe auxiliary power feeds a graphics card, and a SATA data cable carries data rather than power.",
    },
]


WINDOWS_DIAGNOSTICS_QUESTIONS = [
    {
        "id": "ipconfig-apipa",
        "prompt": "What is the most likely interpretation and next diagnostic step?",
        "context": "`ipconfig /all` shows IPv4 Address . . . : 169.254.34.18, Subnet Mask : 255.255.0.0, Default Gateway : (blank), DHCP Enabled : Yes.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The PC self-assigned an APIPA address; check DHCP reachability, lease service, and the network link."},
            {"id": "b", "label": "DNS resolution is working; flush the DNS cache first."},
            {"id": "c", "label": "The default gateway is correct; begin tracing the internet route."},
            {"id": "d", "label": "The PC has a valid private LAN address; reinstall the browser."},
        ],
        "correct": ["a"],
        "explanation": "A 169.254.0.0/16 address with DHCP enabled is APIPA, normally assigned when DHCP cannot be reached. Restore link/DHCP connectivity before investigating DNS or internet routing.",
    },
    {
        "id": "nslookup-nxdomain",
        "prompt": "What does this `nslookup` result indicate?",
        "context": "`Server: dc01.nexus.internal`\n`Address: 10.20.0.10`\n`*** dc01.nexus.internal can't find payroll.nexus.internal: Non-existent domain`",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The DNS server responded, but it has no record for that name; verify the hostname or DNS record."},
            {"id": "b", "label": "The workstation cannot reach its configured DNS server."},
            {"id": "c", "label": "The default gateway is unavailable."},
            {"id": "d", "label": "The route failed after the third hop."},
        ],
        "correct": ["a"],
        "explanation": "The server name and address prove a DNS server answered. 'Non-existent domain' (NXDOMAIN) means that responding server does not have the requested name, so validate the name and its record.",
    },
    {
        "id": "tracert-first-hop",
        "prompt": "Which next step is best supported by this trace?",
        "context": "`tracert 8.8.8.8`\n`1  *  *  *  Request timed out.`\n`2  *  *  *  Request timed out.`\nThe adapter has a valid 10.20.0.55/24 address and default gateway 10.20.0.1.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Test reachability to the default gateway and inspect the local VLAN/link before blaming a remote route."},
            {"id": "b", "label": "Change the public DNS server because the trace uses an IP address."},
            {"id": "c", "label": "Clear Event Viewer logs to remove the timeout."},
            {"id": "d", "label": "Disable all startup applications."},
        ],
        "correct": ["a"],
        "explanation": "The trace never reaches even its first hop, so the local path to the configured gateway is the first thing to verify. DNS is not involved when tracing a numeric IP address.",
    },
    {
        "id": "event-viewer-disk",
        "prompt": "What is the appropriate interpretation of this Event Viewer entry?",
        "context": "System log: Source `Disk`, Event ID `153`: 'The IO operation at logical block address ... was retried.' The user reports intermittent application freezes.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Investigate storage health, cabling/controller events, and back up data; this points to retried disk I/O."},
            {"id": "b", "label": "Treat it as a DNS name-resolution failure."},
            {"id": "c", "label": "Assume the user has entered a wrong password."},
            {"id": "d", "label": "Prioritize changing the display resolution."},
        ],
        "correct": ["a"],
        "explanation": "Disk Event ID 153 reports a retried I/O operation, which can correlate with pauses while storage requests are retried. Check storage diagnostics and protect data rather than treating it as a network or display issue.",
    },
    {
        "id": "task-manager-startup",
        "prompt": "What is the best first action for this startup-performance symptom?",
        "context": "Task Manager > Startup apps lists 'Acme Updater' as Enabled with Startup impact 'High'; it is not required for sign-in or endpoint protection. The PC is slow only immediately after sign-in.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Disable the nonessential updater in Startup apps, then measure the next sign-in before making broader changes."},
            {"id": "b", "label": "Delete the user profile immediately."},
            {"id": "c", "label": "Change the IPv4 default gateway."},
            {"id": "d", "label": "Uninstall the graphics driver."},
        ],
        "correct": ["a"],
        "explanation": "The symptom is limited to sign-in and Task Manager identifies a nonessential, high-impact startup item. Disable that item and retest, preserving security and required management software.",
    },
]


TRIAGE_QUESTIONS = [
    {
        "id": "triage-email-outage",
        "prompt": "Which priority should this ticket receive?",
        "context": "Ticket: 'Nobody in the 180-person office can send or receive email. The webmail and desktop clients both fail, and there is no approved workaround.'",
        "type": "single_choice",
        "options": [{"id": "p1", "label": "P1 Critical"}, {"id": "p2", "label": "P2 High"}, {"id": "p3", "label": "P3 Medium"}, {"id": "p4", "label": "P4 Low"}],
        "correct": ["p1"],
        "explanation": "This is a full outage affecting many users with no workaround, which meets the P1 Critical definition.",
    },
    {
        "id": "triage-vip-workaround",
        "prompt": "Which priority should this ticket receive?",
        "context": "Ticket: 'The CFO cannot use the conference-room printer before a board call. Printing from their laptop works to another nearby printer, so a workaround is available.'",
        "type": "single_choice",
        "options": [{"id": "p1", "label": "P1 Critical"}, {"id": "p2", "label": "P2 High"}, {"id": "p3", "label": "P3 Medium"}, {"id": "p4", "label": "P4 Low"}],
        "correct": ["p2"],
        "explanation": "A time-sensitive executive need increases business impact, but the nearby printer provides a workaround and the organization is not down. That is P2 High, not P1.",
    },
    {
        "id": "triage-single-user-app",
        "prompt": "Which priority should this ticket receive?",
        "context": "Ticket: 'One payroll clerk cannot open the payroll application. The rest of payroll can work, and the clerk can use a shared workstation until their profile is repaired.'",
        "type": "single_choice",
        "options": [{"id": "p1", "label": "P1 Critical"}, {"id": "p2", "label": "P2 High"}, {"id": "p3", "label": "P3 Medium"}, {"id": "p4", "label": "P4 Low"}],
        "correct": ["p3"],
        "explanation": "The issue affects one person and has an approved workaround, although it blocks a business task. That fits P3 Medium under the impact-based rubric.",
    },
    {
        "id": "triage-vpn-degraded",
        "prompt": "Which priority should this ticket receive?",
        "context": "Ticket: 'Thirty remote staff can connect to VPN but sessions drop every few minutes. They can complete urgent work from the office or use the web versions of core tools.'",
        "type": "single_choice",
        "options": [{"id": "p1", "label": "P1 Critical"}, {"id": "p2", "label": "P2 High"}, {"id": "p3", "label": "P3 Medium"}, {"id": "p4", "label": "P4 Low"}],
        "correct": ["p2"],
        "explanation": "Many users are affected by an unstable business service. Workarounds prevent it from being a full P1 outage, but the scale and degradation warrant P2 High.",
    },
    {
        "id": "triage-keyboard-request",
        "prompt": "Which priority should this ticket receive?",
        "context": "Ticket: 'A staff member requests a replacement keyboard because two keys are worn. Their current keyboard remains usable and there is no deadline or service interruption.'",
        "type": "single_choice",
        "options": [{"id": "p1", "label": "P1 Critical"}, {"id": "p2", "label": "P2 High"}, {"id": "p3", "label": "P3 Medium"}, {"id": "p4", "label": "P4 Low"}],
        "correct": ["p4"],
        "explanation": "This is a single-user request with no outage, no urgent deadline, and a usable device. It fits P4 Low.",
    },
]


def reconcile_week_zero_requirements(db: Session) -> dict:
    """Keep only the current orientation lesson and checkpoint quiz required.

    Requirement flags update in place; activities and student history remain.
    """
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    week = db.query(TrainingWeek).filter(TrainingWeek.week_number == 0).first()
    if week is None:
        return {"updated": 0, "skipped": True, "reason": "week_missing"}
    orientation = (
        db.query(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .filter(Module.code == "MOD-000", Lesson.title == ORIENTATION_LESSON_TITLE)
        .first()
    )
    checkpoint = db.query(Quiz).filter(Quiz.week_number == 0, Quiz.title == ORIENTATION_QUIZ_TITLE).first()
    if orientation is None or checkpoint is None:
        return {"updated": 0, "skipped": True, "reason": "onboarding_content_missing"}

    updated = 0
    activities = db.query(TrainingWeekActivity).filter(TrainingWeekActivity.training_week_id == week.id).all()
    for activity in activities:
        should_be_required = (
            activity.activity_type == "lesson" and activity.content_ref == str(orientation.id)
        ) or (
            activity.activity_type == "quiz" and activity.content_ref == str(checkpoint.id)
        )
        if bool(activity.is_required) != should_be_required:
            activity.is_required = should_be_required
            updated += 1
    db.commit()
    return {"updated": updated, "skipped": False}


def sync_weeks_1_4_practice_realignment(db: Session) -> dict:
    """Replace retired early labs with deterministic, server-graded practice.

    Unlike the initial activity seed, this synchronizer intentionally mutates
    existing curriculum rows so already-seeded installations converge with a
    fresh database. Lab runs point to templates, never weekly activities, so
    retiring obsolete activity rows preserves all historical learner data.
    """
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}

    weeks = {
        week.week_number: week
        for week in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_([1, 2, 3, 4])).all()
    }
    if set(weeks) != {1, 2, 3, 4}:
        return {"updated": 0, "skipped": True, "reason": "weeks_1_4_missing"}

    result = {
        "updated_templates": 0,
        "created_templates": 0,
        "moved_activities": 0,
        "created_activities": 0,
        "deleted_activities": 0,
        "updated_cli_activities": 0,
        "skipped": False,
    }

    def update_template(template: LabTemplate, **values) -> None:
        if any(getattr(template, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(template, key, value)
            result["updated_templates"] += 1

    def next_display_order(week: TrainingWeek) -> int:
        return int(
            db.query(func.max(TrainingWeekActivity.display_order))
            .filter(TrainingWeekActivity.training_week_id == week.id)
            .scalar()
            or 0
        ) + 1

    def ensure_guided_lab_activity(lab: LabTemplate, week_number: int) -> None:
        week = weeks[week_number]
        candidates = (
            db.query(TrainingWeekActivity)
            .filter(
                TrainingWeekActivity.activity_type == "guided_lab",
                TrainingWeekActivity.content_ref == str(lab.id),
            )
            .order_by(TrainingWeekActivity.id)
            .all()
        )
        activity = next((row for row in candidates if row.training_week_id == week.id), candidates[0] if candidates else None)
        for duplicate in candidates:
            if duplicate is not activity:
                db.delete(duplicate)
                result["deleted_activities"] += 1

        if activity is None:
            activity = TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{week_number}-guided_lab-{lab.id}",
                activity_type="guided_lab",
                content_ref=str(lab.id),
                display_order=next_display_order(week),
                is_required=True,
                estimated_minutes=lab.estimated_minutes,
                prerequisite_mode="soft",
                metadata_json={},
            )
            db.add(activity)
            result["created_activities"] += 1
            return

        moved = activity.training_week_id != week.id
        if moved:
            destination_order = next_display_order(week)
            activity.training_week_id = week.id
            activity.display_order = destination_order
        changed = moved
        expected_stable_id = f"week-{week_number}-guided_lab-{lab.id}"
        for key, value in {
            "stable_id": expected_stable_id,
            "is_required": True,
            "estimated_minutes": lab.estimated_minutes,
        }.items():
            if getattr(activity, key) != value:
                setattr(activity, key, value)
                changed = True
        if changed:
            result["moved_activities"] += 1

    hardware = db.get(LabTemplate, 4)
    windows_diagnostics = db.get(LabTemplate, 3)
    retired_labs = [db.get(LabTemplate, 1), db.get(LabTemplate, 2)]
    if hardware is None or windows_diagnostics is None or any(lab is None for lab in retired_labs):
        return {"updated": 0, "skipped": True, "reason": "legacy_lab_templates_missing"}

    update_template(
        hardware,
        week_number=2,
        lab_type="structured_identification",
        required_evidence={},
        success_criteria={"questions": HARDWARE_IDENTIFICATION_QUESTIONS},
    )
    update_template(
        windows_diagnostics,
        week_number=3,
        lab_type="structured_diagnostic",
        required_evidence={},
        success_criteria={"questions": WINDOWS_DIAGNOSTICS_QUESTIONS},
    )
    ensure_guided_lab_activity(hardware, 2)
    ensure_guided_lab_activity(windows_diagnostics, 3)

    for retired_lab in retired_labs:
        if retired_lab.is_published:
            retired_lab.is_published = False
            result["updated_templates"] += 1
        retired_activities = (
            db.query(TrainingWeekActivity)
            .filter(
                TrainingWeekActivity.activity_type == "guided_lab",
                TrainingWeekActivity.content_ref == str(retired_lab.id),
            )
            .all()
        )
        for activity in retired_activities:
            db.delete(activity)
            result["deleted_activities"] += 1

    triage_description = (
        "Triage five incoming support tickets by business impact. Use this rubric: P1 Critical is a full outage "
        "affecting many users with no workaround; P2 High is a major multi-user degradation or an urgent executive "
        "need with a workaround; P3 Medium affects one user or a limited workflow with a workaround; P4 Low is a "
        "routine request with no meaningful interruption."
    )
    triage_setup = "Read the rubric in the lab description, then choose the single priority that matches each ticket's impact and available workaround."
    triage = db.query(LabTemplate).filter(LabTemplate.title == "Prioritize the Queue").first()
    if triage is None:
        triage = LabTemplate(
            title="Prioritize the Queue",
            description=triage_description,
            lab_type="structured_triage",
            week_number=4,
            difficulty=2,
            estimated_minutes=15,
            is_published=True,
            environment_requirements={},
            setup_instructions=triage_setup,
            success_criteria={"questions": TRIAGE_QUESTIONS},
            required_evidence={},
            hints={},
        )
        db.add(triage)
        db.flush()
        result["created_templates"] += 1
    else:
        update_template(
            triage,
            description=triage_description,
            lab_type="structured_triage",
            week_number=4,
            difficulty=2,
            estimated_minutes=15,
            is_published=True,
            setup_instructions=triage_setup,
            success_criteria={"questions": TRIAGE_QUESTIONS},
            required_evidence={},
        )
    ensure_guided_lab_activity(triage, 4)

    cli_activities = (
        db.query(TrainingWeekActivity)
        .filter(
            TrainingWeekActivity.activity_type == "networking_lab",
            TrainingWeekActivity.content_ref == "meet-cli-001",
        )
        .all()
    )
    for activity in cli_activities:
        if not activity.is_required:
            activity.is_required = True
            result["updated_cli_activities"] += 1

    db.commit()
    return result


def sync_initial_training_activities(db: Session) -> dict:
    """Populate references only when the migrated curriculum is still empty."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeek.__tablename__):
        return {"created": 0, "skipped": True, "reason": "migration_not_applied"}
    if db.query(TrainingWeekActivity.id).first():
        return {"created": 0, "skipped": True, "reason": "configuration_exists"}

    weeks = {row.week_number: row for row in db.query(TrainingWeek).all()}
    if not weeks:
        return {"created": 0, "skipped": True, "reason": "weeks_missing"}

    rows_by_week: dict[int, list[TrainingWeekActivity]] = defaultdict(list)

    def add(week_number, activity_type, content_ref, required, minutes=None, metadata=None):
        week = weeks.get(week_number)
        if week is None:
            return
        row = TrainingWeekActivity(
            training_week_id=week.id,
            stable_id=f"week-{week_number}-{activity_type}-{content_ref}",
            activity_type=activity_type,
            content_ref=str(content_ref),
            display_order=len(rows_by_week[week_number]) + 1,
            is_required=required,
            estimated_minutes=minutes,
            prerequisite_mode="soft",
            metadata_json=metadata or {},
        )
        rows_by_week[week_number].append(row)
        db.add(row)

    lessons = (
        db.query(Lesson, Module.module_order)
        .join(Module, Module.id == Lesson.module_id)
        .filter(
            Lesson.status == "published",
            (Module.module_order == 0) | Module.module_order.between(2, 25),
        )
        .order_by(Module.module_order, Lesson.lesson_order)
        .all()
    )
    for lesson, module_order in lessons:
        add(
            0 if module_order == 0 else module_order - 1,
            "lesson",
            lesson.id,
            lesson.id not in OPTIONAL_LESSON_IDS,
            lesson.estimated_minutes,
        )

    videos = {row.id: row for row in db.query(CurriculumVideo).filter(CurriculumVideo.active.is_(True)).all()}
    for week_number, video_ids in VIDEO_WEEKS.items():
        for video_id in video_ids:
            video = videos.get(video_id)
            if video:
                add(
                    week_number,
                    "video",
                    video.id,
                    video_is_required(week_number, video.id, video.job_relevance),
                    metadata=mapping_metadata(video.id),
                )

    quizzes = (
        db.query(Quiz)
        .filter(*student_visible_quiz_filters(), Quiz.week_number.between(0, 24))
        .order_by(Quiz.week_number, Quiz.id)
        .all()
    )
    for quiz in quizzes:
        add(quiz.week_number, "quiz", quiz.id, bool(quiz.is_required), 15)

    labs = (
        db.query(LabTemplate)
        .filter(LabTemplate.is_published.is_(True), LabTemplate.week_number.between(0, 24))
        .order_by(LabTemplate.week_number, LabTemplate.id)
        .all()
    )
    for lab in labs:
        add(lab.week_number, "guided_lab", lab.id, True, lab.estimated_minutes)

    for week_number, scenario_key in SERVICE_DESK_WEEKS.items():
        add(week_number, "service_desk_scenario", scenario_key, True, 30)

    cli_labs = {row.id: row for row in db.query(CliLab).filter(CliLab.id.in_(set(CLI_WEEKS))).all()}
    for lab_id, week_number in CLI_WEEKS.items():
        lab = cli_labs.get(lab_id)
        if lab:
            add(week_number, "networking_lab", lab.id, False, lab.est_minutes)

    capstones = (
        db.query(CapstoneTemplate)
        .filter(CapstoneTemplate.is_published.is_(True), CapstoneTemplate.week_number.between(0, 24))
        .order_by(CapstoneTemplate.week_number, CapstoneTemplate.id)
        .all()
    )
    for capstone in capstones:
        add(capstone.week_number, "capstone", capstone.id, False, (capstone.estimated_hours or 2) * 60)

    # Place a quiz after its exact title-linked video. Similar titles are never
    # treated as evidence of a relationship.
    quizzes_by_title = {quiz.title: quiz for quiz in quizzes}
    for week_number, rows in rows_by_week.items():
        for video in videos.values():
            quiz = quizzes_by_title.get(video.quiz_title)
            if quiz is None:
                continue
            video_row = next((row for row in rows if row.activity_type == "video" and row.content_ref == str(video.id)), None)
            quiz_row = next((row for row in rows if row.activity_type == "quiz" and row.content_ref == str(quiz.id)), None)
            if video_row and quiz_row:
                rows.remove(quiz_row)
                rows.insert(rows.index(video_row) + 1, quiz_row)
        for display_order, row in enumerate(rows, start=1):
            row.display_order = display_order

    db.commit()
    return {"created": sum(len(rows) for rows in rows_by_week.values()), "skipped": False}
