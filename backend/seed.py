from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from app.config import load_env
from app.database import SessionLocal
from app.models.command_reference import CommandReference
from app.models.capstone import CapstoneTemplate
from app.models.lab import LabTemplate
from app.models.learning import Lesson, Module
from app.models.progression import MethodologyFramework, PromotionGate, Role
from app.models.student import Student
from app.models.service_desk import ServiceDeskAssignment, ServiceDeskScenario, ServiceDeskScenarioVersion
from app.models.ticket import Ticket
from app.services.cli_lab_seed import seed_cli_labs
from app.services.verified_question_corrections import apply_verified_question_corrections
from app.services.service_desk_objectives import PROCESS_CATALOG_VERSION
from seed_phase_a import seed_phase_a
from seed_phase_b import seed_phase_b
from seed_phase_c import seed_phase_c
from seed_phase_d import seed_phase_d
from seed_phase_e import seed_phase_e
from seed_phase_f import seed_phase_f
from seed_phase_g import seed_phase_g
from seed_quiz_organization import rebalance_seed_answer_positions, seed_quiz_organization
from app.services.quiz_editorial_mapping import (
    apply_reviewed_legacy_quiz_approvals,
    apply_safe_optional_quiz_mappings,
)
load_env()

# Service Desk simulator fixtures are mirrored from the pilot app as an audit/reference
# definition. Priority maps to scenario difficulty as: low=1, medium=2, high=3, critical=5.
SERVICE_DESK_TICKET_FIXTURES = json.loads(r'''[{"activity":[{"detail":"Created from the employee support portal.","id":"INC2401-created","label":"Ticket created","timestamp":"2026-07-28T09:42:00.000Z"},{"detail":"Queue routing matched this request to your practice shift.","id":"INC2401-assigned","label":"Assigned to you","timestamp":"2026-07-28T09:49:00.000Z","tone":"info"}],"assignedTo":"you","category":"access","createdAt":"2026-07-28T09:42:00.000Z","description":{"businessImpact":"A month-end reconciliation is paused until the analyst can reach the reporting workspace.","issue":"The finance reporting portal accepts the first authentication step, then returns to the sign-in screen before the dashboard loads.","reportedByLine":"Submitted through the employee support portal after two failed sign-in attempts.","troubleshooting":["Closed and reopened the browser.","Confirmed other internal sites load normally.","Tried a private browsing window with the same result."]},"device":{"assetTag":"NX-4831","deviceName":"FIN-LT-27","kind":"laptop","operatingSystem":"Windows 11 Enterprise","state":"active"},"escalated":false,"hints":["Confirm whether the requester can complete the second authentication prompt on another internal service.","Review the directory record for a locked account or an expired access policy.","Check the knowledge base for the finance portal sign-in loop procedure.","Ask the requester to start a fresh session after the account state is corrected."],"id":"INC2401","notes":[],"priority":"high","requester":{"contact":"Ext. 4318","department":"Finance Operations","email":"avery.brooks@nexus.example","location":"North Campus \u00b7 Level 4","name":"Avery Brooks"},"sla":{"dueAt":"2026-07-28T11:15:00.000Z","target":"Respond within 90 minutes"},"status":"in-progress","suggestedTools":["remote-desktop","directory","documentation","company-chat"],"title":"Finance portal returns to sign-in after verification"},{"activity":[{"detail":"Monitoring generated an incident after repeated disconnects.","id":"INC2402-created","label":"Ticket created","timestamp":"2026-07-28T10:08:00.000Z","tone":"warning"}],"assignedTo":null,"category":"network","createdAt":"2026-07-28T10:08:00.000Z","description":{"businessImpact":"Outbound orders are being recorded on paper, slowing dispatch and increasing re-entry work.","issue":"Handheld scanners at two loading lanes disconnect from the warehouse network every few minutes.","reportedByLine":"Reported by the morning dispatch lead after the issue spread to a second lane.","troubleshooting":["Restarted one handheld scanner.","Moved within range of the nearest access point.","Confirmed wired packing stations remain connected."]},"device":{"assetTag":"NX-7714","deviceName":"SCAN-DK-14","kind":"mobile","operatingSystem":"Android Enterprise 15","state":"attention"},"escalated":false,"hints":["Establish whether every affected scanner is using the same wireless access point.","Inspect network health and recent alerts for the loading dock segment.","Compare the affected device configuration with a scanner that remains connected.","Document the stable connection test before returning scanners to the dispatch team."],"id":"INC2402","notes":[],"priority":"critical","requester":{"contact":"Radio channel 3","department":"Distribution","email":"noah.vance@nexus.example","location":"West Warehouse \u00b7 Loading Dock","name":"Noah Vance"},"sla":{"dueAt":"2026-07-28T10:50:00.000Z","target":"Restore service within 45 minutes"},"status":"open","suggestedTools":["remote-desktop","server-room","asset-management","company-chat"],"title":"Loading dock scanners repeatedly lose their wireless connection"},{"activity":[{"id":"INC2403-created","label":"Ticket created","timestamp":"2026-07-28T09:18:00.000Z"}],"assignedTo":null,"category":"software","createdAt":"2026-07-28T09:18:00.000Z","description":{"businessImpact":"The design review can continue, but annotated exports cannot be shared with the supplier.","issue":"The approved PDF editor closes when a large drawing package is exported with comments included.","reportedByLine":"Submitted from the desktop support shortcut with an application crash report attached.","troubleshooting":["Reopened the drawing package.","Exported a single page successfully.","Restarted the workstation before trying the full package again."]},"device":{"assetTag":"NX-3560","deviceName":"DSN-WS-08","kind":"desktop","operatingSystem":"Windows 11 Enterprise","state":"active"},"escalated":false,"hints":["Reproduce the export with a smaller group of annotated pages.","Review the workstation for available disk space and pending application updates.","Check documentation for known large-file export limitations.","Record the smallest repeatable failure before considering escalation."],"id":"INC2403","notes":[],"priority":"medium","requester":{"contact":"Ext. 2874","department":"Product Design","email":"mina.patel@nexus.example","location":"Studio Annex \u00b7 Bay 6","name":"Mina Patel"},"sla":{"dueAt":"2026-07-28T14:00:00.000Z","target":"Respond within 4 hours"},"status":"open","suggestedTools":["remote-desktop","documentation","asset-management"],"title":"PDF editor closes while exporting annotated drawings"},{"activity":[{"detail":"Email intake converted the request into an incident.","id":"INC2404-created","label":"Ticket created","timestamp":"2026-07-28T08:24:00.000Z"}],"assignedTo":null,"category":"hardware","createdAt":"2026-07-28T08:24:00.000Z","description":{"businessImpact":"Calls can still be answered, but the advisor cannot reliably hear customers.","issue":"A USB headset produces short bursts of static after several minutes in a call.","reportedByLine":"Reported by the customer care floor coordinator on behalf of one advisor.","troubleshooting":["Disconnected and reconnected the USB cable.","Tested a second USB port.","Confirmed the problem occurs in two calling applications."]},"device":{"assetTag":"NX-9052","deviceName":"AUDIO-CC-52","kind":"peripheral","operatingSystem":"USB audio device","state":"attention"},"escalated":false,"hints":["Confirm whether the static follows the headset to another workstation.","Review the asset record for warranty and replacement eligibility.","Compare audio behavior with a known-good headset on the same workstation.","Update the requester after deciding whether the fault follows the accessory or the PC."],"id":"INC2404","notes":[],"priority":"medium","requester":{"contact":"Ext. 1189","department":"Customer Care","email":"elliot.ward@nexus.example","location":"South Campus \u00b7 Level 2","name":"Elliot Ward"},"sla":{"dueAt":"2026-07-28T13:30:00.000Z","target":"Respond within 4 hours"},"status":"pending","suggestedTools":["asset-management","shipping-manager","company-chat"],"title":"USB headset develops static during longer calls"},{"activity":[{"id":"INC2405-created","label":"Ticket created","timestamp":"2026-07-28T07:05:00.000Z"}],"assignedTo":null,"category":"access","createdAt":"2026-07-28T07:05:00.000Z","description":{"businessImpact":"A new coordinator can complete orientation but cannot access the shared scheduling calendar.","issue":"The new starter can sign in to email but the facilities scheduling calendar is not listed.","reportedByLine":"Raised by the facilities team lead during the new starter checklist.","troubleshooting":["Signed out and back in to the calendar application.","Searched for the calendar by its full display name.","Confirmed the user can open their personal calendar."]},"device":{"assetTag":"NX-6128","deviceName":"FAC-LT-12","kind":"laptop","operatingSystem":"Windows 11 Enterprise","state":"active"},"escalated":false,"hints":["Verify the requester identity and the intended facilities team membership.","Compare the directory groups with another coordinator in the same role.","Review the access guide before changing any group membership.","Ask the requester to refresh the calendar list after access synchronizes."],"id":"INC2405","notes":[],"priority":"low","requester":{"contact":"Ext. 5520","department":"Facilities","email":"sloane.rivera@nexus.example","location":"Central Office \u00b7 Level 1","name":"Sloane Rivera"},"sla":{"dueAt":"2026-07-29T09:00:00.000Z","target":"Respond by next business day"},"status":"open","suggestedTools":["remote-desktop","directory","documentation","company-chat"],"title":"New coordinator cannot see the facilities calendar"},{"activity":[{"detail":"The requester selected desktop support in the portal.","id":"INC2406-created","label":"Ticket created","timestamp":"2026-07-28T09:55:00.000Z"}],"assignedTo":null,"category":"network","createdAt":"2026-07-28T09:55:00.000Z","description":{"businessImpact":"The project manager can work locally but cannot join the secure partner workspace.","issue":"The remote access client reaches the gateway, then stops while checking the device profile.","reportedByLine":"Submitted from a home network before a scheduled partner review.","troubleshooting":["Restarted the laptop.","Confirmed normal internet browsing works.","Retried the connection after closing other applications."]},"device":{"assetTag":"NX-2047","deviceName":"PM-LT-41","kind":"laptop","operatingSystem":"macOS 16","state":"active"},"escalated":false,"hints":["Confirm the client version and capture the exact device-check stage.","Review the device asset record for compliance status.","Check current remote access guidance for the reported platform.","Retry after correcting any documented client or compliance mismatch."],"id":"INC2406","notes":[],"priority":"high","requester":{"contact":"Mobile ending 604","department":"Program Delivery","email":"harper.kim@nexus.example","location":"Remote \u00b7 Eastern region","name":"Harper Kim"},"sla":{"dueAt":"2026-07-28T11:40:00.000Z","target":"Respond within 2 hours"},"status":"open","suggestedTools":["remote-desktop","documentation","asset-management"],"title":"Remote access pauses during the device compliance check"},{"activity":[{"detail":"Created from the employee support portal.","id":"INC2407-created","label":"Ticket created","timestamp":"2026-07-28T10:02:00.000Z"}],"assignedTo":null,"category":"network","createdAt":"2026-07-28T10:02:00.000Z","description":{"businessImpact":"Operations cannot open the internal scheduling portal, delaying same-day staffing changes.","issue":"The workstation can reach internet sites and known IP addresses, but internal Nexus hostnames do not load.","reportedByLine":"Submitted after the scheduling portal failed in two browsers.","troubleshooting":["Restarted both browsers.","Confirmed a public website loads.","Restarted the workstation once."]},"device":{"assetTag":"NX-8892","deviceName":"OPS-LT-92","kind":"laptop","operatingSystem":"Windows 11 Enterprise","state":"active"},"escalated":false,"hints":["Separate address connectivity from hostname resolution.","Inspect the adapter DNS configuration.","Use an approved resolver and repeat the original name test."],"id":"INC2407","notes":[],"priority":"high","requester":{"contact":"Ext. 8892","department":"Operations","email":"dana.ortiz@nexus.example","location":"North Campus \u00b7 Operations","name":"Dana Ortiz"},"sla":{"dueAt":"2026-07-28T12:02:00.000Z","target":"Restore service within 2 hours"},"status":"open","suggestedTools":["remote-desktop","documentation"],"title":"Internal sites fail while IP connectivity still works"},{"activity":[{"detail":"Created from the desktop support shortcut.","id":"INC2408-created","label":"Ticket created","timestamp":"2026-07-28T09:48:00.000Z"}],"assignedTo":null,"category":"software","createdAt":"2026-07-28T09:48:00.000Z","description":{"businessImpact":"Human Resources cannot print onboarding packets for the morning orientation.","issue":"Print jobs disappear immediately and no test page reaches the office printer.","reportedByLine":"Reported after the same document printed successfully from another workstation.","troubleshooting":["Confirmed the printer is powered on.","Printed the document from a neighboring workstation.","Reopened the document on the affected computer."]},"device":{"assetTag":"NX-4419","deviceName":"HR-WS-19","kind":"desktop","operatingSystem":"Windows 11 Enterprise","state":"attention"},"escalated":false,"hints":["Reproduce the local symptom before changing the printer.","Inspect the Windows service that queues print jobs.","After restoring the service, send another test page."],"id":"INC2408","notes":[],"priority":"high","requester":{"contact":"Ext. 4419","department":"Human Resources","email":"eli.warren@nexus.example","location":"Central Office \u00b7 Human Resources","name":"Eli Warren"},"sla":{"dueAt":"2026-07-28T11:48:00.000Z","target":"Restore service within 2 hours"},"status":"open","suggestedTools":["remote-desktop","documentation"],"title":"Print jobs disappear on the HR workstation"}]''')
SERVICE_DESK_DIFFICULTY_BY_PRIORITY = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 5,
}


# TB-01: seed.py must NEVER create login-able accounts. The 6 real accounts
# come exclusively from scripts/seed_users.py; the old STUDENTS list here
# shipped guessable demo credentials (admin/admin123...) on every deploy.

ROLES = [
    # TB-02: the six curriculum roles (replaces the old 5-role L1/L2 ladder).
    # Old→new remap for existing StudentRole rows happens in seed_roles_and_gates().
    {"name": "Trainee", "rank_order": 1, "description": "New IT support trainee — Weeks 1–4"},
    {"name": "Support Technician I", "rank_order": 2, "description": "Passed Gate 1 — foundational troubleshooting and ticket writing"},
    {"name": "Support Technician II", "rank_order": 3, "description": "Passed Gate 2 — workplace help desk, security, and client networking"},
    {"name": "Network Support Technician", "rank_order": 4, "description": "Passed Gate 3 — switching, VLANs, and network troubleshooting"},
    {"name": "Junior Systems Technician", "rank_order": 5, "description": "Passed Gate 4 — Windows Server, AD, and PowerShell administration"},
    {"name": "Junior Infrastructure Administrator", "rank_order": 6, "description": "Passed Gate 5 — graduated the integrated capstone"},
]

# Old role names → new role names, used to migrate existing StudentRole data.
ROLE_RENAME_MAP = {
    "L1 Help Desk": "Trainee",
    "L2 Help Desk": "Support Technician II",
    "Junior SysAdmin": "Junior Systems Technician",
    "SysAdmin": "Junior Systems Technician",
    "Network Admin": "Network Support Technician",
}

PROMOTION_GATES = [
    # ---- GATE 1: Trainee → Support Technician I (end of Week 4) ----
    {
        "role": "Support Technician I",
        "requirement_type": "required_quiz",
        "config": {"week": 4},
    },
    {
        "role": "Support Technician I",
        "requirement_type": "min_completed_lessons",
        "config": {"module_codes": ["MOD-000", "MOD-001", "MOD-002", "MOD-003", "MOD-004"]},
    },
    {
        "role": "Support Technician I",
        "requirement_type": "min_mastery_by_domain",
        "config": {"thresholds": {"hardware": 70, "software_troubleshooting": 70}},
    },
    {
        "role": "Support Technician I",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"1": 4, "2": 2}},
    },
    {
        "role": "Support Technician I",
        "requirement_type": "practical_checkpoint",
        "config": {"ticket_title": "Multi-Ticket Simulation 1", "max_hints": 0, "min_score": 7},
    },
    {
        "role": "Support Technician I",
        "requirement_type": "min_cli_labs",
        "config": {"min_completed": 9},
    },
    {
        "role": "Support Technician I",
        "requirement_type": "no_unresolved_flags",
        "config": {},
    },
    # ---- GATE 2: Support Technician I → Support Technician II (end of Week 8) ----
    # Ticket/mastery thresholds per the master doc; checkpoint is Simulation 2.
    {
        "role": "Support Technician II",
        "requirement_type": "required_quiz",
        "config": {"week": 8},
    },
    {
        "role": "Support Technician II",
        "requirement_type": "min_completed_lessons",
        "config": {"module_codes": ["MOD-005", "MOD-006", "MOD-007", "MOD-008"]},
    },
    {
        "role": "Support Technician II",
        "requirement_type": "min_mastery_by_domain",
        "config": {"thresholds": {"software_troubleshooting": 70, "networking": 70, "security": 70}},
    },
    {
        "role": "Support Technician II",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"1": 6, "2": 8, "3": 2}},
    },
    {
        "role": "Support Technician II",
        "requirement_type": "practical_checkpoint",
        "config": {"ticket_title": "Multi-Ticket Simulation 2", "max_hints": 1, "min_score": 7},
    },
    {
        "role": "Support Technician II",
        "requirement_type": "no_unresolved_flags",
        "config": {},
    },
    # ---- GATE 3: Support Technician II → Network Support Technician (end of Week 12) ----
    {
        "role": "Network Support Technician",
        "requirement_type": "required_quiz",
        "config": {"week": 12},
    },
    {
        "role": "Network Support Technician",
        "requirement_type": "min_completed_lessons",
        "config": {"module_codes": ["MOD-009", "MOD-010", "MOD-011", "MOD-012"]},
    },
    {
        "role": "Network Support Technician",
        "requirement_type": "min_mastery_by_domain",
        "config": {"thresholds": {"networking": 75}},
    },
    {
        "role": "Network Support Technician",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"3": 3, "4": 2}},
    },
    {
        "role": "Network Support Technician",
        "requirement_type": "min_cli_labs",
        "config": {"min_completed": 20, "pack_prefix": "dev-sw-"},
    },
    {
        "role": "Network Support Technician",
        "requirement_type": "no_unresolved_flags",
        "config": {},
    },
    # ---- GATE 4: Network Support Technician → Junior Systems Technician (end of Week 17) ----
    {
        "role": "Junior Systems Technician",
        "requirement_type": "required_quiz",
        "config": {"week": 17},
    },
    {
        "role": "Junior Systems Technician",
        "requirement_type": "min_completed_lessons",
        "config": {"module_codes": ["MOD-013", "MOD-014", "MOD-015", "MOD-016", "MOD-017"]},
    },
    {
        "role": "Junior Systems Technician",
        "requirement_type": "min_mastery_by_domain",
        "config": {"thresholds": {"windows_server": 75, "active_directory": 75}},
    },
    {
        "role": "Junior Systems Technician",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"3": 3, "4": 1}},
    },
    {
        "role": "Junior Systems Technician",
        "requirement_type": "no_unresolved_flags",
        "config": {},
    },
    # ---- GATE 5 (GRADUATION): Junior Systems Technician → Junior Infrastructure Administrator (end of Week 24) ----
    {
        "role": "Junior Infrastructure Administrator",
        "requirement_type": "required_quiz",
        "config": {"week": 24},
    },
    {
        "role": "Junior Infrastructure Administrator",
        "requirement_type": "min_completed_lessons",
        "config": {"module_codes": ["MOD-018", "MOD-019", "MOD-020", "MOD-021", "MOD-022", "MOD-023", "MOD-024"]},
    },
    {
        "role": "Junior Infrastructure Administrator",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"3": 3, "4": 3}},
    },
    {
        "role": "Junior Infrastructure Administrator",
        "requirement_type": "practical_checkpoint",
        "config": {"ticket_title": "Multi-Ticket Simulation 3", "max_hints": 1, "min_score": 7},
    },
    {
        "role": "Junior Infrastructure Administrator",
        "requirement_type": "no_unresolved_flags",
        "config": {},
    },
]

ORIENTATION_TITLE = "Welcome to Nexus: Your First Week"
ORIENTATION_SUMMARY = """Nexus is your 25-week practice space (Week 0 through Week 24) for becoming an IT-support technician. You will learn the habits, tools, and communication that help real people when technology gets in their way. You do not need an IT background to begin.

WHAT A WEEK MEANS: each week is a small, guided set of learning and practice. Finish the required items in the order shown, then use optional practice when you want more repetition. You are not expected to know everything before you start.

THE FOUR THINGS YOU WILL SEE:
- A LESSON explains one idea in plain language. You can save optional notes and explicitly mark the lesson complete when you are ready.
- A QUIZ is a short checkpoint. It shows what you understand and what to revisit.
- A LAB is a safe place to try a task with guided steps.
- A SERVICE DESK SCENARIO is a realistic support request. You investigate, fix, verify, and document what you did.

REQUIRED VS OPTIONAL: required items keep your weekly path moving. Optional practice, review, and certification questions are there when you want extra reps; they do not block your next required step.

EVIDENCE AND REMEDIATION: evidence is a screenshot, command output, or note that shows what happened. Remediation means a focused retry or extra practice after a missed checkpoint — it is coaching, not a punishment.

XP AND YOUR ROLE: XP is a running total of completed learning work. Your Role is a promotion level based on demonstrated readiness and specific gates. XP can show momentum; it does not promote you by itself.

HOW GRADING WORKS: Service Desk scenarios evaluate the evidence of your investigation, fix, verification, and notes. A mentor may still review your work afterward, especially when judgment, safety, or workplace communication matters. NEEDS REVISION means your work is not final yet: read the feedback, improve the missing part, and try again.

WHEN YOU NEED HELP: ask your mentor or your cohort's agreed help channel. Include the lesson, quiz, lab, or ticket name and what you already tried. That gives people a useful starting point.

YOUR SIMPLE ROUTINE:
1. Open This Week on Home and choose the first item marked Next up.
2. Read the lesson, mark it complete when you are ready, and complete the required quiz or practice.
3. Come back to Home anytime. Your notes, quiz attempts, and submitted work save to your account, and unfinished work stays in This Week.

GUIDED PRACTICE: mark this orientation lesson complete, take the Ticketing Systems Quiz, then write a one-sentence practice response. You may optionally save notes or upload a harmless sample screenshot. This walkthrough is not graded and does not need mentor review.

WHY THIS MATTERS: good support work is not guessing alone. It is knowing what to do next, recording what happened, asking for help early, and improving one small step at a time."""


MODULE_0 = {
    "code": "MOD-000",
    "title": "Troubleshooting Methodology",
    "description": "Learn systematic IT problem-solving and disciplined incident handling.",
    "difficulty_band": 1,
    "estimated_hours": 4,
    "unlock_threshold": 0,
    "module_order": 0,
    "lessons": [
        {
            "title": ORIENTATION_TITLE,
            "summary": ORIENTATION_SUMMARY,
            "outcomes": [],
            "lesson_order": 1,
            "estimated_minutes": 12,
            "required_notes_template": "Write one sentence: What is the first thing you will do when you are unsure what comes next in Nexus?",
        },
    ],
}

FRAMEWORK_STEPS = {
    "steps": [
        "Identify the problem",
        "Establish a theory of probable cause",
        "Test the theory",
        "Establish a plan of action and implement",
        "Verify functionality and implement preventive measures",
        "Document findings, actions, and outcomes",
    ]
}

TICKETS = [
    {
        "title": "User cannot browse the internet — DNS resolution failing",
        "description": (
            "A user reports they can ping 8.8.8.8 successfully but all website names fail to resolve. "
            "Chrome shows DNS_PROBE_FINISHED_NXDOMAIN. They are on a domain-joined Windows 10 machine."
        ),
        "difficulty": 2,
        "week_number": 1,
        "category": "Networking",
        "domain_id": "2.0",
        "root_cause": "Client NIC is pointing to the wrong DNS server address",
        "root_cause_type": "dns_misconfiguration",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Verify IP and DNS settings", "commands": ["ipconfig /all"], "weight": 0.2},
                {"id": 2, "step": "Test DNS resolution", "commands": ["nslookup google.com"], "weight": 0.3},
                {"id": 3, "step": "Identify incorrect DNS server address", "required_mention": ["dns", "incorrect", "wrong"], "weight": 0.3},
                {"id": 4, "step": "Update DNS settings and re-test", "commands": ["nslookup google.com"], "weight": 0.2},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "ipconfig /all showing DNS values", "validation": {"must_contain_text": ["DNS"]}},
                {"type": "screenshot", "description": "Successful resolution after fix", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Identified DNS issue but skipped verification", "8": "Systematic triage with validation", "10": "Root cause proven, fix applied, re-tested, documented"},
        "model_answer": "Run ipconfig /all to confirm the DNS server IP. Update the NIC settings to the correct DNS server. Run nslookup to verify resolution is restored.",
    },
    {
        "title": "User account locked out — cannot log in to Windows",
        "description": (
            "An employee calls reporting their Windows login fails with 'Your account has been locked'. "
            "They tried their password five times yesterday. You have domain admin access."
        ),
        "difficulty": 1,
        "week_number": 1,
        "category": "Authentication",
        "domain_id": "4.0",
        "root_cause": "Account locked due to repeated failed login attempts",
        "root_cause_type": "account_lockout",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Confirm lockout in Active Directory", "commands": ["Active Directory Users and Computers"], "weight": 0.3},
                {"id": 2, "step": "Check Event Viewer for failed logins", "required_mention": ["event viewer", "4740", "failed"], "weight": 0.4},
                {"id": 3, "step": "Unlock and verify user can log in", "required_mention": ["unlock", "test"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Locked account state in ADUC", "validation": {}},
                {"type": "screenshot", "description": "Successful login after unlock", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Unlocked account, no root-cause investigation", "8": "Checked Event Viewer and unlocked", "10": "Investigated source, resolved, and documented"},
        "model_answer": "Open ADUC, find the user, unlock the account. Check Event Viewer for event 4740 to identify the source. Advise user to reset password if cause was credential theft.",
    },
    {
        "title": "Printer offline — user cannot print from Windows",
        "description": (
            "A user reports that their network printer shows 'Offline' in the Windows print queue. "
            "Other users on the same subnet can print without issue. The user is on Windows 11."
        ),
        "difficulty": 2,
        "week_number": 2,
        "category": "Hardware",
        "domain_id": "1.0",
        "root_cause": "Static IP conflict causing the printer to be unreachable from the affected workstation",
        "root_cause_type": "ip_conflict",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Ping the printer IP from the affected PC", "commands": ["ping <printer_ip>"], "weight": 0.25},
                {"id": 2, "step": "Check the printer port configuration", "required_mention": ["port", "ip", "printer properties"], "weight": 0.35},
                {"id": 3, "step": "Update port IP and set printer online", "required_mention": ["update", "online"], "weight": 0.25},
                {"id": 4, "step": "Print a test page to verify", "required_mention": ["test page", "verify"], "weight": 0.15},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Printer showing offline in queue", "validation": {}},
                {"type": "screenshot", "description": "Successful test page print", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Set online, no root-cause analysis", "8": "Verified IP conflict and fixed port", "10": "Root cause identified, validated, test page confirmed"},
        "model_answer": "Ping the printer IP to test reachability. Open printer properties and check the port IP matches the actual printer IP. Correct if wrong. Set 'Use Printer Online' and print a test page.",
    },
    {
        "title": "Laptop cannot connect to corporate Wi-Fi",
        "description": (
            "A remote employee's laptop fails to connect to the office Wi-Fi SSID 'CorpNet'. "
            "Their Windows 11 machine shows 'Can't connect to this network'. "
            "Other devices connect to CorpNet fine. The network uses WPA2-Enterprise."
        ),
        "difficulty": 3,
        "week_number": 2,
        "category": "Networking",
        "domain_id": "2.0",
        "root_cause": "Corrupted wireless profile preventing authentication",
        "root_cause_type": "wireless_profile_corrupt",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Forget and re-add the wireless network", "required_mention": ["forget", "delete", "remove"], "weight": 0.3},
                {"id": 2, "step": "Check for driver or certificate issues", "required_mention": ["driver", "certificate", "device manager"], "weight": 0.4},
                {"id": 3, "step": "Re-join and verify connectivity", "commands": ["ping"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Error message when connecting", "validation": {}},
                {"type": "screenshot", "description": "Successful Wi-Fi connection after fix", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Forgot network, no verification of cause", "8": "Investigated profile and driver", "10": "Root cause identified, resolved, and connectivity confirmed"},
        "model_answer": "Forget the CorpNet profile via Settings > Network. Re-add the network. If it fails again, check Device Manager for driver issues and verify the certificate used for WPA2-Enterprise is valid.",
    },
    {
        "title": "PC running very slowly — high CPU usage on startup",
        "description": (
            "A user reports their Windows 10 desktop takes 10+ minutes to become usable after boot. "
            "Task Manager shows 95–100% CPU for several minutes. The PC is 3 years old with 8 GB RAM."
        ),
        "difficulty": 2,
        "week_number": 3,
        "category": "Performance",
        "domain_id": "1.0",
        "root_cause": "Multiple startup programs consuming CPU; background antivirus scan also scheduled at boot",
        "root_cause_type": "excessive_startup_programs",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Check startup programs in Task Manager", "commands": ["taskmgr"], "required_mention": ["startup", "task manager"], "weight": 0.3},
                {"id": 2, "step": "Identify high-impact startup items", "required_mention": ["startup impact", "disable"], "weight": 0.35},
                {"id": 3, "step": "Reschedule antivirus scan and reboot to test", "required_mention": ["antivirus", "schedule", "reboot"], "weight": 0.35},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Task Manager showing high CPU at boot", "validation": {}},
                {"type": "screenshot", "description": "Startup tab with items disabled", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Disabled items, no antivirus investigation", "8": "Identified all contributors, made targeted changes", "10": "Root causes confirmed, improvements verified, documented"},
        "model_answer": "Open Task Manager > Startup tab. Disable high-impact unnecessary programs. Open the antivirus console and reschedule the daily scan from boot time to a low-usage period. Reboot and confirm boot time improvement.",
    },
    {
        "title": "External hard drive not recognized in Windows",
        "description": (
            "A user plugs in their USB external hard drive but it does not appear in File Explorer. "
            "Device Manager shows a yellow exclamation on the drive under 'Disk drives'. "
            "The drive works fine on another laptop."
        ),
        "difficulty": 2,
        "week_number": 3,
        "category": "Hardware",
        "domain_id": "1.0",
        "root_cause": "Corrupted or missing USB driver on the workstation",
        "root_cause_type": "driver_issue",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Check Device Manager for driver errors", "required_mention": ["device manager", "driver", "yellow"], "weight": 0.3},
                {"id": 2, "step": "Update or reinstall the driver", "required_mention": ["update driver", "reinstall", "uninstall"], "weight": 0.4},
                {"id": 3, "step": "Verify drive appears in Disk Management", "required_mention": ["disk management", "appears"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Device Manager showing the error", "validation": {}},
                {"type": "screenshot", "description": "Drive recognized in Disk Management after fix", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Reinstalled driver without confirming recognition", "8": "Diagnosed driver, reinstalled, verified in Disk Management", "10": "Root cause confirmed, drive fully accessible, documented"},
        "model_answer": "Open Device Manager, right-click the drive with the error, and choose 'Update driver' or 'Uninstall device' then replug. Open Disk Management (diskmgmt.msc) to confirm the drive appears and is accessible.",
    },
    {
        "title": "Email client cannot send mail — SMTP authentication error",
        "description": (
            "A user's Outlook reports 'Cannot send the message. Verify the email address in your account properties. "
            "The server responded: 535 Authentication Failed'. They can receive mail normally."
        ),
        "difficulty": 3,
        "week_number": 4,
        "category": "Email",
        "domain_id": "2.0",
        "root_cause": "Outdated SMTP credentials stored in Outlook credential manager",
        "root_cause_type": "expired_credential",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Check SMTP server and port settings", "required_mention": ["smtp", "port", "587", "465"], "weight": 0.25},
                {"id": 2, "step": "Remove and re-enter credentials in Windows Credential Manager", "required_mention": ["credential manager", "remove", "password"], "weight": 0.45},
                {"id": 3, "step": "Send a test email to verify", "required_mention": ["test", "send", "verify"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Error message in Outlook", "validation": {}},
                {"type": "screenshot", "description": "Successful test email sent", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Re-entered password but no settings check", "8": "Checked SMTP config and refreshed credentials", "10": "Root cause confirmed, sent test, documented fix"},
        "model_answer": "Verify SMTP port (587 TLS or 465 SSL) in Outlook account settings. Open Windows Credential Manager, find and delete the stored Outlook credentials, then re-enter them. Send a test email to confirm.",
    },
    {
        "title": "New employee laptop will not join the Active Directory domain",
        "description": (
            "During new hire setup, joining a Windows 11 Pro laptop to the corp.local domain fails with "
            "'The specified domain either does not exist or could not be contacted'. "
            "The laptop is on the office network and can ping other workstations."
        ),
        "difficulty": 3,
        "week_number": 4,
        "category": "Active Directory",
        "domain_id": "4.0",
        "root_cause": "Laptop DNS is pointing to a public DNS server instead of the domain controller",
        "root_cause_type": "dns_misconfiguration",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Check DNS settings on the laptop NIC", "commands": ["ipconfig /all"], "weight": 0.3},
                {"id": 2, "step": "Change DNS to the domain controller IP", "required_mention": ["dns", "domain controller", "dc"], "weight": 0.4},
                {"id": 3, "step": "Retry domain join and confirm", "required_mention": ["join", "domain", "success"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "ipconfig /all before DNS fix", "validation": {}},
                {"type": "screenshot", "description": "Successful domain join confirmation", "validation": {}},
            ]
        },
        "scoring_anchors": {"6": "Tried rejoin without checking DNS", "8": "Identified DNS issue and fixed", "10": "Root cause confirmed, domain joined, verified login"},
        "model_answer": "Run ipconfig /all and verify the DNS server is the domain controller IP (not 8.8.8.8). Update the NIC preferred DNS to the DC IP. Retry joining the domain via System Properties.",
    },
]

LABS = [
    {
        "title": "IP Addressing & Subnetting Practice",
        "description": "Step-by-step subnetting calculations and address classification",
        "difficulty": 2,
        "week_number": 2,
        "estimated_minutes": 30,
        "lab_type": "guided",
        "setup_instructions": "You will answer subnetting questions using pen and paper or a calculator. No software required.",
        "success_criteria": {
            "tasks": [
                "Identify network class",
                "Calculate subnet mask",
                "Find broadcast address",
                "List valid host range",
            ]
        },
        "hints": [
            "Use the formula 2^n for subnet calculation",
            "Broadcast is always the last address in the range",
        ],
    },
    {
        "title": "Troubleshoot a Network Connectivity Scenario",
        "description": "Given a simulated scenario, identify and resolve the connectivity issue using a structured approach",
        "difficulty": 3,
        "week_number": 3,
        "estimated_minutes": 45,
        "lab_type": "scenario",
        "setup_instructions": "Read the scenario carefully. Use the OSI model layers from bottom to top to diagnose.",
        "success_criteria": {
            "tasks": [
                "Identify OSI layer of failure",
                "Name the likely cause",
                "Describe the fix",
                "Explain how to verify",
            ]
        },
        "hints": [
            "Start at Layer 1 (physical)",
            "Check DHCP before DNS",
        ],
    },
    {
        "title": "Windows Command-Line Diagnostics",
        "description": "Practice using ipconfig, ping, tracert, netstat, and nslookup to diagnose network issues",
        "difficulty": 2,
        "week_number": 4,
        "estimated_minutes": 40,
        "lab_type": "guided",
        "setup_instructions": "Open Command Prompt on your Windows machine. You will run commands and document the output.",
        "success_criteria": {
            "tasks": [
                "Run ipconfig /all and identify gateway",
                "Ping 8.8.8.8 and interpret result",
                "Run tracert and identify hops",
                "Use nslookup to resolve a domain",
            ]
        },
        "hints": [
            "Use ipconfig /all not just ipconfig",
            "tracert shows where packets stop - that's the failure point",
        ],
    },
    {
        "title": "Hardware Component Identification",
        "description": "Identify and describe the purpose of common PC components from photos and descriptions",
        "difficulty": 1,
        "week_number": 1,
        "estimated_minutes": 20,
        "lab_type": "identification",
        "setup_instructions": "Read each component description and answer the identification questions below.",
        "success_criteria": {
            "tasks": [
                "Name the component",
                "Describe its function",
                "Identify the form factor or slot type",
            ]
        },
        "hints": [
            "Focus on form factor - ATX, microATX, M.2, PCIe",
            "RAM slots are longer and narrower than PCIe slots",
        ],
    },
]

CAPSTONES = [
    {
        "title": "CompTIA A+ Module 1 Capstone: Hardware & Troubleshooting",
        "required_role": {"name": "Support Technician I", "rank_order": 2},
        "description": "Demonstrate your knowledge of PC hardware components, assembly, and systematic troubleshooting by completing all required deliverables.",
        "week_number": 4,
        "is_published": True,
        "estimated_hours": 3,
        "requirements": {
            "skills": [
                "Identify all major PC components and their functions",
                "Explain the POST process and common error codes",
                "Apply a systematic troubleshooting methodology",
                "Document findings in a professional format",
            ]
        },
        "deliverables": {
            "items": [
                "Written component identification guide (300+ words)",
                "Troubleshooting scenario walkthrough using the OSI or layered approach",
                "Reflection on what you would do differently next time",
            ]
        },
        "rubric": {
            "technical_accuracy": "Correctly identifies components and troubleshooting steps",
            "documentation_quality": "Clear, structured, professional writing",
            "completeness": "All deliverables submitted with sufficient detail",
        },
    },
    {
        "title": "CompTIA A+ Module 2 Capstone: Networking & OS",
        "required_role": {"name": "Support Technician II", "rank_order": 3},
        "description": "Apply your understanding of networking concepts and Windows/Linux administration by completing a full scenario-based capstone project.",
        "week_number": 8,
        "is_published": True,
        "estimated_hours": 4,
        "requirements": {
            "skills": [
                "Configure TCP/IP settings and understand subnetting",
                "Troubleshoot network connectivity issues methodically",
                "Navigate and administer Windows and Linux from the command line",
                "Explain DNS, DHCP, and common protocols",
            ]
        },
        "deliverables": {
            "items": [
                "Network diagram (text-based or described) for a small office scenario",
                "Step-by-step troubleshooting documentation for a network scenario",
                "Command reference sheet with 10 essential Windows and Linux commands",
            ]
        },
        "rubric": {
            "technical_accuracy": "Correct understanding of networking concepts and commands",
            "problem_solving": "Logical and structured troubleshooting approach",
            "documentation_quality": "Professional format with clear explanations",
        },
    },
]

ANSWER_KEYS = [
    {
        "match": "dns",
        "root_cause": "DNS server misconfiguration on client NIC",
        "root_cause_type": "dns_misconfiguration",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Verify network connectivity", "commands": ["ping 8.8.8.8", "ipconfig"], "weight": 0.2},
                {"id": 2, "step": "Check DNS resolution", "commands": ["nslookup"], "weight": 0.3},
                {"id": 3, "step": "Identify root cause", "required_mention": ["dns server", "incorrect"], "weight": 0.3},
                {"id": 4, "step": "Verify fix", "commands": ["ping internal"], "weight": 0.2},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "ipconfig /all DNS values", "validation": {"must_contain_text": ["DNS"]}},
                {"type": "screenshot", "description": "after-fix resolution test", "validation": {}},
            ]
        },
        "scoring_anchors": {
            "6": "Basic troubleshooting with missing verification detail",
            "8": "Systematic triage and clear verification",
            "10": "Root cause proven, validated, and documented professionally",
        },
    },
    {
        "match": "locked",
        "root_cause": "Account lockout due to repeated failed authentication attempts",
        "root_cause_type": "expired_credential",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Confirm lockout status", "commands": ["Active Directory Users and Computers"], "weight": 0.3},
                {"id": 2, "step": "Investigate source", "required_mention": ["event viewer", "failed logon"], "weight": 0.4},
                {"id": 3, "step": "Verify user can sign in", "required_mention": ["test login"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "account lockout state before unlock", "validation": {}},
                {"type": "screenshot", "description": "successful login after resolution", "validation": {}},
            ]
        },
        "scoring_anchors": {
            "6": "Unlocked account but weak root-cause analysis",
            "8": "Investigated lock source with verification",
            "10": "Resolved, validated, and prevented recurrence",
        },
    },
]

COMMANDS = [
    # Networking (12)
    {"command": "ping", "category": "Networking", "syntax": "ping <host>", "description": "Test connectivity to a host.", "example": "ping 8.8.8.8"},
    {"command": "tracert", "category": "Networking", "syntax": "tracert <host>", "description": "Trace route hops to destination.", "example": "tracert google.com"},
    {"command": "ipconfig", "category": "Networking", "syntax": "ipconfig /all", "description": "Show Windows network configuration.", "example": "ipconfig /all"},
    {"command": "ifconfig", "category": "Networking", "syntax": "ifconfig", "description": "Show interface config on Unix systems.", "example": "ifconfig eth0"},
    {"command": "netstat", "category": "Networking", "syntax": "netstat -ano", "description": "Show sockets and connections.", "example": "netstat -ano"},
    {"command": "nslookup", "category": "Networking", "syntax": "nslookup <domain>", "description": "Query DNS records.", "example": "nslookup microsoft.com"},
    {"command": "dig", "category": "Networking", "syntax": "dig <domain>", "description": "Detailed DNS lookup tool.", "example": "dig example.com"},
    {"command": "arp", "category": "Networking", "syntax": "arp -a", "description": "Inspect ARP cache entries.", "example": "arp -a"},
    {"command": "nmap", "category": "Networking", "syntax": "nmap <target>", "description": "Scan hosts and open ports.", "example": "nmap 192.168.1.0/24"},
    {"command": "ssh", "category": "Networking", "syntax": "ssh user@host", "description": "Open remote secure shell session.", "example": "ssh admin@server01"},
    {"command": "curl", "category": "Networking", "syntax": "curl <url>", "description": "HTTP request from command line.", "example": "curl https://example.com"},
    {"command": "wget", "category": "Networking", "syntax": "wget <url>", "description": "Download files over HTTP/HTTPS.", "example": "wget https://example.com/file.zip"},
    # File System (10)
    {"command": "ls", "category": "File System", "syntax": "ls -la", "description": "List directory contents.", "example": "ls -la /var/log"},
    {"command": "dir", "category": "File System", "syntax": "dir", "description": "List directory contents on Windows.", "example": "dir C:\\Users"},
    {"command": "cd", "category": "File System", "syntax": "cd <path>", "description": "Change current directory.", "example": "cd /etc"},
    {"command": "cp", "category": "File System", "syntax": "cp <src> <dst>", "description": "Copy files/directories.", "example": "cp app.conf app.conf.bak"},
    {"command": "mv", "category": "File System", "syntax": "mv <src> <dst>", "description": "Move or rename files.", "example": "mv old.log archive/"},
    {"command": "rm", "category": "File System", "syntax": "rm -rf <path>", "description": "Delete files/directories.", "example": "rm temp.txt"},
    {"command": "mkdir", "category": "File System", "syntax": "mkdir <dir>", "description": "Create a directory.", "example": "mkdir backups"},
    {"command": "find", "category": "File System", "syntax": "find <path> -name <pattern>", "description": "Search for files by criteria.", "example": "find . -name *.log"},
    {"command": "grep", "category": "File System", "syntax": "grep -R <pattern> <path>", "description": "Search text in files.", "example": "grep -R ERROR /var/log"},
    {"command": "cat", "category": "File System", "syntax": "cat <file>", "description": "Print file content.", "example": "cat hosts"},
    # Users & Permissions (8)
    {"command": "whoami", "category": "Users", "syntax": "whoami", "description": "Show current user identity.", "example": "whoami"},
    {"command": "id", "category": "Users", "syntax": "id <user>", "description": "Show user and group IDs.", "example": "id admin"},
    {"command": "passwd", "category": "Users", "syntax": "passwd <user>", "description": "Change user password.", "example": "passwd student"},
    {"command": "useradd", "category": "Users", "syntax": "useradd <user>", "description": "Create new local user.", "example": "useradd trainee1"},
    {"command": "usermod", "category": "Users", "syntax": "usermod [options] <user>", "description": "Modify local user account.", "example": "usermod -aG wheel trainee1"},
    {"command": "sudo", "category": "Users", "syntax": "sudo <command>", "description": "Run command with elevated rights.", "example": "sudo systemctl restart sshd"},
    {"command": "chown", "category": "Users", "syntax": "chown <owner>:<group> <file>", "description": "Change file ownership.", "example": "chown root:root /etc/ssh/sshd_config"},
    {"command": "last", "category": "Users", "syntax": "last", "description": "Show recent login history.", "example": "last -n 20"},
    # Services & Processes (10)
    {"command": "systemctl", "category": "Services", "syntax": "systemctl <action> <service>", "description": "Manage systemd services.", "example": "systemctl status nginx"},
    {"command": "ps", "category": "Services", "syntax": "ps aux", "description": "List running processes.", "example": "ps aux | grep python"},
    {"command": "top", "category": "Services", "syntax": "top", "description": "Live process resource view.", "example": "top"},
    {"command": "kill", "category": "Services", "syntax": "kill [-9] <pid>", "description": "Terminate a process.", "example": "kill -9 1234"},
    {"command": "journalctl", "category": "Services", "syntax": "journalctl -u <service>", "description": "Read systemd journal logs.", "example": "journalctl -u sshd"},
    {"command": "df", "category": "Services", "syntax": "df -h", "description": "Show filesystem disk usage.", "example": "df -h"},
    {"command": "du", "category": "Services", "syntax": "du -sh <path>", "description": "Show directory size usage.", "example": "du -sh /var/log"},
    {"command": "free", "category": "Services", "syntax": "free -m", "description": "Display memory usage.", "example": "free -m"},
    {"command": "uptime", "category": "Services", "syntax": "uptime", "description": "Show system uptime and load.", "example": "uptime"},
    {"command": "dmesg", "category": "Services", "syntax": "dmesg", "description": "Kernel ring buffer messages.", "example": "dmesg | tail"},
    # Diagnostics (6)
    {"command": "lsof", "category": "Diagnostics", "syntax": "lsof -i", "description": "List open files and sockets.", "example": "lsof -i :443"},
    {"command": "tcpdump", "category": "Diagnostics", "syntax": "tcpdump -i <iface>", "description": "Capture network packets.", "example": "tcpdump -i eth0 port 53"},
    {"command": "netcat", "category": "Diagnostics", "syntax": "nc <host> <port>", "description": "Read/write network connections.", "example": "nc -vz server01 443"},
    {"command": "openssl", "category": "Diagnostics", "syntax": "openssl <subcommand>", "description": "SSL/TLS and cert diagnostics.", "example": "openssl s_client -connect example.com:443"},
    {"command": "strace", "category": "Diagnostics", "syntax": "strace <command>", "description": "Trace system calls.", "example": "strace -p 1234"},
    {"command": "ss", "category": "Diagnostics", "syntax": "ss -tulpen", "description": "Socket statistics and listeners.", "example": "ss -tulpen"},
    # Windows-specific (4 additional, total list = 50)
    {"command": "netsh", "category": "Windows", "syntax": "netsh interface ip show config", "description": "Configure and inspect network settings.", "example": "netsh interface ip show config"},
    {"command": "sc", "category": "Windows", "syntax": "sc query <service>", "description": "Service control manager utility.", "example": "sc query wuauserv"},
    {"command": "tasklist", "category": "Windows", "syntax": "tasklist", "description": "List Windows running processes.", "example": "tasklist /fi \"imagename eq notepad.exe\""},
    {"command": "taskkill", "category": "Windows", "syntax": "taskkill /PID <pid> /F", "description": "Force-stop Windows process.", "example": "taskkill /PID 4321 /F"},
]


def seed_roles(db):
    # TB-02: rename pass FIRST — migrate old L1/L2-era rows in place so existing
    # StudentRole/Student.current_role_id references survive the remap. Renaming
    # in place also avoids rank_order unique-constraint collisions with new rows.
    # Step 0: park EVERY role on a temporary unique negative rank so neither
    # renames nor re-ranking can collide with a legacy row still holding a
    # rank the new ladder needs (e.g. old "SysAdmin" on rank 4).
    for row in db.query(Role).all():
        row.rank_order = -row.id
    db.flush()

    renamed_targets: set[str] = set()
    for old_name, new_name in ROLE_RENAME_MAP.items():
        old_row = db.query(Role).filter(Role.name == old_name).first()
        new_row = db.query(Role).filter(Role.name == new_name).first()
        # Rename in place only when the target name is still free — including
        # free of a rename we just performed in this loop (two old roles can map
        # to the same new role, e.g. Junior SysAdmin + SysAdmin → Junior Systems
        # Technician; the second one is retired by the legacy pass below instead).
        if old_row and not new_row and new_name not in renamed_targets:
            old_row.name = new_name  # keep id; rank/description fixed below
            renamed_targets.add(new_name)
            db.flush()

    target_names = {r["name"] for r in ROLES}

    for role in ROLES:
        exists = db.query(Role).filter(Role.name == role["name"]).first()
        if exists:
            exists.rank_order = role["rank_order"]
            exists.description = role["description"]
        else:
            db.add(Role(**role))
    db.flush()

    # Retire any legacy roles not in the new ladder (e.g. duplicate "SysAdmin"
    # after its rename target already existed): repoint students to the nearest
    # new role, then drop the orphan.
    legacy = db.query(Role).filter(~Role.name.in_(target_names)).all()
    if legacy:
        fallback = db.query(Role).filter(Role.rank_order == 1).first()
        for row in legacy:
            replacement_name = ROLE_RENAME_MAP.get(row.name)
            replacement = (
                db.query(Role).filter(Role.name == replacement_name).first()
                if replacement_name
                else None
            ) or fallback
            if replacement:
                db.query(Student).filter(Student.current_role_id == row.id).update(
                    {"current_role_id": replacement.id}, synchronize_session=False
                )
            db.query(PromotionGate).filter(PromotionGate.role_id == row.id).delete(
                synchronize_session=False
            )
            db.delete(row)
    db.flush()


def seed_default_student_roles(db):
    first_role = db.query(Role).filter(Role.rank_order == 1).first()
    if not first_role:
        return
    for student in db.query(Student).all():
        if student.current_role_id is None:
            student.current_role_id = first_role.id
            student.role_since = datetime.now(timezone.utc)


def seed_promotion_gates(db):
    for gate in PROMOTION_GATES:
        role = db.query(Role).filter(Role.name == gate["role"]).first()
        if not role:
            continue
        exists = db.query(PromotionGate).filter(PromotionGate.role_id == role.id, PromotionGate.requirement_type == gate["requirement_type"]).first()
        if exists:
            exists.requirement_config = gate["config"]
        else:
            db.add(PromotionGate(role_id=role.id, requirement_type=gate["requirement_type"], requirement_config=gate["config"]))


def seed_module0_and_methodology(db):
    module = db.query(Module).filter(Module.code == MODULE_0["code"]).first()
    if module is None:
        module = Module(
            code=MODULE_0["code"],
            title=MODULE_0["title"],
            description=MODULE_0["description"],
            difficulty_band=MODULE_0["difficulty_band"],
            estimated_hours=MODULE_0["estimated_hours"],
            unlock_threshold=MODULE_0["unlock_threshold"],
            module_order=MODULE_0["module_order"],
            active=True,
        )
        db.add(module)
        db.flush()

    # Migration 0031 cannot insert the orientation lesson on a completely fresh
    # database because MOD-000 is created later by this ordinary seed. Keep the
    # complete intended module here as the post-migration source of truth.
    for lesson_data in MODULE_0["lessons"]:
        lesson = db.query(Lesson).filter(Lesson.module_id == module.id, Lesson.title == lesson_data["title"]).first()
        if lesson:
            continue
        db.add(
            Lesson(
                module_id=module.id,
                title=lesson_data["title"],
                summary=lesson_data["summary"],
                lesson_order=lesson_data["lesson_order"],
                outcomes=lesson_data["outcomes"],
                estimated_minutes=lesson_data["estimated_minutes"],
                required_notes_template=lesson_data["required_notes_template"],
                status="published",
            )
        )

    l1 = db.query(Role).filter(Role.rank_order == 1).first()
    framework = db.query(MethodologyFramework).filter(MethodologyFramework.name == "CompTIA 6-Step").first()
    if framework is None:
        db.add(
            MethodologyFramework(
                name="CompTIA 6-Step",
                description="Structured troubleshooting for support professionals",
                steps=FRAMEWORK_STEPS,
                required_for_role=l1.id if l1 else None,
            )
        )


def seed_methodology_completions(db):
    from app.models.progression import StudentMethodologyProgress

    frameworks = db.query(MethodologyFramework).all()
    students = db.query(Student).all()
    for student in students:
        for fw in frameworks:
            exists = (
                db.query(StudentMethodologyProgress)
                .filter_by(student_id=student.id, framework_id=fw.id)
                .first()
            )
            if not exists:
                db.add(
                    StudentMethodologyProgress(
                        student_id=student.id,
                        framework_id=fw.id,
                        completed=True,
                        practice_passed=True,
                        quiz_score=100,
                    )
                )



def _converted_service_desk_ticket(
    ticket_id, title, category, priority, asset_tag, device_name, requester,
    department, issue, impact, troubleshooting, hints,
):
    """Current definitions for legacy content reviewed for Service Desk use.

    These are new stable scenarios, not edits to the archived Ticket rows.
    ``seed_service_desk_scenarios`` versions them immutably like the original
    eight curated cases.
    """
    return {
        "activity": [{"id": f"{ticket_id}-created", "label": "Ticket created", "timestamp": "2026-07-28T10:30:00.000Z"}],
        "assignedTo": "you", "category": category, "createdAt": "2026-07-28T10:30:00.000Z",
        "description": {"businessImpact": impact, "issue": issue, "reportedByLine": "Submitted through the employee support portal.", "troubleshooting": troubleshooting},
        "device": {"assetTag": asset_tag, "deviceName": device_name, "kind": "laptop", "operatingSystem": "Windows 11 Enterprise", "state": "attention"},
        "escalated": False, "hints": hints, "id": ticket_id, "notes": [], "priority": priority,
        "requester": {"contact": "Employee support portal", "department": department, "email": f"{requester.lower().replace(' ', '.')}@nexus.example", "location": "Nexus office", "name": requester},
        "sla": {"dueAt": "2026-07-28T14:30:00.000Z", "target": "Respond within 4 hours"},
        "status": "open", "suggestedTools": ["remote-desktop", "documentation", "company-chat"], "title": title,
    }


SERVICE_DESK_TICKET_FIXTURES.extend([
    _converted_service_desk_ticket("INC2501", "Desktop opens with a temporary Windows profile", "software", "high", "NX-2501", "ACCT-LT-17", "Morgan Ellis", "Accounting", "After signing in, Morgan sees a fresh desktop and cannot find the usual Documents files.", "Month-end work is paused while the user data appears unavailable.", ["The user restarted once.", "A nearby teammate can open the same shared files."], ["Protect user data before profile repair.", "Compare the sign-in profile path with the expected local profile.", "Confirm the original files are available after repairing the profile."]),
    _converted_service_desk_ticket("INC2502", "Excel crashes only when one reporting workbook opens", "software", "medium", "NX-2502", "FIN-WS-44", "Priya Shah", "Finance", "Excel closes when the monthly reporting workbook opens, but other workbooks remain usable.", "The finance team cannot finish the monthly report.", ["A blank workbook opens normally.", "The workbook was copied locally and still crashes."], ["Reproduce the specific crash before changing Office.", "Use Safe Mode or add-in isolation to separate workbook and add-in causes.", "Verify the original workbook opens and saves after the repair."]),
    _converted_service_desk_ticket("INC2503", "One desk lost network after an office move", "network", "high", "NX-2503", "OPS-WS-12", "Jordan Kim", "Operations", "A workstation moved to a new desk has no network while adjacent desks work normally.", "One dispatcher cannot access the order system.", ["The workstation was restarted.", "Nearby workstations remain connected."], ["Start with physical link and compare the nearby working desk.", "Check the assigned switch port and VLAN before renewing addresses.", "Verify the original order system after the port is corrected."]),
    _converted_service_desk_ticket("INC2504", "Department printer stopped after its DHCP address changed", "hardware", "high", "NX-2504", "ENG-WS-09", "Sofia Nguyen", "Engineering", "The shared department printer is reachable from one workstation but this workstation still sends jobs to its old address.", "Engineering cannot print drawing review packets from the affected workstation.", ["The printer is powered on.", "A colleague printed successfully from a nearby computer."], ["Confirm whether this is local or printer-wide.", "Compare the configured print port with the printer’s current address.", "Update the port safely and print a test page."]),
    _converted_service_desk_ticket("INC2505", "New employee cannot open the department share", "access", "medium", "NX-2505", "MKT-LT-05", "Taylor Reed", "Marketing", "A new employee receives Access Denied for the Marketing share that peers can use.", "The new hire cannot access approved team materials.", ["The share opens for the team lead.", "The employee can sign in successfully."], ["Confirm the requested resource and compare an authorized peer.", "Check approved group access before granting anything.", "Verify the original share after the least-privilege change."]),
    _converted_service_desk_ticket("INC2506", "Assistant requests access to restricted salary records", "access", "high", "NX-2506", "HR-LT-21", "Casey Lane", "Executive Office", "An executive assistant asks for access to the restricted HR salary folder to help with a meeting.", "The request needs a timely, safe response without expanding access improperly.", ["The requester has access to general HR materials.", "No written approval is attached."], ["Identify the authorization boundary.", "Do not use a group change as a substitute for approval.", "Document a safe escalation and verify the request is routed correctly."]),
    _converted_service_desk_ticket("INC2507", "Account keeps locking after a password change", "access", "high", "NX-2507", "SALES-LT-08", "Avery Monroe", "Sales", "The account locks again shortly after each successful password reset.", "The employee repeatedly loses access to sales systems.", ["The account was unlocked once.", "The employee can sign in immediately after the reset."], ["Find what is reusing the old credential instead of resetting again.", "Inspect saved mappings, Credential Manager, and scheduled connections.", "Remove the stale credential and monitor for another lockout."]),
    _converted_service_desk_ticket("INC2508", "Employee entered credentials into a phishing page", "access", "high", "NX-2508", "PAY-LT-03", "Riley Brown", "Payroll", "An employee reports entering their password into a page reached from a suspicious email.", "The account and payroll data may be exposed until containment is complete.", ["The employee closed the page.", "No access changes have been made yet."], ["Contain first; do not treat this as ordinary password troubleshooting.", "Reset credentials, revoke active sessions, and escalate through the security path.", "Record the actions and safe follow-up for the employee."]),
    _converted_service_desk_ticket("INC2509", "Workstation disk fills again every few days", "software", "medium", "NX-2509", "SUP-WS-31", "Devon Ross", "Support", "The C: drive fills repeatedly even after temporary files are deleted.", "The support workstation becomes slow and cannot install approved updates.", ["Temporary files were removed last week.", "Free space returned briefly, then fell again."], ["Identify what is growing rather than repeatedly deleting symptoms.", "Inspect log and application storage trends.", "Correct the source safely and verify free space remains stable."]),
    _converted_service_desk_ticket("INC2510", "Restored laptop reports a trust relationship failure", "access", "medium", "NX-2510", "OPS-LT-58", "Sam Ortiz", "Operations", "A restored domain laptop rejects sign-in with a trust relationship error while peer laptops work.", "The employee cannot access the domain workstation after recovery.", ["The network is connected.", "Other domain users can sign in on nearby devices."], ["Separate user credentials from the computer account relationship.", "Confirm the secure-channel failure before changing the user account.", "Repair or escalate the device trust safely and verify domain sign-in."]),
])


SERVICE_DESK_TICKET_CONTENT_PATCHES = {
    "INC2401": {
        "issue": "The finance reporting portal accepts the first authentication step, then returns to the sign-in screen before the dashboard loads on the assigned laptop.",
        "troubleshooting": [
            "Confirmed Avery can sign in to another internal service.",
            "Confirmed the directory account is active and not locked.",
            "The Finance portal returned to sign-in before the dashboard loaded.",
        ],
        "hints": [
            "The employee account is healthy, so distinguish an account problem from a browser-session problem.",
            "Reproduce the Finance sign-in loop and review the local browser/profile evidence.",
            "Clear the stale browser profile storage, then confirm the original Finance portal opens.",
        ],
    },
    "INC2402": {
        "priority": "high",
        "businessImpact": "One loading lane is recording orders on paper, slowing dispatch and increasing re-entry work.",
        "issue": "The scanner at loading lane 2 disconnects from the warehouse network every few minutes. The scanner at the next lane stays connected.",
        "reportedByLine": "Reported by the morning dispatch lead after the issue continued through the first hour of the shift.",
        "troubleshooting": [
            "Restarted the affected scanner.",
            "Moved the affected scanner beside a working scanner; only the affected unit disconnected.",
            "Confirmed wired packing stations remain connected.",
        ],
        "hints": [
            "Use the working scanner beside it to decide whether the fault follows the network area or one device.",
            "Open Remote Desktop and compare the affected scanner's network settings with the working unit.",
            "Repair the affected network profile, renew its address, and then watch the connection long enough to verify stability.",
        ],
    },
    "INC2404": {
        "hints": [
            "Work out whether the fault follows the headset or remains with the workstation.",
            "Use Asset Management to record the confirmed hardware condition, then review replacement options.",
            "Mark the faulty headset as damaged, ship one replacement headset to Elliot Ward, and document how the requester should verify it.",
        ],
    },
    "INC2405": {
        "title": "Facilities calendar shortcut opens an archived workspace",
        "issue": "The new coordinator can sign in and already has Facilities Calendar access, but the desktop calendar shortcut opens an archived-location error.",
        "troubleshooting": [
            "Confirmed the user can open their personal calendar and another current Facilities calendar.",
            "Confirmed the requester is already in the Facilities Calendar access group.",
            "Used the desktop calendar shortcut, which opened an archived-location error.",
        ],
        "hints": [
            "Confirm that the requested calendar exists and that the requester already has legitimate access.",
            "Inspect the calendar workspace shortcut or mapping and compare it with the current Facilities location.",
            "Repair the obsolete mapping and ask the requester to open the original calendar workspace again.",
        ],
    },
    "INC2406": {
        "title": "Partner workspace unavailable while VPN is disconnected",
        "issue": "The laptop has normal internet access, but the secure partner workspace cannot be reached because the company VPN is disconnected.",
        "troubleshooting": [
            "Confirmed normal internet browsing works.",
            "Confirmed the partner share is unavailable from the home network.",
            "The company VPN client is disconnected.",
        ],
        "hints": [
            "Separate ordinary internet access from access to a private company resource.",
            "Confirm whether the secure partner share is reachable before changing its mapped-drive configuration.",
            "Reconnect the company VPN, then verify the original partner workspace opens.",
        ],
    },
}


def _current_service_desk_ticket_fixture(ticket):
    ticket = deepcopy(ticket)
    patch = SERVICE_DESK_TICKET_CONTENT_PATCHES.get(ticket["id"])
    if not patch:
        return ticket
    for field in ("businessImpact", "issue", "reportedByLine", "troubleshooting"):
        if field in patch:
            ticket["description"][field] = patch[field]
    if "title" in patch:
        ticket["title"] = patch["title"]
    if "priority" in patch:
        ticket["priority"] = patch["priority"]
    if "hints" in patch:
        ticket["hints"] = patch["hints"]
    return ticket


def seed_service_desk_scenarios(db):
    """Seed current Service Desk definitions as immutable published versions.

    Existing published versions are never edited.  When the curated content or
    server grading profile changes, this creates the next published version so
    old attempts remain bound to their historical definition.
    """
    scenarios = {}
    for raw_ticket in SERVICE_DESK_TICKET_FIXTURES:
        ticket = _current_service_desk_ticket_fixture(raw_ticket)
        stable_key = ticket["id"].lower()
        scenario = db.query(ServiceDeskScenario).filter_by(stable_key=stable_key).first()
        if scenario is None:
            scenario = ServiceDeskScenario(
                stable_key=stable_key,
                title=ticket["title"],
                description=f'{ticket["description"]["issue"]} {ticket["description"]["businessImpact"]}',
                category=ticket["category"],
                difficulty=SERVICE_DESK_DIFFICULTY_BY_PRIORITY[ticket["priority"]],
                status="active",
            )
            db.add(scenario)
            db.flush()
        else:
            scenario.title = ticket["title"]
            scenario.description = f'{ticket["description"]["issue"]} {ticket["description"]["businessImpact"]}'
            scenario.category = ticket["category"]
            scenario.difficulty = SERVICE_DESK_DIFFICULTY_BY_PRIORITY[ticket["priority"]]
        scenarios[stable_key] = scenario

        definition = {**ticket, "objective_catalog_version": PROCESS_CATALOG_VERSION}
        definition_hash = hashlib.sha256(
            json.dumps(definition, sort_keys=True).encode("utf-8")
        ).hexdigest()
        version = db.query(ServiceDeskScenarioVersion).filter_by(
            scenario_id=scenario.id, definition_hash=definition_hash
        ).first()
        if version is None:
            next_version = (db.query(ServiceDeskScenarioVersion.version_number)
                            .filter_by(scenario_id=scenario.id)
                            .order_by(ServiceDeskScenarioVersion.version_number.desc())
                            .first())
            db.add(
                ServiceDeskScenarioVersion(
                    scenario_id=scenario.id,
                    version_number=(next_version[0] if next_version else 0) + 1,
                    definition_json=definition,
                    definition_hash=definition_hash,
                    validation_status="valid",
                    status="published",
                    published_at=datetime.now(timezone.utc),
                    published_by="seed",
                )
            )
    db.flush()
    return scenarios


def seed_service_desk_assignments(db, scenarios):
    """Assign every simulation scenario to every current non-mentor student."""
    students = db.query(Student).filter(Student.is_mentor.is_(False)).all()
    for student in students:
        for scenario in scenarios.values():
            existing = (
                db.query(ServiceDeskAssignment)
                .filter_by(student_id=student.id, scenario_id=scenario.id, mode="simulation")
                .first()
            )
            if existing is None:
                db.add(
                    ServiceDeskAssignment(
                        student_id=student.id,
                        scenario_id=scenario.id,
                        mode="simulation",
                        is_required=False,
                        assigned_by="seed",
                    )
                )


def seed_tickets(db):
    existing_titles = {row.title for row in db.query(Ticket).all()}
    for t in TICKETS:
        if t["title"] in existing_titles:
            continue
        db.add(
            Ticket(
                title=t["title"],
                description=t["description"],
                difficulty=t["difficulty"],
                week_number=t["week_number"],
                category=t.get("category", "general"),
                domain_id=t.get("domain_id", "1.0"),
                root_cause=t.get("root_cause"),
                root_cause_type=t.get("root_cause_type"),
                required_checkpoints=t.get("required_checkpoints", {}),
                required_evidence=t.get("required_evidence", {}),
                scoring_anchors=t.get("scoring_anchors", {}),
                model_answer=t.get("model_answer"),
            )
        )


def seed_labs(db):
    existing_titles = {row.title for row in db.query(LabTemplate).all()}
    for lab in LABS:
        if lab["title"] in existing_titles:
            continue
        db.add(
            LabTemplate(
                title=lab["title"],
                description=lab["description"],
                lab_type=lab["lab_type"],
                difficulty=lab["difficulty"],
                week_number=lab["week_number"],
                estimated_minutes=lab["estimated_minutes"],
                environment_requirements={},
                setup_instructions=lab["setup_instructions"],
                success_criteria=lab["success_criteria"],
                required_evidence={},
                hints=lab["hints"],
                is_published=True,
            )
        )


def seed_capstones(db):
    for capstone in CAPSTONES:
        role_spec = capstone["required_role"]
        required_role = (
            db.query(Role)
            .filter(Role.name == role_spec["name"], Role.rank_order == role_spec["rank_order"])
            .one()
        )
        existing = db.query(CapstoneTemplate).filter(CapstoneTemplate.title == capstone["title"]).first()
        if existing is None:
            existing = CapstoneTemplate(
                title=capstone["title"],
                description=capstone["description"],
                week_number=capstone["week_number"],
                is_published=capstone["is_published"],
                requirements=capstone["requirements"],
                deliverables=capstone["deliverables"],
                estimated_hours=capstone["estimated_hours"],
                rubric=capstone["rubric"],
            )
            db.add(existing)
        existing.role_level = required_role.id


def seed_answer_keys(db, limit: int = 10):
    tickets = db.query(Ticket).limit(limit).all()
    for ticket in tickets:
        title = (ticket.title or "").lower()
        matched = ANSWER_KEYS[0]
        for template in ANSWER_KEYS:
            if template["match"] in title:
                matched = template
                break
        ticket.root_cause = matched["root_cause"]
        ticket.root_cause_type = matched["root_cause_type"]
        ticket.required_checkpoints = matched["required_checkpoints"]
        ticket.required_evidence = matched["required_evidence"]
        ticket.scoring_anchors = matched["scoring_anchors"]
        ticket.model_answer = "Document symptom, confirm diagnosis, apply fix, and verify restoration."


def seed_commands(db):
    if len(COMMANDS) != 50:
        raise RuntimeError(f"Expected 50 command seeds, found {len(COMMANDS)}")

    allowed = {item["command"].lower() for item in COMMANDS}
    existing_rows = db.query(CommandReference).all()
    by_command = {c.command.lower(): c for c in existing_rows}
    for row in existing_rows:
        if row.command.lower() not in allowed:
            db.delete(row)

    for item in COMMANDS:
        key = item["command"].lower()
        row = by_command.get(key)
        if row is None:
            db.add(
                CommandReference(
                    command=item["command"],
                    description=item["description"],
                    syntax=item["syntax"],
                    example=item["example"],
                    category=item["category"],
                    os="windows" if item["category"] == "Windows" else "mixed",
                )
            )
        else:
            row.description = item["description"]
            row.syntax = item["syntax"]
            row.example = item["example"]
            row.category = item["category"]
            row.os = "windows" if item["category"] == "Windows" else "mixed"


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_default_student_roles(db)
        seed_promotion_gates(db)
        seed_module0_and_methodology(db)
        seed_methodology_completions(db)
        seed_tickets(db)
        service_desk_scenarios = seed_service_desk_scenarios(db)
        seed_service_desk_assignments(db, service_desk_scenarios)
        seed_labs(db)
        seed_capstones(db)
        seed_cli_labs(db)
        db.flush()
        seed_answer_keys(db, limit=10)
        seed_commands(db)
        phase_a = seed_phase_a(db)
        db.commit()
        phase_b = seed_phase_b(db)
        db.commit()
        phase_c = seed_phase_c(db)
        db.commit()
        phase_d = seed_phase_d(db)
        db.commit()
        phase_e = seed_phase_e(db)
        db.commit()
        phase_f = seed_phase_f(db)
        db.commit()
        phase_g = seed_phase_g(db)
        verified_question_corrections = apply_verified_question_corrections(db)
        quiz_organization = seed_quiz_organization(db)
        legacy_quiz_mappings = apply_safe_optional_quiz_mappings(db)
        legacy_quiz_approvals = apply_reviewed_legacy_quiz_approvals(db)
        answer_positions = rebalance_seed_answer_positions(db)
        db.commit()
        print(f"Seed complete: roles(6), gates, module0+methodology, base tickets(8), labs(4), capstones(2), commands(50), phase_a={phase_a}, phase_b={phase_b}, phase_c={phase_c}, phase_d={phase_d}, phase_e={phase_e}, phase_f={phase_f}, phase_g={phase_g}, verified_question_corrections={verified_question_corrections}, quiz_organization={quiz_organization}, legacy_quiz_mappings={legacy_quiz_mappings}, legacy_quiz_approvals={legacy_quiz_approvals}, answer_positions={answer_positions}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
