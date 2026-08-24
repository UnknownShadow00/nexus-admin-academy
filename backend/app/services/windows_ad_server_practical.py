"""Phase 4C.1 Windows, directory, and server evidence cases.

This module intentionally owns only nine in-place LabTemplate conversions.
It is not a workflow engine, terminal emulator, or Service Desk grader.
"""

from __future__ import annotations

from copy import deepcopy

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.lab import LabTemplate
from app.models.training import TrainingWeek, TrainingWeekActivity


def _panel(panel_id: str, label: str, *fields: tuple[str, str]) -> dict:
    return {
        "id": panel_id,
        "label": label,
        "fields": [{"label": name, "value": value} for name, value in fields],
    }


def _question(
    question_id: str,
    prompt: str,
    options: list[tuple[str, str]],
    correct: str | list[str],
    explanation: str,
    *,
    context: str | None = None,
) -> dict:
    answers = [correct] if isinstance(correct, str) else correct
    return {
        "id": question_id,
        "prompt": prompt,
        "context": context,
        "type": "multi_choice" if len(answers) > 1 else "single_choice",
        "options": [{"id": option_id, "label": label} for option_id, label in options],
        "correct": answers,
        "explanation": explanation,
    }


def _verification(label: str, *fields: tuple[str, str]) -> dict:
    return {
        "label": label,
        "description": "Deterministic training evidence returned only after the server accepts the supported plan; no real system was changed.",
        "fields": [{"label": name, "value": value} for name, value in fields],
    }


def _terminal_profile(
    profile_id: str,
    intro: str,
    help_topics: list[str],
    commands: list[dict],
    *,
    prompt: str = "PS C:\\Support> ",
) -> dict:
    return {
        "id": profile_id,
        "shell": "powershell",
        "prompt": prompt,
        "intro": intro,
        "help_topics": help_topics,
        "commands": commands,
    }


def _command(command: str, inspection_id: str | None, *output: str, aliases: list[str] | None = None) -> dict:
    return {
        "command": command,
        "aliases": aliases or [],
        "output": list(output),
        **({"inspection_id": inspection_id} if inspection_id else {}),
    }


WINDOWS_AD_SERVER_CASES: dict[int, dict] = {
    3: {
        "lab_id": 3,
        "role": "practice",
        "lab_type": "structured_evidence_case",
        "difficulty": 1,
        "estimated_minutes": 25,
        "title": "Windows Command-Line Diagnostics",
        "description": "Investigate a slow Windows computer and a repeatedly failing application without assuming the loudest symptom is the cause.",
        "setup_instructions": "Open the relevant Windows evidence. Compare process, service, event, storage, and session state before choosing the safest first response.",
        "workbench": {
            "title": "Windows host evidence case",
            "domain": "windows_host",
            "guidance_level": "practice",
            "complaint": "My computer has become extremely slow and the inventory application keeps failing.",
            "guidance": "Start with scope and resource state, then correlate the event time with the affected process. One record is unrelated.",
            "required_inspections": ["processes", "events", "storage"],
            "panels": [
                _panel("session", "User and session", ("Computer", "NX-WS-103"), ("Signed-in user", "NEXUS\\alina.patel"), ("Other users affected", "Yes — same workstation"), ("Uptime", "19 days")),
                _panel("processes", "Task Manager", ("CPU", "37% total"), ("Memory", "91% used"), ("Top process", "SearchIndexer.exe — 6.8 GB private memory"), ("InventoryClient.exe", "Not responding; 420 MB")),
                _panel("events", "Event Viewer", ("Time", "09:14:22"), ("Source", ".NET Runtime"), ("Event", "InventoryClient terminated after allocation failure"), ("Detail", "System.OutOfMemoryException")),
                _panel("services", "Services", ("Windows Search", "Running; Automatic (Delayed Start)"), ("Inventory Agent", "Running; Automatic"), ("Windows Update", "Running; Manual (Trigger Start)")),
                _panel("storage", "Storage", ("C: free", "184 GB of 476 GB"), ("Disk active time", "8%"), ("SMART", "Healthy"), ("Page file", "System managed")),
                _panel("usb", "Device history", ("Event", "USB headset reconnected"), ("Time", "08:41"), ("Status", "Device started normally")),
            ],
            "verification": _verification("Host state after the safe response", ("SearchIndexer.exe", "Restarted through the approved service action; 310 MB"), ("Memory", "58% used"), ("Inventory application", "Opened and completed a test search"), ("Event check", "No repeat allocation failure during the verification window")),
            "documentation_required": True,
        },
        "questions": [
            _question("scope", "Which scope is best supported by the evidence?", [("host", "A workstation-wide resource problem affecting applications on this host"), ("user", "Only Alina's Windows profile"), ("network", "A company-wide network outage"), ("disk", "A failing system disk")], "host", "The symptom follows the workstation, memory pressure is high, and disk health is normal."),
            _question("cause", "What is the most likely cause of the application failure?", [("indexer", "Runaway SearchIndexer memory use left too little memory for the application"), ("usb", "The headset reconnect damaged the inventory application"), ("storage", "The system disk is full"), ("update", "Windows Update is stopped")], "indexer", "Task Manager and the allocation-failure event correlate; the USB event and storage state do not."),
            _question("action", "What is the safest first response?", [("restart-service", "Capture the evidence, restart the Windows Search service through the approved action, then retest the application"), ("kill-random", "End every high-memory process without recording state"), ("disable-index", "Disable Windows Search permanently"), ("reimage", "Reimage the workstation immediately")], "restart-service", "A scoped service restart after evidence capture is reversible and directly tests the supported cause."),
        ],
    },
    5: {
        "lab_id": 7,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 25,
        "title": "Isolate the Windows Failure",
        "description": "Determine whether a Windows application failure is user-specific, application-specific, or machine-wide after a recent change.",
        "setup_instructions": "Choose which evidence matters. The title does not identify the fault domain, and at least one recent event is only a distractor.",
        "workbench": {
            "title": "Windows troubleshooting case",
            "domain": "windows_host",
            "guidance_level": "troubleshoot",
            "complaint": "The purchasing application closes during launch on my computer, but it worked yesterday.",
            "required_inspections": ["scope-test", "application-event", "changes"],
            "panels": [
                _panel("scope-test", "Scope tests", ("Same user, web portal", "Works"), ("Different Windows user, same PC", "Application launches"), ("Same user, different PC", "Application launches")),
                _panel("application-event", "Application event", ("Faulting app", "PurchaseDesk.exe 6.4"), ("Faulting module", "UserLayout.dll"), ("Exception", "0xc0000005"), ("Profile path", "C:\\Users\\mreyes\\AppData\\Roaming\\PurchaseDesk")),
                _panel("changes", "Change history", ("Application update", "6.3 → 6.4 at 22:15"), ("User layout migration", "Failed for mreyes at first launch"), ("Windows quality update", "Installed on all purchasing PCs; no peer reports")),
                _panel("storage", "Host state", ("C: free", "126 GB"), ("Memory", "44%"), ("Disk health", "Healthy")),
                _panel("startup", "Startup", ("Last boot", "07:42 — normal"), ("Safe Mode", "Not tested"), ("Startup repair", "Not indicated")),
            ],
            "verification": _verification("Application verification", ("User layout", "Recreated from approved default; original backed up"), ("Launch", "PurchaseDesk 6.4 opens for mreyes"), ("Peer users", "Unaffected"), ("Event Viewer", "No repeat UserLayout.dll crash")),
            "documentation_required": True,
            "reinforcement_scenarios": [
                {"key": "inc2501", "ticket_id": "INC2501", "label": "Profile-specific Windows failure", "note": "Independent Service Desk reinforcement when unlocked."},
                {"key": "inc2509", "ticket_id": "INC2509", "label": "Disk/source investigation", "note": "Use after this case to contrast a real storage fault."},
            ],
        },
        "questions": [
            _question("fault-domain", "Which fault domain is supported?", [("profile", "This user's application profile/configuration"), ("machine", "The whole Windows installation"), ("server", "The purchasing service for all users"), ("disk", "Physical disk failure")], "profile", "The application works for another Windows user on the same PC and for this user elsewhere."),
            _question("correlation", "Which change is most relevant?", [("layout", "The failed per-user layout migration during the application update"), ("windows", "The broadly successful Windows quality update"), ("boot", "The normal morning boot"), ("storage", "Healthy free disk space")], "layout", "The crash names the user layout module and the migration failed only for the affected profile."),
            _question("safe-action", "Choose the safest next action.", [("backup-reset", "Back up the user's PurchaseDesk settings, recreate only the approved user layout, and retest"), ("delete-profile", "Delete the entire Windows profile"), ("rollback-all", "Roll back the application for every user"), ("startup-repair", "Run Startup Repair")], "backup-reset", "The narrow, reversible profile-level correction matches the isolated scope."),
        ],
    },
    6: {
        "lab_id": 8,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 25,
        "title": "Make the Safe Access Decision",
        "description": "Trace an on-premises Windows access chain from user through group token and effective share permissions.",
        "setup_instructions": "Identify exactly where USER → GROUP → TOKEN → PERMISSION → RESOURCE stops working. Do not bypass the approved group model.",
        "workbench": {
            "title": "Windows access evidence case",
            "domain": "active_directory",
            "guidance_level": "troubleshoot",
            "complaint": "A new employee can sign in to Windows but cannot open the Finance department share.",
            "required_inspections": ["user", "groups", "token", "permissions"],
            "panels": [
                _panel("user", "User object", ("User", "NEXUS\\devon.hall"), ("Enabled", "Yes"), ("Locked", "No"), ("OU", "OU=Finance Users,OU=Users,DC=nexus,DC=internal")),
                _panel("groups", "Directory groups", ("Direct membership", "GG-Finance-Users"), ("Nested relationship", "GG-Finance-Users → DL-Finance-Share-RW"), ("Approval", "Finance manager approved read/write access")),
                _panel("token", "Current logon token", ("Logon time", "08:02"), ("Group added", "09:17"), ("whoami /groups", "GG-Finance-Users not present"), ("Session", "User has not signed out since onboarding")),
                _panel("permissions", "Effective resource permissions", ("Path", "\\\\FS01\\Finance"), ("Share", "DL-Finance-Share-RW — Change"), ("NTFS", "DL-Finance-Share-RW — Modify"), ("Explicit deny", "None")),
                _panel("network", "Resource reachability", ("DNS", "FS01 resolves to 10.20.14.21"), ("SMB", "TCP 445 reachable"), ("Peer access", "Working")),
            ],
            "verification": _verification("Access-chain verification", ("New token", "GG-Finance-Users and nested DL-Finance-Share-RW present"), ("Share test", "\\\\FS01\\Finance opens"), ("Write test", "Approved test file created and removed"), ("Direct user ACL", "Not added")),
            "documentation_required": True,
            "reinforcement_scenarios": [{"key": "inc2505", "ticket_id": "INC2505", "label": "Shared-drive access ticket", "note": "Existing optional Service Desk assessment; no new dependency."}],
        },
        "questions": [
            _question("chain-break", "Where does the access chain currently break?", [("token", "The current logon token predates the approved group membership"), ("account", "The user account is disabled"), ("acl", "The share has an explicit deny"), ("network", "FS01 is unreachable")], "token", "Directory membership and ACLs are correct, but the live token does not contain the group added after logon."),
            _question("relationship", "What does the nested group evidence prove?", [("agd", "The user group receives resource access through the domain-local permission group"), ("direct", "Devon needs a direct NTFS grant"), ("cloud", "An Entra role grants the SMB access"), ("deny", "Nested groups always deny access")], "agd", "The approved global-to-domain-local nesting is the intended on-prem access path."),
            _question("action", "What is the safest next action?", [("relogon", "Have Devon sign out and back in, then recheck the token and resource"), ("full-control", "Grant Devon direct Full Control"), ("restart-fs", "Restart FS01"), ("disable-inheritance", "Disable NTFS inheritance")], "relogon", "A new logon token is the least disruptive way to activate the already-correct group change."),
        ],
    },
    7: {
        "lab_id": 9,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 25,
        "title": "Choose the Safe Endpoint Response",
        "description": "Separate reachability, Remote Desktop state, firewall scope, and authorization without weakening endpoint protections.",
        "setup_instructions": "Use the evidence to find the narrow security boundary preventing remote support. Broad firewall or Defender disablement is unsafe.",
        "workbench": {
            "title": "Remote support evidence case",
            "domain": "windows_host",
            "guidance_level": "troubleshoot",
            "complaint": "A technician cannot remotely connect to an employee workstation for an approved support session.",
            "required_inspections": ["reachability", "rdp", "firewall", "authorization"],
            "panels": [
                _panel("reachability", "Reachability", ("Computer", "NX-LT-207"), ("Device check-in", "4 minutes ago"), ("Ping", "Reply from 10.20.7.44"), ("TCP 3389", "Timed out")),
                _panel("rdp", "Remote Desktop state", ("Remote Desktop", "Enabled"), ("TermService", "Running"), ("Listening", "0.0.0.0:3389"), ("NLA", "Required")),
                _panel("firewall", "Windows Firewall", ("Profiles", "Domain active; all profiles enabled"), ("Remote Desktop rule", "Enabled for Private only"), ("Domain-scope rule", "Disabled"), ("Defender", "Healthy; no active detection")),
                _panel("authorization", "Authorization", ("Technician", "NEXUS\\sam.lee"), ("Approved group", "GG-Remote-Support"), ("Local Remote Desktop Users", "GG-Remote-Support"), ("Session approval", "Ticket CHG-1842 approved")),
                _panel("power", "Power and session", ("Power", "AC connected"), ("Sleep", "Awake"), ("Console user", "Signed in")),
            ],
            "verification": _verification("Remote-support verification", ("Firewall profile", "Domain"), ("Approved RDP rule", "Enabled for Domain; scoped to support subnet"), ("TCP 3389", "Succeeded from support network"), ("NLA connection", "Authorized technician reached credential prompt")),
            "documentation_required": True,
        },
        "questions": [
            _question("fault", "Which boundary is blocking the approved session?", [("firewall-scope", "The RDP firewall rule is not enabled on the active Domain profile"), ("offline", "The workstation is offline"), ("service", "Remote Desktop Services is stopped"), ("authorization", "The technician lacks authorization")], "firewall-scope", "The host is reachable, RDP is listening, and authorization is present; TCP 3389 is blocked by the profile mismatch."),
            _question("unsafe", "Which proposed shortcut is unsafe?", [("disable-all", "Disable Windows Firewall and Defender until support is finished"), ("narrow-rule", "Enable the approved Domain-profile RDP rule scoped to the support subnet"), ("verify-port", "Retest TCP 3389 before opening the session"), ("document", "Record the active profile and rule change")], "disable-all", "Broadly disabling protections creates unnecessary exposure and is not an acceptable troubleshooting resolution."),
            _question("action", "Choose the safe corrective action.", [("enable-scoped", "Enable the approved Domain-profile Remote Desktop rule for the support subnet, then verify port and NLA access"), ("turn-off", "Turn off every firewall profile"), ("remove-nla", "Disable NLA"), ("local-admin", "Add the technician as a local administrator")], "enable-scoped", "The narrow approved rule fixes the supported boundary while preserving firewall and NLA protections."),
        ],
    },
    13: {
        "lab_id": 12,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 25,
        "title": "Handle the AD Account Request",
        "description": "Investigate an Active Directory sign-in complaint by separating account, computer, group, OU, and resource state.",
        "setup_instructions": "Select the directory evidence that identifies the fault domain. Treat architecture trivia as out of scope.",
        "workbench": {
            "title": "Directory evidence case",
            "domain": "active_directory",
            "guidance_level": "troubleshoot",
            "complaint": "A returning employee cannot sign in at their assigned workstation after being rehired.",
            "required_inspections": ["user", "auth", "computer", "groups"],
            "panels": [
                _panel("user", "User object", ("sAMAccountName", "rcooper"), ("Enabled", "Yes"), ("Locked out", "No"), ("Password last set", "Today 08:35"), ("OU", "OU=Reactivated Users,OU=Users,DC=nexus,DC=internal")),
                _panel("auth", "Authentication events", ("Workstation", "NX-WS-318"), ("Result", "Logon failure 0xC0000072"), ("Referenced account", "NEXUS\\rcooper-old"), ("Successful test", "NEXUS\\rcooper succeeds on support workstation")),
                _panel("computer", "Computer object", ("Name", "NX-WS-318"), ("Enabled", "Yes"), ("OU", "OU=Workstations,DC=nexus,DC=internal"), ("Secure channel", "Healthy")),
                _panel("groups", "Group membership", ("rcooper", "GG-Sales-Users; GG-VPN-Users"), ("rcooper-old", "Disabled; no groups"), ("Resource approval", "Sales baseline approved")),
                _panel("profile", "Credential context", ("Windows sign-in tile", "Other user"), ("Saved username", "NEXUS\\rcooper-old"), ("Last interactive user", "Former account")),
            ],
            "verification": _verification("Directory sign-in verification", ("Entered identity", "NEXUS\\rcooper"), ("Authentication", "Success on NX-WS-318"), ("Account state", "Enabled; not locked"), ("Old object", "Remains disabled; not reactivated")),
            "documentation_required": True,
            "reinforcement_scenarios": [{"key": "inc2507", "ticket_id": "INC2507", "label": "Recurring account lockout", "note": "Independent ticket for credential-source investigation when unlocked."}],
        },
        "questions": [
            _question("fault-domain", "Does the evidence point to the account, computer, or credential context?", [("credential", "The workstation is attempting the disabled former account, not the active rehired account"), ("active-user", "The active rcooper account is disabled"), ("computer", "The computer secure channel is broken"), ("group", "Sales group membership blocks interactive sign-in")], "credential", "The failure names rcooper-old while rcooper succeeds elsewhere and the computer trust is healthy."),
            _question("unsafe-action", "Which action would create avoidable risk?", [("reactivate-old", "Reactivate rcooper-old to make the saved credential work"), ("enter-current", "Select Other user and enter the approved current account"), ("verify", "Confirm the successful logon is recorded for rcooper"), ("note", "Document the stale identity source")], "reactivate-old", "Reactivating a stale identity bypasses the approved rehire object and creates duplicate-account risk."),
            _question("action", "What is the safest first response?", [("current-identity", "Use the current approved identity, verify sign-in, then remove the stale saved username through the supported process"), ("reset-again", "Reset rcooper's password again"), ("rejoin", "Unjoin and rejoin the workstation"), ("move-ou", "Move the computer to the Domain Controllers OU")], "current-identity", "The supported fix addresses the stale credential context without changing healthy account or computer state."),
        ],
    },
    14: {
        "lab_id": 13,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 30,
        "title": "Repair Domain Access Safely",
        "description": "Distinguish identity, DNS/connectivity, computer trust, and file permissions after a restored laptop returns to service.",
        "setup_instructions": "Follow the access path in order. Do not duplicate the existing trust ticket by assuming every restored machine needs a domain rejoin.",
        "workbench": {
            "title": "Domain access evidence case",
            "domain": "active_directory",
            "guidance_level": "troubleshoot",
            "complaint": "A restored laptop accepts cached Windows sign-in, but domain resources and the department share are unavailable.",
            "required_inspections": ["client-network", "dns", "trust", "resource"],
            "panels": [
                _panel("client-network", "Client network", ("Computer", "NX-LT-144"), ("IPv4", "10.20.14.44/24"), ("Gateway", "10.20.14.1 — reachable"), ("DNS servers", "8.8.8.8, 1.1.1.1")),
                _panel("dns", "Name resolution", ("dc02.nexus.internal", "NXDOMAIN from 8.8.8.8"), ("fs01.nexus.internal", "NXDOMAIN from 8.8.8.8"), ("Internet names", "Resolve normally"), ("Peer domain laptop DNS", "10.20.0.10, 10.20.0.11")),
                _panel("trust", "Computer and trust", ("Computer object", "NX-LT-144 — enabled"), ("Last password update", "12 days ago"), ("Secure-channel test", "Cannot locate domain controller"), ("Restore age", "1 day")),
                _panel("identity", "User account", ("User", "NEXUS\\tnguyen"), ("Enabled", "Yes"), ("Locked", "No"), ("Recent domain login", "Success from another workstation")),
                _panel("resource", "Share access", ("Path", "\\\\FS01\\Operations"), ("Group", "DL-Operations-Share-RW present in token"), ("Share/NTFS", "Modify allowed"), ("Observed error", "The network path was not found")),
            ],
            "verification": _verification("Domain access verification", ("DNS servers", "Approved internal resolvers"), ("DC lookup", "dc02.nexus.internal → 10.20.0.12"), ("Secure channel", "Healthy after domain discovery"), ("Share", "\\\\FS01\\Operations opens with expected Modify access")),
            "documentation_required": True,
            "reinforcement_scenarios": [{"key": "inc2510", "ticket_id": "INC2510", "label": "Domain trust after restore", "note": "Existing optional Service Desk case for a true trust failure."}],
        },
        "questions": [
            _question("isolation", "Which layer fails first in the current access path?", [("dns", "Client DNS is pointed at public resolvers that cannot locate domain services"), ("identity", "The user account is locked"), ("trust", "The evidence already proves a broken secure channel"), ("permission", "NTFS denies access")], "dns", "The client cannot discover the domain because it uses public DNS; trust cannot be judged until discovery works."),
            _question("trust-claim", "What can you safely conclude about the trust relationship now?", [("retest", "It is unproven; correct DNS and retest the secure channel before repairing or rejoining"), ("broken", "It is definitely broken because the laptop was restored"), ("healthy", "It is definitely healthy because the computer object exists"), ("irrelevant", "Trust never affects domain resources")], "retest", "The current trust test failed at domain-controller discovery, not at secure-channel validation."),
            _question("action", "Choose the safest first action.", [("dns-first", "Restore the documented internal DNS settings, verify DC discovery and the secure channel, then retest the share"), ("rejoin", "Immediately unjoin and rejoin the domain"), ("acl", "Grant the user direct Full Control"), ("delete", "Delete the computer object")], "dns-first", "Correcting the first failed layer is safe, reversible, and preserves a potentially healthy trust and permission path."),
        ],
    },
    15: {
        "lab_id": 5,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 30,
        "title": "Diagnose the Group Policy Result",
        "description": "Investigate why an expected user policy is absent by reading resultant-policy, OU/link, and security applicability evidence.",
        "setup_instructions": "The complaint does not identify the cause. Use the focused PowerShell terminal and directory panels; command buttons do not reveal the sequence.",
        "workbench": {
            "title": "Group Policy evidence case",
            "domain": "active_directory",
            "guidance_level": "troubleshoot",
            "complaint": "A Finance employee signed in this morning, but the Finance drive mapping is missing.",
            "required_inspections": ["terminal:gpresult", "directory", "gpo"],
            "panels": [
                _panel("directory", "Directory placement", ("User", "NEXUS\\miles.chen"), ("User OU", "OU=Finance Users,OU=Users,DC=nexus,DC=internal"), ("Computer OU", "OU=Workstations,DC=nexus,DC=internal"), ("Group", "GG-Finance-Users")),
                _panel("gpo", "GPO scope", ("GPO", "Finance Drive Map"), ("Settings", "User Configuration"), ("Link", "OU=Finance Users"), ("Security filter", "GG-Finance-Drive-Eligible"), ("Link enabled", "Yes")),
                _panel("change", "Recent changes", ("Request", "Finance access approved yesterday"), ("Group change", "Added to GG-Finance-Users"), ("Eligibility group", "No membership recorded"), ("Sign-in", "Today 08:06")),
                _panel("resource", "Drive target", ("Path", "\\\\FS01\\Finance"), ("DNS/SMB", "Reachable"), ("Direct access test", "Opens with existing read permission")),
            ],
            "terminal_profile": _terminal_profile(
                "gpo-finance-drive-filter",
                "Focused case terminal for resultant-policy and directory inspection. Outputs belong only to Miles's current incident.",
                ["Resultant policy", "Identity and group context", "Policy refresh result"],
                [
                    _command("whoami", None, "NEXUS\\miles.chen"),
                    _command("whoami /groups", None, "GROUP INFORMATION", "GG-Finance-Users", "GG-Standard-Users", "GG-Finance-Drive-Eligible is not present"),
                    _command("gpresult /r", "terminal:gpresult", "USER SETTINGS", "    Applied Group Policy Objects", "        Nexus Standard User Policy", "    The following GPOs were not applied because they were filtered out", "        Finance Drive Map", "            Filtering: Denied (Security)"),
                    _command("gpupdate /force", None, "Updating policy...", "User Policy update completed successfully.", "Finance Drive Map remains filtered: Denied (Security)."),
                ],
            ),
            "verification": _verification("Resultant-policy verification", ("Approved membership", "GG-Finance-Drive-Eligible present"), ("gpupdate", "User policy refresh completed"), ("gpresult", "Finance Drive Map applied"), ("Mapped drive", "F: opens \\\\FS01\\Finance")),
            "documentation_required": True,
        },
        "questions": [
            _question("scope", "Does the missing setting belong to user or computer policy?", [("user", "User policy, linked to the Finance Users OU"), ("computer", "Computer policy, linked to Workstations"), ("local", "Local policy only"), ("domain", "A domain-controller security policy")], "user", "The GPO contains User Configuration and is linked where the user object resides."),
            _question("cause", "Why is the expected policy absent?", [("filter", "The user is outside the GPO's security filter even though OU and basic Finance membership are correct"), ("dns", "The share hostname does not resolve"), ("refresh", "gpupdate has never been run, so filtering cannot apply"), ("computer-ou", "The computer is not in the Finance Users OU")], "filter", "gpresult explicitly reports Denied (Security), and the eligibility group is missing."),
            _question("action", "What is the safe next action?", [("approved-group", "Confirm approval for the eligibility group, correct that scoped membership, refresh, and prove application with gpresult"), ("authenticated-users", "Change the GPO filter to Authenticated Users"), ("direct-map", "Map the drive manually and close the ticket"), ("relink", "Link the GPO to the domain root")], "approved-group", "The scoped approved membership corrects the actual filter without broadening the policy."),
        ],
    },
    16: {
        "lab_id": 14,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 30,
        "title": "Investigate with PowerShell First",
        "description": "Use PowerShell to inspect a server application's service, IP, DNS, and port path instead of memorizing cmdlet names.",
        "setup_instructions": "You receive symptoms and a focused server shell. Decide which state to inspect; success is based on the incident diagnosis and verified outcome, not command text in a transcript.",
        "workbench": {
            "title": "Windows Server investigation",
            "domain": "windows_server",
            "guidance_level": "troubleshoot",
            "complaint": "The payroll application on SRV-APP-02 cannot connect to its database after network maintenance.",
            "required_inspections": ["terminal:net-ip", "terminal:dns", "change"],
            "panels": [
                _panel("change", "Maintenance record", ("Change", "Retired DNS resolver 10.20.99.10"), ("Approved DNS", "10.20.0.10, 10.20.0.11"), ("Application changes", "None"), ("Window closed", "02:30")),
                _panel("application", "Application state", ("Service", "NexusPayrollApp — Running"), ("Error", "Database host db01.nexus.internal could not be resolved"), ("Affected", "Payroll users only")),
                _panel("server", "Server record", ("Host", "SRV-APP-02"), ("IPv4", "10.20.16.22/24"), ("Gateway", "10.20.16.1"), ("Last reboot", "7 days ago")),
                _panel("distractor", "Storage", ("C: free", "112 GB"), ("D: application data", "61% free"), ("Disk events", "None")),
            ],
            "terminal_profile": _terminal_profile(
                "server-dns-after-maintenance",
                "Focused PowerShell case on SRV-APP-02. Use inspection cmdlets to isolate service, network, DNS, and port state.",
                ["Service state", "IP and resolver configuration", "Name resolution", "TCP reachability"],
                [
                    _command("Get-Service NexusPayrollApp", None, "Status   Name              DisplayName", "Running  NexusPayrollApp  Nexus Payroll Application", aliases=["get-service -name nexuspayrollapp"]),
                    _command("Get-NetIPConfiguration", "terminal:net-ip", "InterfaceAlias       : Ethernet0", "IPv4Address          : 10.20.16.22", "IPv4DefaultGateway   : 10.20.16.1", "DNSServer            : 10.20.99.10"),
                    _command("Resolve-DnsName db01.nexus.internal", "terminal:dns", "Resolve-DnsName: db01.nexus.internal : DNS name does not exist", "Server: 10.20.99.10", "Query timed out."),
                    _command("Test-NetConnection 10.20.16.25 -Port 1433", None, "ComputerName     : 10.20.16.25", "RemotePort       : 1433", "InterfaceAlias   : Ethernet0", "TcpTestSucceeded : True"),
                    _command("Test-NetConnection db01.nexus.internal -Port 1433", None, "WARNING: Name resolution of db01.nexus.internal failed", "TcpTestSucceeded : False"),
                ],
                prompt="PS SRV-APP-02\\Support> ",
            ),
            "verification": _verification("Server connectivity verification", ("DNS servers", "10.20.0.10, 10.20.0.11"), ("Resolve-DnsName", "db01.nexus.internal → 10.20.16.25"), ("TCP 1433", "Succeeded"), ("Payroll test", "Application health check connected to database")),
            "documentation_required": True,
        },
        "questions": [
            _question("scope", "Which layer is failing?", [("dns", "Server-side DNS configuration/name resolution"), ("service", "The payroll application service is stopped"), ("port", "The database port is closed"), ("disk", "Application storage is full")], "dns", "The service runs and the database port works by IP, while the configured retired resolver cannot resolve the hostname."),
            _question("evidence", "Which evidence most strongly separates DNS from database availability?", [("ip-port", "TCP 1433 succeeds by database IP while the hostname lookup fails"), ("free-space", "The application disk has free space"), ("uptime", "The server has not rebooted recently"), ("users", "Payroll users reported the symptom")], "ip-port", "Successful numeric-IP reachability proves the network/port path while the name path fails."),
            _question("action", "Choose the safe response.", [("restore-dns", "Restore the approved DNS servers through the change process, then verify name resolution, port reachability, and application health"), ("hosts-file", "Add a permanent hosts-file entry"), ("restart", "Repeatedly restart the payroll service"), ("public-dns", "Use a public resolver for internal names")], "restore-dns", "The documented resolver correction addresses the incident state and includes layered verification."),
        ],
    },
    17: {
        "lab_id": 15,
        "role": "prove",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 35,
        "title": "Verify the Server Recovery Plan",
        "description": "Independently investigate an overnight department-service outage, choose a safe first response, verify it, and prepare a useful handoff.",
        "setup_instructions": "You have symptoms, a focused server shell, and change records. Decide what to inspect. Do not perform destructive recovery or assume the whole server failed.",
        "workbench": {
            "title": "Windows Server prove case",
            "domain": "windows_server",
            "guidance_level": "prove",
            "complaint": "Users report the department synchronization service stopped updating records overnight.",
            "required_inspections": ["terminal:service", "terminal:event", "change", "backup"],
            "panels": [
                _panel("change", "Change record", ("Time", "Yesterday 16:40"), ("Change", "Password rotated for NEXUS\\svc-deptsync"), ("Owner", "Identity Operations"), ("Dependent task update", "Not recorded")),
                _panel("backup", "Recovery readiness", ("Last successful data backup", "Yesterday 23:00"), ("Restore test", "Passed last month"), ("Data corruption alert", "None"), ("DC recovery", "Not indicated")),
                _panel("monitoring", "Monitoring", ("Server", "SRV-OPS-01 reachable"), ("CPU", "18%"), ("Memory", "52%"), ("C: free", "94 GB"), ("Alert", "DeptSync service stopped at 01:00")),
                _panel("users", "Affected scope", ("Department sync", "All departments stale since 01:00"), ("File shares", "Working"), ("Authentication", "Working"), ("Other services", "Healthy")),
            ],
            "terminal_profile": _terminal_profile(
                "server-deptsync-credential-failure",
                "Focused PowerShell case on SRV-OPS-01. Inspect current state and the first relevant overnight failure before choosing a response.",
                ["Service state", "Relevant event log", "Scheduled task result", "Resource state", "Remote port state"],
                [
                    _command("Get-Service NexusDeptSync", "terminal:service", "Status   Name            DisplayName", "Stopped  NexusDeptSync   Nexus Department Sync"),
                    _command("Get-WinEvent -FilterHashtable @{LogName='System'; Id=7038} -MaxEvents 5", "terminal:event", "TimeCreated : 01:00:03", "Id          : 7038", "Message     : NexusDeptSync could not log on as NEXUS\\svc-deptsync due to the following error: The user name or password is incorrect."),
                    _command("Get-ScheduledTaskInfo -TaskName 'Department Sync Nightly'", None, "LastRunTime    : Today 01:00:00", "LastTaskResult : 2147943726 (logon failure)", "NextRunTime    : Tomorrow 01:00:00"),
                    _command("Get-PSDrive C", None, "Name Used (GB) Free (GB) Provider Root", "C    382.1     93.9      FileSystem C:\\"),
                    _command("Test-NetConnection SRV-OPS-01 -Port 445", None, "ComputerName     : SRV-OPS-01", "RemotePort       : 445", "TcpTestSucceeded : True"),
                ],
                prompt="PS SRV-OPS-01\\Support> ",
            ),
            "verification": _verification("Department service verification", ("Stored service credential", "Updated by authorized Identity Operations owner"), ("Service", "NexusDeptSync running"), ("Controlled sync", "Completed; 42 records processed"), ("User check", "New department record visible"), ("Monitoring", "Healthy for 15-minute observation window")),
            "documentation_required": True,
            "additional_note_fields": [{"id": "handoff", "label": "Escalation / handoff", "placeholder": "Name the owning team, evidence attached, and the exact authorized follow-up."}],
            "reinforcement_scenarios": [{"key": "inc2408", "ticket_id": "INC2408", "label": "Print Spooler service ticket", "note": "Existing Service Desk case for a smaller service-state incident."}],
        },
        "questions": [
            _question("classification", "Which incident class best fits all the evidence?", [("credential", "A service/task logon failure after the run-as account password changed"), ("resource", "Server disk exhaustion"), ("network", "The server is broadly unreachable"), ("recovery", "Directory data corruption requiring DC recovery")], "credential", "Service and task failures align with the password rotation; server resources, reachability, and other services are healthy."),
            _question("first-response", "What is the safe first response at this support level?", [("coordinate", "Preserve the failure evidence and escalate to the authorized service-account owner to update the stored credential, with a controlled rerun plan"), ("own-reset", "Reset the service account password yourself and restart everything"), ("restore", "Restore the entire server from backup"), ("local-system", "Run the service permanently as Local System")], "coordinate", "Credential ownership and dependent services require controlled coordination; broad recovery or privilege expansion is unsupported."),
            _question("verify", "Which verification set is sufficient before handoff?", [("layered", "Service running, controlled sync succeeds, user-visible data updates, and monitoring remains healthy"), ("button", "The Start button no longer appears"), ("ping", "The server answers ping"), ("backup", "A backup exists")], "layered", "State, transaction, user outcome, and observation together prove the service—not just the host—recovered."),
        ],
    },
}


def _target_rows(db: Session, week_number: int, lab_id: int) -> tuple[LabTemplate | None, TrainingWeekActivity | None]:
    lab = db.get(LabTemplate, lab_id)
    week = db.query(TrainingWeek).filter_by(week_number=week_number).first()
    if lab is None or week is None:
        return lab, None
    activity = (
        db.query(TrainingWeekActivity)
        .filter_by(training_week_id=week.id, activity_type="guided_lab", content_ref=str(lab_id))
        .first()
    )
    return lab, activity


def sync_windows_ad_server_practical_upgrade(db: Session) -> dict:
    """Convert the nine existing labs in place; never creates activities."""
    bind = db.get_bind()
    if not inspect(bind).has_table(TrainingWeekActivity.__tablename__):
        return {"updated_templates": 0, "updated_activities": 0, "skipped": True, "reason": "migration_not_applied"}

    result = {"updated_templates": 0, "updated_activities": 0, "missing_targets": [], "skipped": False}
    for week_number, spec in WINDOWS_AD_SERVER_CASES.items():
        lab, activity = _target_rows(db, week_number, spec["lab_id"])
        if lab is None or activity is None:
            result["missing_targets"].append({"week_number": week_number, "lab_id": spec["lab_id"]})
            continue

        values = {
            "title": spec["title"],
            "description": spec["description"],
            "lab_type": spec["lab_type"],
            "week_number": week_number,
            "difficulty": spec["difficulty"],
            "estimated_minutes": spec["estimated_minutes"],
            "is_published": True,
            "environment_requirements": {},
            "setup_instructions": spec["setup_instructions"],
            "success_criteria": {
                "evidence_case_workbench": deepcopy(spec["workbench"]),
                "questions": deepcopy(spec["questions"]),
            },
            "required_evidence": {},
            "hints": {},
        }
        if any(getattr(lab, field) != value for field, value in values.items()):
            for field, value in values.items():
                setattr(lab, field, value)
            result["updated_templates"] += 1

        metadata = dict(activity.metadata_json or {})
        if spec["role"] == "practice":
            metadata.pop("learning_role", None)
        else:
            metadata["learning_role"] = spec["role"]
        if activity.metadata_json != metadata or activity.estimated_minutes != spec["estimated_minutes"]:
            activity.metadata_json = metadata
            activity.estimated_minutes = spec["estimated_minutes"]
            result["updated_activities"] += 1

    db.commit()
    return result


def restore_pre_4c1_practical_labs(db: Session) -> dict:
    """Restore only the nine owned templates/role overrides for downgrade."""
    from app.services.training_curriculum_seed import (
        WEEK_3_CLI_COMMANDS,
        WEEKS_11_14_QUALITY,
        WEEKS_15_18_QUALITY,
        WEEKS_7_10_QUALITY,
        WINDOWS_DIAGNOSTICS_QUESTIONS,
        WINDOWS_TROUBLESHOOTING_PRACTICE,
        ACCESS_DECISION_PRACTICE,
    )

    legacy_specs: dict[int, dict] = {
        3: {
            "description": "Run the required Windows commands in the real Nexus practice terminal, read the output, then diagnose each result.",
            "lab_type": "structured_cli",
            "difficulty": 1,
            "estimated_minutes": 25,
            "setup_instructions": "Use the command buttons as prompts, run every command, and read what each output proves before answering.",
            "success_criteria": {"questions": WINDOWS_DIAGNOSTICS_QUESTIONS, "required_commands": WEEK_3_CLI_COMMANDS},
        },
        5: {"questions": WINDOWS_TROUBLESHOOTING_PRACTICE, "lab_type": "structured_diagnostic"},
        6: {"questions": ACCESS_DECISION_PRACTICE, "lab_type": "structured_diagnostic"},
    }
    for number in (7,):
        legacy_specs[number] = deepcopy(WEEKS_7_10_QUALITY[number]["lab"])
    for number in (13, 14):
        legacy_specs[number] = deepcopy(WEEKS_11_14_QUALITY[number]["lab"])
    for number in (15, 16, 17):
        legacy_specs[number] = deepcopy(WEEKS_15_18_QUALITY[number]["lab"])

    restored = 0
    for week_number, case in WINDOWS_AD_SERVER_CASES.items():
        lab, activity = _target_rows(db, week_number, case["lab_id"])
        if lab is None or activity is None:
            continue
        legacy = legacy_specs[week_number]
        if week_number in {5, 6}:
            values = {
                "description": "Work through realistic support symptoms and choose the safest evidence-based next action.",
                "lab_type": legacy["lab_type"],
                "difficulty": 1,
                "estimated_minutes": 25,
                "setup_instructions": "Read each symptom and evidence block. Choose the next action you could defend in a support ticket.",
                "success_criteria": {"questions": legacy["questions"]},
            }
        elif week_number == 3:
            values = legacy
        else:
            values = {
                "description": legacy.get("description", "Work through realistic evidence and choose the safest support action before moving to an independent case."),
                "lab_type": legacy["lab_type"],
                "difficulty": 1,
                "estimated_minutes": legacy.get("estimated_minutes", 20),
                "setup_instructions": legacy.get("setup_instructions", "Read each symptom and evidence block. Choose the action you could defend in a support ticket."),
                "success_criteria": {
                    "questions": legacy["questions"],
                    **({"required_commands": legacy["required_commands"]} if legacy.get("required_commands") else {}),
                    **({"terminal_profile": legacy["terminal_profile"]} if legacy.get("terminal_profile") else {}),
                },
            }
        for field, value in values.items():
            setattr(lab, field, deepcopy(value))
        metadata = dict(activity.metadata_json or {})
        metadata.pop("learning_role", None)
        activity.metadata_json = metadata
        activity.estimated_minutes = values["estimated_minutes"]
        restored += 1
    db.commit()
    return {"restored": restored}
