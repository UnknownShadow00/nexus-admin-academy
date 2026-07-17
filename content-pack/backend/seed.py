from datetime import datetime, timezone

from app.config import load_env
from app.database import SessionLocal
from app.models.command_reference import CommandReference
from app.models.capstone import CapstoneTemplate
from app.models.lab import LabTemplate
from app.models.learning import Lesson, Module
from app.models.progression import MethodologyFramework, PromotionGate, Role
from app.models.student import Student
from app.models.ticket import Ticket
from app.services.cli_lab_seed import seed_cli_labs
from seed_phase_a import seed_phase_a
from seed_phase_b import seed_phase_b
from seed_phase_c import seed_phase_c
from seed_phase_d import seed_phase_d
from seed_phase_e import seed_phase_e
from seed_phase_f import seed_phase_f
from seed_phase_g import seed_phase_g
from app.services.auth_service import hash_password

load_env()

STUDENTS = [
    ("Admin", "admin@nexus.local", "admin", "admin123"),
    ("Alex", "alex@nexus.local", "alex", "alex123"),
    ("Jordan", "jordan@nexus.local", "jordan", "jordan123"),
    ("Sam", "sam@nexus.local", "sam", "sam123"),
    ("Taylor", "taylor@nexus.local", "taylor", "taylor123"),
    ("Riley", "riley@nexus.local", "riley", "riley123"),
]

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
            "title": "CompTIA 6-Step Process",
            "summary": "Define, theorize, test, plan, verify, and document.",
            "outcomes": ["Can identify symptoms", "Can test theories", "Can verify fixes"],
            "lesson_order": 1,
            "estimated_minutes": 45,
        }
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


def seed_students(db):
    existing = {row.email for row in db.query(Student).all()}
    for name, email, username, password in STUDENTS:
        if email in existing:
            continue
        db.add(Student(name=name, email=email, username=username, password_hash=hash_password(password), total_xp=0))


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

    for lesson_data in MODULE_0["lessons"]:
        lesson = db.query(Lesson).filter(Lesson.module_id == module.id, Lesson.lesson_order == lesson_data["lesson_order"]).first()
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
    existing_titles = {row.title for row in db.query(CapstoneTemplate).all()}
    for capstone in CAPSTONES:
        if capstone["title"] in existing_titles:
            continue
        db.add(
            CapstoneTemplate(
                title=capstone["title"],
                description=capstone["description"],
                week_number=capstone["week_number"],
                is_published=capstone["is_published"],
                requirements=capstone["requirements"],
                deliverables=capstone["deliverables"],
                estimated_hours=capstone["estimated_hours"],
                rubric=capstone["rubric"],
            )
        )


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
        seed_students(db)
        db.flush()
        seed_roles(db)
        seed_default_student_roles(db)
        seed_promotion_gates(db)
        seed_module0_and_methodology(db)
        seed_methodology_completions(db)
        seed_tickets(db)
        seed_labs(db)
        seed_capstones(db)
        seed_cli_labs(db)
        db.flush()
        seed_answer_keys(db, limit=10)
        seed_commands(db)
        db.commit()
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
        db.commit()
        print(f"Seed complete: roles(6), gates, module0+methodology, base tickets(8), labs(4), capstones(2), commands(50), phase_a={phase_a}, phase_b={phase_b}, phase_c={phase_c}, phase_d={phase_d}, phase_e={phase_e}, phase_f={phase_f}, phase_g={phase_g}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
