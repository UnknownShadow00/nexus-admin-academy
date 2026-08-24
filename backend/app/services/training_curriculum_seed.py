"""Idempotently populate weekly references after normal content seeding.

Production upgrades receive these rows in migration 0032. A brand-new database
runs migrations before the ordinary seed scripts have created content, so
``seed_curriculum.py`` calls this synchronizer after its final commit. Existing
weekly configuration is never overwritten.
"""

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func, inspect
from sqlalchemy.orm import Session

from app.models.capstone import CapstoneTemplate
from app.models.cli_lab import CliLab
from app.models.curriculum_video import CurriculumVideo
from app.models.lab import LabTemplate
from app.models.learning import Lesson, Module
from app.models.progression import PromotionGate, Role
from app.models.quiz import Question, Quiz
from app.models.service_desk import ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.training import TrainingWeek, TrainingWeekActivity
from app.services.quiz_visibility import student_visible_quiz_filters
from app.services.training_quiz_mapping import OPTIONAL_LESSON_IDS, OPTIONAL_LESSON_TITLES, mapping_metadata, video_is_required


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
        "visualId": "cpu-socket",
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
        "visualId": "dimm-generation",
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
        "visualId": "storage-interface",
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
        "visualId": "pcie-slot-size",
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
        "visualId": "psu-connectors",
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
        "id": "netstat-process",
        "prompt": "What should you do with the PID in this `netstat -ano` result?",
        "context": "`TCP  192.168.1.100:52341  203.0.113.40:443  ESTABLISHED  9012`",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Match PID 9012 to a process in Task Manager Details before deciding whether the connection is expected."},
            {"id": "b", "label": "Block port 443 immediately because every established connection is malicious."},
            {"id": "c", "label": "Change the workstation's DNS server."},
            {"id": "d", "label": "Delete the user profile."},
        ],
        "correct": ["a"],
        "explanation": "netstat identifies the connection and PID, but the PID must be matched to its process before the technician can judge whether the traffic is expected.",
    },
    {
        "id": "identity-before-action",
        "prompt": "Why run `hostname` and `whoami` at the start of a remote support session?",
        "context": "The user has two open remote sessions and says, 'Fix the policy on my laptop.'",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "They confirm the computer and signed-in account before you collect evidence or make a change."},
            {"id": "b", "label": "They reset the computer name and password."},
            {"id": "c", "label": "They force every Group Policy setting to refresh."},
            {"id": "d", "label": "They prove that DNS is healthy."},
        ],
        "correct": ["a"],
        "explanation": "Support evidence is only useful when it comes from the intended device and account. hostname and whoami establish that context before action.",
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


WEEK_3_CLI_COMMANDS = [
    "hostname",
    "whoami",
    "ipconfig /all",
    "ping 192.168.1.1",
    "nslookup intranet.nexus.internal",
    "tracert intranet.nexus.internal",
    "netstat -ano",
]


WINDOWS_TROUBLESHOOTING_PRACTICE = [
    {
        "id": "safe-mode-fork",
        "prompt": "Windows hangs during a normal boot but reaches the desktop in Safe Mode. What should you investigate first?",
        "context": "Safe Mode loads only a minimal set of drivers and services.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "A recently added driver, startup app, or third-party service"},
            {"id": "b", "label": "The monitor cable"},
            {"id": "c", "label": "A complete Windows reinstall"},
            {"id": "d", "label": "The user's cloud password"},
        ],
        "correct": ["a"],
        "explanation": "A successful Safe Mode boot points toward software that normal startup loads, so investigate recent drivers, startup apps, and services before destructive repair.",
    },
    {
        "id": "workbook-crash",
        "prompt": "Excel opens other files but closes when one workbook opens. What is the best first isolation step?",
        "context": "The problem follows one file, not every Excel session.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Test a copy of that workbook and check the Application log for the crash module"},
            {"id": "b", "label": "Replace the workstation immediately"},
            {"id": "c", "label": "Delete the user's Windows profile"},
            {"id": "d", "label": "Disable the network adapter"},
        ],
        "correct": ["a"],
        "explanation": "When other files work, preserve the original and isolate the file while Event Viewer identifies the faulting application or add-in.",
    },
    {
        "id": "disk-writer",
        "prompt": "A workstation regains 8 GB after cleanup but fills again every week. What should the ticket's next action be?",
        "context": "Repeated cleanup treats the symptom, not the cause.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Measure which folder or log is growing and fix the process writing it"},
            {"id": "b", "label": "Delete unfamiliar folders"},
            {"id": "c", "label": "Manually remove pagefile.sys"},
            {"id": "d", "label": "Schedule an automatic weekly deletion of user data"},
        ],
        "correct": ["a"],
        "explanation": "A recurring full disk needs before-and-after measurement and identification of the growing writer so the problem does not return.",
    },
]


ACCESS_DECISION_PRACTICE = [
    {
        "id": "two-permission-gates",
        "prompt": "Share permissions allow Change, but NTFS permissions allow only Read. What can the user do over the network?",
        "context": "Remote access must pass both permission gates.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Read files but not change them"},
            {"id": "b", "label": "Change any file"},
            {"id": "c", "label": "Take ownership automatically"},
            {"id": "d", "label": "Nothing; the share is always denied"},
        ],
        "correct": ["a"],
        "explanation": "The most restrictive effective permission wins. Share Change cannot override NTFS Read.",
    },
    {
        "id": "fresh-token",
        "prompt": "A manager-approved group was added correctly, but the user is still denied. What should happen before changing permissions again?",
        "context": "The user's current sign-in token was created before the group change.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Have the user sign out and sign back in, then retest"},
            {"id": "b", "label": "Grant the user Full Control directly"},
            {"id": "c", "label": "Disable inheritance"},
            {"id": "d", "label": "Restart the file server"},
        ],
        "correct": ["a"],
        "explanation": "A new logon creates a fresh token containing the updated group membership.",
    },
    {
        "id": "sensitive-access",
        "prompt": "A contractor requests urgent read access to Payroll and says the CFO is waiting. What is the safe action?",
        "context": "Urgency changes priority, not authorization.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Escalate with the requester, business reason, duration, and named approver"},
            {"id": "b", "label": "Grant read-only access for one hour"},
            {"id": "c", "label": "Add the contractor to the broad Finance group"},
            {"id": "d", "label": "Close the request without documenting it"},
        ],
        "correct": ["a"],
        "explanation": "Sensitive cross-department access requires authorized approval; a complete escalation is the correct resolution at this support level.",
    },
]


WEEKS_3_6_BRIEFS = {
    3: {
        "description": "Use Windows commands to identify the computer, test network reachability, check DNS, and gather evidence before changing anything.",
        "learning_goals": [
            "hostname and whoami confirm which computer and user you are supporting.",
            "ipconfig /all shows the IP address, gateway, DHCP state, and DNS servers; a 169.254 address usually means DHCP failed.",
            "Ping the gateway, then an internet IP, then a name to separate local, internet, and DNS failures.",
            "nslookup tests DNS directly, tracert shows the route, and netstat -ano links connections to process IDs.",
        ],
    },
    4: {
        "description": "Work the queue by business impact and urgency, then communicate a safe next step without overpromising.",
        "learning_goals": [
            "P1 is a broad outage with no workaround; P2 is major degradation; P3 is a limited interruption; P4 is a routine request.",
            "A workaround lowers urgency, while the number of affected users raises impact.",
            "An incident restores broken service; a service request asks for something new; risky changes and unauthorized access must be escalated.",
            "A useful handoff records the current state, evidence, exact next step, and any promised update time.",
        ],
    },
    5: {
        "description": "Isolate Windows startup, application, and disk problems with the least destructive useful test.",
        "learning_goals": [
            "If normal boot fails but Safe Mode works, investigate a recent driver, startup app, or third-party service.",
            "Event 1000 identifies an application crash module; a hang while opening a network file may be a network problem wearing an app symptom.",
            "Test another Windows user to separate per-user configuration from a machine-wide application failure.",
            "Measure what consumes disk space, use approved cleanup tools, and verify both the space recovered and the cause.",
        ],
    },
    6: {
        "description": "Resolve account and file-access requests without bypassing identity checks, approval, or least privilege.",
        "learning_goals": [
            "Verify identity before a password reset, and investigate the saved credential that causes a recurring lockout.",
            "Remote file access uses both share and NTFS permissions; the most restrictive effective result wins.",
            "After a group change, sign out and back in so Windows creates a fresh access token.",
            "Urgency is not authorization: package sensitive access requests with the business reason and approver, then escalate.",
        ],
    },
}


WEEKS_3_6_REQUIRED_VIDEOS = {3: {117, 118}, 4: {169}, 5: {162}, 6: {139}}
WEEKS_3_6_REQUIRED_QUIZZES = {3: 4, 4: 5, 5: 6, 6: 7}


def sync_weeks_3_6_quality(db: Session) -> dict:
    """Align the first post-foundation batch without replacing history rows."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    weeks = {
        week.week_number: week
        for week in db.query(TrainingWeek).filter(TrainingWeek.week_number.between(3, 6)).all()
    }
    if set(weeks) != {3, 4, 5, 6}:
        return {"updated": 0, "skipped": True, "reason": "weeks_missing"}
    seeded_week_ids = {
        row[0]
        for row in db.query(TrainingWeekActivity.training_week_id)
        .filter(
            TrainingWeekActivity.training_week_id.in_({week.id for week in weeks.values()}),
            TrainingWeekActivity.activity_type.in_(["lesson", "video", "quiz"]),
        )
        .distinct()
        .all()
    }
    if seeded_week_ids != {week.id for week in weeks.values()}:
        return {"updated": 0, "skipped": True, "reason": "curriculum_not_seeded"}

    result = {
        "updated_weeks": 0,
        "updated_activities": 0,
        "updated_templates": 0,
        "created_templates": 0,
        "created_activities": 0,
        "skipped": False,
    }

    for number, brief in WEEKS_3_6_BRIEFS.items():
        week = weeks[number]
        for field, value in brief.items():
            if getattr(week, field) != value:
                setattr(week, field, value)
                result["updated_weeks"] += 1

    quiz_rows = {quiz.id: quiz for quiz in db.query(Quiz).filter(Quiz.id.in_({2, 3, 4, 5, 6, 7})).all()}
    required_quiz_ids = set(WEEKS_3_6_REQUIRED_QUIZZES.values())
    for quiz_id, quiz in quiz_rows.items():
        should_be_required = quiz_id in required_quiz_ids
        # A quiz already marked "gate" backs a role-promotion requirement
        # (see PROMOTION_GATES in seed.py). Never downgrade that purpose here
        # or the gate becomes permanently unsatisfiable.
        expected_purpose = quiz.quiz_purpose if quiz.quiz_purpose == "gate" else ("required" if should_be_required else "practice")
        if (
            bool(quiz.is_required) != should_be_required
            or bool(quiz.show_in_weekly_checklist) != should_be_required
            or quiz.quiz_purpose != expected_purpose
        ):
            quiz.is_required = should_be_required
            quiz.show_in_weekly_checklist = should_be_required
            quiz.quiz_purpose = expected_purpose

    for number, week in weeks.items():
        required_quiz = str(WEEKS_3_6_REQUIRED_QUIZZES[number])
        required_videos = {str(item) for item in WEEKS_3_6_REQUIRED_VIDEOS[number]}
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        for activity in activities:
            if activity.activity_type == "lesson":
                should_be_required = False
            elif activity.activity_type == "video":
                should_be_required = activity.content_ref in required_videos
            elif activity.activity_type == "quiz":
                should_be_required = activity.content_ref == required_quiz
            elif activity.activity_type == "service_desk_scenario":
                should_be_required = number in {5, 6}
            else:
                continue
            if bool(activity.is_required) != should_be_required:
                activity.is_required = should_be_required
                result["updated_activities"] += 1

    def update_template(lab: LabTemplate, **values) -> None:
        changed = False
        for field, value in values.items():
            if getattr(lab, field) != value:
                setattr(lab, field, value)
                changed = True
        if changed:
            result["updated_templates"] += 1

    def ensure_lab(
        title: str,
        week_number: int,
        questions: list,
        *,
        cli: bool = False,
        description: str | None = None,
        setup_instructions: str | None = None,
        estimated_minutes: int = 25,
    ) -> LabTemplate:
        lab = db.query(LabTemplate).filter(LabTemplate.title == title).first()
        values = {
            "description": description or (
                "Run the required Windows commands in the real Nexus practice terminal, read the output, then diagnose each result."
                if cli
                else "Work through realistic support symptoms and choose the safest evidence-based next action."
            ),
            "lab_type": "structured_cli" if cli else "structured_diagnostic",
            "week_number": week_number,
            "difficulty": 1,
            "estimated_minutes": estimated_minutes,
            "is_published": True,
            "environment_requirements": {},
            "setup_instructions": setup_instructions or (
                "Use the command buttons as prompts, run every command, and read what each output proves before answering."
                if cli
                else "Read each symptom and evidence block. Choose the next action you could defend in a support ticket."
            ),
            "success_criteria": {
                "questions": questions,
                **({"required_commands": WEEK_3_CLI_COMMANDS} if cli else {}),
            },
            "required_evidence": {},
            "hints": {},
        }
        if lab is None:
            lab = LabTemplate(title=title, **values)
            db.add(lab)
            db.flush()
            result["created_templates"] += 1
        else:
            update_template(lab, **values)
        return lab

    labs = {
        3: ensure_lab("Windows Command-Line Diagnostics", 3, WINDOWS_DIAGNOSTICS_QUESTIONS, cli=True),
        4: ensure_lab(
            "Prioritize the Queue",
            4,
            TRIAGE_QUESTIONS,
            description=(
                "Triage five incoming support tickets by business impact. P1 Critical is a broad outage with no workaround; "
                "P2 High is major multi-user degradation; P3 Medium is a limited interruption; P4 Low is a routine request."
            ),
            setup_instructions="Read the impact, urgency, and workaround in each ticket, then choose the priority you could defend to the queue lead.",
            estimated_minutes=15,
        ),
        5: ensure_lab("Isolate the Windows Failure", 5, WINDOWS_TROUBLESHOOTING_PRACTICE),
        6: ensure_lab("Make the Safe Access Decision", 6, ACCESS_DECISION_PRACTICE),
    }

    for number, lab in labs.items():
        week = weeks[number]
        activity = (
            db.query(TrainingWeekActivity)
            .filter_by(training_week_id=week.id, activity_type="guided_lab", content_ref=str(lab.id))
            .first()
        )
        if activity is None:
            apply_order = (
                db.query(func.min(TrainingWeekActivity.display_order))
                .filter(
                    TrainingWeekActivity.training_week_id == week.id,
                    TrainingWeekActivity.activity_type.in_(["service_desk_scenario", "capstone"]),
                )
                .scalar()
            )
            if apply_order is None:
                display_order = (
                    db.query(func.max(TrainingWeekActivity.display_order))
                    .filter_by(training_week_id=week.id)
                    .scalar()
                    or 0
                ) + 1
            else:
                rows = (
                    db.query(TrainingWeekActivity)
                    .filter(
                        TrainingWeekActivity.training_week_id == week.id,
                        TrainingWeekActivity.display_order >= apply_order,
                    )
                    .order_by(TrainingWeekActivity.display_order.desc())
                    .all()
                )
                for row in rows:
                    row.display_order += 1
                    db.flush()
                display_order = apply_order
            activity = TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{number}-guided_lab-{lab.id}",
                activity_type="guided_lab",
                content_ref=str(lab.id),
                display_order=display_order,
                is_required=True,
                estimated_minutes=lab.estimated_minutes,
                prerequisite_mode="soft",
                metadata_json={},
            )
            db.add(activity)
            result["created_activities"] += 1
        else:
            for field, value in {"is_required": True, "estimated_minutes": lab.estimated_minutes}.items():
                if getattr(activity, field) != value:
                    setattr(activity, field, value)
                    result["updated_activities"] += 1

    db.commit()
    return result


ENDPOINT_RESPONSE_PRACTICE = [
    {
        "id": "active-compromise",
        "prompt": "Defender quarantined malware, but the workstation still makes unusual outbound connections. What should the help desk do next?",
        "context": "The detection may be contained, but there are signs the compromise is still active.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Disconnect the network, preserve evidence, record the timeline, and escalate to security"},
            {"id": "b", "label": "Delete the quarantine and return the PC to the user"},
            {"id": "c", "label": "Turn off Defender so the alert stops"},
            {"id": "d", "label": "Power off the PC immediately without recording anything"},
        ],
        "correct": ["a"],
        "explanation": "Active indicators require containment and escalation. Keep the machine powered on so volatile evidence is not lost.",
    },
    {
        "id": "phished-credentials",
        "prompt": "A user entered their password into a fake sign-in page. Which action has priority?",
        "context": "Assume the password and active sessions may now be controlled by someone else.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Reset the password from a trusted device, revoke sessions, and escalate with the timeline"},
            {"id": "b", "label": "Only delete the email"},
            {"id": "c", "label": "Open the link again to confirm it is fake"},
            {"id": "d", "label": "Wait for another alert before acting"},
        ],
        "correct": ["a"],
        "explanation": "Credential theft needs immediate account containment; a malware scan alone does not revoke stolen credentials or sessions.",
    },
    {
        "id": "firewall-finding",
        "prompt": "An application works only while Windows Firewall is disabled. What is the correct next step?",
        "context": "Disabling the firewall proved where to investigate, but it weakened the endpoint.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Re-enable the firewall and identify the narrow approved rule the application needs"},
            {"id": "b", "label": "Leave the firewall disabled and close the ticket"},
            {"id": "c", "label": "Disable Defender as well"},
            {"id": "d", "label": "Reimage the endpoint immediately"},
        ],
        "correct": ["a"],
        "explanation": "A disabled firewall is a diagnostic finding, not a safe resolution. Restore protection and fix the specific rule or escalate.",
    },
]


CLIENT_NETWORK_CLI_PRACTICE = [
    {
        "id": "apipa-local",
        "prompt": "One workstation shows 169.254.40.7 while nearby workstations have valid leases. Which fault domain should you check first?",
        "context": "`ipconfig /all` shows DHCP Enabled: Yes and no default gateway.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "That workstation's link, adapter, switch port, or DHCP path"},
            {"id": "b", "label": "The public DNS root servers"},
            {"id": "c", "label": "Every office router"},
            {"id": "d", "label": "The user's browser cache"},
        ],
        "correct": ["a"],
        "explanation": "APIPA on one machine points to its local path to DHCP, not a broad DNS or internet outage.",
    },
    {
        "id": "upstream-failure",
        "prompt": "The gateway replies, but `ping 1.1.1.1` fails. What evidence-based escalation should you make?",
        "context": "The client has a valid address, gateway, and DNS configuration.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Upstream routing failure, with both ping results attached"},
            {"id": "b", "label": "Local keyboard failure"},
            {"id": "c", "label": "Configured DNS failure"},
            {"id": "d", "label": "User profile corruption"},
        ],
        "correct": ["a"],
        "explanation": "The local path reaches the gateway, while numeric internet reachability fails beyond it. DNS has not been tested yet and is not needed for a numeric IP.",
    },
    {
        "id": "configured-dns",
        "prompt": "The configured resolver times out, but `nslookup intranet.nexus.internal 1.1.1.1` gets a response. What should you diagnose?",
        "context": "IP connectivity is already confirmed.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The configured DNS server or the client's DNS setting"},
            {"id": "b", "label": "The Ethernet cable"},
            {"id": "c", "label": "The monitor driver"},
            {"id": "d", "label": "The user's password"},
        ],
        "correct": ["a"],
        "explanation": "A known alternate resolver answering after the configured one fails isolates the problem to the configured DNS path or setting.",
    },
]


SUBNET_SUPPORT_PRACTICE = [
    {
        "id": "gateway-same-subnet",
        "prompt": "A PC is 192.168.10.45/24 and its gateway is 192.168.20.1. What is wrong?",
        "context": "A host must be able to reach its gateway on the local subnet before it can send remote traffic.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The gateway is outside the PC's /24 subnet"},
            {"id": "b", "label": "The PC address is a broadcast address"},
            {"id": "c", "label": "The mask should always be /16"},
            {"id": "d", "label": "Nothing is wrong"},
        ],
        "correct": ["a"],
        "explanation": "192.168.10.0/24 and 192.168.20.0/24 are different networks, so the PC cannot reach that gateway directly.",
    },
    {
        "id": "slash-26-bracket",
        "prompt": "Which subnet contains 192.168.1.70/26?",
        "context": "/26 has a block size of 64: .0, .64, .128, .192.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "192.168.1.64/26"},
            {"id": "b", "label": "192.168.1.0/26"},
            {"id": "c", "label": "192.168.1.128/26"},
            {"id": "d", "label": "192.168.1.192/26"},
        ],
        "correct": ["a"],
        "explanation": "70 falls between the .64 network address and .127 broadcast address.",
    },
    {
        "id": "slash-28-hosts",
        "prompt": "How many usable host addresses are in a /28 subnet?",
        "context": "A /28 contains 16 total addresses; network and broadcast are reserved.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "14"},
            {"id": "b", "label": "16"},
            {"id": "c", "label": "30"},
            {"id": "d", "label": "8"},
        ],
        "correct": ["a"],
        "explanation": "Sixteen total addresses minus the network and broadcast addresses leaves fourteen usable hosts.",
    },
    {
        "id": "slash-27-broadcast",
        "prompt": "What is the broadcast address for the subnet containing 10.1.1.100/27?",
        "context": "/27 has a block size of 32. The address 100 is in the .96-.127 block.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "10.1.1.127"},
            {"id": "b", "label": "10.1.1.95"},
            {"id": "c", "label": "10.1.1.128"},
            {"id": "d", "label": "10.1.1.255"},
        ],
        "correct": ["a"],
        "explanation": "The .96/27 subnet ends at .127, so .127 is its broadcast address.",
    },
]


WEEKS_7_10_QUALITY = {
    7: {
        "description": "Recognize endpoint threats, contain risk without destroying evidence, and escalate at the right moment.",
        "learning_goals": [
            "For active compromise: disconnect the network, keep power on, preserve what the user saw, and escalate with a timeline.",
            "If credentials entered a fake page, reset them from a trusted device and revoke active sessions immediately.",
            "Defender Protection History records the detection and action; quick, full, and offline scans serve different levels of suspicion.",
            "Turning off the firewall can isolate a cause, but it is never the final fix; restore it and use the narrow approved rule.",
        ],
        "required_videos": {137, 138, 143},
        "required_quiz": 8,
        "required_service_desk": False,
        "lab": {
            "title": "Choose the Safe Endpoint Response",
            "lab_type": "structured_security",
            "questions": ENDPOINT_RESPONSE_PRACTICE,
            "estimated_minutes": 20,
        },
    },
    8: {
        "description": "Use a repeatable command sequence to separate local, upstream, and DNS failures on a Windows client.",
        "learning_goals": [
            "Start with ipconfig /all: 169.254 means DHCP failed; a missing or off-subnet gateway blocks remote traffic.",
            "Ping the gateway, then 1.1.1.1, then a hostname so each result narrows the fault domain.",
            "If an alternate resolver works while the configured resolver fails, diagnose the configured DNS server or client setting.",
            "Do not hide DHCP failure with an unmanaged static address; it can create a later address conflict.",
        ],
        "required_videos": {6, 18, 61, 123},
        "required_quiz": 9,
        "required_service_desk": False,
        "lab": {
            "id": 2,
            "title": "Troubleshoot a Network Connectivity Scenario",
            "new_title": "Diagnose the Client Network",
            "lab_type": "structured_cli",
            "questions": CLIENT_NETWORK_CLI_PRACTICE,
            "required_commands": ["ipconfig /all", "ping 192.168.1.1", "ping 1.1.1.1", "nslookup intranet.nexus.internal"],
            "estimated_minutes": 25,
        },
    },
    9: {
        "description": "Read an IPv4 address and mask well enough to spot a bad gateway, find the subnet, and avoid assigning network or broadcast addresses.",
        "learning_goals": [
            "Hosts on the same subnet use ARP and switch directly; different subnets send traffic to the default gateway.",
            "/24 has 254 usable hosts; /25 splits the last octet in half; /26 uses blocks of 64; /27 uses 32; /28 uses 16.",
            "Network is the first address in a block, broadcast is the last, and usable hosts sit between them.",
            "For entry-level support, use block size to answer 'same subnet?' and validate a static address—not to design a complex VLSM plan.",
        ],
        "required_videos": {14, 15},
        "required_quiz": 10,
        "required_service_desk": False,
        "lab": {
            "id": 1,
            "title": "IP Addressing & Subnetting Practice",
            "lab_type": "structured_subnet",
            "questions": SUBNET_SUPPORT_PRACTICE,
            "estimated_minutes": 25,
        },
    },
    10: {
        "description": "Read switch state, recover a disabled port, and place an access port in the correct VLAN using the existing Cisco CLI simulator.",
        "learning_goals": [
            "The prompt shows the CLI mode: > user, # privileged, (config)# global configuration, and (config-if)# interface configuration.",
            "Use show interfaces status and show vlan brief before changing a port, then run no shutdown only when the evidence supports it.",
            "An access port belongs to one VLAN; a device moved to a port in the wrong VLAN may receive the wrong subnet or no lease.",
            "Use change → verify → save so a working running-config survives reboot.",
        ],
        "required_videos": {12, 13},
        "required_quiz": 12,
        "required_service_desk": False,
        "required_networking_labs": {"dev-sw-act-04", "dev-sw-act-18"},
    },
}


NETWORK_SERVICE_PATH_PRACTICE = [
    {
        "id": "trunk-scope",
        "prompt": "VLAN 10 works across both switches, but VLAN 20 fails only on the newly added switch. What should you check first?",
        "context": "Access ports and client addressing are correct. The switches connect through one trunk.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Whether VLAN 20 is allowed on the trunk at both ends"},
            {"id": "b", "label": "Every workstation network driver"},
            {"id": "c", "label": "The public DNS resolver"},
            {"id": "d", "label": "The printer queue"},
        ],
        "correct": ["a"],
        "explanation": "One working VLAN proves the link is alive. A single VLAN failing across it points to trunk membership or a mismatch.",
    },
    {
        "id": "relay-scope",
        "prompt": "Every client in a new VLAN gets 169.254 addresses; other VLANs receive leases normally. What is the best diagnosis?",
        "context": "The central DHCP server is healthy and has a scope for the new VLAN.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The new VLAN's DHCP relay/helper path is missing or wrong"},
            {"id": "b", "label": "The central DHCP service is down for everyone"},
            {"id": "c", "label": "DNS is returning an old record"},
            {"id": "d", "label": "The clients need unmanaged static addresses"},
        ],
        "correct": ["a"],
        "explanation": "DHCP broadcasts do not cross a router without relay. The working VLANs show the server itself is available.",
    },
    {
        "id": "svi-scope",
        "prompt": "A PC reaches peers in its own VLAN but cannot reach any other subnet. Which evidence should you gather next?",
        "context": "Its address and mask are correct.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Default gateway reachability and the VLAN SVI/router-interface state"},
            {"id": "b", "label": "The PC's display resolution"},
            {"id": "c", "label": "The switch fan speed"},
            {"id": "d", "label": "The user's mailbox quota"},
        ],
        "correct": ["a"],
        "explanation": "Same-VLAN traffic does not need routing. Cross-subnet failure points to the gateway or inter-VLAN route.",
    },
    {
        "id": "dns-scope",
        "prompt": "A server opens by IP address but not by hostname. What should the ticket say?",
        "context": "Ping to the server IP succeeds from the affected PC.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "IP reachability works; capture nslookup output and investigate DNS"},
            {"id": "b", "label": "The entire network is down"},
            {"id": "c", "label": "Replace the client network adapter"},
            {"id": "d", "label": "Disable the firewall permanently"},
        ],
        "correct": ["a"],
        "explanation": "Successful IP traffic isolates the failure to name resolution rather than basic connectivity.",
    },
]


SECURE_NETWORK_ADMIN_PRACTICE = [
    {
        "id": "ssh-not-telnet",
        "prompt": "A switch accepts Telnet but not SSH. What is the safe support goal?",
        "context": "Remote administration is required; Telnet sends credentials without encryption.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Configure and verify SSH, then restrict VTY access to SSH"},
            {"id": "b", "label": "Keep Telnet because it is faster"},
            {"id": "c", "label": "Expose the console port to the internet"},
            {"id": "d", "label": "Disable authentication on VTY lines"},
        ],
        "correct": ["a"],
        "explanation": "SSH provides encrypted remote administration; Telnet should not remain as the shortcut.",
    },
    {
        "id": "port-security",
        "prompt": "A desk port is err-disabled and the log reports a port-security violation. What comes first?",
        "context": "A small unmanaged switch was connected at the desk.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Remove or approve the unexpected device, then recover and verify the port"},
            {"id": "b", "label": "Run no shutdown repeatedly without checking the trigger"},
            {"id": "c", "label": "Delete the user's VLAN"},
            {"id": "d", "label": "Turn off port security everywhere"},
        ],
        "correct": ["a"],
        "explanation": "Recovering the port without resolving the violation causes another shutdown and ignores a security signal.",
    },
    {
        "id": "evidence-escalation",
        "prompt": "Which escalation gives the network team the most useful starting point?",
        "context": "About 60 users in VLAN 30 lost access at 09:15.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "VLAN 30 only; SVI is down in show ip interface brief; no change made"},
            {"id": "b", "label": "The network is broken—please fix"},
            {"id": "c", "label": "Probably DNS; reboot everything"},
            {"id": "d", "label": "One user says the internet feels slow"},
        ],
        "correct": ["a"],
        "explanation": "Scope, time, command evidence, and actions taken let the next technician act safely.",
    },
]


AD_ACCOUNT_PRACTICE = [
    {
        "id": "disabled-user",
        "prompt": "A manager asks you to re-enable a disabled employee account immediately. What should you do first?",
        "context": "The ticket does not explain why the account was disabled.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Verify the disable reason and required approval before changing it"},
            {"id": "b", "label": "Enable it because a manager asked"},
            {"id": "c", "label": "Delete and recreate the account"},
            {"id": "d", "label": "Add the user to Domain Admins"},
        ],
        "correct": ["a"],
        "explanation": "A disabled account may be a leaver or security hold. Confirm the authority and reason first.",
    },
    {
        "id": "group-access",
        "prompt": "Five Finance employees need the same folder access. What is the maintainable change?",
        "context": "An approved Finance security group already exists.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Add the users to the approved Finance group"},
            {"id": "b", "label": "Grant five separate user permissions"},
            {"id": "c", "label": "Give Everyone full control"},
            {"id": "d", "label": "Make all five local administrators"},
        ],
        "correct": ["a"],
        "explanation": "Group-based access is auditable and keeps the resource permission model consistent.",
    },
    {
        "id": "repeat-lockout",
        "prompt": "An AD account is unlocked but locks again minutes later. What should you investigate?",
        "context": "The user recently changed their password and has a phone and laptop.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "A device or service repeatedly using the old password"},
            {"id": "b", "label": "The user's monitor cable"},
            {"id": "c", "label": "The domain's folder naming convention"},
            {"id": "d", "label": "Whether the printer has paper"},
        ],
        "correct": ["a"],
        "explanation": "Repeated lockout after a password change commonly comes from stored stale credentials.",
    },
]


DOMAIN_OPERATIONS_PRACTICE = [
    {
        "id": "join-dns",
        "prompt": "A new PC can browse the web but says the domain cannot be found during join. What should you inspect first?",
        "context": "ipconfig /all shows the home router as the DNS server.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Point the client at the approved domain DNS and retry after verifying resolution"},
            {"id": "b", "label": "Reinstall Windows"},
            {"id": "c", "label": "Disable the computer account"},
            {"id": "d", "label": "Use a public resolver"},
        ],
        "correct": ["a"],
        "explanation": "Domain join depends on DNS records that locate a domain controller; ordinary internet access does not prove that lookup works.",
    },
    {
        "id": "secure-channel",
        "prompt": "A restored laptop reports that its trust relationship failed. What is the least disruptive first repair?",
        "context": "Peer laptops authenticate normally and the computer account still exists.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Repair the computer secure channel with approved credentials"},
            {"id": "b", "label": "Delete the user's account"},
            {"id": "c", "label": "Rebuild the domain"},
            {"id": "d", "label": "Always unjoin and rejoin first"},
        ],
        "correct": ["a"],
        "explanation": "A secure-channel repair addresses the broken machine trust without the disruption of a full unjoin/rejoin.",
    },
    {
        "id": "missing-drive",
        "prompt": "A newly added group member still cannot see the mapped drive. Which checks belong in your next step?",
        "context": "The access request was approved and the correct group was used.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Have the user sign out and back in to refresh the token"},
            {"id": "b", "label": "Check Group Policy drive-map processing"},
            {"id": "c", "label": "Grant direct Full Control to bypass groups"},
            {"id": "d", "label": "Check effective share and NTFS access"},
        ],
        "correct": ["a", "b", "d"],
        "explanation": "Token refresh, policy processing, and effective permissions are the relevant evidence; direct grants undermine the group model.",
    },
]


WEEKS_11_14_QUALITY = {
    11: {
        "description": "Trace a network-service failure across VLAN trunks, gateways, DHCP relay, routing, and DNS.",
        "learning_goals": [
            "An access port carries one VLAN; a trunk carries tagged VLANs, and both ends must agree on allowed and native VLANs.",
            "Same-VLAN traffic is switched; traffic to another subnet needs a reachable gateway, an up router/SVI interface, and a route.",
            "A whole VLAN getting APIPA while other VLANs work points to that VLAN's DHCP relay/helper path.",
            "IP works but names fail means gather DNS evidence; do not call it a total network outage.",
        ],
        "required_videos": {9, 10, 11},
        "required_quiz": 13,
        "required_service_desk": False,
        "lab": {"title": "Trace the Network Service Failure", "lab_type": "structured_network", "questions": NETWORK_SERVICE_PATH_PRACTICE, "estimated_minutes": 20},
    },
    12: {
        "description": "Troubleshoot shared network equipment safely and hand off evidence that another technician can use.",
        "learning_goals": [
            "Manage switches with encrypted SSH, keep a verified off-device configuration backup, and read logs before changing state.",
            "Err-disabled plus a port-security violation is a security clue: remove or approve the trigger before recovering the port.",
            "Work bottom-up: physical link, VLAN/trunk, addressing/routing, then DNS, firewall, and application.",
            "For shared infrastructure, change one thing, verify it, know the rollback, and escalate broad-impact changes with scope and command evidence.",
        ],
        "required_videos": set(),
        "required_quiz": 14,
        "required_service_desk": False,
        "lab": {"title": "Make the Safe Network Admin Decision", "lab_type": "structured_security", "questions": SECURE_NETWORK_ADMIN_PRACTICE, "estimated_minutes": 20},
    },
    13: {
        "description": "Use Active Directory structure and safety checks to handle common account and group requests.",
        "learning_goals": [
            "A domain centralizes users, computers, and policy; OUs organize objects and receive Group Policy.",
            "Security groups grant access; distribution groups are email lists. Prefer group membership over direct user permissions.",
            "For resets, unlocks, disabled accounts, and access changes: verify identity or approval, make the smallest change, and document it.",
            "A repeat lockout after a password change usually means a device or service still holds the old credential.",
        ],
        "required_videos": {140},
        "required_quiz": 15,
        "required_service_desk": False,
        "lab": {"title": "Handle the AD Account Request", "lab_type": "structured_security", "questions": AD_ACCOUNT_PRACTICE, "estimated_minutes": 20},
    },
    14: {
        "description": "Diagnose domain-join, secure-channel, and group-based file-access failures without disruptive shortcuts.",
        "learning_goals": [
            "A client must use the domain's DNS to locate a domain controller before a domain join can work.",
            "A trust-relationship error means the computer secure channel is broken; repair it before reaching for unjoin/rejoin.",
            "Use Accounts → Global group → Domain Local group → Permissions so access remains auditable and maintainable.",
            "After a group change, refresh the sign-in token and check Group Policy plus effective share and NTFS permissions.",
        ],
        "required_videos": set(),
        "required_quiz": 16,
        "required_service_desk": False,
        "lab": {"title": "Repair Domain Access Safely", "lab_type": "structured_windows", "questions": DOMAIN_OPERATIONS_PRACTICE, "estimated_minutes": 25},
    },
}


GROUP_POLICY_CLI_PRACTICE = [
    {
        "id": "applied-gpo",
        "prompt": "Which command output proves which user and computer policies actually applied?",
        "context": "The terminal shows separate COMPUTER SETTINGS and USER SETTINGS sections.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "gpresult /r"},
            {"id": "b", "label": "ipconfig /all"},
            {"id": "c", "label": "nslookup"},
            {"id": "d", "label": "sfc /scannow"},
        ],
        "correct": ["a"],
        "explanation": "gpresult reports the resultant user and computer policy instead of making you guess from the GPO editor.",
    },
    {
        "id": "wrong-ou",
        "prompt": "A drive-map GPO is linked to the Finance Users OU, but gpresult does not list it for the user. What should you verify next?",
        "context": "The GPO is enabled and other Finance users receive the drive.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The user's OU placement and security filtering"},
            {"id": "b", "label": "The user's monitor driver"},
            {"id": "c", "label": "The switch native VLAN"},
            {"id": "d", "label": "The printer toner level"},
        ],
        "correct": ["a"],
        "explanation": "A working policy for peers points to scope: the object must be under the link and allowed by filtering.",
    },
    {
        "id": "refresh-policy",
        "prompt": "After correcting scope, what is the safe verification sequence?",
        "context": "The policy is a user setting and the user's work is saved.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Run gpupdate, sign out/in if needed, then confirm with gpresult"},
            {"id": "b", "label": "Reboot every domain controller"},
            {"id": "c", "label": "Disable inheritance for the domain"},
            {"id": "d", "label": "Edit the local registry until the setting appears"},
        ],
        "correct": ["a"],
        "explanation": "Refresh the affected client and verify resultant policy; broad infrastructure changes are unnecessary.",
    },
]


POWERSHELL_SERVER_PRACTICE = [
    {
        "id": "discover-first",
        "prompt": "You do not remember the syntax for inspecting a service. What should you do before changing anything?",
        "context": "The practice terminal provides Get-Command, Get-Help, and Get-Service.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Use Get-Command to discover available commands"},
            {"id": "b", "label": "Use Get-Help Get-Service to inspect syntax"},
            {"id": "c", "label": "Guess a Stop-Service command in production"},
            {"id": "d", "label": "Use Get-Service to read current state"},
        ],
        "correct": ["a", "b", "d"],
        "explanation": "PowerShell supports a safe discover → inspect → act workflow; read state before issuing a change.",
    },
    {
        "id": "dhcp-reservation",
        "prompt": "A network printer needs the same address while remaining centrally managed. What should the DHCP admin create?",
        "context": "The printer is currently a normal DHCP client.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "A reservation for the printer's MAC address"},
            {"id": "b", "label": "A duplicate manual address inside the pool"},
            {"id": "c", "label": "A public DNS record"},
            {"id": "d", "label": "A second default gateway"},
        ],
        "correct": ["a"],
        "explanation": "A reservation keeps central DHCP control while consistently assigning the same address.",
    },
    {
        "id": "whatif",
        "prompt": "A PowerShell command would change 200 directory objects. What safety step belongs before execution?",
        "context": "The cmdlet supports the common -WhatIf parameter.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Run it with -WhatIf and inspect the exact targets"},
            {"id": "b", "label": "Turn off audit logging"},
            {"id": "c", "label": "Test directly against all 200 objects"},
            {"id": "d", "label": "Restart Active Directory first"},
        ],
        "correct": ["a"],
        "explanation": "-WhatIf previews supported changes so scope mistakes can be caught before mutation.",
    },
]


SERVER_RECOVERY_PRACTICE = [
    {
        "id": "restore-proof",
        "prompt": "A deleted department file has been restored. What must you verify before resolving the ticket?",
        "context": "The restore tool reports Success.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "The file opens and contains the expected data"},
            {"id": "b", "label": "The expected owner and permissions were restored"},
            {"id": "c", "label": "The user can access it from their normal path"},
            {"id": "d", "label": "The backup job name sounds correct"},
        ],
        "correct": ["a", "b", "c"],
        "explanation": "A successful job is not proof of a usable restore. Validate content, permissions, and the user's access path.",
    },
    {
        "id": "scheduled-task",
        "prompt": "A nightly task started failing immediately after its service-account password changed. What is the likely cause?",
        "context": "The task history records a logon failure at its normal start time.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The task still stores the old run-as credential"},
            {"id": "b", "label": "The DNS zone was deleted"},
            {"id": "c", "label": "Every server needs replacement"},
            {"id": "d", "label": "The user's desktop is asleep"},
        ],
        "correct": ["a"],
        "explanation": "The timing and logon error point to stale scheduled-task credentials.",
    },
    {
        "id": "patch-plan",
        "prompt": "Which plan is appropriate before patching a production server?",
        "context": "The service has a maintenance window and affects many users.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Confirm backup/rollback, notify users, patch in-window, and verify service health"},
            {"id": "b", "label": "Install immediately with no rollback plan"},
            {"id": "c", "label": "Disable monitoring so alerts stay quiet"},
            {"id": "d", "label": "Delete old event logs before recording a baseline"},
        ],
        "correct": ["a"],
        "explanation": "Shared services need a rollback, controlled timing, communication, and post-change verification.",
    },
]


LINUX_CLI_PRACTICE = [
    {
        "id": "read-permissions",
        "prompt": "ls -l shows -rw-r----- root support app.conf. Who can read the file?",
        "context": "The first triplet is owner, the second group, and the third others.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "root and members of the support group"},
            {"id": "b", "label": "Every local user"},
            {"id": "c", "label": "Only users with sudo, regardless of ownership"},
            {"id": "d", "label": "Nobody"},
        ],
        "correct": ["a"],
        "explanation": "Owner has read/write, group has read, and others have no permissions.",
    },
    {
        "id": "service-evidence",
        "prompt": "Before restarting a Linux service, which evidence should you capture?",
        "context": "The terminal supports systemctl status and journalctl.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Current service state and recent errors"},
            {"id": "b", "label": "Relevant journal entries"},
            {"id": "c", "label": "The user's wallpaper"},
            {"id": "d", "label": "The exact time and affected scope"},
        ],
        "correct": ["a", "b", "d"],
        "explanation": "State, logs, time, and scope preserve the evidence needed to explain whether a restart helped.",
    },
    {
        "id": "least-permission",
        "prompt": "A technician suggests chmod 777 because an application cannot read one file. What is the better approach?",
        "context": "The application runs under a known service account and group.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Inspect owner/group/mode and grant only the needed access"},
            {"id": "b", "label": "Give everyone full control"},
            {"id": "c", "label": "Delete and recreate the server"},
            {"id": "d", "label": "Run the application as root permanently"},
        ],
        "correct": ["a"],
        "explanation": "Fix the specific ownership or mode problem; 777 creates unnecessary write and execute access.",
    },
]


WEEKS_15_18_QUALITY = {
    15: {
        "description": "Use resultant-policy evidence to fix Group Policy scope and refresh problems without guessing.",
        "learning_goals": [
            "GPOs link to sites, domains, or OUs; computer settings apply to machines and user settings apply at user logon.",
            "Processing is Local → Site → Domain → OU, with closer applicable policy normally winning unless inheritance controls change it.",
            "Use gpresult /r to see what applied or was filtered, then verify OU placement and security filtering.",
            "After a scoped correction, refresh policy, sign out/in when required, and use gpresult again as proof.",
        ],
        "required_videos": set(),
        "required_quiz": 17,
        "required_service_desk": False,
        "lab": {"id": 5, "title": "AD Break-Fix: locked and misplaced account on a live domain", "new_title": "Diagnose the Group Policy Result", "lab_type": "structured_cli", "questions": GROUP_POLICY_CLI_PRACTICE, "required_commands": ["whoami", "gpresult /r", "gpupdate /force"], "estimated_minutes": 25},
    },
    16: {
        "description": "Use PowerShell safely to inspect Windows services and support DNS, DHCP, and directory operations.",
        "learning_goals": [
            "PowerShell cmdlets return objects: discover with Get-Command, learn syntax with Get-Help, and inspect properties before acting.",
            "Use -WhatIf and a narrowly verified target set before supported bulk changes.",
            "AD clients locate domain controllers through DNS; DHCP reservations give managed devices stable addresses without unmanaged statics.",
            "A full DHCP scope causes clients in that subnet to lose leases; gather scope and lease evidence before changing exclusions or duration.",
        ],
        "required_videos": {178, 179},
        "required_quiz": 18,
        "required_service_desk": False,
        "lab": {"title": "Investigate with PowerShell First", "lab_type": "structured_cli", "questions": POWERSHELL_SERVER_PRACTICE, "required_commands": ["get-command", "get-help get-service", "get-service"], "estimated_minutes": 25},
    },
    17: {
        "description": "Operate shared servers with evidence, tested restores, rollback plans, and careful verification.",
        "learning_goals": [
            "For a failed service or task, capture status, the first relevant error, time, scope, and run-as identity before restarting it.",
            "A backup is useful only when restore is tested; verify restored content, ownership, permissions, and user access.",
            "Patch shared servers in a maintenance window with notification, a tested rollback, baseline evidence, and post-change checks.",
            "A junior assists rather than independently leading a Domain Controller or AD system-state recovery.",
        ],
        "required_videos": {170},
        "required_quiz": 19,
        "required_service_desk": False,
        "lab": {"title": "Verify the Server Recovery Plan", "lab_type": "structured_operations", "questions": SERVER_RECOVERY_PRACTICE, "estimated_minutes": 20},
    },
    18: {
        "description": "Use the existing practice terminal to navigate Linux, read permissions, and gather service evidence safely.",
        "learning_goals": [
            "Linux starts at /; configuration usually lives in /etc, logs in /var/log, and user files in /home.",
            "Read ls -l as owner, group, and others; change only the ownership or permissions the service actually needs.",
            "Use id for group membership, systemctl status for service state, and journalctl for recent event evidence.",
            "Use sudo only for the specific approved command; avoid chmod 777 and permanent root execution as shortcuts.",
        ],
        "required_videos": {128, 129, 130},
        "required_quiz": 20,
        "required_service_desk": False,
        "lab": {"title": "Investigate the Linux Host", "lab_type": "structured_cli", "questions": LINUX_CLI_PRACTICE, "required_commands": ["pwd", "ls -l", "id", "systemctl status ssh", "journalctl"], "terminal_profile": "linux", "estimated_minutes": 30},
    },
}


LINUX_SERVICE_PRACTICE = [
    {
        "id": "failed-service",
        "prompt": "A service is enabled but inactive after boot. What should you read before restarting it?",
        "context": "systemctl status reports failed and names the unit; journalctl contains its recent messages.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "systemctl status for current state"},
            {"id": "b", "label": "journalctl for the first relevant error"},
            {"id": "c", "label": "The desktop wallpaper"},
            {"id": "d", "label": "The time and affected service scope"},
        ],
        "correct": ["a", "b", "d"],
        "explanation": "Capture state, the causal error, time, and scope so a restart does not erase the useful story.",
    },
    {
        "id": "linux-network",
        "prompt": "A Linux host has an address but no remote connectivity. Which command output identifies its default gateway?",
        "context": "You ran ip a and ip r in the practice terminal.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "ip r"},
            {"id": "b", "label": "ls -l"},
            {"id": "c", "label": "crontab -l"},
            {"id": "d", "label": "whoami"},
        ],
        "correct": ["a"],
        "explanation": "ip r shows the routing table, including the default route and interface.",
    },
    {
        "id": "cron-time",
        "prompt": "What does 0 2 * * * mean at the start of a cron entry?",
        "context": "The five fields are minute, hour, day of month, month, and day of week.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Run every day at 02:00"},
            {"id": "b", "label": "Run every two minutes"},
            {"id": "c", "label": "Run only on February 2"},
            {"id": "d", "label": "Run at noon"},
        ],
        "correct": ["a"],
        "explanation": "Minute 0 and hour 2 with wildcards for the remaining fields means daily at 02:00.",
    },
]


LINUX_PRODUCTION_PRACTICE = [
    {
        "id": "test-config",
        "prompt": "What should you do immediately before reloading nginx after a configuration edit?",
        "context": "The practice terminal's nginx -t reports whether syntax is valid.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Run nginx -t and stop if validation fails"},
            {"id": "b", "label": "Delete the old configuration"},
            {"id": "c", "label": "Open every firewall port"},
            {"id": "d", "label": "Reboot the server without testing"},
        ],
        "correct": ["a"],
        "explanation": "Syntax validation catches a bad change before a reload turns it into an outage.",
    },
    {
        "id": "disk-full",
        "prompt": "df reports / is 96% full and du shows /var/log uses 8.1 GB. What is the next safe action?",
        "context": "The application recently began writing a large repeated error.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Find the growing log and its cause, then use the approved rotation/cleanup path"},
            {"id": "b", "label": "Delete random files under /var"},
            {"id": "c", "label": "Restart only the application and ignore capacity"},
            {"id": "d", "label": "Run chmod 777 on /var/log"},
        ],
        "correct": ["a"],
        "explanation": "Measure first, address the error generating growth, and clean up through a controlled retention process.",
    },
    {
        "id": "local-not-remote",
        "prompt": "A web service responds locally but remote clients are refused. Which evidence is most relevant next?",
        "context": "The service is listening and nginx configuration validation succeeds.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Listening address and port"},
            {"id": "b", "label": "Host or upstream firewall rules"},
            {"id": "c", "label": "The user's local screen resolution"},
            {"id": "d", "label": "Whether the failure affects all remote sources"},
        ],
        "correct": ["a", "b", "d"],
        "explanation": "Local success proves the process responds; listener binding, firewall, and scope isolate the remote path.",
    },
]


CLOUD_IDENTITY_PRACTICE = [
    {
        "id": "signin-log",
        "prompt": "A user can sign into their laptop but not Microsoft 365. What should you inspect first?",
        "context": "The organization synchronizes identities from on-premises AD to Entra ID.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Entra sign-in logs and synchronization state"},
            {"id": "b", "label": "The laptop display driver"},
            {"id": "c", "label": "The office printer queue"},
            {"id": "d", "label": "Reset every authentication method immediately"},
        ],
        "correct": ["a"],
        "explanation": "The split between local and cloud sign-in points to cloud policy, sign-in evidence, or directory synchronization.",
    },
    {
        "id": "mfa-lost-phone",
        "prompt": "A caller says their phone was lost and asks for an MFA reset. What is the first required action?",
        "context": "The caller is in a hurry and can provide their username.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Verify identity using the approved recovery process"},
            {"id": "b", "label": "Remove MFA based on the username"},
            {"id": "c", "label": "Give them an administrator's phone number"},
            {"id": "d", "label": "Disable Conditional Access"},
        ],
        "correct": ["a"],
        "explanation": "An MFA reset changes an account's trust boundary, so identity verification comes first.",
    },
    {
        "id": "responsibility",
        "prompt": "An application service inside an Azure IaaS VM has stopped. Who owns that operating-system fix?",
        "context": "Azure reports that the VM and host platform are healthy.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Your organization, because IaaS customers manage the guest OS"},
            {"id": "b", "label": "The cloud provider, because every cloud layer is theirs"},
            {"id": "c", "label": "The user's internet provider"},
            {"id": "d", "label": "Nobody"},
        ],
        "correct": ["a"],
        "explanation": "In IaaS the provider runs the physical platform, while the customer operates the guest OS and applications.",
    },
]


AZURE_TRIAGE_PRACTICE = [
    {
        "id": "ssh-layer",
        "prompt": "A running Azure Linux VM cannot be reached by SSH. Which cloud-layer evidence should you check before changing the guest?",
        "context": "The VM overview reports Running and boot diagnostics look normal.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Effective NSG rules for TCP 22 and the source range"},
            {"id": "b", "label": "The current public IP and whether it changed"},
            {"id": "c", "label": "The user's keyboard layout"},
            {"id": "d", "label": "Azure activity log for recent network changes"},
        ],
        "correct": ["a", "b", "d"],
        "explanation": "NSG, endpoint address, and control-plane changes are the cloud wrapper around an otherwise normal SSH service.",
    },
    {
        "id": "safe-rdp",
        "prompt": "Which NSG rule is safer for temporary RDP support?",
        "context": "Only one approved administrator public IP needs access during the maintenance window.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Allow TCP 3389 from the approved admin IP only, then remove the temporary rule"},
            {"id": "b", "label": "Allow TCP 3389 from Any forever"},
            {"id": "c", "label": "Allow every port from the internet"},
            {"id": "d", "label": "Disable VM authentication"},
        ],
        "correct": ["a"],
        "explanation": "Narrow source, port, and duration reduce exposure while still enabling the approved support action.",
    },
    {
        "id": "sas-expired",
        "prompt": "An external partner's blob link worked yesterday and now reports authorization failure. What should you verify?",
        "context": "Internal users can still access the storage account.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "The SAS token expiry and permissions"},
            {"id": "b", "label": "The partner's monitor cable"},
            {"id": "c", "label": "Whether the VM needs a reboot"},
            {"id": "d", "label": "The on-premises domain functional level"},
        ],
        "correct": ["a"],
        "explanation": "A time-limited SAS commonly stops working at expiry while other authorized paths remain healthy.",
    },
]


WEEKS_19_22_QUALITY = {
    19: {
        "description": "Use Linux service, journal, network, and cron evidence to diagnose before restarting or editing.",
        "learning_goals": [
            "systemctl status shows current and boot state; journalctl shows the errors that explain a failure.",
            "On Linux, ip a shows interface addresses, ip r shows the gateway and routes, and dig tests DNS directly.",
            "Read cron as minute, hour, day-of-month, month, day-of-week; a limited PATH is a common manual-works/cron-fails cause.",
            "Capture state, first relevant error, time, and scope before a restart so you can verify what changed.",
        ],
        "required_videos": set(),
        "required_quiz": 21,
        "required_service_desk": False,
        "lab": {"title": "Diagnose the Linux Service", "lab_type": "structured_cli", "questions": LINUX_SERVICE_PRACTICE, "required_commands": ["systemctl status ssh", "journalctl -u ssh -e", "ip a", "ip r", "crontab -l"], "terminal_profile": "linux", "estimated_minutes": 30},
    },
    20: {
        "description": "Validate web configuration, isolate remote-access failures, and respond to capacity alerts with evidence.",
        "learning_goals": [
            "Test nginx configuration before reload; a working service with 403 often points to web-root ownership or permissions.",
            "If a service works locally but not remotely, inspect its listening address, firewall path, and affected scope.",
            "Use df to find a full filesystem and du to find the consuming path; do not delete random logs or restart around a full disk.",
            "Treat an alert as a lead: confirm it is real, identify impact and cause, act safely, then verify recovery.",
        ],
        "required_videos": set(),
        "required_quiz": 22,
        "required_service_desk": False,
        "lab": {"title": "Triage the Linux Production Alert", "lab_type": "structured_cli", "questions": LINUX_PRODUCTION_PRACTICE, "required_commands": ["nginx -t", "systemctl status nginx", "df -h", "du -sh /var/*", "ufw status"], "terminal_profile": "linux", "estimated_minutes": 30},
    },
    21: {
        "description": "Route cloud tickets by shared responsibility and handle Entra identity problems with sign-in evidence and verification.",
        "learning_goals": [
            "In IaaS the provider owns hardware and virtualization while your organization owns the guest OS, services, and data.",
            "Azure resources sit under tenant → subscription → resource group → resource; identify the right scope before acting.",
            "Start Entra login triage with sign-in logs, block state, Conditional Access result, and hybrid synchronization evidence.",
            "Verify identity before MFA reset or unblock, and change a synced identity at its authoritative directory.",
        ],
        "required_videos": {53, 54, 55, 56},
        "required_quiz": 23,
        "required_service_desk": False,
        # No "lab" spec here: Phase 4B.1 (sync_microsoft_workplace_foundations)
        # moves this week's guided lab ("Route the Cloud Identity Ticket",
        # LabTemplate id 19) to the new Entra module at week 26, since its
        # content fits there far better than this general-cloud module. Do
        # not re-add a lab spec here or _sync_quality_batch will recreate a
        # duplicate on every re-seed after the move has happened.
    },
    22: {
        "description": "Separate Azure control-plane failures from guest-OS failures and make narrowly scoped access changes.",
        "learning_goals": [
            "For an unreachable VM, check state, current IP, NSG rules, boot diagnostics, and activity log before blaming the guest OS.",
            "Never expose RDP or SSH from Any as a convenience; scope source, port, and duration to the approved need.",
            "A stopped/deallocated VM can lose a dynamic public IP; compare the current endpoint before troubleshooting credentials.",
            "For storage, check SAS expiry and permission plus network access rules; the activity log answers who changed a cloud resource and when.",
        ],
        "required_videos": set(),
        "required_quiz": 24,
        "required_service_desk": False,
        "lab": {"title": "Diagnose the Azure Access Path", "lab_type": "structured_cloud", "questions": AZURE_TRIAGE_PRACTICE, "estimated_minutes": 25},
    },
}


MIXED_QUEUE_PRACTICE = [
    {
        "id": "queue-order",
        "prompt": "Which item should lead this mixed queue?",
        "context": "A: one user's printer is offline.\nB: 60 users cannot reach the order system and monitoring confirms the service is down.\nC: an approved software install is due tomorrow.\nD: one user wants a new monitor.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "B — broad business impact and an active outage"},
            {"id": "b", "label": "A — it arrived first"},
            {"id": "c", "label": "C — all approved work outranks incidents"},
            {"id": "d", "label": "D — hardware requests always lead"},
        ],
        "correct": ["a"],
        "explanation": "Prioritize by impact and urgency. A confirmed multi-user business outage leads the queue.",
    },
    {
        "id": "incident-update",
        "prompt": "Which first incident update is most useful?",
        "context": "The order system failed at 10:05. The team is checking service and database health. The next update is due at 10:25.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Order system unavailable since 10:05; team investigating service/database health; next update 10:25"},
            {"id": "b", "label": "Something is broken; no ETA"},
            {"id": "c", "label": "Database failure caused by the last technician"},
            {"id": "d", "label": "Wait until the root cause is proven before communicating"},
        ],
        "correct": ["a"],
        "explanation": "An early update should state confirmed impact, current action, and the next communication time without guessing cause.",
    },
    {
        "id": "handoff",
        "prompt": "Your shift ends before the incident is resolved. What belongs in the handoff?",
        "context": "Another technician will continue immediately.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Current state and affected scope"},
            {"id": "b", "label": "What was ruled out, with evidence"},
            {"id": "c", "label": "The next safest action and any user promise"},
            {"id": "d", "label": "An unsupported root-cause guess"},
        ],
        "correct": ["a", "b", "c"],
        "explanation": "A handoff preserves state, evidence, next action, and commitments so work continues without repetition.",
    },
]


FINAL_SUPPORT_SHIFT_PRACTICE = [
    {
        "id": "shift-triage",
        "prompt": "Your shift starts with four tickets at once. Which two do you work first?",
        "context": (
            "(A) VPN authentication is failing for the entire remote workforce. "
            "(B) One user's mapped drive is slow. "
            "(C) A manager's routine password reset is queued. "
            "(D) A laptop's antivirus just logged a real-time malware detection; the user has not reported anything yet."
        ),
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "(A) the organization-wide VPN outage"},
            {"id": "b", "label": "(B) the one user's slow mapped drive"},
            {"id": "c", "label": "(C) the manager's routine password reset"},
            {"id": "d", "label": "(D) the unreported antivirus detection"},
        ],
        "correct": ["a", "d"],
        "explanation": "Impact and urgency drive priority, not arrival order or title: a wide-scale outage and a live security signal outrank a single slow drive and a routine reset.",
    },
    {
        "id": "windows-evidence",
        "prompt": "The practice terminal's ipconfig /all reports a DNS Servers entry pointing at 10.20.0.10, the correct internal resolver. Users still cannot reach the internal helpdesk site by name. What do you check next?",
        "context": "Use the practice terminal to run ipconfig /all before answering.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Run nslookup for the helpdesk hostname to see what address it actually resolves to"},
            {"id": "b", "label": "Reinstall the network adapter driver"},
            {"id": "c", "label": "Assume the DNS server itself is fully broken and escalate immediately"},
            {"id": "d", "label": "Change the user's IP address to static"},
        ],
        "correct": ["a"],
        "explanation": "The resolver address is correct, so the next evidence to gather is what that resolver actually returns for the failing name.",
    },
    {
        "id": "dns-evidence",
        "prompt": "nslookup helpdesk.nexus.internal returns a stale IP address that stopped being used after last month's server move. What is the correct next action?",
        "context": "Other recently rebooted machines resolve the name correctly.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Confirm on a second host, then clear the affected client's DNS resolver cache before escalating further"},
            {"id": "b", "label": "Edit every workstation's hosts file by hand"},
            {"id": "c", "label": "Delete the DNS server's zone file"},
            {"id": "d", "label": "Tell the user to ignore it"},
        ],
        "correct": ["a"],
        "explanation": "A stale answer that clears on other hosts points at a cached record on this client; verify with a second host, then clear the local cache instead of a destructive server-side change.",
    },
    {
        "id": "account-access",
        "prompt": "gpresult /r shows the current Nexus Standard User Policy applied, but the user's permissions still match an older, retired policy. What is the next diagnostic step?",
        "context": "The account's group membership changed yesterday.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Run gpupdate /force and confirm the refreshed result before making any manual change"},
            {"id": "b", "label": "Manually edit the local registry to match the new policy"},
            {"id": "c", "label": "Delete the user's profile"},
            {"id": "d", "label": "Add the user to every security group to be safe"},
        ],
        "correct": ["a"],
        "explanation": "A stale applied policy after a group change is usually a refresh timing issue; force a policy update and re-verify before any manual workaround.",
    },
    {
        "id": "remediate-or-escalate",
        "prompt": "Back to ticket (D): the antivirus detection is confirmed real, on a laptop with access to shared finance drives. What do you do?",
        "context": "You have not yet involved the security team.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "Isolate the device from the network, preserve evidence, and escalate to security immediately"},
            {"id": "b", "label": "Quietly re-image the laptop yourself and close the ticket"},
            {"id": "c", "label": "Ignore it since no user has complained"},
            {"id": "d", "label": "Delete the detected file and move on"},
        ],
        "correct": ["a"],
        "explanation": "A confirmed detection with access to sensitive shares is a suspected-compromise case: contain, preserve evidence, and escalate rather than improvising a fix.",
    },
    {
        "id": "documentation",
        "prompt": "You are closing out the VPN outage ticket. Which pieces belong in the ticket note?",
        "context": "Another technician may pick this up on the next shift.",
        "type": "multi_choice",
        "options": [
            {"id": "a", "label": "Confirmed impact and current state"},
            {"id": "b", "label": "The evidence gathered (command output, logs) and what it ruled out"},
            {"id": "c", "label": "The action taken and how the fix was verified"},
            {"id": "d", "label": "An unverified guess about root cause written as fact"},
        ],
        "correct": ["a", "b", "c"],
        "explanation": "A usable handoff records state, evidence-backed eliminations, and a verified action — never a guess presented as confirmed cause.",
    },
    {
        "id": "ready-proof",
        "prompt": "Looking back at this shift, which best shows you are ready for the role-gated capstone?",
        "context": "The capstone evaluates an integrated workflow, not memorized trivia.",
        "type": "single_choice",
        "options": [
            {"id": "a", "label": "You can prioritize, gather evidence, diagnose, remediate or escalate, and document across the course domains"},
            {"id": "b", "label": "You can recite every command without context"},
            {"id": "c", "label": "You mark every optional lesson complete"},
            {"id": "d", "label": "You never ask for approval or escalate"},
        ],
        "correct": ["a"],
        "explanation": "The capstone asks for repeatable support judgment across systems, including knowing when to escalate — this shift practiced exactly that.",
    },
]


WEEKS_23_24_QUALITY = {
    23: {
        "description": "Prioritize a mixed support queue, communicate during an incident, and hand work off without losing evidence.",
        "learning_goals": [
            "Classify each ticket by domain, failing layer, and owner, then prioritize by impact and urgency rather than arrival order.",
            "During an incident, send an early update with confirmed impact, current action, and the next update time—without guessing cause.",
            "Preserve evidence and follow the escalation path for suspected compromise; do not improvise a forensic response.",
            "A useful handoff records current state, evidence-backed eliminations, next action, and promises already made.",
        ],
        "required_videos": {174},
        "required_quiz": 25,
        "required_service_desk": False,
        "lab": {"title": "Work the Mixed Support Queue", "lab_type": "structured_operations", "questions": MIXED_QUEUE_PRACTICE, "estimated_minutes": 25},
    },
    24: {
        "description": "Run a full support shift: triage the queue, gather CLI evidence, diagnose, choose remediation or escalation, and document the outcome.",
        "learning_goals": [
            "Prioritize a mixed queue by impact and urgency, not arrival order or ticket title.",
            "Use ipconfig, nslookup, and gpresult evidence from the practice terminal to diagnose network, DNS, and Group Policy problems.",
            "Recognize when a finding needs escalation—such as a suspected compromise—instead of an improvised local fix.",
            "Write a ticket note that preserves state, evidence, and verification for the next technician.",
        ],
        "required_videos": set(),
        "required_quiz": None,
        "required_service_desk": False,
        "lab": {
            "title": "Final Support Shift",
            "lab_type": "structured_capstone",
            "questions": FINAL_SUPPORT_SHIFT_PRACTICE,
            "required_commands": ["ipconfig /all", "nslookup helpdesk.nexus.internal", "gpresult /r"],
            "estimated_minutes": 35,
        },
    },
}


def _sync_quality_batch(db: Session, specs: dict[int, dict]) -> dict:
    weeks = {
        week.week_number: week
        for week in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_(set(specs))).all()
    }
    if set(weeks) != set(specs):
        return {"updated": 0, "skipped": True, "reason": "weeks_missing"}
    seeded_week_ids = {
        row[0]
        for row in db.query(TrainingWeekActivity.training_week_id)
        .filter(
            TrainingWeekActivity.training_week_id.in_({week.id for week in weeks.values()}),
            TrainingWeekActivity.activity_type.in_(["lesson", "video", "quiz"]),
        )
        .distinct()
        .all()
    }
    if seeded_week_ids != {week.id for week in weeks.values()}:
        return {"updated": 0, "skipped": True, "reason": "curriculum_not_seeded"}

    result = {
        "updated_weeks": 0,
        "updated_activities": 0,
        "updated_templates": 0,
        "created_templates": 0,
        "created_activities": 0,
        "skipped": False,
    }

    quiz_activity_ids = set()
    for number, spec in specs.items():
        week = weeks[number]
        for field in ("description", "learning_goals"):
            if getattr(week, field) != spec[field]:
                setattr(week, field, spec[field])
                result["updated_weeks"] += 1

        required_videos = {str(value) for value in spec.get("required_videos", set())}
        required_quiz = str(spec["required_quiz"]) if spec.get("required_quiz") is not None else None
        required_networking_labs = spec.get("required_networking_labs", set())
        activities = db.query(TrainingWeekActivity).filter_by(training_week_id=week.id).all()
        for activity in activities:
            if activity.activity_type == "lesson":
                should_be_required = False
            elif activity.activity_type == "video":
                should_be_required = activity.content_ref in required_videos
            elif activity.activity_type == "quiz":
                quiz_activity_ids.add(int(activity.content_ref))
                should_be_required = activity.content_ref == required_quiz
            elif activity.activity_type == "service_desk_scenario":
                should_be_required = bool(spec.get("required_service_desk"))
            elif activity.activity_type == "networking_lab":
                should_be_required = activity.content_ref in required_networking_labs
            else:
                continue
            if bool(activity.is_required) != should_be_required:
                activity.is_required = should_be_required
                result["updated_activities"] += 1

    required_quiz_ids = {spec["required_quiz"] for spec in specs.values() if spec.get("required_quiz") is not None}
    for quiz in db.query(Quiz).filter(Quiz.id.in_(quiz_activity_ids)).all():
        should_be_required = quiz.id in required_quiz_ids
        # A quiz already marked "gate" backs a role-promotion requirement
        # (see PROMOTION_GATES in seed.py). Never downgrade that purpose here
        # or the gate becomes permanently unsatisfiable.
        expected_purpose = quiz.quiz_purpose if quiz.quiz_purpose == "gate" else ("required" if should_be_required else "practice")
        quiz.is_required = should_be_required
        quiz.show_in_weekly_checklist = should_be_required
        quiz.quiz_purpose = expected_purpose

    def ensure_practice_activity(week: TrainingWeek, lab: LabTemplate) -> None:
        activity = (
            db.query(TrainingWeekActivity)
            .filter_by(training_week_id=week.id, activity_type="guided_lab", content_ref=str(lab.id))
            .first()
        )
        if activity is not None:
            for field, value in {"is_required": True, "estimated_minutes": lab.estimated_minutes}.items():
                if getattr(activity, field) != value:
                    setattr(activity, field, value)
                    result["updated_activities"] += 1
            return

        apply_order = (
            db.query(func.min(TrainingWeekActivity.display_order))
            .filter(
                TrainingWeekActivity.training_week_id == week.id,
                TrainingWeekActivity.activity_type.in_(["service_desk_scenario", "capstone"]),
            )
            .scalar()
        )
        if apply_order is None:
            display_order = (
                db.query(func.max(TrainingWeekActivity.display_order)).filter_by(training_week_id=week.id).scalar() or 0
            ) + 1
        else:
            rows = (
                db.query(TrainingWeekActivity)
                .filter(
                    TrainingWeekActivity.training_week_id == week.id,
                    TrainingWeekActivity.display_order >= apply_order,
                )
                .order_by(TrainingWeekActivity.display_order.desc())
                .all()
            )
            for row in rows:
                row.display_order += 1
                db.flush()
            display_order = apply_order
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{week.week_number}-guided_lab-{lab.id}",
                activity_type="guided_lab",
                content_ref=str(lab.id),
                display_order=display_order,
                is_required=True,
                estimated_minutes=lab.estimated_minutes,
                prerequisite_mode="soft",
                metadata_json={},
            )
        )
        result["created_activities"] += 1

    for number, spec in specs.items():
        lab_spec = spec.get("lab")
        if not lab_spec:
            continue
        lab = db.get(LabTemplate, lab_spec.get("id")) if lab_spec.get("id") else None
        if lab is None:
            lab = db.query(LabTemplate).filter(LabTemplate.title == lab_spec["title"]).first()
        values = {
            "title": lab_spec.get("new_title", lab_spec["title"]),
            "description": lab_spec.get(
                "description",
                "Work through realistic evidence and choose the safest support action before moving to an independent case.",
            ),
            "lab_type": lab_spec["lab_type"],
            "week_number": number,
            "difficulty": 1,
            "estimated_minutes": lab_spec.get("estimated_minutes", 20),
            "is_published": True,
            "environment_requirements": {},
            "setup_instructions": lab_spec.get(
                "setup_instructions",
                "Read each symptom and evidence block. Choose the action you could defend in a support ticket.",
            ),
            "success_criteria": {
                "questions": lab_spec["questions"],
                **({"required_commands": lab_spec["required_commands"]} if lab_spec.get("required_commands") else {}),
                **({"terminal_profile": lab_spec["terminal_profile"]} if lab_spec.get("terminal_profile") else {}),
            },
            "required_evidence": {},
            "hints": {},
        }
        if lab is None:
            lab = LabTemplate(**values)
            db.add(lab)
            db.flush()
            result["created_templates"] += 1
        else:
            changed = False
            for field, value in values.items():
                if getattr(lab, field) != value:
                    setattr(lab, field, value)
                    changed = True
            if changed:
                result["updated_templates"] += 1
        ensure_practice_activity(weeks[number], lab)

    db.commit()
    return result


def sync_weeks_7_10_quality(db: Session) -> dict:
    """Align endpoint and networking foundations with real practice."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    result = _sync_quality_batch(db, WEEKS_7_10_QUALITY)
    if result.get("skipped"):
        return result

    # Accounts & Access cases remain locked until two Desktop Support passes.
    # Week 6 follows only one required Desktop case, so requiring inc2505 there
    # creates a dead Apply button. Move the already-unlocked password-reset
    # scenario from its old, mismatched Week 3 slot into Week 6 instead. The
    # scenario and every historical attempt remain unchanged.
    weeks = {
        week.week_number: week
        for week in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_({3, 6})).all()
    }
    password_reset = (
        db.query(TrainingWeekActivity)
        .filter_by(activity_type="service_desk_scenario", content_ref="password-reset")
        .first()
    )
    if set(weeks) == {3, 6} and password_reset is not None:
        week_6 = weeks[6]
        if password_reset.training_week_id != week_6.id:
            apply_order = (
                db.query(func.min(TrainingWeekActivity.display_order))
                .filter_by(training_week_id=week_6.id, activity_type="service_desk_scenario")
                .scalar()
            )
            if apply_order is None:
                apply_order = (
                    db.query(func.max(TrainingWeekActivity.display_order))
                    .filter_by(training_week_id=week_6.id)
                    .scalar()
                    or 0
                ) + 1
            else:
                rows = (
                    db.query(TrainingWeekActivity)
                    .filter(
                        TrainingWeekActivity.training_week_id == week_6.id,
                        TrainingWeekActivity.display_order >= apply_order,
                    )
                    .order_by(TrainingWeekActivity.display_order.desc())
                    .all()
                )
                for row in rows:
                    row.display_order += 1
                    db.flush()
            password_reset.training_week_id = week_6.id
            password_reset.display_order = apply_order
            password_reset.stable_id = "week-6-service_desk_scenario-password-reset"
            result["updated_activities"] += 1
            db.flush()
        for activity in db.query(TrainingWeekActivity).filter_by(
            training_week_id=week_6.id,
            activity_type="service_desk_scenario",
        ):
            should_be_required = activity.content_ref == "password-reset"
            if bool(activity.is_required) != should_be_required:
                activity.is_required = should_be_required
                result["updated_activities"] += 1
        db.commit()
    return result


def sync_weeks_11_14_quality(db: Session) -> dict:
    """Align network services and directory foundations with graded practice."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    return _sync_quality_batch(db, WEEKS_11_14_QUALITY)


def sync_weeks_15_18_quality(db: Session) -> dict:
    """Align Group Policy, server operations, and Linux with real practice."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    return _sync_quality_batch(db, WEEKS_15_18_QUALITY)


def sync_weeks_19_22_quality(db: Session) -> dict:
    """Align Linux production and cloud support with deterministic practice."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    return _sync_quality_batch(db, WEEKS_19_22_QUALITY)


def sync_weeks_23_24_quality(db: Session) -> dict:
    """Align the integrated-operations finish and capstone readiness path."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}
    weeks = {
        week.week_number: week
        for week in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_({23, 24})).all()
    }
    if set(weeks) != {23, 24}:
        return {"updated": 0, "skipped": True, "reason": "weeks_missing"}

    # Quiz 25 assesses mixed-queue triage, incident updates, and handoffs—the
    # Week 23 outcomes. Move its existing activity instead of cloning it so
    # student activity history remains attached to the same row.
    readiness_quiz = (
        db.query(TrainingWeekActivity)
        .filter_by(activity_type="quiz", content_ref="25")
        .first()
    )
    moved_quiz = False
    if readiness_quiz is not None and readiness_quiz.training_week_id != weeks[23].id:
        readiness_quiz.training_week_id = weeks[23].id
        readiness_quiz.stable_id = "week-23-quiz-25"
        readiness_quiz.display_order = (
            db.query(func.max(TrainingWeekActivity.display_order))
            .filter_by(training_week_id=weeks[23].id)
            .scalar()
            or 0
        ) + 1
        moved_quiz = True
    quiz = db.get(Quiz, 25)
    if quiz is not None and quiz.week_number != 23:
        quiz.week_number = 23
    db.flush()

    week_24_title = "Capstone: Final Support Shift"
    if weeks[24].title != week_24_title:
        weeks[24].title = week_24_title

    result = _sync_quality_batch(db, WEEKS_23_24_QUALITY)
    if moved_quiz:
        result["updated_activities"] += 1
    return result


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


def reconcile_optional_lesson_requirements(db: Session) -> dict:
    """Retire selected standalone lessons without removing their activities or history."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}

    optional_ids = {
        str(lesson.id)
        for lesson in db.query(Lesson).filter(Lesson.title.in_(OPTIONAL_LESSON_TITLES)).all()
    }
    if not optional_ids:
        return {"updated": 0, "skipped": True, "reason": "optional_lessons_missing"}

    updated = 0
    activities = (
        db.query(TrainingWeekActivity)
        .filter(
            TrainingWeekActivity.activity_type == "lesson",
            TrainingWeekActivity.content_ref.in_(optional_ids),
        )
        .all()
    )
    for activity in activities:
        if activity.is_required:
            activity.is_required = False
            updated += 1
    db.commit()
    return {"updated": updated, "skipped": False}


def reconcile_video_requirements(db: Session) -> dict:
    """Keep existing video activities' is_required in sync with video_is_required().

    VIDEO_WEEKS and BEGINNER_REQUIRED_VIDEO_IDS only drive is_required for rows
    created by sync_initial_training_activities(), which never runs again once
    any activity exists. This reconciler updates already-seeded video rows in
    place so curriculum edits (e.g. re-scoping which videos gate a week) reach
    production without resetting student history.
    """
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated": 0, "skipped": True, "reason": "migration_not_applied"}

    videos = {row.id: row for row in db.query(CurriculumVideo).all()}
    weeks_by_id = {week.id: week.week_number for week in db.query(TrainingWeek).all()}

    updated = 0
    activities = db.query(TrainingWeekActivity).filter(TrainingWeekActivity.activity_type == "video").all()
    for activity in activities:
        week_number = weeks_by_id.get(activity.training_week_id)
        video = videos.get(int(activity.content_ref))
        if week_number is None or video is None:
            continue
        should_be_required = video_is_required(week_number, video.id, video.job_relevance)
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

    def practice_display_order(week: TrainingWeek) -> int:
        """Return a display_order that lands before this week's Apply step.

        Practice (guided_lab) must precede Apply (service_desk_scenario /
        capstone) in the Learn -> Quiz -> Practice -> Apply sequence. Appending
        to the end of the week (next_display_order) would place Practice after
        an already-seeded Apply activity, so instead take the slot immediately
        before the earliest Apply activity and shift everything at/after it
        down by one to make room.
        """
        apply_min = (
            db.query(func.min(TrainingWeekActivity.display_order))
            .filter(
                TrainingWeekActivity.training_week_id == week.id,
                TrainingWeekActivity.activity_type.in_(["service_desk_scenario", "capstone"]),
            )
            .scalar()
        )
        if apply_min is None:
            return next_display_order(week)
        # Shift highest-first with an immediate flush per row: a single bulk
        # UPDATE can transiently collide with the (training_week_id,
        # display_order) unique constraint, since SQLite checks it per row
        # rather than deferring to end-of-statement.
        to_shift = (
            db.query(TrainingWeekActivity)
            .filter(
                TrainingWeekActivity.training_week_id == week.id,
                TrainingWeekActivity.display_order >= apply_min,
            )
            .order_by(TrainingWeekActivity.display_order.desc())
            .all()
        )
        for row in to_shift:
            row.display_order += 1
            db.flush()
        return apply_min

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
                display_order=practice_display_order(week),
                is_required=True,
                estimated_minutes=lab.estimated_minutes,
                prerequisite_mode="soft",
                metadata_json={},
            )
            db.add(activity)
            result["created_activities"] += 1
            return

        moved = activity.training_week_id != week.id
        apply_min = (
            db.query(func.min(TrainingWeekActivity.display_order))
            .filter(
                TrainingWeekActivity.training_week_id == week.id,
                TrainingWeekActivity.activity_type.in_(["service_desk_scenario", "capstone"]),
            )
            .scalar()
        )
        misordered = apply_min is not None and activity.display_order >= apply_min
        if moved or misordered:
            # Compute the destination order *before* touching training_week_id:
            # practice_display_order() issues queries that autoflush pending
            # changes, and flushing a half-updated training_week_id (new week,
            # stale display_order) can collide with an existing row already
            # occupying that display_order in the destination week.
            new_order = practice_display_order(week)
            activity.training_week_id = week.id
            activity.display_order = new_order
        changed = moved or misordered
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
            lesson.id not in OPTIONAL_LESSON_IDS and lesson.title not in OPTIONAL_LESSON_TITLES,
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


# Phase 4A.1: sequence advanced/infrastructure networking (Switching & VLANs,
# Routing & Network Services, Secure Network Administration -- weeks 10-12)
# after Identity & Access (weeks 13-15) and the future Microsoft 365/Entra/
# Endpoint Management stage, matching the job-ready Stage order documented in
# docs/JOB_READY_CURRICULUM_BLUEPRINT.md. Only TrainingWeek.display_order
# changes here. week_number is the stable identity key used everywhere else
# (MODULE_WEEKS, CLI_PACK_WEEKS, SERVICE_DESK_PACKS, curriculum_structure.py
# source_week_number, Quiz.week_number, legacy Module.code mapping, and every
# activity/progress record) and is intentionally left untouched, so this is a
# presentation/sequencing change only -- it does not move, duplicate, or
# reset any student's completion evidence.
_ADVANCED_NETWORKING_RESEQUENCE_TARGETS = {
    # week_number -> new display_order
    10: 13,  # Switching & VLANs
    11: 14,  # Routing & Network Services
    12: 15,  # Secure Network Administration
    13: 10,  # Active Directory Foundations
    14: 11,  # Domain Operations & File Services
    15: 12,  # Group Policy
}


_M365_MOVED_LAB_19_UPDATE = {
    "title": "Investigate the Entra Identity Ticket",
    "week_number": 26,
    "success_criteria": {
        "questions": [
            {
                "id": "signin-log",
                "prompt": "A user can sign into their laptop but not Microsoft 365. What should you inspect first?",
                "context": "The organization synchronizes identities from on-premises AD to Entra ID.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Entra sign-in logs and synchronization state"},
                    {"id": "b", "label": "The laptop display driver"},
                    {"id": "c", "label": "The office printer queue"},
                    {"id": "d", "label": "Reset every authentication method immediately"},
                ],
                "correct": ["a"],
                "explanation": "The split between local and cloud sign-in points to cloud policy, sign-in evidence, or directory synchronization.",
            },
            {
                "id": "mfa-lost-phone",
                "prompt": "A caller says their phone was lost and asks for an MFA reset. What is the first required action?",
                "context": "The caller is in a hurry and can provide their username.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Verify identity using the approved recovery process"},
                    {"id": "b", "label": "Remove MFA based on the username"},
                    {"id": "c", "label": "Give them an administrator's phone number"},
                    {"id": "d", "label": "Disable Conditional Access"},
                ],
                "correct": ["a"],
                "explanation": "An MFA reset changes an account's trust boundary, so identity verification comes first.",
            },
            {
                "id": "group-vs-individual",
                "prompt": "A department needs five new hires to have the same file and app access as the rest of the team. What is the safest way to grant it?",
                "context": "Individual access grants for this team are already inconsistent from past one-off requests.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Add each new hire to the team's existing Entra group"},
                    {"id": "b", "label": "Grant each new hire Global Administrator to be safe"},
                    {"id": "c", "label": "Copy permissions individually from a random existing employee"},
                    {"id": "d", "label": "Leave access ungranted until someone complains"},
                ],
                "correct": ["a"],
                "explanation": "Group-based access is the same discipline from on-prem AD, still true in Entra: consistent, auditable, and reversible in one place.",
            },
        ],
    },
}

_M365_NEW_LABS = {
    27: {
        "title": "Investigate the Suspicious MFA Prompt",
        "lab_type": "structured_cloud",
        "description": "Recognize account-takeover risk in an MFA event and choose the safe response instead of the fast one.",
        "estimated_minutes": 20,
        "questions": [
            {
                "id": "unexpected-prompt",
                "prompt": "A user reports approving an MFA prompt they didn't expect, then immediately became worried. What should you do first?",
                "context": "The user says they tapped Approve before thinking, from their home wifi, during their normal work hours.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Treat this as a possible account compromise: investigate sign-in activity and involve security escalation, not just reset MFA and close the ticket"},
                    {"id": "b", "label": "Reset MFA and close the ticket -- the user is fine now"},
                    {"id": "c", "label": "Tell the user it's nothing to worry about"},
                    {"id": "d", "label": "Ignore it since no data loss was reported"},
                ],
                "correct": ["a"],
                "explanation": "An unexpected approved MFA prompt is a classic account-takeover indicator (MFA fatigue/push-bombing). A reset alone doesn't establish whether the account was already accessed -- investigate sign-in activity and escalate per policy.",
            },
            {
                "id": "not-auto-reset",
                "prompt": "Why is 'just reset their MFA and move on' the wrong first move for a suspicious-prompt ticket, even though it's the correct move for a lost-phone ticket?",
                "context": "Compare this to a routine 'I lost my phone' MFA-reset request.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "A suspicious prompt may mean the account is already compromised -- resetting MFA without investigating could let an attacker re-register a new method just as easily as the legitimate user"},
                    {"id": "b", "label": "It's actually the same situation and the same fix applies"},
                    {"id": "c", "label": "Resetting MFA is technically impossible for this ticket type"},
                    {"id": "d", "label": "The user hasn't paid for MFA reset support"},
                ],
                "correct": ["a"],
                "explanation": "A lost-phone request has a known, verifiable cause. A suspicious prompt has an unknown cause that might be active compromise -- the investigation step changes what's safe to do next.",
            },
            {
                "id": "escalation-criteria",
                "prompt": "What should you document and hand off if you escalate a suspicious-MFA ticket to security/a senior technician?",
                "context": "You are not authorized to make the final compromise determination yourself.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "The exact prompt timing, sign-in log evidence you reviewed, and why the pattern looked suspicious"},
                    {"id": "b", "label": "Nothing -- just forward the ticket with no notes"},
                    {"id": "c", "label": "Your guess about who the attacker might be"},
                    {"id": "d", "label": "A promise that you already reset the account, so no further action is needed"},
                ],
                "correct": ["a"],
                "explanation": "A useful escalation hands off the evidence you gathered, not just the ticket -- that's what lets the next responder act quickly without repeating your investigation.",
            },
        ],
    },
    28: {
        "title": "Diagnose the Mailbox Permission Ticket",
        "lab_type": "structured_cloud",
        "description": "Work through a shared-mailbox permission report and an Outlook client complaint using the right evidence for each.",
        "estimated_minutes": 20,
        "questions": [
            {
                "id": "full-access-no-send",
                "prompt": "Daniel reports: 'I can open the shared mailbox but I can't send from it.' Evidence shows Full Access is granted and Send As is not. What should you do?",
                "context": "The original request only asked for Daniel to be able to read and triage messages in the shared mailbox.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Confirm what Daniel is actually authorized to do, then grant Send As or Send on Behalf only if that authorization covers sending"},
                    {"id": "b", "label": "Grant Send As immediately since he asked"},
                    {"id": "c", "label": "Remove his Full Access instead"},
                    {"id": "d", "label": "Tell him it's impossible to send from a shared mailbox"},
                ],
                "correct": ["a"],
                "explanation": "Full Access without Send As/Send on Behalf is expected behavior, not a bug -- the fix is confirming authorization before granting more than was originally requested.",
            },
            {
                "id": "outlook-vs-server",
                "prompt": "A user's desktop Outlook keeps prompting for credentials and won't finish connecting. Outlook on the web works fine for the same account. Where is the problem?",
                "context": "No other users report mail delivery issues.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Local to the desktop Outlook profile/cache, not the mailbox"},
                    {"id": "b", "label": "The Exchange Online service is down"},
                    {"id": "c", "label": "The mailbox has been deleted"},
                    {"id": "d", "label": "The user's license was revoked"},
                ],
                "correct": ["a"],
                "explanation": "A working web client with a failing desktop client isolates the fault to the local profile/cache, not the server side.",
            },
            {
                "id": "least-privilege-mailbox",
                "prompt": "A manager asks for Full Access AND Send As on a shared mailbox 'just in case,' but the actual task is only reading incoming orders. What should you do?",
                "context": "You have the technical ability to grant both immediately.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Grant only what the stated task requires, and note that broader access can be requested separately with justification"},
                    {"id": "b", "label": "Grant everything requested to avoid a follow-up ticket"},
                    {"id": "c", "label": "Deny all access since the request seems excessive"},
                    {"id": "d", "label": "Grant Global Administrator instead"},
                ],
                "correct": ["a"],
                "explanation": "Least privilege applies to mailbox permissions like anything else -- match the grant to the justified task, not the broadest possible ask.",
            },
        ],
    },
    29: {
        "title": "Diagnose the Collaboration Ticket",
        "lab_type": "structured_cloud",
        "description": "Work through OneDrive sync and SharePoint access reports using the identity/permission-first approach.",
        "estimated_minutes": 20,
        "questions": [
            {
                "id": "onedrive-wrong-account",
                "prompt": "A user says OneDrive stopped syncing this morning. The sync icon shows a personal Microsoft account, not their work account. What is the fix?",
                "context": "The user recently set up a new laptop and signed into several apps quickly.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Sign OneDrive out of the personal account and back in with the correct work account"},
                    {"id": "b", "label": "Reinstall Windows"},
                    {"id": "c", "label": "Delete all local files and start over"},
                    {"id": "d", "label": "Escalate to network engineering"},
                ],
                "correct": ["a"],
                "explanation": "Wrong-account sign-in is one of the most common OneDrive 'stopped syncing' causes, especially on freshly set-up devices.",
            },
            {
                "id": "known-folder-move",
                "prompt": "A user says their Desktop files 'disappeared' right after IT rolled out a new OneDrive policy. What should you check before treating this as data loss?",
                "context": "The organization recently enabled Known Folder Move for all managed devices.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "Whether Known Folder Move redirected their Desktop/Documents into their OneDrive folder"},
                    {"id": "b", "label": "Whether the hard drive failed"},
                    {"id": "c", "label": "Whether their license was removed"},
                    {"id": "d", "label": "Whether the files were emailed to someone else"},
                ],
                "correct": ["a"],
                "explanation": "Known Folder Move relocates, not deletes, these folders -- checking there avoids an unnecessary data-loss escalation.",
            },
            {
                "id": "sharepoint-permission-not-sync",
                "prompt": "A user reports a SharePoint-synced folder 'won't update' with a colleague's changes, and Explorer shows a padlock on the files. What is the likely cause?",
                "context": "The library recently changed its permission and checkout requirements for this team.",
                "type": "single_choice",
                "options": [
                    {"id": "a", "label": "The user's SharePoint permission level, not a broken sync client"},
                    {"id": "b", "label": "A corrupted OneDrive installation that must be reinstalled first"},
                    {"id": "c", "label": "A DNS problem"},
                    {"id": "d", "label": "A hardware fault on their device"},
                ],
                "correct": ["a"],
                "explanation": "A padlock and stale content after a permission change point at the SharePoint permission/checkout layer, not the sync engine -- confirm access before touching the client.",
            },
        ],
    },
}

_M365_SERVICE_DESK_TICKETS = json.loads(r'''[
{
  "id": "INC2601",
  "stableKey": "m365-entra-auth-method",
  "title": "Authenticator stopped working after a device upgrade",
  "category": "access",
  "priority": "medium",
  "status": "open",
  "assignedTo": "you",
  "escalated": false,
  "createdAt": "2026-08-10T08:20:00.000Z",
  "requester": {
    "name": "Priya Nair",
    "department": "Marketing",
    "email": "priya.nair@nexus.example",
    "location": "North Campus",
    "contact": "Employee support portal"
  },
  "device": {
    "assetTag": "NX-5140",
    "deviceName": "MKT-LT-19",
    "kind": "laptop",
    "operatingSystem": "Windows 11 Enterprise",
    "state": "active"
  },
  "description": {
    "issue": "I set up my new phone yesterday and now Microsoft Authenticator won't approve my sign-in prompts. My password still works fine.",
    "businessImpact": "Priya cannot reach the campaign approval dashboard before this afternoon's deadline.",
    "reportedByLine": "Submitted through the employee support portal after the password step succeeded twice.",
    "troubleshooting": [
      "Confirmed the password step succeeds every time.",
      "The old phone was traded in as part of a carrier upgrade.",
      "Has not attempted to approve any prompts she doesn't recognize."
    ]
  },
  "sla": {"target": "Respond within 4 hours", "dueAt": "2026-08-10T12:20:00.000Z"},
  "hints": [
    "Confirm the password step succeeds separately from the second-factor problem.",
    "Review the registered authentication methods after the approved identity check.",
    "Re-register only the unusable method, then verify the account is ready to sign in."
  ],
  "notes": [],
  "activity": [
    {"id": "INC2601-created", "label": "Ticket created", "timestamp": "2026-08-10T08:20:00.000Z", "detail": "Created from the employee support portal."},
    {"id": "INC2601-assigned", "label": "Assigned to you", "timestamp": "2026-08-10T08:24:00.000Z", "detail": "Starter Support routed this case to your shift.", "tone": "info"}
  ],
  "suggestedTools": ["directory", "documentation"],
  "objective_catalog_version": "process-v3"
},
{
  "id": "INC2602",
  "stableKey": "m365-signin-conditional-access",
  "title": "Sign-in blocked even though the password is correct",
  "category": "access",
  "priority": "high",
  "status": "open",
  "assignedTo": "you",
  "escalated": false,
  "createdAt": "2026-08-11T09:05:00.000Z",
  "requester": {
    "name": "Owen Mackay",
    "department": "Field Sales",
    "email": "owen.mackay@nexus.example",
    "location": "Remote - Traveling",
    "contact": "Employee support portal"
  },
  "device": {
    "assetTag": "NX-6203",
    "deviceName": "SALES-LT-08",
    "kind": "laptop",
    "operatingSystem": "Windows 11 Enterprise",
    "state": "attention"
  },
  "description": {
    "issue": "My password is definitely correct but Microsoft 365 won't let me sign in. It just says my sign-in was blocked.",
    "businessImpact": "Owen cannot access the client order system while traveling for a same-day meeting.",
    "reportedByLine": "Submitted from an airport lounge network, confirmed the password step succeeded before the block appeared.",
    "troubleshooting": [
      "Confirmed the password is correct.",
      "Tried again from the same network with the same result.",
      "Has not tried from a different network yet."
    ]
  },
  "sla": {"target": "Respond within 2 hours", "dueAt": "2026-08-11T11:05:00.000Z"},
  "hints": [
    "Check the sign-in log's Authentication Details tab for the exact block reason before assuming a password problem.",
    "Determine whether this was a Conditional Access policy block tied to a risk signal, not a credential failure.",
    "Confirm identity before re-enabling the account, the same as any other account-state change."
  ],
  "notes": [],
  "activity": [
    {"id": "INC2602-created", "label": "Ticket created", "timestamp": "2026-08-11T09:05:00.000Z", "detail": "Created from the employee support portal.", "tone": "warning"},
    {"id": "INC2602-assigned", "label": "Assigned to you", "timestamp": "2026-08-11T09:09:00.000Z", "detail": "Starter Support routed this case to your shift.", "tone": "info"}
  ],
  "suggestedTools": ["directory", "documentation"],
  "objective_catalog_version": "process-v3"
}
]''')

_M365_CAPSTONE = {
    "title": "Microsoft Workplace Support Shift",
    "description": (
        "A short realistic shift with several unrelated Microsoft 365 requests. Prioritize, investigate, "
        "resolve or escalate, verify, and document each one -- the same integrated skill as a real first-line shift, "
        "scoped to this stage's content."
    ),
    "week_number": 29,
    "estimated_hours": 2,
    "requirements": {
        "tickets": [
            {"summary": "A user cannot sign in; password is correct.", "expected_skill": "Distinguish a Conditional Access block from a credential failure using sign-in log evidence."},
            {"summary": "A user has a mailbox permission complaint (can open, can't send as).", "expected_skill": "Distinguish Full Access from Send As and grant only what was authorized."},
            {"summary": "A user reports OneDrive sync failure.", "expected_skill": "Rule out wrong-account sign-in and Known Folder Move before treating it as data loss."},
            {"summary": "A suspicious, unrequested MFA approval prompt.", "expected_skill": "Recognize account-takeover risk and escalate instead of resetting and closing."},
        ],
        "process": ["prioritize", "investigate", "resolve_or_escalate", "verify", "document"],
    },
    "deliverables": {
        "notes": "One documented resolution or escalation per ticket, each stating the evidence reviewed and the action taken.",
    },
    "rubric": {
        "prioritization": "Addressed the suspicious-MFA and blocked-sign-in tickets before the lower-urgency requests.",
        "evidence_first": "Investigated before acting on every ticket, especially the two identity-adjacent ones.",
        "safe_process": "Did not reset or grant access beyond what each ticket's evidence and authorization supported.",
        "documentation": "Left a clear, evidence-based note or escalation reason for every ticket.",
    },
}


def sync_advanced_networking_resequence(db: Session) -> dict:
    """Idempotently move weeks 10-12 (advanced networking) after weeks 13-15
    (Identity & Access) in TrainingWeek.display_order. Safe to call whether or
    not the swap has already been applied; never touches week_number.

    Once Phase 4B.1 (sync_microsoft_workplace_foundations) has run, its own
    _M365_DISPLAY_ORDER_SHIFT further moves weeks 10-12 from display_order
    13-15 to 18-20 to make room for the new Microsoft Workplace weeks. This
    function's _ADVANCED_NETWORKING_RESEQUENCE_TARGETS predates that and
    would otherwise "fix" weeks 10-12 back to their now-stale 13-15 targets
    on every later idempotent re-seed. Skip once week 25 exists -- Phase
    4B.1's shift is authoritative for those rows from that point on.
    """
    if db.query(TrainingWeek).filter(TrainingWeek.week_number == 25).first():
        return {"weeks_checked": 0, "weeks_updated": 0, "skipped": True, "reason": "superseded_by_microsoft_workplace_shift"}
    weeks = {
        row.week_number: row
        for row in db.query(TrainingWeek)
        .filter(TrainingWeek.week_number.in_(_ADVANCED_NETWORKING_RESEQUENCE_TARGETS))
        .all()
    }
    updated = 0
    for week_number, desired_order in _ADVANCED_NETWORKING_RESEQUENCE_TARGETS.items():
        week = weeks.get(week_number)
        if week is None:
            continue
        if week.display_order != desired_order:
            week.display_order = desired_order
            updated += 1
    db.commit()
    return {"weeks_checked": len(weeks), "weeks_updated": updated}


def sync_microsoft_workplace_foundations(db: Session) -> dict:
    """Idempotently build the Phase 4B.1 Microsoft 365, Entra & Endpoint
    Management stage: new weeks 25-29, their content, and the System B
    (progression_service.py / service_desk_progression.py) reconciliation
    documented in docs/MICROSOFT_WORKPLACE_CURRICULUM.md.

    Safe to call whether or not it has already run. Never renumbers an
    existing week_number; only shifts TrainingWeek.display_order for the 12
    rows in _M365_DISPLAY_ORDER_SHIFT, and only moves (not deletes) Lesson 58
    and LabTemplate 19 out of week 21 into the new week 26.
    """
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeek.__tablename__):
        return {"skipped": True, "reason": "migration_not_applied"}
    if db.query(TrainingWeek).filter(TrainingWeek.week_number == 25).first():
        return {"skipped": True, "reason": "already_applied"}
    # This function is called both from migration 0057's upgrade() (self-
    # contained production deploy, matching sync_weeks_23_24_quality's
    # established pattern) and again from seed_curriculum.py after
    # sync_initial_training_activities. On a truly fresh/empty database the
    # migration runs before any base-curriculum TrainingWeekActivity rows
    # exist; creating rows here first would trip
    # sync_initial_training_activities's own "already configured" guard and
    # silently skip populating weeks 0-24 entirely. Defer to the later call.
    base_curriculum_seeded = (
        db.query(TrainingWeekActivity.id)
        .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
        .filter(TrainingWeek.week_number == 0)
        .first()
    )
    if not base_curriculum_seeded:
        return {"skipped": True, "reason": "base_curriculum_not_seeded"}

    result = {"skipped": False, "weeks_created": 0, "weeks_shifted": 0, "modules_created": 0,
               "lessons_created": 0, "quizzes_created": 0, "questions_created": 0,
               "labs_created": 0, "labs_moved": 0, "tickets_created": 0, "capstones_created": 0,
               "activities_created": 0, "activities_moved": 0, "gates_updated": 0}

    # 1. Shift display_order for the 12 existing weeks that must move to make
    # room -- week_number is never touched.
    existing_weeks = {
        row.week_number: row
        for row in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_(_M365_DISPLAY_ORDER_SHIFT)).all()
    }
    for week_number, new_order in _M365_DISPLAY_ORDER_SHIFT.items():
        week = existing_weeks.get(week_number)
        if week is not None and week.display_order != new_order:
            week.display_order = new_order
            result["weeks_shifted"] += 1
    db.flush()

    # 2. Create the 5 new TrainingWeek rows.
    new_weeks: dict[int, TrainingWeek] = {}
    for week_number, spec in _M365_NEW_WEEKS.items():
        week = TrainingWeek(
            week_number=week_number,
            display_order=spec["display_order"],
            title=spec["title"],
            description=spec["description"],
            learning_goals=spec["learning_goals"],
            is_active=True,
            requires_previous_week=True,
        )
        db.add(week)
        new_weeks[week_number] = week
        result["weeks_created"] += 1
    db.flush()

    # 3. Create the 5 legacy Module rows (MOD-025..029) so System B
    # (progression_service.MODULE_WEEKS, min_completed_lessons gates) has a
    # concrete container to point at, matching the MOD-000..024 pattern.
    legacy_modules: dict[int, Module] = {}
    for week_number, (code, title) in _M365_LEGACY_MODULES.items():
        module = db.query(Module).filter_by(code=code).first()
        if module is None:
            module = Module(
                code=code,
                title=title,
                description=_M365_NEW_WEEKS[week_number]["description"],
                module_order=week_number + 1,
                difficulty_band=3,
                active=True,
            )
            db.add(module)
            result["modules_created"] += 1
        legacy_modules[week_number] = module
    db.flush()

    # 4. New Lesson rows (weeks 25, 27, 28, 29). Week 26 reuses the existing,
    # moved Lesson 58 instead of a new row (see step 6).
    lessons: dict[int, Lesson] = {}
    for week_number, spec in _M365_LESSONS.items():
        lesson = Lesson(
            module_id=legacy_modules[week_number].id,
            title=spec["title"],
            summary=spec["summary"],
            lesson_order=1,
            outcomes=spec["outcomes"],
            estimated_minutes=12,
            status="published",
        )
        db.add(lesson)
        lessons[week_number] = lesson
        result["lessons_created"] += 1
    db.flush()

    # 5. Move Lesson 58 ("Entra ID: Cloud Identity Administration") out of
    # week 21 / MOD-021 into the new week 26 / MOD-026. Lesson.id is
    # unchanged, so StudentLessonProgress (keyed on lesson_id) is untouched.
    moved_lesson = db.get(Lesson, 58)
    if moved_lesson is not None and moved_lesson.module_id != legacy_modules[26].id:
        moved_lesson.module_id = legacy_modules[26].id
        moved_lesson.lesson_order = 1
        lessons[26] = moved_lesson
        result["activities_moved"] += 1
    elif moved_lesson is not None:
        lessons[26] = moved_lesson

    # 6. New Quiz + Question rows.
    quizzes: dict[int, Quiz] = {}
    for week_number, spec in _M365_QUIZZES.items():
        quiz = Quiz(
            title=spec["title"],
            week_number=week_number,
            domain_id="4.0",
            status="published",
            quiz_purpose=spec.get("quiz_purpose", "required"),
            is_required=True,
            show_in_weekly_checklist=True,
            show_in_practice_library=True,
            editorial_status="validated",
            question_count=len(spec["questions"]),
            answer_keys_validated=True,
            explanations_complete=True,
            is_active=True,
        )
        db.add(quiz)
        db.flush()
        quizzes[week_number] = quiz
        result["quizzes_created"] += 1
        for index, question in enumerate(spec["questions"], start=1):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    question_text=question["question_text"],
                    option_a=question["option_a"],
                    option_b=question["option_b"],
                    option_c=question["option_c"],
                    option_d=question["option_d"],
                    correct_answer=question["correct_answer"],
                    explanation=question["explanation"],
                    difficulty=2,
                    seed_key=f"m365-week{week_number}-q{index}",
                )
            )
            result["questions_created"] += 1
    db.flush()

    # 7. New LabTemplate rows (weeks 27, 28, 29) -- evidence-interpretation
    # troubleshooting exercises. Exchange/OneDrive/SharePoint have no live
    # simulation tool surface (see service_desk_progression.py comment), so
    # these use the same question-based guided_lab mechanism as the existing
    # "Route the Cloud Identity Ticket" lab rather than fabricated tool
    # evidence the grader cannot evaluate.
    labs: dict[int, LabTemplate] = {}
    for week_number, spec in _M365_NEW_LABS.items():
        lab = LabTemplate(
            title=spec["title"],
            description=spec["description"],
            lab_type=spec["lab_type"],
            week_number=week_number,
            difficulty=2,
            estimated_minutes=spec["estimated_minutes"],
            is_published=True,
            environment_requirements={},
            setup_instructions="Read each symptom and evidence block. Choose the action you could defend in a support ticket.",
            success_criteria={"questions": spec["questions"]},
            required_evidence={},
            hints={},
        )
        db.add(lab)
        db.flush()
        labs[week_number] = lab
        result["labs_created"] += 1

    # 8. Move LabTemplate 19 ("Route the Cloud Identity Ticket") out of week
    # 21 into week 26, trimmed to its Entra-relevant questions plus one new
    # group-based-access question (the cloud-responsibility/IaaS question it
    # previously carried stays out of scope for this module).
    # Looked up by its ORIGINAL title, not a hardcoded id: on an existing
    # (production) database this row already exists from history, at
    # whatever id it was originally assigned, and moving it (not recreating
    # it) preserves any LabRun history tied to that id. On a truly fresh
    # install nothing creates "Route the Cloud Identity Ticket" any more
    # (its old WEEKS_19_22_QUALITY spec entry was intentionally removed, see
    # that constant's comment) -- there, no row exists to move, so one is
    # created directly under its final identity instead, same as the other
    # _M365_NEW_LABS.
    moved_lab = db.query(LabTemplate).filter_by(title="Route the Cloud Identity Ticket").first()
    if moved_lab is not None:
        if moved_lab.week_number != 26:
            moved_lab.title = _M365_MOVED_LAB_19_UPDATE["title"]
            moved_lab.week_number = _M365_MOVED_LAB_19_UPDATE["week_number"]
            moved_lab.success_criteria = _M365_MOVED_LAB_19_UPDATE["success_criteria"]
            result["labs_moved"] += 1
        labs[26] = moved_lab
    else:
        moved_lab = db.query(LabTemplate).filter_by(title=_M365_MOVED_LAB_19_UPDATE["title"]).first()
        if moved_lab is None:
            moved_lab = LabTemplate(
                title=_M365_MOVED_LAB_19_UPDATE["title"],
                description="Work through realistic evidence and choose the safest support action before moving to an independent case.",
                lab_type="structured_cloud",
                week_number=_M365_MOVED_LAB_19_UPDATE["week_number"],
                difficulty=2,
                estimated_minutes=20,
                is_published=True,
                environment_requirements={},
                setup_instructions="Read each symptom and evidence block. Choose the action you could defend in a support ticket.",
                success_criteria=_M365_MOVED_LAB_19_UPDATE["success_criteria"],
                required_evidence={},
                hints={},
            )
            db.add(moved_lab)
            db.flush()
            result["labs_created"] += 1
        labs[26] = moved_lab

    # 9. Service Desk scenarios (live, server-graded tickets). Objectives
    # live in app.services.service_desk_objectives.SCENARIO_OBJECTIVES,
    # keyed by these same stable_key values.
    scenarios: dict[str, ServiceDeskScenario] = {}
    for ticket in _M365_SERVICE_DESK_TICKETS:
        stable_key = ticket["stableKey"]
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=stable_key).first()
        if scenario is None:
            scenario = ServiceDeskScenario(
                stable_key=stable_key,
                title=ticket["title"],
                description=f'{ticket["description"]["issue"]} {ticket["description"]["businessImpact"]}',
                category=ticket["category"],
                difficulty=2,
                status="active",
            )
            db.add(scenario)
            db.flush()
            result["tickets_created"] += 1
        scenarios[stable_key] = scenario
        definition_hash = hashlib.sha256(json.dumps(ticket, sort_keys=True).encode("utf-8")).hexdigest()
        version_exists = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id, definition_hash=definition_hash)
            .first()
        )
        if version_exists is None:
            next_version = (
                db.query(ServiceDeskScenarioVersion.version_number)
                .filter_by(scenario_id=scenario.id)
                .order_by(ServiceDeskScenarioVersion.version_number.desc())
                .first()
            )
            db.add(
                ServiceDeskScenarioVersion(
                    scenario_id=scenario.id,
                    version_number=(next_version[0] if next_version else 0) + 1,
                    definition_json=ticket,
                    definition_hash=definition_hash,
                    validation_status="valid",
                    status="published",
                    published_at=datetime.now(timezone.utc),
                    published_by="seed",
                )
            )
    db.flush()

    # 10. One integrated Prove-level capstone at the end of the stage. Role-gated
    # like every other seeded capstone (seed.py's seed_capstones) -- an
    # ungated role_level would surface "Capstones" in nav for every student,
    # including a brand-new Trainee, regardless of curriculum position.
    capstone = db.query(CapstoneTemplate).filter_by(title=_M365_CAPSTONE["title"]).first()
    if capstone is None:
        capstone_role = db.query(Role).filter_by(name="Junior Systems Technician").first()
        capstone = CapstoneTemplate(
            title=_M365_CAPSTONE["title"],
            description=_M365_CAPSTONE["description"],
            week_number=_M365_CAPSTONE["week_number"],
            is_published=True,
            requirements=_M365_CAPSTONE["requirements"],
            deliverables=_M365_CAPSTONE["deliverables"],
            estimated_hours=_M365_CAPSTONE["estimated_hours"],
            rubric=_M365_CAPSTONE["rubric"],
            role_level=capstone_role.id if capstone_role is not None else None,
        )
        db.add(capstone)
        db.flush()
        result["capstones_created"] += 1

    # 11. Wire everything into TrainingWeekActivity. Evidence-interpretation
    # labs and the tickets are all troubleshooting work by design (Step 9/10
    # of the Phase 4B.1 brief), so their learning_role is explicitly
    # overridden to "troubleshoot" rather than the guided_lab default of
    # "practice" -- these are diagnostic exercises, not build/practice labs.
    def add_activity(week_number, activity_type, content_ref, is_required, minutes=None, metadata=None):
        week = new_weeks.get(week_number) or existing_weeks.get(week_number)
        if week is None:
            return
        order = (
            db.query(func.coalesce(func.max(TrainingWeekActivity.display_order), 0))
            .filter_by(training_week_id=week.id)
            .scalar()
            or 0
        ) + 1
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{week_number}-{activity_type}-{content_ref}",
                activity_type=activity_type,
                content_ref=str(content_ref),
                display_order=order,
                is_required=is_required,
                estimated_minutes=minutes,
                prerequisite_mode="soft",
                metadata_json=metadata or {},
            )
        )
        db.flush()
        result["activities_created"] += 1

    for week_number, lesson in lessons.items():
        add_activity(week_number, "lesson", lesson.id, True, lesson.estimated_minutes)
    for week_number, quiz in quizzes.items():
        add_activity(week_number, "quiz", quiz.id, True, 15)
    for week_number, lab in labs.items():
        add_activity(week_number, "guided_lab", lab.id, True, lab.estimated_minutes, {"learning_role": "troubleshoot"})
    for ticket in _M365_SERVICE_DESK_TICKETS:
        week_number = 26 if ticket["stableKey"] == "m365-entra-auth-method" else 27
        add_activity(week_number, "service_desk_scenario", ticket["stableKey"], True, 30)
    add_activity(29, "capstone", capstone.id, False, (capstone.estimated_hours or 2) * 60)

    # 12. Remove the old week-21 TrainingWeekActivity rows for the moved
    # lesson/lab (they now live at week 26) and compact week 21's remaining
    # display_order.
    if moved_lesson is not None or moved_lab is not None:
        old_week_21 = existing_weeks.get(21) or db.query(TrainingWeek).filter_by(week_number=21).first()
        if old_week_21 is not None:
            stale_ids = []
            if moved_lesson is not None:
                stale_ids.append(f"week-21-lesson-{moved_lesson.id}")
            if moved_lab is not None:
                stale_ids.append(f"week-21-guided_lab-{moved_lab.id}")
            stale_rows = (
                db.query(TrainingWeekActivity)
                .filter(TrainingWeekActivity.training_week_id == old_week_21.id, TrainingWeekActivity.stable_id.in_(stale_ids))
                .all()
            )
            for row in stale_rows:
                db.delete(row)
                result["activities_moved"] += 1
            db.flush()
            remaining = (
                db.query(TrainingWeekActivity)
                .filter_by(training_week_id=old_week_21.id)
                .order_by(TrainingWeekActivity.display_order)
                .all()
            )
            for order, row in enumerate(remaining, start=1):
                row.display_order = order

    # 13. Reconcile System B (progression_service.MODULE_WEEKS is a code-level
    # dict updated separately; here we update the seeded PromotionGate rows
    # for the graduating role so required Microsoft-stage content is not
    # silently skippable). See docs/MICROSOFT_WORKPLACE_CURRICULUM.md.
    final_role = db.query(Role).filter_by(name="Junior Infrastructure Administrator").first()
    if final_role is not None:
        lessons_gate = (
            db.query(PromotionGate)
            .filter_by(role_id=final_role.id, requirement_type="min_completed_lessons")
            .first()
        )
        if lessons_gate is not None:
            codes = list(lessons_gate.requirement_config.get("module_codes", []))
            new_codes = [code for _, (code, _) in _M365_LEGACY_MODULES.items() if code not in codes]
            if new_codes:
                lessons_gate.requirement_config = {"module_codes": codes + new_codes}
                result["gates_updated"] += 1

        if not db.query(PromotionGate).filter_by(role_id=final_role.id, requirement_type="required_quiz", requirement_config={"week": 27}).first():
            db.add(
                PromotionGate(
                    role_id=final_role.id,
                    requirement_type="required_quiz",
                    requirement_config={"week": 27},
                )
            )
            result["gates_updated"] += 1

        if not db.query(PromotionGate).filter_by(role_id=final_role.id, requirement_type="min_service_desk_passes", requirement_config={"pack_key": "microsoft-workplace", "min_passed": 2}).first():
            db.add(
                PromotionGate(
                    role_id=final_role.id,
                    requirement_type="min_service_desk_passes",
                    requirement_config={"pack_key": "microsoft-workplace", "min_passed": 2},
                )
            )
            result["gates_updated"] += 1

    db.commit()
    return result


# Phase 4B.1: Microsoft 365, Entra & Endpoint Management stage (job-ready
# curriculum content build). See docs/MICROSOFT_WORKPLACE_CURRICULUM.md for
# the full research/design record, including exactly why this uses new
# week_number 25-29 (never reusing/renumbering 0-24) and how System A
# (TrainingWeek.display_order) and System B (progression_service.py,
# service_desk_progression.py) both had to be updated so this content is
# neither invisible to graduation nor stuck as a parallel path. Only
# TrainingWeek.display_order moves for the 12 existing rows below; their
# week_number is untouched.
_M365_DISPLAY_ORDER_SHIFT = {
    # week_number -> new display_order (+5, opening 13-17 for the new weeks)
    10: 18, 11: 19, 12: 20,
    16: 21, 17: 22,
    18: 23, 19: 24, 20: 25,
    21: 26, 22: 27,
    23: 28, 24: 29,
}

_M365_NEW_WEEKS = {
    25: {
        "display_order": 13,
        "title": "Microsoft 365 Support Foundations",
        "description": "Relate the M365 tenant, licensing, and admin centers to the accounts and services a technician actually touches.",
        "learning_goals": [
            "Explain how M365 services relate to one Entra identity",
            "Locate which admin center answers a given support question",
            "Distinguish a licensing/permission problem from an application problem",
        ],
    },
    26: {
        "display_order": 14,
        "title": "Entra Users, Groups & Access",
        "description": "Administer Entra users/groups and investigate account-state and sign-in failures with evidence.",
        "learning_goals": [
            "Administer Entra users/groups with the same safety rails as on-prem AD",
            "Investigate sign-in failures via the Entra sign-in log instead of guessing",
            "Handle MFA-reset requests with strict identity verification",
        ],
    },
    27: {
        "display_order": 15,
        "title": "Sign-In & MFA Troubleshooting",
        "description": "Read sign-in and Conditional Access evidence, and handle MFA support safely under account-takeover risk.",
        "learning_goals": [
            "Distinguish a Conditional Access block from an authentication-method failure using sign-in log evidence",
            "Explain current authentication-method guidance and the SSPR registration requirement",
            "Follow a diagnostic order that avoids guessing at MFA fixes",
        ],
    },
    28: {
        "display_order": 16,
        "title": "Exchange Online & Outlook Support",
        "description": "Diagnose mailbox permission and Outlook client problems technicians see every day.",
        "learning_goals": [
            "Distinguish Full Access, Send As, and Send on Behalf and pick the correct one for a request",
            "Separate an Outlook client problem from a mailbox/server problem",
            "Grant only the specific permission a request and its authorization justify",
        ],
    },
    29: {
        "display_order": 17,
        "title": "Teams, OneDrive & SharePoint Support",
        "description": "Troubleshoot the collaboration tools that generate the highest-volume M365 tickets.",
        "learning_goals": [
            "Separate a Teams client issue from an OS device-permission issue",
            "Diagnose common OneDrive sync failures including Known Folder Move confusion",
            "Recognize when a SharePoint 'sync' failure is really a lost permission",
        ],
    },
}

_M365_LEGACY_MODULES = {
    25: ("MOD-025", "Microsoft 365 Support Foundations"),
    26: ("MOD-026", "Entra Users, Groups & Access"),
    27: ("MOD-027", "Sign-In & MFA Troubleshooting"),
    28: ("MOD-028", "Exchange Online & Outlook Support"),
    29: ("MOD-029", "Teams, OneDrive & SharePoint Support"),
}

_M365_QUIZZES = {
    25: {
        "title": "Microsoft 365 Support Foundations Check",
        "questions": [
            {
                "question_text": "A user reports that a Microsoft 365 app is greyed out and won't open. What should you check first?",
                "option_a": "Reinstall the Microsoft 365 apps",
                "option_b": "Whether a license is assigned to the user",
                "option_c": "Restart their computer",
                "option_d": "Reset their password",
                "correct_answer": "B",
                "explanation": "A greyed-out or missing app is very often a licensing gap, checkable on the account, not a broken install.",
            },
            {
                "question_text": "Which admin surface would you use to review a user's Conditional Access policy?",
                "option_a": "Microsoft 365 admin center",
                "option_b": "Exchange admin center",
                "option_c": "Entra admin center",
                "option_d": "SharePoint admin center",
                "correct_answer": "C",
                "explanation": "Conditional Access, MFA, and sign-in logs live in the Entra admin center, separate from the M365 admin center's user/license work.",
            },
            {
                "question_text": "A user can't find a file a colleague shared with them. What is the more likely first cause?",
                "option_a": "Group or permission membership",
                "option_b": "A tenant-wide outage",
                "option_c": "A licensing outage",
                "option_d": "The file was deleted",
                "correct_answer": "A",
                "explanation": "Sharing/permission scope, usually group-based, is the far more common cause than an outage or deletion.",
            },
            {
                "question_text": "A technician reinstalls Teams before checking whether the user's account or license is correct. What is the risk of this order?",
                "option_a": "None -- reinstalling is always a safe first step",
                "option_b": "It wastes time solving a client problem that isn't the actual cause",
                "option_c": "It will delete the user's mailbox",
                "option_d": "It automatically escalates the ticket",
                "correct_answer": "B",
                "explanation": "Checking account/license/permission first avoids fixing the wrong layer.",
            },
        ],
    },
    26: {
        "title": "Entra Users, Groups & Access Check",
        "questions": [
            {
                "question_text": "A user's account shows 'Block sign-in' enabled in Entra. What should you do first?",
                "option_a": "Re-enable sign-in immediately since the user is asking",
                "option_b": "Find out why sign-in was blocked before re-enabling",
                "option_c": "Delete and recreate the account",
                "option_d": "Ignore it -- Block sign-in is cosmetic",
                "correct_answer": "B",
                "explanation": "Same rule as an on-prem disabled account: find out why before undoing it.",
            },
            {
                "question_text": "A lockout ticket comes in with no other detail. Where should you start investigating?",
                "option_a": "The Entra sign-in log for that user",
                "option_b": "The user's personal email",
                "option_c": "A guess based on the ticket title",
                "option_d": "The company's public website status page",
                "correct_answer": "A",
                "explanation": "The sign-in log shows success/failure, the reason, and where the attempt came from -- start there, not with guessing.",
            },
            {
                "question_text": "A user's password works on their laptop but sign-in to Microsoft 365 fails, and the organization syncs on-prem AD to Entra. What should you suspect?",
                "option_a": "A hybrid identity / Entra Connect sync issue",
                "option_b": "A broken keyboard",
                "option_c": "An expired Microsoft 365 license only",
                "option_d": "A SharePoint permission problem",
                "correct_answer": "A",
                "explanation": "A password that works locally but not in the cloud often means the change happened in the wrong place, or sync is unhealthy.",
            },
            {
                "question_text": "Which is the correct order of operations for an MFA-reset request?",
                "option_a": "Reset MFA immediately, then verify identity afterward",
                "option_b": "Verify identity through the approved process, then reset MFA",
                "option_c": "Ask a coworker to confirm the request",
                "option_d": "Reset MFA only if the user sounds confident",
                "correct_answer": "B",
                "explanation": "An MFA reset changes the account's trust boundary; identity verification always comes first.",
            },
        ],
    },
    27: {
        "title": "Sign-In & MFA Troubleshooting Check",
        "quiz_purpose": "gate",
        "questions": [
            {
                "question_text": "A user's password is correct, but Entra sign-in logs show a Conditional Access failure. What should you investigate next?",
                "option_a": "The specific Conditional Access policy that blocked the attempt, and why",
                "option_b": "Whether the password is really correct",
                "option_c": "Nothing -- reset MFA immediately",
                "option_d": "The user's internet speed",
                "correct_answer": "A",
                "explanation": "A Conditional Access block is a policy/device conversation, not a password conversation -- the Authentication Details tab shows the exact policy and reason.",
            },
            {
                "question_text": "A user says their Authenticator app stopped working after they got a new phone. What is happening in 2026 terms?",
                "option_a": "Their previously registered authentication method needs to be re-registered on the new device",
                "option_b": "Their license expired",
                "option_c": "SharePoint permissions changed",
                "option_d": "The tenant is down",
                "correct_answer": "A",
                "explanation": "This is the standard 'lost/replaced device' MFA scenario -- the fix is re-registration under verified identity, not a mailbox or license fix.",
            },
            {
                "question_text": "A user asks why Self-Service Password Reset (SSPR) won't work for them. What is a likely, current (2026) cause?",
                "option_a": "SSPR requires a registered authentication method, and none is registered",
                "option_b": "SSPR was permanently discontinued",
                "option_c": "Their mailbox is full",
                "option_d": "Their device is out of storage",
                "correct_answer": "A",
                "explanation": "SSPR now requires an explicitly registered recovery method; unregistered users can't self-serve until they register one.",
            },
            {
                "question_text": "What is the correct diagnostic order for a 'can't sign in' ticket?",
                "option_a": "Reset MFA, then check the password, then check policy",
                "option_b": "Check whether the password step alone succeeds, then the authentication method used, then Conditional Access",
                "option_c": "Escalate immediately without investigating",
                "option_d": "Ask the user to guess what's wrong",
                "correct_answer": "B",
                "explanation": "Isolating password, then method, then policy prevents guessing and identifies the actual failing layer.",
            },
        ],
    },
    28: {
        "title": "Exchange Online & Outlook Support Check",
        "questions": [
            {
                "question_text": "A user can open a shared mailbox but gets a permission error when trying to send AS that mailbox. Which permission should you investigate?",
                "option_a": "Full Access",
                "option_b": "Send As",
                "option_c": "Calendar permissions",
                "option_d": "Mailbox storage quota",
                "correct_answer": "B",
                "explanation": "Full Access alone lets someone open a mailbox but cannot send as it -- that requires Send As (or Send on Behalf, which appears differently to recipients).",
            },
            {
                "question_text": "Outlook on the desktop repeatedly prompts to sign in, but Outlook on the web works fine for the same account. What does this tell you?",
                "option_a": "The mailbox itself is broken",
                "option_b": "The problem is local to the desktop Outlook profile/cache",
                "option_c": "The account is locked",
                "option_d": "The license was removed",
                "correct_answer": "B",
                "explanation": "If the web client works, the server-side mailbox is healthy -- the fault is local to that client's cached profile.",
            },
            {
                "question_text": "A request asks only for a user to be able to read a shared mailbox's messages. What should you grant?",
                "option_a": "Full Access only",
                "option_b": "Full Access plus Send As, to be safe",
                "option_c": "Global Administrator",
                "option_d": "Send As only",
                "correct_answer": "A",
                "explanation": "Grant exactly what the request and its authorization justify -- Full Access covers reading; adding Send As beyond what was requested is over-granting.",
            },
            {
                "question_text": "What is the practical difference between Send As and Send on Behalf?",
                "option_a": "There is no difference",
                "option_b": "Send As shows mail as coming from the shared mailbox; Send on Behalf shows the delegate's name alongside it",
                "option_c": "Send on Behalf is more restrictive and blocks sending entirely",
                "option_d": "Send As only works for distribution groups",
                "correct_answer": "B",
                "explanation": "Recipients see a different From line depending on which permission was used -- a real, visible distinction, not just an admin technicality.",
            },
        ],
    },
    29: {
        "title": "Teams, OneDrive & SharePoint Support Check",
        "questions": [
            {
                "question_text": "A user says, 'my files stopped syncing.' What should you check before touching the OneDrive client?",
                "option_a": "Whether the requester still has permission on the affected library, and which account OneDrive is signed into",
                "option_b": "The building's WiFi router",
                "option_c": "The user's printer",
                "option_d": "The user's mailbox size",
                "correct_answer": "A",
                "explanation": "Lost permission and wrong-account sign-in are the most common causes -- rule those out before resetting the client.",
            },
            {
                "question_text": "A user says all their Desktop files disappeared after a Windows update. What should you investigate first?",
                "option_a": "Assume data loss and restore from backup immediately",
                "option_b": "Whether Known Folder Move redirected Desktop/Documents/Pictures into OneDrive",
                "option_c": "Reformat the drive",
                "option_d": "Reset the user's password",
                "correct_answer": "B",
                "explanation": "Known Folder Move commonly explains 'disappeared' files that are actually just relocated into OneDrive.",
            },
            {
                "question_text": "Synced files from a SharePoint library show a padlock icon in File Explorer. What does that most likely mean?",
                "option_a": "The files are corrupted",
                "option_b": "The user has read-only access, or the library requires checkout",
                "option_c": "OneDrive is out of storage",
                "option_d": "The tenant is offline",
                "correct_answer": "B",
                "explanation": "A padlock indicates a permission or checkout restriction, not file corruption.",
            },
            {
                "question_text": "A user's camera doesn't work in Teams meetings, but works fine in other apps. What should you check?",
                "option_a": "The Teams license",
                "option_b": "OS-level camera privacy/permission settings for Teams specifically",
                "option_c": "The user's SharePoint permissions",
                "option_d": "The Exchange mailbox size",
                "correct_answer": "B",
                "explanation": "A camera that works elsewhere but not in Teams usually means Teams is blocked at the OS privacy-permission level, not a hardware fault.",
            },
        ],
    },
}


_M365_LESSONS = {
    25: {
        "title": "Microsoft 365 Support Foundations",
        "summary": (
            "Microsoft 365 is a bundle of cloud services (Exchange Online, Teams, OneDrive, SharePoint, and more) tied "
            "together by ONE identity: the user's Entra account. Understand this and most 'random' M365 tickets stop "
            "being random.\n\n"
            "THE TENANT: your organization has one Microsoft 365 tenant. Every user, license, and mailbox lives inside "
            "it. A user 'not having access' to something is almost always a LICENSE or GROUP question, not a broken app.\n\n"
            "LICENSING, AT TECHNICIAN DEPTH: users are assigned license SKUs that light up which services they can use. "
            "You don't need to memorize SKU names -- you need to know that 'the app is greyed out / missing' is often "
            "'no license assigned,' checkable from the user's account, not from reinstalling anything.\n\n"
            "ADMIN CENTERS: the Microsoft 365 admin center is where user/license work happens; there is a SEPARATE "
            "Entra admin center for identity/security (Conditional Access, MFA, sign-in logs), and separate admin "
            "surfaces for Exchange, Teams, and SharePoint. Knowing WHICH center answers WHICH question is itself a "
            "skill.\n\n"
            "WHY A TECH NEEDS THIS: 'I can't open the file,' 'Teams won't load,' and 'my email didn't come through' "
            "all trace back to the same small set of questions: is the account healthy, is the right license assigned, "
            "and does the user have permission on the specific resource.\n\n"
            "COMMON MISTAKE: troubleshooting an app in isolation (reinstalling Teams, clearing Outlook cache) before "
            "checking whether the account/license/permission layer underneath is even correct."
        ),
        "outcomes": [
            "Explain how M365 services relate to one Entra identity",
            "Locate which admin center answers a given support question",
            "Distinguish a licensing/permission problem from an application problem",
        ],
    },
    27: {
        "title": "Reading Sign-In Evidence & Conditional Access",
        "summary": (
            "Most 'I can't sign in even though my password is right' tickets are not password problems -- they're "
            "SECOND-FACTOR or POLICY problems. This goes one layer deeper than the account administration you learned "
            "in the Entra module: how to read WHY a sign-in was blocked, not just THAT it was blocked.\n\n"
            "CONDITIONAL ACCESS, IN ONE SENTENCE: a rule engine that adds conditions on top of a correct password -- "
            "e.g. 'block sign-in from an unmanaged device,' 'require MFA from outside the corporate network,' 'block "
            "a sign-in flagged as risky.' A user can be 100% correct on their password and still be blocked -- that's "
            "not a bug, it's policy working.\n\n"
            "THE SIGN-IN LOG'S AUTHENTICATION DETAILS TAB shows the exact policy that fired and why. Read it BEFORE "
            "guessing. 'Blocked by Conditional Access policy X' is a completely different ticket than 'invalid "
            "credentials' -- the first is a policy/device conversation, the second is a password conversation.\n\n"
            "AUTHENTICATION METHODS TODAY: Microsoft Authenticator (push or passkey) is the default method Entra "
            "pushes users toward -- passkeys became the default MFA prompt in September 2026, and SMS/voice is being "
            "phased out as a Microsoft-hosted delivery option. A 'broken MFA' ticket today is usually a lost/replaced "
            "device with a registered Authenticator/passkey, not a lost phone number. Self-Service Password Reset "
            "(SSPR) now requires the user to have already registered a recovery method -- 'SSPR isn't working' is "
            "often 'nothing is registered,' which the technician fixes going forward, not by bypassing verification "
            "now.\n\n"
            "DIAGNOSTIC ORDER: (1) does the password step alone succeed? (2) which authentication method did they "
            "attempt, and is it the one actually registered? (3) did Conditional Access block the attempt, and why? "
            "Answer in that order and you stop guessing.\n\n"
            "COMMON MISTAKE: resetting or re-registering MFA before confirming which layer failed -- a Conditional "
            "Access block looks identical to a broken authenticator from the user's seat, but the fix is completely "
            "different, and a bypass in the wrong case creates real risk."
        ),
        "outcomes": [
            "Distinguish a Conditional Access block from an authentication-method failure using sign-in log evidence",
            "Explain current authentication-method guidance and the SSPR registration requirement",
            "Follow a diagnostic order that avoids guessing at MFA fixes",
        ],
    },
    28: {
        "title": "Exchange Mailbox Permissions & Outlook Support",
        "summary": (
            "Two completely different kinds of ticket live here: 'I can't access this mailbox the way I expect' (a "
            "PERMISSIONS question) and 'Outlook is broken on my machine' (a CLIENT question). Mixing them up wastes "
            "time.\n\n"
            "SHARED MAILBOX PERMISSIONS -- the most common confusion:\n"
            "- FULL ACCESS lets someone OPEN and read a mailbox's content. It does NOT let them send mail as that "
            "mailbox.\n"
            "- SEND AS makes outgoing mail look like it came FROM the shared mailbox itself.\n"
            "- SEND ON BEHALF makes outgoing mail show '[User] on behalf of [Mailbox]' -- a visible difference "
            "recipients will notice.\n"
            "'I can open it but can't send as it' is almost always Full Access granted, Send As missing -- not a "
            "broken mailbox.\n\n"
            "DISTRIBUTION GROUPS VS. M365 GROUPS (awareness): a distribution group is mail-routing only. An M365 "
            "Group also provisions a shared mailbox, calendar, and Teams/SharePoint presence. 'Add me to the DL' and "
            "'add me to the Team' can both look like a groups request but resolve very differently.\n\n"
            "OUTLOOK CLIENT PROBLEMS: repeated sign-in prompts, a stuck 'Trying to connect,' or mail not updating are "
            "usually a broken/expired cached profile, not a server-side mail problem. Fast diagnostic: does Outlook "
            "on the web work for the same account? If web works and the desktop client doesn't, the problem is local "
            "to that Outlook profile/cache.\n\n"
            "MAIL FLOW (awareness only): Autodiscover is what points the client at the right mailbox; 'Outlook can't "
            "find my mailbox' right after a new setup is often an Autodiscover propagation delay, not a broken "
            "account.\n\n"
            "COMMON MISTAKE: granting broader mailbox permission than the ticket actually asked for because it's the "
            "'easy' fix -- Full Access is not a substitute for reading what the requester actually needs to do."
        ),
        "outcomes": [
            "Distinguish Full Access, Send As, and Send on Behalf and pick the correct one for a request",
            "Separate an Outlook client problem from a mailbox/server problem",
            "Grant only the specific permission a request and its authorization justify",
        ],
    },
    29: {
        "title": "Teams, OneDrive & SharePoint Support",
        "summary": (
            "These three tools share one identity (the same Entra account) and, for Teams/SharePoint-backed files, "
            "the same underlying storage -- which is exactly why their problems get confused.\n\n"
            "TEAMS: most 'Teams is broken' tickets are sign-in, cache, or device-permission issues (camera/mic "
            "blocked at the OS level, not inside Teams), not real outages. A clean sign-out/sign-in and cache clear "
            "resolves a large share of client complaints. Teams identity comes straight from Entra -- a Teams "
            "sign-in problem is usually an account-state problem you already know how to read.\n\n"
            "ONEDRIVE: 'my files stopped syncing' has a short list of real causes: signed into the WRONG account "
            "(very common on a personal + work device), a sync CONFLICT/error the client is flagging, or a "
            "storage/path problem (unsupported characters, a path that's too long). 'All my Desktop files "
            "disappeared' is frequently KNOWN FOLDER MOVE -- OneDrive redirected the Desktop/Documents/Pictures "
            "folders into itself -- not deleted files; look there before escalating as data loss.\n\n"
            "SHAREPOINT: files 'not syncing' from a Teams channel or SharePoint library is very often a PERMISSIONS "
            "change, not a sync-engine failure -- confirm the user still has access to the site/library/channel "
            "before touching the sync client. A padlock icon on synced files means read-only sync (no edit "
            "permission, or a library requiring checkout), not corruption.\n\n"
            "THE THROUGH-LINE: for all three, check identity and permission FIRST. The client-side fix (restart, "
            "re-sign-in, reset sync) is usually the second step, not the first.\n\n"
            "COMMON MISTAKE: resetting/reinstalling the sync client before confirming the user still has permission "
            "on the underlying site or library -- that just reproduces the same failure."
        ),
        "outcomes": [
            "Separate a Teams client issue from an OS device-permission issue",
            "Diagnose common OneDrive sync failures including Known Folder Move confusion",
            "Recognize when a SharePoint 'sync' failure is really a lost permission",
        ],
    },
}


# Phase 4B.2: Intune & Windows 11 Endpoint Management (job-ready curriculum
# content build). See docs/INTUNE_ENDPOINT_MANAGEMENT_CURRICULUM.md for the
# full research/design record and docs/JOB_READY_CURRICULUM_BLUEPRINT.md
# section 9 for the original module plan this fulfills. Uses new
# week_number 30-34 (never reusing/renumbering 0-29) inside the existing
# stage.microsoft_workplace Stage -- its description text already earmarked
# this. Only TrainingWeek.display_order moves for the 12 existing rows
# below; their week_number is untouched. Sources verified 2026-08-23; see
# the doc for per-topic freshness notes (Windows 10 EOL, Autopilot Device
# Preparation, and the platform-specific Company Portal / Intune app split).

_INTUNE_DISPLAY_ORDER_SHIFT = {
    # week_number -> new display_order (+5, opening 18-22 for the new weeks)
    10: 23, 11: 24, 12: 25,
    16: 26, 17: 27,
    18: 28, 19: 29, 20: 30,
    21: 31, 22: 32,
    23: 33, 24: 34,
}

_INTUNE_NEW_WEEKS = {
    30: {
        "display_order": 18,
        "title": "Intune & Managed Endpoint Foundations",
        "description": "Read a device record and determine its identity, management, and compliance state before touching anything.",
        "learning_goals": [
            "Explain what Intune/MDM management means for a Windows device",
            "Distinguish Entra registered, joined, and hybrid joined",
            "Read a device record to determine join type, management state, and likely ownership",
        ],
    },
    31: {
        "display_order": 19,
        "title": "Windows Enrollment & Autopilot",
        "description": "Diagnose how a Windows 11 device reaches Intune management and why enrollment sometimes fails.",
        "learning_goals": [
            "Explain automatic MDM enrollment and BYOD/Company Portal enrollment",
            "Compare Windows Autopilot and Autopilot Device Preparation",
            "Diagnose a device that is Entra joined but not Intune managed",
        ],
    },
    32: {
        "display_order": 20,
        "title": "Policies, Compliance & Applications",
        "description": "Trace why a setting, app, or access decision did or did not reach a managed device.",
        "learning_goals": [
            "Distinguish configuration policy from compliance policy",
            "Trace the device state -> compliance -> Conditional Access -> access chain",
            "Diagnose a failed application install using detection-rule evidence",
        ],
    },
    33: {
        "display_order": 21,
        "title": "Windows 11 Endpoint Troubleshooting & BitLocker",
        "description": "Support update, driver, and BitLocker recovery problems, and weigh device-action risk before acting.",
        "learning_goals": [
            "Triage common Windows Update and driver/firmware problems",
            "Handle a BitLocker recovery request safely, with identity verification first",
            "Choose the correctly-scoped device action for a given risk level",
        ],
    },
    34: {
        "display_order": 22,
        "title": "Device Lifecycle, Onboarding, Offboarding & Mobile",
        "description": "Run a device through its full lifecycle safely, including the highest-risk offboarding handoffs.",
        "learning_goals": [
            "Complete the device/M365 side of a new-hire onboarding",
            "Offboard a device safely without leaving open access or losing data-handling steps",
            "Recognize basic mobile MDM concepts and the safe retire-vs-wipe decision",
        ],
    },
}

_INTUNE_LEGACY_MODULES = {
    30: ("MOD-030", "Intune & Managed Endpoint Foundations"),
    31: ("MOD-031", "Windows Enrollment & Autopilot"),
    32: ("MOD-032", "Policies, Compliance & Applications"),
    33: ("MOD-033", "Windows 11 Endpoint Troubleshooting & BitLocker"),
    34: ("MOD-034", "Device Lifecycle, Onboarding, Offboarding & Mobile"),
}

# Each week now carries more than one lesson (unlike the single-lesson-per-week
# _M365_LESSONS shape), so this is keyed by week_number -> an ordered list of
# lesson specs.
_INTUNE_LESSONS: dict[int, list[dict]] = {
    30: [
        {
            "title": "What Intune Actually Does",
            "summary": (
                "Intune is Microsoft's cloud service for managing Windows, iOS/iPadOS, and Android devices -- it is "
                "how an organization pushes settings, deploys apps, and checks whether a device meets its security "
                "requirements, all without an admin physically touching the machine. This lesson is the foundation "
                "for every other lesson in this module: what 'managed' means, and how to read a device record.\n\n"
                "MANAGED VS UNMANAGED: a 'managed' device has enrolled in Intune and is receiving policy from it. An "
                "unmanaged device (a personal phone with no MDM profile, a brand-new laptop before enrollment) gets "
                "none of that -- no pushed settings, no compliance evaluation, no ability for IT to act on it "
                "remotely. Most 'why isn't this policy applying' tickets start with confirming the device is even "
                "managed in the first place.\n\n"
                "THE DEVICE RECORD: every managed device has a record in Intune with fields a technician reads "
                "constantly: owner (corporate vs personal), primary user, join type, enrollment date, OS version, "
                "management state, compliance state, and last check-in time. Reading this record correctly, before "
                "guessing, is the single most useful skill in this whole module.\n\n"
                "LAST CHECK-IN MATTERS: a device only reports its current state when it checks in (roughly every "
                "few hours by default, or immediately after a manual Sync). A device that hasn't checked in for "
                "days might be off, asleep, offline, or genuinely broken -- 'last check-in: 6 days ago' is itself "
                "important evidence, not just a timestamp to skim past.\n\n"
                "WINDOWS 11 IS THE BASELINE: general servicing for Windows 10 reached end of support on October 14, "
                "2025. Extended Security Updates and separately serviced LTSC releases are explicit exceptions, not "
                "a reason to present Windows 10 as the current endpoint baseline. Microsoft still allows a Windows "
                "10 device to enroll in Intune, but explicitly "
                "does not guarantee full functionality on an unsupported OS. Treat a Windows 10 device you encounter "
                "as a legacy/at-risk device worth flagging, not the normal endpoint you're troubleshooting toward. "
                "Windows 11 is the expected device throughout the rest of this module.\n\n"
                "COMMON MISTAKE: assuming a device is managed just because it's a company laptop. Ownership and "
                "management are different facts -- always confirmed from the record, never assumed from context."
            ),
            "outcomes": [
                "Explain what 'managed' means and why an unmanaged device receives no policy",
                "Identify the core device-record fields technicians read: owner, join type, enrollment, compliance, last check-in",
                "State why Windows 11 is the baseline device and Windows 10 is legacy/at-risk",
            ],
        },
        {
            "title": "Entra Device Identity: Registered, Joined, Hybrid Joined",
            "summary": (
                "Before a device can be managed, it has an identity relationship with Entra ID -- and that "
                "relationship is one of three kinds. Getting this right predicts whether a device even CAN receive "
                "management or Conditional-Access-gated resources, before you look at anything else.\n\n"
                "ENTRA REGISTERED: the weakest relationship. A personal device (phone, home PC) that added a work or "
                "school account -- think 'added a work account on a personal device.' It does not make the "
                "organization account the Windows sign-in. This is the normal BYOD identity shape, but registration "
                "alone does NOT tell you whether Intune MDM enrollment exists: depending on tenant policy and the "
                "enrollment flow, a registered personal device can be unmanaged, app-protected only, or enrolled in "
                "Intune. Read the management state separately.\n\n"
                "ENTRA JOINED: the normal corporate-owned Windows 11 device. The organization's account is the "
                "primary sign-in at the Windows lock screen itself, the device gets a full trust token (a PRT) at "
                "sign-in, and it's the standard path into full Intune management and Autopilot. When this course "
                "says 'a managed corporate laptop,' this is almost always what it means.\n\n"
                "ENTRA HYBRID JOINED: joined to an on-premises Active Directory domain AND registered in Entra at "
                "the same time. This exists in organizations still running on-prem AD alongside the cloud -- the "
                "device gets GPO from on-prem AND cloud policy from Intune. The classic failure mode: a hybrid-"
                "joined device needs periodic line-of-sight to a domain controller to keep its Entra registration "
                "healthy, and when that sync breaks, the device can look 'stuck,' with cloud policy simply not "
                "arriving even though the device seems fine locally.\n\n"
                "WHY THIS MATTERS FIRST: before troubleshooting 'why didn't this policy apply' or 'why can't this "
                "user reach that resource,' the very first fact to establish is which of these three the device is "
                "in -- it changes what's even possible, not just what's likely.\n\n"
                "OUT OF SCOPE: how federation or Entra Connect sync is architected/configured. You need to "
                "recognize a hybrid-join sync problem from symptoms, not configure the sync engine yourself."
            ),
            "outcomes": [
                "Define Entra registered, joined, and hybrid joined at a support level",
                "Explain why hybrid-joined devices can have delayed or stuck cloud policy",
                "Identify which relationship a device likely has from support-visible evidence",
            ],
        },
    ],
    31: [
        {
            "title": "How a Windows 11 Device Gets Into Intune",
            "summary": (
                "A device doesn't become 'managed' by accident -- it enrolls through one of a few known paths, and "
                "knowing which path a device took explains a lot about what's wrong when it isn't managed yet.\n\n"
                "AUTOMATIC MDM ENROLLMENT: the most common ad-hoc path. A user Entra-joins a Windows 11 device (at "
                "setup, or later through Settings > Accounts > Access work or school) and the device automatically "
                "enrolls into Intune on that same sign-in, as long as auto-enrollment is configured for the tenant. "
                "This is the path for a device that wasn't pre-staged through Autopilot -- most commonly an "
                "already-purchased or reassigned machine.\n\n"
                "BYOD / USER ENROLLMENT: a personal Windows device can add a work account through Settings or use "
                "Company Portal, depending on the organization's enrollment design. Company Portal remains current "
                "on Windows, iOS/iPadOS, macOS, and Android; some Android scenarios use the separate Microsoft Intune "
                "app. A BYOD device is commonly Entra REGISTERED, but its management state must still be checked: it "
                "might be unmanaged, protected only at the app layer, or enrolled in Intune MDM. Personal ownership "
                "does not by itself mean 'app-only.'\n\n"
                "GROUP POLICY / CO-MANAGEMENT (RECOGNIZE ONLY): older organizations sometimes still enroll via "
                "Group Policy, or run co-management with an on-prem tool like Configuration Manager alongside "
                "Intune. You should recognize this exists as a bridge/legacy pattern -- you are not expected to "
                "configure it.\n\n"
                "WINDOWS AUTOPILOT AND AUTOPILOT DEVICE PREPARATION are the ZERO-TOUCH paths -- pre-staged before "
                "the device ever reaches the user, covered in full in the next lesson.\n\n"
                "READING WHICH PATH A DEVICE TOOK: the device record's enrollment type field, combined with join "
                "type (registered commonly indicates a BYOD/user-enrollment path; joined/hybrid joined commonly "
                "indicates automatic enrollment or Autopilot), helps narrow which path a device came through. Confirm "
                "the enrollment type rather than inferring management from join type alone.\n\n"
                "COMMON MISTAKE: assuming every unmanaged device needs to be re-imaged. Most of the time it needs "
                "the right enrollment path completed, not a rebuild."
            ),
            "outcomes": [
                "Describe automatic MDM enrollment and BYOD/Company Portal enrollment",
                "Recognize Group Policy/co-management enrollment as a legacy bridge pattern",
                "Determine which enrollment path a device likely took from its record",
            ],
        },
        {
            "title": "Windows Autopilot vs Autopilot Device Preparation",
            "summary": (
                "Microsoft currently runs TWO zero-touch Windows provisioning systems side by side, and as of 2026 "
                "you'll see both in the wild -- teaching only one would leave you unable to support the other.\n\n"
                "WINDOWS AUTOPILOT (the classic system): hardware is pre-registered by the vendor or IT (its "
                "hardware hash is uploaded ahead of time), then shipped straight to the user. On first boot, the "
                "Autopilot profile takes over the out-of-box setup experience (OOBE), the device Entra-joins (or "
                "hybrid-joins -- Autopilot supports both), auto-enrolls into Intune, and pulls its assigned apps and "
                "policies. Supports several deployment modes (User-Driven being the common one you'll see).\n\n"
                "AUTOPILOT DEVICE PREPARATION (the newer system, Windows-11-focused, actively updated through "
                "2026): does NOT require pre-registering the hardware hash ahead of time -- a real reduction in "
                "deployment friction. Entra-JOINED only (no hybrid-join support in its current form), faster "
                "provisioning, and near-real-time deployment status instead of the standard delay. Its first "
                "release supports fewer deployment modes than classic Autopilot.\n\n"
                "WHERE THEY OVERLAP: both get a device from unboxed to fully Entra-joined, Intune-enrolled, and "
                "policy/app-configured with no IT hands-on-keyboard. Both produce a device you'd read the same way "
                "afterward.\n\n"
                "WHERE THEY DIFFER (what actually matters to you): if a device needs hybrid join, it must use "
                "classic Autopilot -- Device Preparation can't do that yet. If both a classic Autopilot profile and "
                "Device Preparation could apply to the same device, the Autopilot profile takes priority.\n\n"
                "WHAT YOU DO NOT NEED: you are not provisioning hardware hashes or designing deployment profiles "
                "yourself -- that's deployment-engineer work. You need to recognize which system a stuck/failed "
                "device went through and read its deployment status evidence, covered next.\n\n"
                "COMMON MISTAKE: assuming a deployment failure means 'imaging is broken' and reaching for an old-"
                "style reimage. Both systems fail in specific, diagnosable ways from their own status/evidence -- "
                "that's the skill, not starting over."
            ),
            "outcomes": [
                "Compare Windows Autopilot and Autopilot Device Preparation on join type, pre-registration, and status",
                "Explain when hybrid join forces classic Autopilot over Device Preparation",
                "Avoid defaulting to a full reimage when a specific deployment-status diagnosis is available",
            ],
        },
    ],
    32: [
        {
            "title": "Configuration Profiles & the Settings Catalog",
            "summary": (
                "A configuration profile is how Intune PUSHES a setting to a device -- Wi-Fi configuration, a "
                "desktop restriction, a certificate, anything the organization wants set consistently. This lesson "
                "is entirely about reading whether that push actually worked.\n\n"
                "SETTINGS CATALOG: the current, unified way to build a configuration profile -- pick individual "
                "settings from a searchable catalog rather than a fixed template. You are not expected to build "
                "these; you need to read what one is reporting.\n\n"
                "TARGETING: a profile is assigned to a group of USERS or a group of DEVICES. This matters "
                "diagnostically -- a user-targeted profile follows the person across devices; a device-targeted "
                "profile applies no matter who signs in. 'It works on my other computer' or 'it doesn't apply for "
                "this one user' are both targeting clues.\n\n"
                "THE FIVE PROFILE STATUS STATES, which you must be able to read on sight:\n"
                "  - SUCCEEDED: applied successfully. Working as intended.\n"
                "  - ERROR: the policy failed to apply. Read the error code and setting-level detail.\n"
                "  - PENDING: the device hasn't reported back yet -- it hasn't checked in, or the check-in hasn't "
                "happened since assignment. Often resolves with time or a manual Sync.\n"
                "  - CONFLICT: two policies disagree on the same setting, or something already configured on the "
                "device is blocking it. This needs investigation, not just waiting.\n"
                "  - NOT APPLICABLE: the setting doesn't apply to this device's platform/edition. Not an error -- "
                "expected behavior for a mismatched target.\n\n"
                "POLICY REFRESH: devices don't get new policy instantly -- they check in periodically, or "
                "immediately after a manual Sync action. 'I just assigned this five minutes ago and it's not there '"
                "yet' is very often simply Pending, not a defect.\n\n"
                "COMMON MISTAKE: treating every Pending status as broken and escalating immediately, instead of "
                "confirming the device has actually checked in since the assignment was made."
            ),
            "outcomes": [
                "Explain what a configuration profile does and how the Settings Catalog works at a support level",
                "Distinguish user-targeted from device-targeted profile assignment",
                "Read and correctly interpret Succeeded, Error, Pending, Conflict, and Not applicable profile states",
            ],
        },
        {
            "title": "Compliance Policy vs Configuration Policy, and Conditional Access",
            "summary": (
                "This is the single most important distinction in this whole module, and it's commonly confused: "
                "configuration policy and compliance policy sound similar but do fundamentally different jobs.\n\n"
                "CONFIGURATION POLICY pushes and enforces a setting. It changes something on the device. It "
                "reports Succeeded/Error/Pending/Conflict/Not applicable -- states about whether the PUSH succeeded.\n\n"
                "COMPLIANCE POLICY evaluates and reports whether a device meets a set of rules -- minimum OS "
                "version, BitLocker enabled, not jailbroken/rooted, and similar. It changes NOTHING on the device by "
                "itself. It reports the device as COMPLIANT or NONCOMPLIANT, plus which specific rule failed.\n\n"
                "THE CHAIN THAT MATTERS MOST ON THE JOB:\n"
                "  DEVICE STATE -> INTUNE COMPLIANCE -> CONDITIONAL ACCESS -> RESOURCE ACCESS\n"
                "A device's real state (is BitLocker on? is the OS current?) is evaluated by a compliance policy. "
                "That compliance result is reported to Entra ID. Conditional Access policies can then use "
                "'require compliant device' as a condition for reaching a resource (email, SharePoint, an app). A "
                "noncompliant device isn't 'broken' -- it's correctly being blocked from a resource until whatever "
                "rule failed is fixed.\n\n"
                "WHY THE FIX IS NEVER 'WEAKEN THE POLICY': the temptation on a single blocked user is to loosen "
                "Conditional Access or turn off a compliance rule to make the block go away. That fixes one ticket "
                "by breaking the security guarantee for everyone -- the correct fix is bringing the DEVICE into "
                "compliance (enable BitLocker, update the OS, whatever the specific failed rule says), never "
                "weakening the policy.\n\n"
                "COMPLIANCE EVALUATION TIMING: like configuration profiles, compliance status updates on check-in, "
                "not instantly -- a device that just became compliant may still show noncompliant until its next "
                "evaluation or a manual Sync.\n\n"
                "COMMON MISTAKE: confusing a Pending configuration profile with a Noncompliant device -- read which "
                "one the evidence is actually reporting before deciding what's wrong."
            ),
            "outcomes": [
                "State the distinction between configuration policy (pushes settings) and compliance policy (evaluates rules)",
                "Trace the device state -> compliance -> Conditional Access -> access chain",
                "Explain why weakening a policy to fix one user is the wrong response to a compliance block",
            ],
        },
        {
            "title": "Application Deployment & the Detection-Rule Trap",
            "summary": (
                "Getting an app onto a managed device involves assignment, install, and DETECTION -- and the gap "
                "between 'installed fine' and 'detected as installed' is where most real app tickets live.\n\n"
                "REQUIRED VS AVAILABLE: a Required app installs automatically for its assigned group. An Available "
                "app shows up in Company Portal / the Intune app for the user to install on demand. 'The app isn't "
                "there for the user to install' vs 'the app was supposed to install automatically and didn't' are "
                "different tickets depending on which assignment type is in play.\n\n"
                "APP TYPES AT A GLANCE: Microsoft Store apps (simplest), and Win32 apps (traditional installers "
                "wrapped for Intune, most common for line-of-business software). You do not need packaging depth -- "
                "you need to read install status.\n\n"
                "THE DETECTION-RULE TRAP: after a Win32 app installs, Intune runs a DETECTION RULE to confirm it's "
                "actually there (checking a registry key, a file, or an MSI product code, depending on how it was "
                "packaged) -- both right after install and periodically afterward. If the detection rule is "
                "wrong or too narrow, a genuinely successful install can still show as FAILED, because Intune "
                "never found evidence it recognizes. This is the single most common real-world app-deployment "
                "failure mode, and it looks identical to a truly failed install from the support seat.\n\n"
                "READING APP STATUS: assigned, in progress, failed, and (where available) the specific error "
                "detail. A failure right after assignment often means a targeting/prerequisite problem; a failure "
                "that alternates with evidence the app is actually present is the detection-rule pattern above.\n\n"
                "WHAT A TECHNICIAN DOES: check whether the app is genuinely present on the device (ask the user, "
                "or check locally) before assuming the install itself failed -- and retry/Sync before escalating a "
                "packaging-level fix, which is out of scope for this role.\n\n"
                "COMMON MISTAKE: reporting every 'Failed' app status as a broken install without first checking "
                "whether the app is actually sitting right there on the device."
            ),
            "outcomes": [
                "Distinguish required from available app assignment",
                "Explain the Win32 app detection-rule concept and why a successful install can still show Failed",
                "Investigate whether an app is genuinely missing before assuming the install itself failed",
            ],
        },
    ],
    33: [
        {
            "title": "Windows Update, Drivers & Firmware at the Support Desk",
            "summary": (
                "Most Windows Update tickets a support technician sees are not update-engineering problems -- "
                "they're restart, driver, or firmware problems wearing an update costume.\n\n"
                "MANAGED UPDATE AWARENESS: organizations commonly control WHEN updates install through policy "
                "(deferral/pause windows), not whether they install at all. A device 'stuck' on an old update may "
                "simply be inside its organization's deferral window -- not broken, not neglected.\n\n"
                "RESTART REQUIREMENTS: many updates need a restart to finish applying, and Windows will nag "
                "increasingly about it. 'This computer has felt slow/off since the update' is very often 'the "
                "update is still pending a restart' -- check that before deeper troubleshooting.\n\n"
                "UPDATE FAILURES: a failed update can leave a device in a partially-updated state. Standard first "
                "moves: confirm sufficient disk space, confirm connectivity, retry. Deep update-engine repair is "
                "beyond this role's depth -- know when a failure needs escalation instead of repeated manual "
                "retries.\n\n"
                "DRIVER AND FIRMWARE PROBLEMS: a new problem appearing right after an update (a device that won't "
                "wake properly, a peripheral that stops working, a device that suddenly asks for a BitLocker "
                "recovery key -- covered next lesson) often traces to a driver or firmware change bundled with that "
                "update, not the update mechanism itself.\n\n"
                "ROLLBACK AWARENESS: Windows keeps the ability to roll back a recent feature update for a limited "
                "time after install. Know this exists as an option to consider/escalate for a update that clearly "
                "broke something -- you are not expected to be the one architecting an org-wide rollback policy.\n\n"
                "COMMON MISTAKE: treating 'the update broke my computer' as always requiring a rebuild, instead of "
                "checking the much more common causes first: pending restart, and a driver/firmware side effect."
            ),
            "outcomes": [
                "Recognize managed update deferral as expected behavior, not a fault",
                "Diagnose a pending-restart symptom before deeper troubleshooting",
                "Connect a post-update driver/firmware problem to its likely cause",
            ],
        },
        {
            "title": "BitLocker, Windows Hello, and Device-Action Risk",
            "summary": (
                "This lesson covers the module's two highest-stakes topics: safely handling a BitLocker recovery "
                "request, and understanding that Intune's remote device actions are NOT interchangeable in risk.\n\n"
                "WHAT BITLOCKER PROTECTS: full-disk encryption -- if a drive is removed from its device, its data "
                "is unreadable without the recovery key. It's a data-protection control, not a login screen.\n\n"
                "WHY RECOVERY PROMPTS APPEAR: a firmware/BIOS update, a TPM change, disabling Secure Boot, or "
                "certain hardware changes can make the device's boot measurements no longer match what BitLocker "
                "expects, triggering a recovery prompt as a genuine, expected safety response -- not corruption.\n\n"
                "WHERE THE RECOVERY KEY LIVES: Intune management by itself does not prove that a key was escrowed. "
                "For Microsoft Entra joined devices, organizations should configure BitLocker recovery policy to "
                "back up recovery information to Entra ID, ideally before encryption is allowed. Confirm that the "
                "expected key exists for the exact device before relying on it. If tenant policy permits, a signed-in "
                "user can often retrieve their OWN device's key through the account portal -- that's the first thing "
                "to point them to. When a technician retrieves "
                "one on a user's behalf, it is a logged, audited, role-gated administrative action, the same "
                "sensitivity tier as reading someone else's password.\n\n"
                "THE RULE THAT MATTERS MOST: NEVER disclose a recovery key before verifying both the requester's "
                "identity and that the device is genuinely theirs. A caller who sounds legitimate is not evidence. "
                "This is a safety-critical rule you will be assessed on, not a suggestion.\n\n"
                "WHEN NOT TO DISABLE BITLOCKER: disabling encryption to make a recovery prompt 'go away' removes "
                "real data protection -- never do this as a shortcut.\n\n"
                "WINDOWS HELLO (narrow): a PIN is tied to the specific device and its TPM -- it never travels over "
                "the network the way a password does. 'Wrong PIN' is usually a credential problem; 'Hello won't set "
                "up at all' often points to a TPM/device problem instead. Keep this distinction; you don't need "
                "deeper Hello depth for this role.\n\n"
                "DEVICE-ACTION RISK LADDER (technician-risk awareness, not a rigid platform-universal ordering):\n"
                "  LOWER RISK: Sync (just forces check-in), Restart (disruptive but reversible).\n"
                "  HIGHER RISK: Retire (removes managed data/profiles), Delete (removes the Intune record and "
                "initiates retirement), Fresh Start (removes apps/settings; retention and re-enrollment behavior "
                "depends on the selected user-data option), Autopilot Reset (wipes files/apps/settings while "
                "preserving the managed deployment relationship), and Wipe (factory reset; Windows offers variants, "
                "including a keep-enrollment option, but the destructive/default paths remove data and can make a "
                "device unusable if interrupted).\n"
                "SYNC AND WIPE ARE NOT THE SAME KIND OF ACTION. Every higher-risk action needs real authorization "
                "and verification before you touch it, never habit or convenience."
            ),
            "outcomes": [
                "Explain what BitLocker protects and why a recovery prompt is a legitimate safety response",
                "State the mandatory identity/device verification rule before disclosing a recovery key",
                "Rank Intune device actions by risk and explain why Sync and Wipe are not equivalent",
            ],
        },
    ],
    34: [
        {
            "title": "The Device Lifecycle: Received to Retired",
            "summary": (
                "Every managed device moves through the same lifecycle, and knowing where a device sits in it "
                "tells you what should be true about it right now.\n\n"
                "THE LIFECYCLE: DEVICE RECEIVED -> ASSIGNED (to a person/purpose) -> ENROLLED (Intune management "
                "begins) -> CONFIGURED (policies/apps land) -> SUPPORTED (normal day-to-day) -> REPLACED / "
                "REASSIGNED (hardware swap, new owner) -> RETIRED / WIPED (removed from service).\n\n"
                "WHY THIS MATTERS FOR TRIAGE: a device stuck between ASSIGNED and ENROLLED has a completely "
                "different problem than one stuck between CONFIGURED and SUPPORTED -- knowing the expected stage "
                "narrows what's actually wrong before you look at anything else.\n\n"
                "REPLACEMENT/REASSIGNMENT: when a device changes hands (new employee inherits an old laptop, a "
                "broken device is swapped), the record's primary user needs to change and the device typically "
                "needs a reset step first -- carrying over the previous person's profile/data to a new assignee is "
                "a data-handling mistake, not a shortcut.\n\n"
                "THIS LESSON SETS UP THE NEXT TWO: onboarding is the ASSIGNED-through-SUPPORTED stretch of this "
                "lifecycle done right; offboarding is the safe path into RETIRED/REASSIGNED when someone leaves.\n\n"
                "COMMON MISTAKE: treating every device problem as a fresh mystery instead of first asking 'what "
                "lifecycle stage is this device supposed to be in right now, and does the evidence match that.'"
            ),
            "outcomes": [
                "State the full device lifecycle from received to retired",
                "Use lifecycle stage as a first triage question",
                "Explain why reassigning a device to a new owner requires a reset step, not a handoff as-is",
            ],
        },
        {
            "title": "Endpoint Onboarding: Beyond the AD Account",
            "summary": (
                "Onboarding a new hire's ACCOUNT (creating the directory account, license, and group membership) "
                "is only the identity half of the job -- this lesson covers the device/M365 half that has to "
                "happen alongside it, building directly on the account-creation skills you already have.\n\n"
                "WHAT'S ALREADY COVERED ELSEWHERE: creating the AD account, assigning groups, and granting basic "
                "access are directory/identity tasks you've already practiced -- this lesson does not re-teach "
                "them.\n\n"
                "THE DEVICE/M365 LAYER a technician adds on top:\n"
                "  - PREREQUISITES: confirm the account exists and has the right license assigned before anything "
                "device-related -- a device enrolling for an unlicensed account will surface confusing gaps later.\n"
                "  - DEVICE ASSIGNMENT: the specific device (new or reassigned, see the lifecycle lesson) is "
                "recorded as belonging to this person.\n"
                "  - ENROLLMENT: the device is Entra-joined and Intune-enrolled through whichever path applies "
                "(automatic, Autopilot, or Device Preparation).\n"
                "  - APPS AND POLICIES: confirm the expected required apps and configuration profiles actually "
                "landed -- using the profile/app status evidence from earlier in this module, not just assuming.\n"
                "  - MFA REGISTRATION: the new hire registers their authentication method as part of first sign-"
                "in -- a step that's easy to skip and then surfaces later as a confusing sign-in ticket.\n"
                "  - ACCESS VERIFICATION: confirm the person can actually reach what they need (mail, Teams, the "
                "specific shares/sites their role requires) before calling onboarding done.\n"
                "  - DOCUMENTATION: record what was done -- the device assigned, what was verified -- the same "
                "documentation discipline as every other ticket type in this program.\n\n"
                "COMMON MISTAKE: calling onboarding complete once the account exists, without ever confirming the "
                "device actually enrolled, received its apps/policies, and that access was verified end to end."
            ),
            "outcomes": [
                "Identify the device/M365 steps onboarding adds on top of AD account creation",
                "Explain why license and account prerequisites must be confirmed before device work",
                "State the verification and documentation steps that complete an onboarding request",
            ],
        },
        {
            "title": "Offboarding Safely, and Mobile Device Basics",
            "summary": (
                "Offboarding is the highest-risk routine task in this whole module -- getting it wrong leaves "
                "either open access for a departed employee or a mishandled corporate device. This lesson also "
                "covers the small amount of mobile MDM awareness this program expects.\n\n"
                "OFFBOARDING, IN ORDER:\n"
                "  1. AUTHORIZATION -- confirm the offboarding request is genuinely authorized (HR/manager), the "
                "same discipline as verifying identity before any other account-state change.\n"
                "  2. ACCOUNT AND ACCESS STATE -- block sign-in and revoke active sessions so access stops "
                "immediately, not just 'eventually.'\n"
                "  3. CORPORATE DEVICE RECOVERY -- the device needs to physically come back or be confirmed "
                "returned before the next step; you cannot safely reset a device you don't have.\n"
                "  4. DATA HANDLING -- corporate data on the device needs proper handling (per your organization's "
                "policy) before the device is repurposed -- this is exactly why a reset happens before reassignment, "
                "not after.\n"
                "  5. DEVICE STATE/REASSIGNMENT -- the correct lifecycle action (reset, then reassign or retire) "
                "runs only once authorization, access removal, and data handling are all already done -- never "
                "before.\n"
                "  6. DOCUMENTATION -- record what was done and confirmed.\n\n"
                "WHY ORDER MATTERS: resetting/reassigning a device before access is revoked or before data handling "
                "is confirmed is the same category of mistake as disclosing a BitLocker key before verifying "
                "identity -- a safety-critical failure, not a shortcut.\n\n"
                "MOBILE DEVICE BASICS (kept intentionally small): iOS/iPadOS and Android both support enrollment "
                "through Company Portal or, for supported Android scenarios, the Microsoft Intune app. ANDROID WORK "
                "PROFILE creates a genuinely separate container on a personal device -- Intune policy only touches "
                "the work side; personal apps/data are untouched. The same MANAGED VS PERSONAL distinction applies "
                "as everywhere else in this module. For a lost or departing-employee mobile device: RETIRE removes "
                "only the managed/work data, leaving personal data on a BYOD device alone -- the appropriate default. "
                "WIPE resets the entire device and is reserved for a corporate-owned device or a security-critical "
                "situation -- choosing between them is a real decision with real consequences, not a coin flip."
            ),
            "outcomes": [
                "Execute the offboarding sequence in the correct order and explain why order matters",
                "Explain the managed/personal boundary on a mobile device via work profile / User Enrollment",
                "Choose correctly between Retire and Wipe for a mobile device based on ownership and risk",
            ],
        },
    ],
}

_INTUNE_QUIZZES = {
    30: {
        "title": "Intune & Managed Endpoint Foundations Check",
        "questions": [
            {
                "question_text": "A laptop is company-owned but its Intune record shows no enrollment. What does this mean?",
                "option_a": "It is managed because the company owns it",
                "option_b": "It is not receiving any Intune policy, regardless of who owns it",
                "option_c": "It will automatically enroll within 24 hours with no action needed",
                "option_d": "Ownership and management are the same thing",
                "correct_answer": "B",
                "explanation": "Ownership and management are separate facts. An unmanaged device gets no pushed policy no matter who owns the hardware.",
            },
            {
                "question_text": "A device is Entra registered rather than joined. What does that tell you?",
                "option_a": "It is the strongest possible management relationship",
                "option_b": "It is likely a personal (BYOD) identity relationship; its separate management state still determines whether it is unmanaged, app-protected, or Intune-enrolled",
                "option_c": "It is definitely hybrid joined",
                "option_d": "It cannot run Windows 11",
                "correct_answer": "B",
                "explanation": "Registered typically describes a personal/BYOD identity relationship, but it does not prove the management state. Registered Windows devices can also enroll in Intune MDM.",
            },
            {
                "question_text": "A device's last check-in was 6 days ago. What should you conclude?",
                "option_a": "The device is definitely broken",
                "option_b": "This is meaningless and can be ignored",
                "option_c": "The record is stale -- the device may be off, offline, or genuinely having a problem, and this needs investigating, not ignoring",
                "option_d": "Check-in time only matters for compliance, never for anything else",
                "correct_answer": "C",
                "explanation": "A stale check-in is real evidence worth investigating, not a fact to skim past or over-interpret as a guaranteed failure.",
            },
            {
                "question_text": "A user's device is running Windows 10. What is the correct framing for 2026?",
                "option_a": "Windows 10 is the modern business standard, same as Windows 11",
                "option_b": "General Windows 10 servicing ended in October 2025; absent an explicit ESU/LTSC exception, treat it as a legacy, at-risk device to flag, not the normal endpoint",
                "option_c": "Windows 10 devices can never enroll in Intune",
                "option_d": "Windows 10 is newer than Windows 11",
                "correct_answer": "B",
                "explanation": "General Windows 10 servicing ended Oct 14, 2025. ESU and separately serviced LTSC releases are explicit exceptions; Windows 11 remains the normal supported baseline.",
            },
        ],
    },
    31: {
        "title": "Windows Enrollment & Autopilot Check",
        "questions": [
            {
                "question_text": "A user Entra-joins their Windows 11 laptop through Settings, and it enrolls into Intune on the same sign-in with no other action. What enrollment path is this?",
                "option_a": "Windows Autopilot",
                "option_b": "Automatic MDM enrollment",
                "option_c": "Autopilot Device Preparation",
                "option_d": "Group Policy enrollment",
                "correct_answer": "B",
                "explanation": "This is the automatic MDM enrollment path -- the device Entra-joins and auto-enrolls without any pre-staging.",
            },
            {
                "question_text": "A device needs to be hybrid joined during its zero-touch deployment. Which system supports that?",
                "option_a": "Only Autopilot Device Preparation",
                "option_b": "Neither system supports hybrid join",
                "option_c": "Windows Autopilot (classic)",
                "option_d": "Only BYOD/Company Portal enrollment",
                "correct_answer": "C",
                "explanation": "Autopilot Device Preparation is Entra-joined only in its current form. Hybrid join requires classic Windows Autopilot.",
            },
            {
                "question_text": "What is a genuine advantage of Autopilot Device Preparation over classic Autopilot?",
                "option_a": "It requires more manual imaging steps",
                "option_b": "It does not require pre-registering the device's hardware hash ahead of time, and gives near-real-time deployment status",
                "option_c": "It is the only option that can ever enroll a device",
                "option_d": "It replaces the need for Intune entirely",
                "correct_answer": "B",
                "explanation": "Device Preparation removes the pre-registration step and reports status in near-real-time -- a real reduction in deployment friction, not a replacement for Intune.",
            },
            {
                "question_text": "A device is Entra joined but its Intune record shows it was never enrolled. What is the most useful next step?",
                "option_a": "Reimage the device immediately",
                "option_b": "Assume the device is unfixable",
                "option_c": "Check whether auto-enrollment is configured and whether the user has actually signed in with the work account since joining",
                "option_d": "Delete the device record and start over with no investigation",
                "correct_answer": "C",
                "explanation": "Entra-joined-but-not-enrolled is a specific, diagnosable gap -- check the auto-enrollment configuration and sign-in history before reaching for a rebuild.",
            },
        ],
    },
    32: {
        "title": "Policies, Compliance & Applications Check",
        "questions": [
            {
                "question_text": "A configuration profile shows status 'Pending' for a device. What does that mean?",
                "option_a": "The setting failed and needs troubleshooting immediately",
                "option_b": "The device has not reported back since the profile was assigned -- it hasn't checked in yet",
                "option_c": "The setting does not apply to this device",
                "option_d": "Two policies are in conflict",
                "correct_answer": "B",
                "explanation": "Pending means the device hasn't checked in and reported status since assignment -- often resolves with time or a manual Sync, not an error by itself.",
            },
            {
                "question_text": "What is the key difference between a configuration policy and a compliance policy?",
                "option_a": "There is no real difference; the terms are interchangeable",
                "option_b": "A configuration policy pushes/enforces a setting; a compliance policy evaluates and reports whether the device meets a rule, without changing anything",
                "option_c": "Compliance policies always push settings, configuration policies only report",
                "option_d": "Configuration policies only apply to mobile devices",
                "correct_answer": "B",
                "explanation": "Configuration = push/enforce a setting. Compliance = evaluate/report pass-fail against a rule. They do fundamentally different jobs.",
            },
            {
                "question_text": "A device is marked noncompliant because BitLocker is disabled, and the user is blocked from email by Conditional Access. What is the correct fix?",
                "option_a": "Weaken the Conditional Access policy so the user can get through",
                "option_b": "Turn off the compliance rule that's causing the block",
                "option_c": "Bring the device into compliance by enabling BitLocker, which will then satisfy the Conditional Access requirement",
                "option_d": "Tell the user email is not available for security reasons and take no further action",
                "correct_answer": "C",
                "explanation": "The correct fix addresses the actual device state (enable BitLocker), not weakening policy to bypass the check for one user.",
            },
            {
                "question_text": "A Win32 app shows as 'Failed' immediately after what looked like a successful install. What is a likely cause worth checking before assuming the install failed?",
                "option_a": "The detection rule may not be matching a genuinely successful install",
                "option_b": "Win32 apps never actually install correctly",
                "option_c": "The device has been wiped",
                "option_d": "The app was never assigned to anyone",
                "correct_answer": "A",
                "explanation": "A detection-rule mismatch is the most common real-world cause of a 'Failed' status on an app that actually installed -- worth checking before assuming the install itself failed.",
            },
            {
                "question_text": "What is the difference between a Required and an Available app assignment?",
                "option_a": "Required apps install automatically for the assigned group; Available apps are offered for the user to install on demand",
                "option_b": "There is no difference",
                "option_c": "Available apps always install automatically; Required apps never do",
                "option_d": "Required apps can only be Microsoft Store apps",
                "correct_answer": "A",
                "explanation": "Required = automatic install for the assignment. Available = shown in Company Portal / the Intune app for the user to choose to install.",
            },
        ],
    },
    33: {
        "quiz_purpose": "gate",
        "title": "Windows 11 Endpoint Troubleshooting & BitLocker Check",
        "questions": [
            {
                "question_text": "A user says their computer has felt slow and off since a Windows update. What is a common, simple first check?",
                "option_a": "Immediately reimage the device",
                "option_b": "Whether the update is still pending a restart",
                "option_c": "Assume the update engine is permanently broken",
                "option_d": "Disable future updates for that device",
                "correct_answer": "B",
                "explanation": "Many post-update symptoms trace to a pending restart the update is waiting on -- check that before deeper troubleshooting.",
            },
            {
                "question_text": "A device asks for a BitLocker recovery key right after a firmware update. What does this most likely mean?",
                "option_a": "The disk is corrupted",
                "option_b": "The firmware change altered the boot measurements BitLocker expects, triggering a legitimate recovery prompt",
                "option_c": "The user is being hacked",
                "option_d": "BitLocker has failed permanently and must be disabled",
                "correct_answer": "B",
                "explanation": "Firmware/TPM changes commonly trigger a legitimate BitLocker recovery prompt as an expected safety response, not corruption or compromise.",
            },
            {
                "question_text": "A caller asks for their BitLocker recovery key over the phone, sounding confident and providing their name. What must happen before you disclose it?",
                "option_a": "Nothing further -- sounding legitimate is enough",
                "option_b": "Verify the caller's identity and that the device is genuinely theirs through the approved process, every time",
                "option_c": "Only verify identity if the caller sounds suspicious",
                "option_d": "Disclose it, then verify identity afterward",
                "correct_answer": "B",
                "explanation": "Identity and device ownership must always be verified before disclosure -- sounding legitimate is never sufficient evidence.",
            },
            {
                "question_text": "Which of these device actions is the LEAST risky to perform?",
                "option_a": "Wipe",
                "option_b": "Sync",
                "option_c": "Autopilot Reset",
                "option_d": "Fresh Start",
                "correct_answer": "B",
                "explanation": "Sync simply forces a check-in and changes nothing destructive on the device -- the lowest-risk action on the list.",
            },
            {
                "question_text": "Why should a technician never disable BitLocker just to stop a recovery prompt from appearing?",
                "option_a": "It's technically impossible to disable BitLocker",
                "option_b": "Disabling it removes real data protection from the device as a shortcut around a legitimate prompt",
                "option_c": "It has no real effect either way",
                "option_d": "It automatically re-enables itself within a day",
                "correct_answer": "B",
                "explanation": "Disabling encryption to make a recovery prompt go away trades away real data protection -- never an acceptable shortcut.",
            },
        ],
    },
    34: {
        "title": "Device Lifecycle, Onboarding, Offboarding & Mobile Check",
        "questions": [
            {
                "question_text": "What is the correct device lifecycle order?",
                "option_a": "Received -> Assigned -> Enrolled -> Configured -> Supported -> Replaced/Reassigned -> Retired/Wiped",
                "option_b": "Retired -> Received -> Supported -> Enrolled",
                "option_c": "Enrolled -> Received -> Configured -> Retired",
                "option_d": "There is no meaningful order",
                "correct_answer": "A",
                "explanation": "Knowing the expected lifecycle stage narrows what should be true about a device before troubleshooting anything else.",
            },
            {
                "question_text": "An onboarding ticket's AD account and license are already created. What does a technician still need to confirm before calling it done?",
                "option_a": "Nothing further is needed once the account exists",
                "option_b": "Device assignment, enrollment, apps/policies landing, MFA registration, and access verification",
                "option_c": "Only that the user has an email address",
                "option_d": "Only that the device powers on",
                "correct_answer": "B",
                "explanation": "The account is only half the job -- device enrollment, app/policy delivery, MFA registration, and access verification complete an onboarding.",
            },
            {
                "question_text": "During offboarding, why must a device be reset before it's reassigned to someone else?",
                "option_a": "It doesn't matter -- resetting is optional",
                "option_b": "So the previous employee's corporate data and access do not carry over to the new assignee",
                "option_c": "Resetting is only needed for mobile devices",
                "option_d": "To make the device slower on purpose",
                "correct_answer": "B",
                "explanation": "Carrying over a previous person's profile/data to a new assignee is a data-handling failure -- the device must be reset first.",
            },
            {
                "question_text": "What is the correct order-of-operations risk in offboarding?",
                "option_a": "Order doesn't matter as long as everything eventually happens",
                "option_b": "Resetting/reassigning the device before access is revoked and data handling is confirmed is a safety-critical mistake",
                "option_c": "Access should be revoked last, after the device is already reassigned",
                "option_d": "Authorization can be skipped if the requester seems trustworthy",
                "correct_answer": "B",
                "explanation": "Resetting or reassigning before authorization, access revocation, and data handling are confirmed can create real security exposure -- order matters.",
            },
            {
                "question_text": "A personal (BYOD) mobile device with a work profile needs to be handled because the employee is leaving. What is the appropriate default action?",
                "option_a": "Wipe the entire device including personal data",
                "option_b": "Retire, which removes only the managed/work data and leaves personal data untouched",
                "option_c": "Do nothing since it's a personal device",
                "option_d": "Physically confiscate the phone",
                "correct_answer": "B",
                "explanation": "Retire is the appropriate default for a BYOD device -- it removes only the managed/work side, respecting the personal/work data boundary.",
            },
        ],
    },
}

# Guided endpoint labs use the reusable evidence workbench declared below:
# students open evidence, make staged decisions, verify a deterministic
# simulated outcome, and document a support conclusion. "role" drives the TrainingWeekActivity
# metadata_json learning_role override applied in the sync function below:
# practice labs use the guided_lab default (no override needed), troubleshoot
# and prove labs are explicitly overridden -- see Step 10 of the user's brief
# ("do not merely label every guided lab Troubleshoot").
_INTUNE_NEW_LABS: dict[int, list[dict]] = {
    30: [
        {
            "role": "practice",
            "title": "Read a Device Record",
            "lab_type": "structured_endpoint",
            "description": "Walk through a real device record field by field and state what each one tells you.",
            "estimated_minutes": 15,
            "questions": [
                {
                    "id": "read-join-type",
                    "prompt": "A device record shows: Join type: Microsoft Entra joined. Primary user: Dana Ruiz. Management state: Managed. What can you conclude?",
                    "context": "This is a straightforward evidence-reading exercise -- read the fields, don't guess beyond them.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "This is a corporate device, fully joined, currently under Intune management, primarily used by Dana Ruiz"},
                        {"id": "b", "label": "This is a personal device with no management"},
                        {"id": "c", "label": "The join type field is irrelevant to support work"},
                        {"id": "d", "label": "Management state has no bearing on what policy the device receives"},
                    ],
                    "correct": ["a"],
                    "explanation": "Each field states a specific fact -- joined + managed together describe a normal, fully-managed corporate device belonging to the listed primary user.",
                },
                {
                    "id": "read-last-checkin",
                    "prompt": "The same record shows: Last check-in: 11 minutes ago. Compliance: Compliant. What does this tell you about the reliability of the compliance status?",
                    "context": "Recency of check-in affects how much you should trust a status field.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The status is recent evidence and less likely to be stale, but important decisions should still be correlated with the policy and device details"},
                        {"id": "b", "label": "The compliance status is meaningless without a check-in"},
                        {"id": "c", "label": "Compliance status never depends on check-in recency"},
                        {"id": "d", "label": "The device is definitely broken"},
                    ],
                    "correct": ["a"],
                    "explanation": "A recent check-in makes the status more useful and less likely to be stale; it does not make a single status field infallible or replace corroborating evidence.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "Diagnose Join, Management & Ownership",
            "lab_type": "structured_endpoint",
            "description": "Given a realistic device record, determine join type, management state, likely ownership, and whether a reported problem is identity-side, enrollment-side, or device-side.",
            "estimated_minutes": 20,
            "questions": [
                {
                    "id": "identity-vs-enrollment",
                    "prompt": "A device record shows: Join type: Microsoft Entra registered. Management state: Unmanaged. The user says 'IT policies aren't applying to my laptop.' What is actually going on?",
                    "context": "The user believes this should be a fully managed corporate laptop.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "This is registered and currently unmanaged -- likely a personal device that has not completed an Intune MDM enrollment; confirm the intended BYOD enrollment policy before promising full management"},
                        {"id": "b", "label": "The device is broken and needs a reimage"},
                        {"id": "c", "label": "The user's account is locked"},
                        {"id": "d", "label": "Policies always apply eventually regardless of join type"},
                    ],
                    "correct": ["a"],
                    "explanation": "Registered commonly describes BYOD identity, while Unmanaged is the field proving that no Intune policy is arriving. Registered personal Windows devices can be MDM-enrolled, so read both fields.",
                },
                {
                    "id": "hybrid-stuck-policy",
                    "prompt": "A device is Entra hybrid joined. Cloud (Intune) policy hasn't applied in over a week, but the device works fine on the local domain network. What should you suspect first?",
                    "context": "The device is on-site and connects to the corporate network daily.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "A hybrid-join sync health problem preventing the device from completing its cloud registration/check-in properly"},
                        {"id": "b", "label": "The device has been stolen"},
                        {"id": "c", "label": "Cloud policy never applies to hybrid-joined devices"},
                        {"id": "d", "label": "The user's password is wrong"},
                    ],
                    "correct": ["a"],
                    "explanation": "A hybrid-joined device needing periodic domain-controller line-of-sight to keep its Entra registration healthy is the classic cause of stuck cloud policy despite normal local domain function.",
                },
                {
                    "id": "ownership-vs-management",
                    "prompt": "A device is confirmed company-owned (asset tag on file) but its record shows Management state: Unmanaged. Is this a contradiction?",
                    "context": "The requester is confused because 'the company owns it, so it should be managed.'",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "No -- ownership and management are separate facts; a company-owned device can still be unenrolled and therefore unmanaged"},
                        {"id": "b", "label": "Yes -- ownership always implies management"},
                        {"id": "c", "label": "The record must be wrong and should be deleted"},
                        {"id": "d", "label": "Unmanaged devices cannot be company-owned by definition"},
                    ],
                    "correct": ["a"],
                    "explanation": "Ownership and management are independent facts on the device record -- this lesson's core distinction, applied here to a real evidence read.",
                },
            ],
        },
    ],
    31: [
        {
            "role": "practice",
            "title": "Read Enrollment Evidence",
            "lab_type": "structured_endpoint",
            "description": "Read a device's enrollment fields and identify how it was enrolled.",
            "estimated_minutes": 15,
            "questions": [
                {
                    "id": "read-enrollment-type",
                    "prompt": "A device record shows: Enrollment type: Automatic MDM enrollment. Enrolled: same day as Entra join. What does this tell you about how the device reached management?",
                    "context": "Read the field directly -- this is not a diagnosis exercise yet.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The user Entra-joined the device and it auto-enrolled on the same sign-in, without any pre-staging"},
                        {"id": "b", "label": "The device was pre-staged through Windows Autopilot"},
                        {"id": "c", "label": "The device enrolled through Group Policy"},
                        {"id": "d", "label": "Enrollment type never affects troubleshooting"},
                    ],
                    "correct": ["a"],
                    "explanation": "This is the automatic MDM enrollment signature -- join and enrollment happening together, with no Autopilot profile involved.",
                },
                {
                    "id": "read-autopilot-profile",
                    "prompt": "A different device record shows: Enrolled via: Windows Autopilot profile 'Sales-Onboarding'. What does the presence of a named Autopilot profile tell you?",
                    "context": "Compare this to the automatic-enrollment record above.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "This device was pre-staged and went through zero-touch provisioning under that specific profile"},
                        {"id": "b", "label": "This is identical to automatic MDM enrollment"},
                        {"id": "c", "label": "Autopilot profiles are irrelevant to how a device was set up"},
                        {"id": "d", "label": "The device is definitely unmanaged"},
                    ],
                    "correct": ["a"],
                    "explanation": "A named Autopilot profile is direct evidence of zero-touch, pre-staged deployment -- a different path than ad-hoc automatic enrollment.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "Entra Joined But Not Intune Managed",
            "lab_type": "structured_endpoint",
            "description": "A device is Entra joined but its Intune record shows it was never enrolled. Work out why.",
            "estimated_minutes": 20,
            "questions": [
                {
                    "id": "narrow-the-cause",
                    "prompt": "A laptop's record shows: Join type: Microsoft Entra joined (confirmed 3 days ago). Intune enrollment: none on record. The user has not opened Company Portal. What is the most likely explanation?",
                    "context": "Auto-enrollment is confirmed enabled for this tenant.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The user joined the device but hasn't yet completed the sign-in step that triggers automatic enrollment (or enrollment silently failed) -- worth having them sign in again and checking for an enrollment error"},
                        {"id": "b", "label": "Entra join and Intune enrollment are unrelated and this is expected forever"},
                        {"id": "c", "label": "The device must be reimaged immediately"},
                        {"id": "d", "label": "This can only be fixed by deleting the Entra join"},
                    ],
                    "correct": ["a"],
                    "explanation": "Join without enrollment is a specific, diagnosable gap -- check whether the triggering sign-in actually completed, and look for an enrollment error, before anything more drastic.",
                },
                {
                    "id": "identity-side-vs-device-side",
                    "prompt": "You confirm the same user's OTHER device enrolled successfully last month with no issue. What does that tell you about where the problem likely sits?",
                    "context": "Same user, same tenant, same license -- one device enrolled fine.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The problem is more likely device-side (this specific machine) than identity-side (the user's account), since the account clearly works for enrollment elsewhere"},
                        {"id": "b", "label": "The problem must be the user's account since accounts cause every issue"},
                        {"id": "c", "label": "This comparison provides no useful information"},
                        {"id": "d", "label": "The license must be revoked"},
                    ],
                    "correct": ["a"],
                    "explanation": "A working enrollment elsewhere for the same identity narrows the cause toward this specific device rather than the account/license layer.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "Autopilot Deployment Stuck",
            "lab_type": "structured_endpoint",
            "description": "A new device's Autopilot/Device Preparation deployment is stuck partway through. Read the status evidence to diagnose it.",
            "estimated_minutes": 20,
            "questions": [
                {
                    "id": "stuck-at-apps",
                    "prompt": "Deployment status shows: Device Entra-joined: complete. Intune enrollment: complete. App installation: 2 of 5 required apps installed, stuck for 40 minutes. What should you check first?",
                    "context": "The device has completed the identity/enrollment steps successfully.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Whether the specific stuck app assignments have a known issue (e.g. a detection-rule or network problem), since the identity/enrollment steps already succeeded"},
                        {"id": "b", "label": "Restart the entire Autopilot profile from scratch"},
                        {"id": "c", "label": "Assume Entra join failed"},
                        {"id": "d", "label": "Delete the device from Entra"},
                    ],
                    "correct": ["a"],
                    "explanation": "Since join and enrollment both succeeded, the stuck stage is specifically app installation -- investigate that stage, not the already-completed earlier ones.",
                },
                {
                    "id": "device-prep-vs-autopilot-symptom",
                    "prompt": "Two brand-new laptops both fail deployment during OOBE. One shows near-real-time status updates as it fails; the other shows the standard delayed status. What does that difference suggest?",
                    "context": "Both devices are Windows 11 and Entra-joined only, no hybrid join involved.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The near-real-time one is likely going through Autopilot Device Preparation, and the delayed one through classic Autopilot -- worth confirming which profile applies to each before troubleshooting further"},
                        {"id": "b", "label": "Status timing has no diagnostic value"},
                        {"id": "c", "label": "Both are definitely on the exact same deployment path"},
                        {"id": "d", "label": "This means one device is defective hardware"},
                    ],
                    "correct": ["a"],
                    "explanation": "Near-real-time status is a distinguishing trait of Autopilot Device Preparation versus classic Autopilot's standard delay -- useful evidence for narrowing which system's failure mode you're actually looking at.",
                },
            ],
        },
    ],
    32: [
        {
            "role": "practice",
            "title": "Read Profile Status Evidence",
            "lab_type": "structured_endpoint",
            "description": "Practice reading and correctly interpreting the four configuration-profile status states.",
            "estimated_minutes": 15,
            "questions": [
                {
                    "id": "read-conflict",
                    "prompt": "A profile shows status: Conflict, with the detail 'setting already configured by another profile.' What should you do?",
                    "context": "This is a status-reading exercise -- interpret the evidence given.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Investigate which two policies disagree on this setting -- Conflict needs investigation, it will not resolve itself by waiting"},
                        {"id": "b", "label": "Wait 24 hours and it will fix itself like Pending does"},
                        {"id": "c", "label": "This means the setting doesn't apply to this device"},
                        {"id": "d", "label": "This always means the device is broken"},
                    ],
                    "correct": ["a"],
                    "explanation": "Conflict is a distinct state from Pending -- it means two policies actively disagree, and needs investigation rather than a wait-and-see approach.",
                },
                {
                    "id": "read-not-applicable",
                    "prompt": "A profile targeting a Windows-only setting shows 'Not applicable' for a specific device. Is this an error?",
                    "context": "Check what you know about this specific status.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "No -- Not applicable is expected behavior when a setting doesn't match the device's platform/edition, not a failure"},
                        {"id": "b", "label": "Yes -- this always requires escalation"},
                        {"id": "c", "label": "Not applicable and Conflict mean the same thing"},
                        {"id": "d", "label": "This means the device is unmanaged"},
                    ],
                    "correct": ["a"],
                    "explanation": "Not applicable is expected, not an error -- it simply means the setting doesn't match this device's platform or edition.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "The App That Says It Failed",
            "lab_type": "structured_endpoint",
            "description": "An assigned app shows Failed. Work out whether this is a real install failure, an assignment problem, or a detection-rule mismatch.",
            "estimated_minutes": 20,
            "questions": [
                {
                    "id": "app-present-but-failed",
                    "prompt": "An app shows 'Failed' in Intune, but the user confirms the app is right there on their desktop and works fine. What is the most likely explanation?",
                    "context": "The app genuinely works when the user opens it.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "A detection-rule mismatch -- Intune isn't recognizing evidence of the successful install, even though the app is genuinely present"},
                        {"id": "b", "label": "The user is mistaken and the app isn't really there"},
                        {"id": "c", "label": "The device must be reimaged"},
                        {"id": "d", "label": "Failed status is always accurate and the app must be reinstalled destructively"},
                    ],
                    "correct": ["a"],
                    "explanation": "This is the classic detection-rule trap -- a genuinely successful install can still show Failed if Intune's detection check doesn't recognize it.",
                },
                {
                    "id": "app-truly-missing",
                    "prompt": "A different app shows 'Failed,' and the user confirms it is NOT present anywhere on the device. What does that change about your next step?",
                    "context": "This time, the app is genuinely absent.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "This points toward a real install failure (prerequisite, network, or targeting issue) rather than a detection-rule mismatch, and a retry/Sync plus checking assignment is the reasonable next step"},
                        {"id": "b", "label": "Treat it identically to the detection-rule case above"},
                        {"id": "c", "label": "Nothing can be done and the ticket should be closed"},
                        {"id": "d", "label": "Immediately escalate to app packaging without any further evidence"},
                    ],
                    "correct": ["a"],
                    "explanation": "Confirming the app is genuinely absent (not just misreported) changes the likely cause -- now a real install problem, worth a retry/Sync and an assignment check before escalating.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "Blocked and Stuck: Compliance Meets a Pending Profile",
            "lab_type": "structured_endpoint",
            "description": "A user is blocked from a resource by Conditional Access, and a separate configuration profile shows Pending. Work out which fact explains the access block, and what's actually needed to fix the profile.",
            "estimated_minutes": 20,
            "questions": [
                {
                    "id": "which-fact-blocks-access",
                    "prompt": "Device evidence: Compliance: Noncompliant (reason: BitLocker not enabled). A separate Wi-Fi configuration profile: Pending. The user is blocked from SharePoint by Conditional Access. Which fact explains the block?",
                    "context": "Two different pieces of evidence exist -- only one is directly relevant to the access block.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The Noncompliant status -- Conditional Access is gating on compliance, and the Pending Wi-Fi profile is a separate, unrelated fact"},
                        {"id": "b", "label": "The Pending Wi-Fi profile is the cause of the access block"},
                        {"id": "c", "label": "Both facts are equally responsible and unrelated to each other"},
                        {"id": "d", "label": "Neither fact is relevant; the block is random"},
                    ],
                    "correct": ["a"],
                    "explanation": "Compliance state is what Conditional Access checks -- the noncompliant BitLocker reason is the actual cause. The Pending Wi-Fi profile is a separate, unrelated piece of evidence.",
                },
                {
                    "id": "correct-fix-not-bypass",
                    "prompt": "The user asks you to just get them into SharePoint right now. What is the correct response?",
                    "context": "The user is frustrated and wants a fast fix.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Explain that the fix is enabling BitLocker to bring the device into compliance, not bypassing the Conditional Access policy"},
                        {"id": "b", "label": "Temporarily disable Conditional Access for this user"},
                        {"id": "c", "label": "Mark the device compliant manually without fixing anything"},
                        {"id": "d", "label": "Tell the user there is no possible fix"},
                    ],
                    "correct": ["a"],
                    "explanation": "The correct, safe fix addresses the real device state -- weakening policy or manually overriding compliance defeats the security control for everyone.",
                },
            ],
        },
        {
            "role": "prove",
            "title": "Diagnose the Multi-Signal Ticket",
            "lab_type": "structured_endpoint",
            "description": "An unfamiliar ticket arrives with several device, app, and policy evidence points at once and no walkthrough. Determine the actual cause yourself.",
            "estimated_minutes": 25,
            "questions": [
                {
                    "id": "multi-signal-diagnosis",
                    "prompt": "Which two evidence findings explain the missing TimeTrack app and the SharePoint block?",
                    "context": "Select only findings that directly explain a reported symptom.",
                    "type": "multi_choice",
                    "options": [
                        {"id": "a", "label": "TimeTrack is not targeted to the device's group, so no install was attempted"},
                        {"id": "b", "label": "BitLocker noncompliance fails the Conditional Access grant requirement for SharePoint"},
                        {"id": "c", "label": "The successful wallpaper profile caused both symptoms"},
                        {"id": "d", "label": "The device must be wiped because two symptoms exist"},
                    ],
                    "correct": ["a", "b"],
                    "explanation": "Not targeted explains why no app install occurred. BitLocker noncompliance separately explains why Conditional Access blocked SharePoint.",
                },
                {
                    "id": "multi-signal-action",
                    "prompt": "What is the safest repair plan?",
                    "context": "Address each supported cause without weakening access controls or using destructive device actions.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Correct TimeTrack targeting, enable and escrow BitLocker through the approved process, sync, then re-evaluate compliance and access"},
                        {"id": "b", "label": "Exclude the user from Conditional Access and manually mark the app installed"},
                        {"id": "c", "label": "Wipe the device and hope both symptoms disappear"},
                        {"id": "d", "label": "Change the successful wallpaper profile"},
                    ],
                    "correct": ["a"],
                    "explanation": "The safe plan repairs both evidenced causes and verifies them without bypassing Conditional Access or destroying the device.",
                },
                {
                    "id": "multi-signal-verification",
                    "prompt": "Which evidence set proves the case is resolved?",
                    "context": "Do not close on an action alone; require outcome evidence for both symptoms.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "TimeTrack is targeted and reports Installed; compliance reports Compliant after sync; SharePoint access satisfies the Conditional Access grant"},
                        {"id": "b", "label": "The remediation buttons were clicked"},
                        {"id": "c", "label": "The wallpaper profile still reports Succeeded"},
                        {"id": "d", "label": "The user says it probably works now"},
                    ],
                    "correct": ["a"],
                    "explanation": "Resolution requires resulting evidence for app delivery, compliance, and the access decision—not merely attempted actions.",
                },
            ],
        },
    ],
    33: [
        {
            "role": "practice",
            "title": "Read Update and Driver Evidence",
            "lab_type": "structured_endpoint",
            "description": "Practice reading Windows Update and device-health evidence to identify what it's telling you.",
            "estimated_minutes": 15,
            "questions": [
                {
                    "id": "read-pending-restart",
                    "prompt": "Device status shows: Update installed: yes. Restart required: yes, pending 3 days. What is the most useful first thing to tell the user?",
                    "context": "This is a straightforward evidence read.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "The update installed but needs a restart to finish applying -- restarting will likely resolve the symptom"},
                        {"id": "b", "label": "The update completely failed"},
                        {"id": "c", "label": "The device needs to be reimaged"},
                        {"id": "d", "label": "Restart requirements are unrelated to update behavior"},
                    ],
                    "correct": ["a"],
                    "explanation": "A completed install with a long-pending restart is a direct, simple explanation for lingering symptoms -- restart first.",
                },
                {
                    "id": "read-deferral",
                    "prompt": "Device status shows: Update policy: deferred 14 days (organizational policy). Current OS build: one cycle behind latest. Is this a problem?",
                    "context": "The organization intentionally staggers updates.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "No -- this is expected behavior under a deliberate deferral policy, not neglect or a fault"},
                        {"id": "b", "label": "Yes -- any device behind the latest build is automatically broken"},
                        {"id": "c", "label": "Deferral policies don't actually exist"},
                        {"id": "d", "label": "This always means the device is unmanaged"},
                    ],
                    "correct": ["a"],
                    "explanation": "A managed deferral window is intentional -- a device lagging behind within its policy window is expected, not a problem to fix.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "Choose the Right Device Action",
            "lab_type": "structured_endpoint",
            "description": "Given a support request, choose the correctly-scoped device action and justify the risk involved.",
            "estimated_minutes": 20,
            "questions": [
                {
                    "id": "just-force-checkin",
                    "prompt": "A newly-assigned policy should have reached a device an hour ago. The user wants to know if it's stuck. What is the appropriate first action?",
                    "context": "There is no evidence yet of anything actually wrong.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Sync -- it forces a check-in with no destructive risk, and is the proportionate first step"},
                        {"id": "b", "label": "Wipe the device to force a clean policy pull"},
                        {"id": "c", "label": "Retire the device"},
                        {"id": "d", "label": "Delete the device record"},
                    ],
                    "correct": ["a"],
                    "explanation": "Sync is the lowest-risk action that directly addresses 'has this device checked in and gotten current policy yet' -- always the proportionate first move.",
                },
                {
                    "id": "repurpose-not-wipe",
                    "prompt": "A working laptop is being repurposed for a different department and needs OEM bloat and old settings cleared, but should stay enrolled in Intune under the new profile. What action fits?",
                    "context": "The device is not leaving the organization, just changing roles.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Fresh Start, after reviewing the user-data option and expected re-enrollment behavior -- it removes OEM apps/settings without treating the device as permanently retired"},
                        {"id": "b", "label": "Wipe -- fully unenrolls the device, which isn't appropriate since it's staying in service"},
                        {"id": "c", "label": "Delete the device record"},
                        {"id": "d", "label": "Sync -- does nothing destructive so it won't clear anything"},
                    ],
                    "correct": ["a"],
                    "explanation": "Fresh Start is designed to remove OEM apps/settings, but its data and MDM outcome depends on the selected option. Verify those choices instead of assuming enrollment is always retained.",
                },
                {
                    "id": "authorization-before-destructive",
                    "prompt": "A user asks you to Wipe their laptop right now because 'it's acting weird.' What must happen before you take that action?",
                    "context": "Wipe is the most destructive action on the risk ladder.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Confirm this is actually the appropriate, authorized action for the situation -- a vague 'acting weird' complaint does not justify the most destructive available action without further investigation and authorization"},
                        {"id": "b", "label": "Perform the Wipe immediately since the user asked"},
                        {"id": "c", "label": "Skip investigation since Wipe fixes everything"},
                        {"id": "d", "label": "Authorization is never required for device actions"},
                    ],
                    "correct": ["a"],
                    "explanation": "The most destructive action requires real justification and authorization, not just a user's request -- matching the module's core safety principle.",
                },
            ],
        },
    ],
    34: [
        {
            "role": "practice",
            "title": "Walk the Onboarding Checklist",
            "lab_type": "structured_endpoint",
            "description": "Given a new-hire request with the AD account already created, work through the remaining device/M365 onboarding steps in order.",
            "estimated_minutes": 15,
            "questions": [
                {
                    "id": "next-step-after-account",
                    "prompt": "A new hire's AD account and license are confirmed. What is the next step in the onboarding checklist?",
                    "context": "This is a guided walkthrough -- follow the checklist order from the lesson.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Confirm/assign the specific device this person will use"},
                        {"id": "b", "label": "Immediately reset the device"},
                        {"id": "c", "label": "Skip straight to access verification with no device involved"},
                        {"id": "d", "label": "Offboard a different employee first"},
                    ],
                    "correct": ["a"],
                    "explanation": "Device assignment is the step that follows account/license confirmation, before enrollment can even begin.",
                },
                {
                    "id": "verify-before-closing",
                    "prompt": "The device is enrolled, and required apps/policies show landed. What must still happen before the onboarding ticket is complete?",
                    "context": "The checklist has more steps after technical setup.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Confirm MFA registration and verify the new hire can actually access what they need, then document what was done"},
                        {"id": "b", "label": "Nothing further -- technical setup completing is sufficient"},
                        {"id": "c", "label": "Immediately begin offboarding preparation"},
                        {"id": "d", "label": "Delete the device record"},
                    ],
                    "correct": ["a"],
                    "explanation": "MFA registration and access verification, plus documentation, are the closing steps -- technical setup alone doesn't confirm the person can actually work.",
                },
            ],
        },
        {
            "role": "troubleshoot",
            "title": "Lost Phone: Retire or Wipe",
            "lab_type": "structured_endpoint",
            "description": "A mobile device is reported lost. Decide between Retire and Wipe based on ownership and risk, and justify the choice.",
            "estimated_minutes": 15,
            "questions": [
                {
                    "id": "byod-lost-phone",
                    "prompt": "An employee's PERSONAL phone, enrolled as BYOD with a work profile, is reported lost. What is the appropriate action?",
                    "context": "The phone contains the employee's personal photos, apps, and accounts alongside the work profile.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "Retire -- removes only the managed work data/profile, leaving the employee's personal data on the device untouched"},
                        {"id": "b", "label": "Wipe -- resets the entire device including all personal data"},
                        {"id": "c", "label": "Take no action since it's a personal device"},
                        {"id": "d", "label": "There is no difference between Retire and Wipe for this case"},
                    ],
                    "correct": ["a"],
                    "explanation": "Retire is the correct default for a lost BYOD device -- it protects corporate data without destroying the owner's personal data.",
                },
                {
                    "id": "corporate-owned-security-critical",
                    "prompt": "A CORPORATE-OWNED phone containing sensitive client data is reported stolen, not just lost, with signs of active tampering. What changes about the appropriate action?",
                    "context": "This is a security-critical situation, not a routine misplaced-device report.",
                    "type": "single_choice",
                    "options": [
                        {"id": "a", "label": "A full Wipe is now appropriate given the corporate ownership and the active security risk, following escalation/authorization procedure for a security-critical event"},
                        {"id": "b", "label": "Retire is still sufficient regardless of the theft/tampering signals"},
                        {"id": "c", "label": "No action should be taken until the device is physically recovered"},
                        {"id": "d", "label": "Ownership and risk level never affect which action is appropriate"},
                    ],
                    "correct": ["a"],
                    "explanation": "Corporate ownership plus active compromise risk changes the calculus -- Wipe is appropriate here, unlike the BYOD lost-phone case above. Recognizing when the situation escalates is the actual skill.",
                },
            ],
        },
    ],
}


def _endpoint_panel(panel_id: str, label: str, *fields: tuple[str, str]) -> dict:
    return {
        "id": panel_id,
        "label": label,
        "fields": [{"label": field_label, "value": value} for field_label, value in fields],
    }


def _endpoint_workbench(
    role: str,
    brief: str,
    panels: list[dict],
    verification_fields: list[tuple[str, str]],
    guidance: str | None = None,
    required_inspections: list[str] | None = None,
) -> dict:
    workbench = {
        "guidance_level": role,
        "brief": brief,
        "panels": panels,
        "required_inspections": required_inspections or [panel["id"] for panel in panels],
        "verification": {
            "label": "Simulated device state after action",
            "description": "This is deterministic training evidence, not a claim that a real device changed.",
            "fields": [
                {"label": field_label, "value": value}
                for field_label, value in verification_fields
            ],
        },
        "documentation_required": True,
    }
    if guidance:
        workbench["guidance"] = guidance
    return workbench


# One deliberately small evidence-workbench schema serves all endpoint guided
# labs. It is presentation data for deterministic training cases, not a device
# model, Intune API, or alternate grading engine. Answer keys remain solely in
# each lab's server-side question definitions.
_INTUNE_ENDPOINT_WORKBENCHES = {
    "Read a Device Record": _endpoint_workbench(
        "practice",
        "Dana's managed laptop is healthy. Read the record and judge what each field actually proves.",
        [
            _endpoint_panel("device", "Device", ("Hostname", "NEX-LT-1042"), ("Serial", "NX7-DANA-1042"), ("Owner", "Corporate"), ("Primary user", "Dana Ruiz"), ("OS", "Windows 11 Enterprise")),
            _endpoint_panel("identity", "Identity & management", ("Join type", "Microsoft Entra joined"), ("Management state", "Managed"), ("Enrollment", "Intune MDM")),
            _endpoint_panel("health", "Health", ("Compliance", "Compliant"), ("Last check-in", "11 minutes ago")),
        ],
        [("Check-in", "Current"), ("Compliance", "Still compliant after refresh")],
        "Open Device, then compare Identity & management with Health. Do not infer more than the fields prove.",
    ),
    "Diagnose Join, Management & Ownership": _endpoint_workbench(
        "troubleshoot",
        "Jordan can sign in to Windows, but the laptop never receives company policy.",
        [
            _endpoint_panel("device", "Device", ("Hostname", "JORDAN-BYOD"), ("Owner", "Personal"), ("Asset record", "No corporate asset match")),
            _endpoint_panel("identity", "Identity", ("Join type", "Microsoft Entra registered"), ("Primary user", "Jordan Lee")),
            _endpoint_panel("management", "Management", ("Management state", "Unmanaged"), ("MDM enrollment", "No record"), ("Last Intune check-in", "Never")),
        ],
        [("Next evidence", "Confirm intended BYOD enrollment policy"), ("Safety", "Do not promise corporate policy until enrollment is confirmed")],
    ),
    "Read Enrollment Evidence": _endpoint_workbench(
        "practice",
        "Compare two healthy Windows 11 devices that reached management through different enrollment paths.",
        [
            _endpoint_panel("device-a", "Device A", ("Join", "Microsoft Entra joined"), ("Enrollment", "Automatic MDM enrollment"), ("Joined / enrolled", "09:14 / 09:14")),
            _endpoint_panel("device-b", "Device B", ("Enrollment", "Windows Autopilot"), ("Deployment profile", "Sales-Onboarding"), ("Pre-provisioned", "Yes")),
            _endpoint_panel("assignment", "Assignment", ("Device A profile", "None"), ("Device B profile", "Sales-Onboarding")),
        ],
        [("Device A", "Managed after user-driven join"), ("Device B", "Managed through its assigned Autopilot deployment profile")],
        "Open both device records and compare the Enrollment and Deployment profile fields.",
    ),
    "Entra Joined But Not Intune Managed": _endpoint_workbench(
        "troubleshoot",
        "A Windows 11 laptop joined Microsoft Entra ID three days ago, but company applications never arrived.",
        [
            _endpoint_panel("identity", "Identity", ("Join type", "Microsoft Entra joined"), ("Join date", "3 days ago"), ("User license", "Intune enabled")),
            _endpoint_panel("enrollment", "Enrollment", ("Intune record", "None"), ("Automatic enrollment scope", "User included"), ("Enrollment event", "Sign-in trigger did not complete")),
            _endpoint_panel("comparison", "Comparison device", ("Same user", "Enrolled successfully last month"), ("Tenant / license", "Same")),
        ],
        [("Simulated retry", "Enrollment sign-in completed"), ("Management state", "Managed"), ("Next check", "Confirm policy and app delivery")],
    ),
    "Autopilot Deployment Stuck": _endpoint_workbench(
        "troubleshoot",
        "A new Windows 11 laptop stalls during out-of-box provisioning.",
        [
            _endpoint_panel("deployment", "Deployment", ("Microsoft Entra join", "Complete"), ("Intune enrollment", "Complete"), ("Required apps", "2 of 5 installed; no progress for 40 minutes")),
            _endpoint_panel("applications", "Applications", ("Finance Client", "Installing"), ("Detection", "No result"), ("Content download", "Timed out")),
            _endpoint_panel("profile", "Profile", ("Deployment type", "Autopilot Device Preparation"), ("Status reporting", "Near real time"), ("Assigned group", "Finance-NewDevices")),
        ],
        [("App content retry", "Download resumed"), ("Required apps", "5 of 5 installed"), ("Provisioning", "Ready to continue")],
    ),
    "Read Profile Status Evidence": _endpoint_workbench(
        "practice",
        "Two configuration settings did not report Succeeded. Decide which one is a fault and which is expected.",
        [
            _endpoint_panel("profile-a", "Profile A", ("Profile", "Windows Security Baseline"), ("Setting", "Firewall enabled"), ("Status", "Conflict"), ("Detail", "Configured differently by another profile")),
            _endpoint_panel("profile-b", "Profile B", ("Profile", "Windows Enterprise Kiosk"), ("Device edition", "Windows 11 Pro"), ("Status", "Not applicable")),
            _endpoint_panel("assignment", "Assignments", ("Profile A", "All corporate Windows devices"), ("Profile B", "Kiosk pilot")),
        ],
        [("Conflict", "Escalate policy overlap for correction"), ("Not applicable", "Document as expected for this edition")],
        "Compare status, detail, platform, and assignment. Conflict and Not applicable do not mean the same thing.",
    ),
    "The App That Says It Failed": _endpoint_workbench(
        "troubleshoot",
        "A user can launch the assigned finance application, but Intune reports the deployment as Failed.",
        [
            _endpoint_panel("applications", "Applications", ("App", "Finance Desktop"), ("Assignment", "Required / Finance Devices"), ("Install command", "Exit code 0"), ("Install state", "Failed")),
            _endpoint_panel("detection", "Detection", ("Expected file", "C:\\Program Files\\Finance\\finance.exe"), ("Observed file", "C:\\Program Files\\Finance Desktop\\finance.exe"), ("Detection result", "Not detected")),
            _endpoint_panel("device", "Device", ("User launch test", "Application opens"), ("Last check-in", "8 minutes ago")),
        ],
        [("Detection rule", "Corrected path evaluated"), ("Install state", "Installed"), ("User launch", "Successful")],
    ),
    "Blocked and Stuck: Compliance Meets a Pending Profile": _endpoint_workbench(
        "troubleshoot",
        "A user can sign in to Windows but SharePoint access is blocked. A Wi-Fi profile is also pending.",
        [
            _endpoint_panel("access", "Access", ("Resource", "SharePoint"), ("Conditional Access", "Blocked"), ("Grant control", "Require compliant device")),
            _endpoint_panel("compliance", "Compliance", ("Overall", "Noncompliant"), ("Reason", "BitLocker required"), ("Last evaluation", "6 minutes ago")),
            _endpoint_panel("policies", "Policies", ("Wi-Fi profile", "Pending"), ("Security baseline", "Succeeded")),
        ],
        [("BitLocker", "Enabled in simulation"), ("Compliance after sync", "Compliant"), ("Conditional Access evaluation", "Grant requirements satisfied")],
    ),
    "Diagnose the Multi-Signal Ticket": _endpoint_workbench(
        "prove",
        "Finance reports that TimeTrack was assigned yesterday but is unavailable, and this device is blocked from SharePoint. Resolve the evidence case without a walkthrough.",
        [
            _endpoint_panel("device", "Device", ("Hostname", "FIN-LT-2088"), ("Join type", "Microsoft Entra joined"), ("Management", "Intune enrolled")),
            _endpoint_panel("applications", "Applications", ("TimeTrack assignment", "Not targeted for Finance-Pilot"), ("Install state", "No install attempted"), ("Detection", "No result")),
            _endpoint_panel("compliance", "Compliance", ("Overall", "Noncompliant"), ("Reason", "BitLocker required")),
            _endpoint_panel("access", "Access", ("SharePoint", "Blocked"), ("Conditional Access", "Require compliant device")),
            _endpoint_panel("policies", "Policies", ("Wallpaper profile", "Succeeded"), ("Relevance", "No reported wallpaper symptom")),
        ],
        [("App targeting", "Finance-Pilot assignment corrected"), ("BitLocker", "Enabled and escrow confirmed"), ("Compliance", "Compliant after sync"), ("SharePoint", "Grant requirements satisfied")],
        required_inspections=["device", "applications", "compliance", "access"],
    ),
    "Read Update and Driver Evidence": _endpoint_workbench(
        "practice",
        "A Windows 11 laptop behaves differently after an update window. Read update, restart, and driver evidence before acting.",
        [
            _endpoint_panel("updates", "Updates", ("Quality update", "Installed"), ("Restart required", "Yes — pending 3 days"), ("Deferral policy", "14 days")),
            _endpoint_panel("device", "Device", ("Current build", "One approved cycle behind latest"), ("Last restart", "17 days ago")),
            _endpoint_panel("drivers", "Drivers", ("Display driver", "Healthy"), ("Device Manager errors", "None")),
        ],
        [("Simulated restart", "Completed"), ("Restart required", "No"), ("Update policy", "Still within approved deferral")],
        "Open Updates first, then compare restart age and driver health. Start with the least disruptive explanation.",
    ),
    "Choose the Right Device Action": _endpoint_workbench(
        "troubleshoot",
        "A managed laptop has a recently assigned policy and a vague request for a destructive reset.",
        [
            _endpoint_panel("device", "Device", ("Hostname", "OPS-LT-4402"), ("Owner", "Corporate"), ("Management", "Managed"), ("Last check-in", "2 hours ago")),
            _endpoint_panel("policies", "Policies", ("New profile", "Assigned 1 hour ago"), ("Evaluation", "Pending next check-in")),
            _endpoint_panel("request", "Request & authorization", ("User request", "Wipe it; it is acting weird"), ("Destructive action approval", "Not present"), ("Device disposition", "Staying in service")),
        ],
        [("Safe first action", "Sync requested"), ("Policy evaluation", "Succeeded"), ("Destructive action", "Not performed")],
    ),
    "Walk the Onboarding Checklist": _endpoint_workbench(
        "practice",
        "A new hire starts Monday. The account and license exist; complete the remaining endpoint evidence trail.",
        [
            _endpoint_panel("identity", "Identity", ("User", "Priya Shah"), ("Account", "Enabled"), ("License", "Assigned"), ("MFA", "Registration pending")),
            _endpoint_panel("device", "Device", ("Assigned asset", "None"), ("Enrollment", "Not started")),
            _endpoint_panel("readiness", "Readiness", ("Required apps", "Not evaluated"), ("Policies", "Not evaluated"), ("Access test", "Not performed")),
        ],
        [("Assigned device", "NEX-LT-5120"), ("Enrollment / apps / policies", "Complete"), ("MFA and access test", "Verified with user")],
        "Follow the evidence gap: identity exists, but a device must be assigned before enrollment, delivery, and user verification.",
    ),
    "Lost Phone: Retire or Wipe": _endpoint_workbench(
        "troubleshoot",
        "A phone is reported missing. Decide the least destructive safe action from ownership, enrollment, and risk evidence.",
        [
            _endpoint_panel("device", "Device", ("Platform", "Android"), ("Ownership", "Personal / BYOD"), ("Enrollment", "Personally owned work profile")),
            _endpoint_panel("risk", "Risk & report", ("Status", "Lost"), ("Active tampering", "No evidence"), ("Corporate data", "Work profile only")),
            _endpoint_panel("actions", "Action impact", ("Retire", "Remove managed work data/profile"), ("Wipe", "Factory reset; personal data at risk"), ("Authorization", "Routine lost-BYOD procedure approved")),
        ],
        [("Simulated action", "Retire command accepted"), ("Managed work profile", "Removal requested"), ("Personal side", "Not targeted")],
    ),
}

# The two live, server-graded endpoint-management tickets. deviceId/contactId
# values here must exactly match the device_id/requester_contact_id/ticket_id
# arguments passed to _device_process() in service_desk_objectives.py.
_INTUNE_SERVICE_DESK_TICKETS = json.loads(r'''[
{
  "id": "INC3001",
  "stableKey": "bitlocker-recovery",
  "title": "BitLocker recovery key requested after a firmware update",
  "category": "hardware",
  "priority": "high",
  "status": "open",
  "assignedTo": "you",
  "escalated": false,
  "createdAt": "2026-08-12T07:40:00.000Z",
  "requester": {
    "name": "Morgan Ellis",
    "department": "Finance Operations",
    "email": "morgan.ellis@nexus.example",
    "location": "North Campus - Level 3",
    "contact": "Employee support portal"
  },
  "device": {
    "assetTag": "NX-2214",
    "deviceName": "NEX-LT-2214",
    "kind": "laptop",
    "operatingSystem": "Windows 11 Enterprise",
    "state": "attention"
  },
  "description": {
    "issue": "My laptop rebooted after a firmware update overnight and now it's asking for a BitLocker recovery key. I need access right now for month-end close.",
    "businessImpact": "Morgan cannot reach the month-end reconciliation workbook until the device unlocks.",
    "reportedByLine": "Submitted through the employee support portal immediately after the recovery prompt appeared.",
    "troubleshooting": [
      "Confirmed the recovery prompt appears on every boot attempt.",
      "The firmware update was pushed by IT overnight per the standard maintenance window.",
      "Has not attempted to enter any recovery key yet."
    ]
  },
  "sla": {"target": "Respond within 1 hour", "dueAt": "2026-08-12T08:40:00.000Z"},
  "hints": [
    "Inspect the device record before anything else -- confirm this is genuinely NEX-LT-2214, not a similar asset tag.",
    "Verify Morgan's identity through the approved process before touching the recovery key.",
    "Record why the recovery prompt appeared (the overnight firmware update) as the diagnosis before releasing the key.",
    "After providing the key through the approved channel, confirm the device actually boots successfully before closing."
  ],
  "notes": [],
  "activity": [
    {"id": "INC3001-created", "label": "Ticket created", "timestamp": "2026-08-12T07:40:00.000Z", "detail": "Created from the employee support portal.", "tone": "warning"},
    {"id": "INC3001-assigned", "label": "Assigned to you", "timestamp": "2026-08-12T07:43:00.000Z", "detail": "Endpoint Management routed this case to your shift.", "tone": "info"}
  ],
  "suggestedTools": ["device-management", "company-chat", "documentation"],
  "objective_catalog_version": "process-v3"
},
{
  "id": "INC3002",
  "stableKey": "offboarding-device-reassignment",
  "title": "Returned laptop from a departed employee needs reassignment",
  "category": "access",
  "priority": "medium",
  "status": "open",
  "assignedTo": "you",
  "escalated": false,
  "createdAt": "2026-08-13T10:15:00.000Z",
  "requester": {
    "name": "Adebayo Coker",
    "department": "Human Resources",
    "email": "adebayo.coker@nexus.example",
    "location": "Central Office - HR",
    "contact": "Employee support portal"
  },
  "device": {
    "assetTag": "NX-3390",
    "deviceName": "NEX-LT-3390",
    "kind": "laptop",
    "operatingSystem": "Windows 11 Enterprise",
    "state": "active"
  },
  "description": {
    "issue": "A former employee's laptop was returned to the office this morning. We have a new hire starting Monday who needs a device -- can this one be prepared for them?",
    "businessImpact": "The incoming employee has no assigned device for their start date if this laptop isn't ready in time.",
    "reportedByLine": "Submitted by HR after physically receiving the returned device at the front desk.",
    "troubleshooting": [
      "Confirmed the device physically arrived at the office today.",
      "The employment termination was processed in the HR system three days ago.",
      "The offboarding record confirms sign-in was blocked and active sessions were revoked before the device handoff.",
      "A similar laptop, NX-3391, remains checked out to a current employee and is not part of this request."
    ]
  },
  "sla": {"target": "Respond within 1 business day", "dueAt": "2026-08-14T10:15:00.000Z"},
  "hints": [
    "Inspect the device record and confirm it's genuinely NEX-LT-3390 -- a similar asset tag (NX-3391) belongs to a different, still-active employee and is not part of this request.",
    "Verify the offboarding/termination authorization with HR before taking any action on the device.",
    "Record that authorization, access revocation, and corporate-data reset handling are all confirmed before resetting anything.",
    "Confirm the device is genuinely ready for a new assignee before closing -- don't hand it off unresolved."
  ],
  "notes": [],
  "activity": [
    {"id": "INC3002-created", "label": "Ticket created", "timestamp": "2026-08-13T10:15:00.000Z", "detail": "Created from the employee support portal."},
    {"id": "INC3002-assigned", "label": "Assigned to you", "timestamp": "2026-08-13T10:18:00.000Z", "detail": "Endpoint Management routed this case to your shift.", "tone": "info"}
  ],
  "suggestedTools": ["device-management", "company-chat", "documentation"],
  "objective_catalog_version": "process-v3"
}
]''')


def sync_intune_endpoint_management(db: Session) -> dict:
    """Idempotently build the Phase 4B.2 Intune & Windows 11 endpoint
    management content: new weeks 30-34 inside the existing
    stage.microsoft_workplace Stage, and the System B reconciliation
    documented in docs/INTUNE_ENDPOINT_MANAGEMENT_CURRICULUM.md.

    Safe to call whether or not it has already run. Never renumbers an
    existing week_number; only shifts TrainingWeek.display_order for the 12
    rows in _INTUNE_DISPLAY_ORDER_SHIFT. Unlike Phase 4B.1, nothing existing
    is moved/relocated -- every row this function creates is new.
    """
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeek.__tablename__):
        return {"skipped": True, "reason": "migration_not_applied"}
    if db.query(TrainingWeek).filter(TrainingWeek.week_number == 30).first():
        return {"skipped": True, "reason": "already_applied"}
    # Same base_curriculum_seeded guard as sync_microsoft_workplace_foundations,
    # for the same reason: called both from migration 0058's upgrade() and
    # again from seed_curriculum.py, and must defer to the later call on a
    # truly fresh database so sync_initial_training_activities isn't tricked
    # into skipping the entire base curriculum.
    base_curriculum_seeded = (
        db.query(TrainingWeekActivity.id)
        .join(TrainingWeek, TrainingWeek.id == TrainingWeekActivity.training_week_id)
        .filter(TrainingWeek.week_number == 0)
        .first()
    )
    if not base_curriculum_seeded:
        return {"skipped": True, "reason": "base_curriculum_not_seeded"}
    # Also defer until Phase 4B.1's weeks 25-29 exist -- this function shifts
    # display_order for weeks currently sitting after them (18-29), and must
    # run after sync_microsoft_workplace_foundations, not before it.
    if not db.query(TrainingWeek).filter(TrainingWeek.week_number == 25).first():
        return {"skipped": True, "reason": "microsoft_workplace_not_seeded"}

    result = {"skipped": False, "weeks_created": 0, "weeks_shifted": 0, "modules_created": 0,
              "lessons_created": 0, "quizzes_created": 0, "questions_created": 0,
              "labs_created": 0, "tickets_created": 0,
              "activities_created": 0, "gates_updated": 0}

    # 1. Shift display_order for the 12 existing weeks that must move to make
    # room -- week_number is never touched.
    existing_weeks = {
        row.week_number: row
        for row in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_(_INTUNE_DISPLAY_ORDER_SHIFT)).all()
    }
    for week_number, new_order in _INTUNE_DISPLAY_ORDER_SHIFT.items():
        week = existing_weeks.get(week_number)
        if week is not None and week.display_order != new_order:
            week.display_order = new_order
            result["weeks_shifted"] += 1
    db.flush()

    # 2. Create the 5 new TrainingWeek rows.
    new_weeks: dict[int, TrainingWeek] = {}
    for week_number, spec in _INTUNE_NEW_WEEKS.items():
        week = TrainingWeek(
            week_number=week_number,
            display_order=spec["display_order"],
            title=spec["title"],
            description=spec["description"],
            learning_goals=spec["learning_goals"],
            is_active=True,
            requires_previous_week=True,
        )
        db.add(week)
        new_weeks[week_number] = week
        result["weeks_created"] += 1
    db.flush()

    # 3. Create the 5 legacy Module rows (MOD-030..034) for System B.
    legacy_modules: dict[int, Module] = {}
    for week_number, (code, title) in _INTUNE_LEGACY_MODULES.items():
        module = db.query(Module).filter_by(code=code).first()
        if module is None:
            module = Module(
                code=code,
                title=title,
                description=_INTUNE_NEW_WEEKS[week_number]["description"],
                module_order=week_number + 1,
                difficulty_band=3,
                active=True,
            )
            db.add(module)
            result["modules_created"] += 1
        legacy_modules[week_number] = module
    db.flush()

    # 4. New Lesson rows, several per week.
    lessons_by_week: dict[int, list[Lesson]] = {}
    for week_number, specs in _INTUNE_LESSONS.items():
        lessons_by_week[week_number] = []
        for order, spec in enumerate(specs, start=1):
            existing_lesson = (
                db.query(Lesson)
                .filter_by(module_id=legacy_modules[week_number].id, title=spec["title"])
                .first()
            )
            if existing_lesson is not None:
                lessons_by_week[week_number].append(existing_lesson)
                continue
            lesson = Lesson(
                module_id=legacy_modules[week_number].id,
                title=spec["title"],
                summary=spec["summary"],
                lesson_order=order,
                outcomes=spec["outcomes"],
                estimated_minutes=12,
                status="published",
            )
            db.add(lesson)
            lessons_by_week[week_number].append(lesson)
            result["lessons_created"] += 1
    db.flush()

    # 5. New Quiz + Question rows.
    quizzes: dict[int, Quiz] = {}
    for week_number, spec in _INTUNE_QUIZZES.items():
        quiz = Quiz(
            title=spec["title"],
            week_number=week_number,
            domain_id="4.0",
            status="published",
            quiz_purpose=spec.get("quiz_purpose", "required"),
            is_required=True,
            show_in_weekly_checklist=True,
            show_in_practice_library=True,
            editorial_status="validated",
            question_count=len(spec["questions"]),
            answer_keys_validated=True,
            explanations_complete=True,
            is_active=True,
        )
        db.add(quiz)
        db.flush()
        quizzes[week_number] = quiz
        result["quizzes_created"] += 1
        for index, question in enumerate(spec["questions"], start=1):
            db.add(
                Question(
                    quiz_id=quiz.id,
                    question_text=question["question_text"],
                    option_a=question["option_a"],
                    option_b=question["option_b"],
                    option_c=question["option_c"],
                    option_d=question["option_d"],
                    correct_answer=question["correct_answer"],
                    explanation=question["explanation"],
                    difficulty=2,
                    seed_key=f"intune-week{week_number}-q{index}",
                )
            )
            result["questions_created"] += 1
    db.flush()

    # 6. New LabTemplate rows (guided simulations), several per week.
    labs_by_week: dict[int, list[tuple[LabTemplate, str]]] = {}
    for week_number, specs in _INTUNE_NEW_LABS.items():
        labs_by_week[week_number] = []
        for spec in specs:
            existing_lab = db.query(LabTemplate).filter_by(title=spec["title"]).first()
            if existing_lab is not None:
                labs_by_week[week_number].append((existing_lab, spec["role"]))
                continue
            lab = LabTemplate(
                title=spec["title"],
                description=spec["description"],
                lab_type=spec["lab_type"],
                week_number=week_number,
                difficulty=2,
                estimated_minutes=spec["estimated_minutes"],
                is_published=True,
                environment_requirements={},
                setup_instructions="Inspect the available evidence, decide on a safe response, verify the simulated outcome, and write a concise support note.",
                success_criteria={
                    "questions": spec["questions"],
                    "endpoint_workbench": _INTUNE_ENDPOINT_WORKBENCHES[spec["title"]],
                },
                required_evidence={},
                hints={},
            )
            db.add(lab)
            db.flush()
            labs_by_week[week_number].append((lab, spec["role"]))
            result["labs_created"] += 1

    # 7. Service Desk scenarios (live, server-graded tickets). Objectives
    # live in app.services.service_desk_objectives.SCENARIO_OBJECTIVES,
    # keyed by these same stable_key values.
    scenarios: dict[str, ServiceDeskScenario] = {}
    for ticket in _INTUNE_SERVICE_DESK_TICKETS:
        stable_key = ticket["stableKey"]
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=stable_key).first()
        if scenario is None:
            scenario = ServiceDeskScenario(
                stable_key=stable_key,
                title=ticket["title"],
                description=f'{ticket["description"]["issue"]} {ticket["description"]["businessImpact"]}',
                category=ticket["category"],
                difficulty=3,
                status="active",
            )
            db.add(scenario)
            db.flush()
            result["tickets_created"] += 1
        scenarios[stable_key] = scenario
        definition_hash = hashlib.sha256(json.dumps(ticket, sort_keys=True).encode("utf-8")).hexdigest()
        version_exists = (
            db.query(ServiceDeskScenarioVersion)
            .filter_by(scenario_id=scenario.id, definition_hash=definition_hash)
            .first()
        )
        if version_exists is None:
            next_version = (
                db.query(ServiceDeskScenarioVersion.version_number)
                .filter_by(scenario_id=scenario.id)
                .order_by(ServiceDeskScenarioVersion.version_number.desc())
                .first()
            )
            db.add(
                ServiceDeskScenarioVersion(
                    scenario_id=scenario.id,
                    version_number=(next_version[0] if next_version else 0) + 1,
                    definition_json=ticket,
                    definition_hash=definition_hash,
                    validation_status="valid",
                    status="published",
                    published_at=datetime.now(timezone.utc),
                    published_by="seed",
                )
            )
    db.flush()

    # 8. Wire everything into TrainingWeekActivity. Guided labs get their
    # learning_role explicitly set from spec["role"] -- practice labs use
    # the guided_lab default ("practice") so no override is written, but
    # troubleshoot/prove labs are explicitly overridden. This is
    # deliberately not "everything is Troubleshoot" (see Step 10 of the
    # Phase 4B.2 brief).
    def add_activity(week_number, activity_type, content_ref, is_required, minutes=None, metadata=None):
        week = new_weeks.get(week_number) or existing_weeks.get(week_number)
        if week is None:
            return
        order = (
            db.query(func.coalesce(func.max(TrainingWeekActivity.display_order), 0))
            .filter_by(training_week_id=week.id)
            .scalar()
            or 0
        ) + 1
        db.add(
            TrainingWeekActivity(
                training_week_id=week.id,
                stable_id=f"week-{week_number}-{activity_type}-{content_ref}",
                activity_type=activity_type,
                content_ref=str(content_ref),
                display_order=order,
                is_required=is_required,
                estimated_minutes=minutes,
                prerequisite_mode="soft",
                metadata_json=metadata or {},
            )
        )
        db.flush()
        result["activities_created"] += 1

    for week_number, week_lessons in lessons_by_week.items():
        for lesson in week_lessons:
            add_activity(week_number, "lesson", lesson.id, True, lesson.estimated_minutes)
    for week_number, quiz in quizzes.items():
        add_activity(week_number, "quiz", quiz.id, True, 15)
    for week_number, week_labs in labs_by_week.items():
        for lab, role in week_labs:
            metadata = {"learning_role": role} if role != "practice" else None
            add_activity(week_number, "guided_lab", lab.id, True, lab.estimated_minutes, metadata)
    add_activity(33, "service_desk_scenario", "bitlocker-recovery", True, 30)
    add_activity(34, "service_desk_scenario", "offboarding-device-reassignment", True, 30)

    # 9. Reconcile System B: extend the seeded PromotionGate rows for the
    # graduating role so required endpoint-management content is not
    # silently skippable. progression_service.MODULE_WEEKS and
    # service_desk_progression.SERVICE_DESK_PACKS are code-level and were
    # already extended directly (see those files).
    final_role = db.query(Role).filter_by(name="Junior Infrastructure Administrator").first()
    if final_role is not None:
        lessons_gate = (
            db.query(PromotionGate)
            .filter_by(role_id=final_role.id, requirement_type="min_completed_lessons")
            .first()
        )
        if lessons_gate is not None:
            codes = list(lessons_gate.requirement_config.get("module_codes", []))
            new_codes = [code for _, (code, _) in _INTUNE_LEGACY_MODULES.items() if code not in codes]
            if new_codes:
                lessons_gate.requirement_config = {
                    **lessons_gate.requirement_config,
                    "module_codes": codes + new_codes,
                }
                result["gates_updated"] += 1

        if not db.query(PromotionGate).filter_by(role_id=final_role.id, requirement_type="required_quiz", requirement_config={"week": 33}).first():
            db.add(
                PromotionGate(
                    role_id=final_role.id,
                    requirement_type="required_quiz",
                    requirement_config={"week": 33},
                )
            )
            result["gates_updated"] += 1

        if not db.query(PromotionGate).filter_by(role_id=final_role.id, requirement_type="min_service_desk_passes", requirement_config={"pack_key": "endpoint-management", "min_passed": 2}).first():
            db.add(
                PromotionGate(
                    role_id=final_role.id,
                    requirement_type="min_service_desk_passes",
                    requirement_config={"pack_key": "endpoint-management", "min_passed": 2},
                )
            )
            result["gates_updated"] += 1

    db.commit()
    return result
