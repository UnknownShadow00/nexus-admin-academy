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
        expected_purpose = "required" if should_be_required else "practice"
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


def _sync_quality_batch(db: Session, specs: dict[int, dict]) -> dict:
    weeks = {
        week.week_number: week
        for week in db.query(TrainingWeek).filter(TrainingWeek.week_number.in_(set(specs))).all()
    }
    if set(weeks) != set(specs):
        return {"updated": 0, "skipped": True, "reason": "weeks_missing"}

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
        required_quiz = str(spec["required_quiz"])
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

    required_quiz_ids = {spec["required_quiz"] for spec in specs.values()}
    for quiz in db.query(Quiz).filter(Quiz.id.in_(quiz_activity_ids)).all():
        should_be_required = quiz.id in required_quiz_ids
        expected_purpose = "required" if should_be_required else "practice"
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
