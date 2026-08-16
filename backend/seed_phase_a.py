"""Phase A (Weeks 1-4) curriculum content — CB-02/03/04.

Structured, maintainable seed source (Part 7 of the phase prompt). Idempotent:
matched by module code / quiz title / ticket title; re-running updates in place.

Content matches NEXUS_WEEKS_1-4_PACKAGE.md. Retrofits upgrade the 8 original
seed tickets with five-anchor rubrics, 4-step hint ladders, and parameters.
"""

NOTES_TEMPLATE = (
    "SYMPTOM (what the user reports, verbatim where useful):\n\n"
    "QUESTIONS ASKED / INFO GATHERED:\n\n"
    "EVIDENCE (command output, screenshots, event IDs):\n\n"
    "HYPOTHESIS:\n\n"
    "CHANGE MADE (one change at a time; how to undo it):\n\n"
    "VERIFICATION (how you proved it is fixed):\n\n"
    "USER-FACING MESSAGE (plain language, no jargon):\n"
)

MODULES = [
    {
        "code": "MOD-001",
        "title": "The Ticket Is the Job",
        "description": "Ticket writing, internal vs user-facing notes, and first command-line contact. Week 1.",
        "target_role": "Support Technician I",
        "difficulty_band": 1,
        "estimated_hours": 6,
        "module_order": 2,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Anatomy of a Good Ticket",
                "lesson_order": 1,
                "estimated_minutes": 60,
                "summary": (
                    "A ticket is the product of your work — the fix is invisible if the ticket is bad. "
                    "A good ticket lets a stranger continue your work without re-asking the user anything.\n\n"
                    "INTERNAL NOTES answer: what was reported, what you checked, what you found, what you "
                    "changed, how you verified. Written for technicians: precise, command names, event IDs, "
                    "timestamps.\n\nUSER-FACING TEXT answers: what was wrong (in their words), what you did "
                    "about it, what they should do now. No jargon — 'a wrong address-book (DNS) setting', "
                    "not 'NIC DNS misconfiguration'.\n\nNEVER MIX THEM. Users don't need your registry paths; "
                    "the next tech can't work from 'fixed the thing'.\n\n"
                    "WHY IT MATTERS ON THE JOB: MSPs bill from notes, escalation teams triage from notes, "
                    "and your reputation inside a help desk IS your notes. Techs with clean tickets get "
                    "promoted to the interesting work.\n\n"
                    "GUIDED PRACTICE: rewrite the two bad notes below into the Nexus template.\n"
                    "Bad note 1: 'user pc broken, fixed it, closing.'\n"
                    "Bad note 2: 'reinstalled everything and now it seems ok probably was a virus or "
                    "something, told user to be careful.'\n\n"
                    "COMMON MISTAKES: writing the novel of everything you tried with no structure; blaming "
                    "the user in writing; claiming success without stating how you verified.\n\n"
                    "RESOURCES (free): Nexus original material; any real ticket you've seen at work is a "
                    "case study — anonymize and dissect it."
                ),
                "outcomes": [
                    "Write an internal note a stranger could act on without contacting the user again",
                    "Write a user-facing resolution free of jargon in three sentences or fewer",
                    "Keep internal and user-facing content strictly separated",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Meet the Command Line",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "GUI status icons summarize; command output proves. Technicians trust command output "
                    "because it is exact, timestamped, copyable into a ticket, and identical over remote "
                    "sessions where GUIs are slow or unavailable.\n\n"
                    "ACTIVITY: use the CLI practice link below to navigate a simulated network device, run "
                    "show commands, and read real-looking output under guidance.\n\n"
                    "VERIFICATION HABIT: after any change, run the command that would show the OLD bad "
                    "state and confirm it now shows the new good state. Paste that output into the ticket.\n\n"
                    "COMMON MISTAKES: typing commands from memory into production without checking syntax; "
                    "trusting 'it looks connected' over 'ping succeeded 4/4'.\n\n"
                    "JOB RELEVANCE: every interview for desktop/network roles asks you to interpret "
                    "ipconfig or ping output. Reading output calmly is the skill."
                ),
                "outcomes": [
                    "Navigate the simulated CLI and complete guided command drills",
                    "Explain why command output is stronger ticket evidence than GUI status",
                ],
                "related_activity_stable_id": "week-1-networking_lab-meet-cli-001",
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-002",
        "title": "Hardware That Generates Tickets",
        "description": "Symptom-first hardware diagnosis: storage, RAM/CPU/power/POST, BIOS/UEFI. Week 2.",
        "target_role": "Support Technician I",
        "difficulty_band": 1,
        "estimated_hours": 14,
        "module_order": 3,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Storage: Symptoms Before Specs",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "You will never be asked 'what is an SSD'. You WILL be asked why a laptop takes five "
                    "minutes to boot. Storage symptoms map to causes:\n"
                    "- Clicking/grinding from an HDD → mechanical failure imminent. STOP. Data safety first.\n"
                    "- S.M.A.R.T. warning at boot → pre-failure. Back up NOW, then replace.\n"
                    "- Very slow I/O, 100% disk in Task Manager → dying HDD, exhausted SSD, or a runaway "
                    "process — evidence decides which.\n"
                    "- Drive disappears intermittently → cable/connector or controller before 'dead drive'.\n\n"
                    "THE DECISION: replace vs troubleshoot is a DATA question first. 'Is there a backup?' "
                    "changes every next step. Never run repair tools that write heavily (chkdsk /f) on a "
                    "drive making mechanical noise — you may destroy the last good read.\n\n"
                    "GUIDED PRACTICE: six written mini-scenarios in the quiz; for each pick the next SAFE "
                    "diagnostic and justify it.\n\n"
                    "SAFETY: unplug before opening a case; ground yourself; label cables.\n\n"
                    "RESOURCES: Professor Messer storage videos already linked in the Video Tracker "
                    "(job-critical tags)."
                ),
                "outcomes": [
                    "Map storage symptoms (clicking, SMART warning, slow I/O, disappearing drive) to likely causes",
                    "Choose replace-vs-troubleshoot using data-safety-first reasoning",
                    "State why backup status changes every storage decision",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "RAM, CPU, Power, and POST",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "No-POST triage is pattern recognition:\n"
                    "- Nothing at all (no fans, no LEDs) → power path: outlet, cable, PSU switch, PSU.\n"
                    "- Fans spin, no display → RAM/GPU/board. Reseat RAM first — it fixes a shocking share.\n"
                    "- Beep patterns → the board telling you which component; record the pattern verbatim.\n"
                    "- Boot loop → PSU under load, overheating, or corrupted firmware settings.\n\n"
                    "STANDARD FIRST BENCH STEP: minimal boot — board, CPU, one RAM stick, PSU. If that "
                    "POSTs, add parts back one at a time.\n\n"
                    "SCOPE HONESTY: as a remote/junior tech you diagnose and DOCUMENT; board-level repair "
                    "is escalation to depot. Writing a clean diagnostic note ('power verified at wall and "
                    "cable, minimal boot attempted, 3-beep pattern recorded') IS the win — that is exactly "
                    "what ticket W2 'Desktop won't turn on' grades.\n\n"
                    "COMMON MISTAKES: swapping three parts at once (you learn nothing); skipping the wall "
                    "outlet check (embarrassing % of 'dead PCs')."
                ),
                "outcomes": [
                    "Interpret no-POST symptom patterns into a ranked component shortlist",
                    "Describe minimal-boot as the standard first bench diagnostic",
                    "Recognize when hardware work is out of scope and escalate with a complete diagnostic note",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "BIOS/UEFI and Boot Order",
                "lesson_order": 3,
                "estimated_minutes": 60,
                "summary": (
                    "'No operating system found' has three very different causes: boot order pointing at "
                    "the wrong device (cheap fix), a dead disk (data conversation), or a broken bootloader "
                    "(repair procedure). Firmware tells you which: if the disk is VISIBLE in firmware but "
                    "not booting, the disk is alive and the problem is order or bootloader.\n\n"
                    "PRACTICE (evidence drill): on your own PC or the class VM, enter firmware setup, "
                    "screenshot the firmware version and current boot order, and submit both. Change "
                    "nothing else.\n\n"
                    "DO-NOT-TOUCH LIST on corporate devices without approval: Secure Boot, TPM state "
                    "(BitLocker will demand its recovery key), virtualization flags on managed images. "
                    "Changing TPM/Secure Boot casually can lock a company laptop out of its own disk.\n\n"
                    "COMMON MISTAKES: 'resetting BIOS to defaults' as a first move (destroys evidence and "
                    "settings); confusing boot order with boot failure."
                ),
                "outcomes": [
                    "Check and change boot order safely and capture firmware evidence",
                    "Differentiate boot-order vs disk vs bootloader causes of 'no OS found'",
                    "List firmware settings never changed without approval on corporate devices",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-003",
        "title": "Windows 11 as Your Workbench",
        "description": "Accounts, permissions, the investigator's toolkit, CLI diagnostics, updates and Defender. Week 3.",
        "target_role": "Support Technician I",
        "difficulty_band": 1,
        "estimated_hours": 15,
        "module_order": 4,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Accounts, Profiles, and Permissions",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Three concepts generate half of desktop tickets:\n"
                    "ACCOUNTS: local accounts live on one machine; Microsoft accounts sync settings and "
                    "enable cloud recovery; domain accounts (Week 13) are managed centrally. Support "
                    "implication: password reset paths are COMPLETELY different for each.\n"
                    "PROFILES: a profile is the user's world (Desktop, Documents, HKCU). Corrupt-profile "
                    "signature: user logs in, everything looks factory-fresh, files 'gone'. Files are "
                    "usually NOT gone — Windows loaded a TEMP profile. Event Viewer → User Profile Service "
                    "events 1511/1515 confirm it.\n"
                    "NTFS PERMISSIONS: Read/Write/Modify/Full Control; DENY beats ALLOW; permissions "
                    "inherit down folders; effective access = what actually applies after group math.\n\n"
                    "GUIDED PRACTICE (evidence drill): create local test user 'labuser'; create folder "
                    "C:\\PracticeShare; grant labuser Read only; prove with screenshots that labuser can "
                    "open but not modify a file. Delete the account after.\n\n"
                    "COMMON MISTAKES: granting Full Control to 'just make it work' (it works — and fails "
                    "the least-privilege anchor); editing permissions on a folder you haven't backed up."
                ),
                "outcomes": [
                    "Create and inspect local users and groups; explain local vs Microsoft account support implications",
                    "Read NTFS permissions and predict effective access for a user",
                    "Recognize the temp-profile symptom pattern and its Event Viewer evidence",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "The Investigator's Toolkit",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "Four tools answer 'what is actually happening on this machine':\n"
                    "EVENT VIEWER: Windows Logs → System and Application. Read Level (Error/Warning), "
                    "Source, Event ID, and timestamp. Event IDs are searchable — 'Event 7000 service name' "
                    "finds the answer faster than any guess. Filter Current Log is your friend.\n"
                    "TASK MANAGER: Processes for CPU/RAM/disk hogs; Startup for login slowness; Details "
                    "for PIDs (pairs with netstat -ano).\n"
                    "SERVICES: services.msc — check Status and Startup Type; a stopped 'Automatic' service "
                    "is a clue. Know when NOT to kill a process: unsaved user work, database/system "
                    "processes — stop the service properly instead of killing the process.\n"
                    "DISK MANAGEMENT: volume health, free space, and whether the disk Windows sees matches "
                    "what should be installed.\n\n"
                    "GUIDED PRACTICE (scavenger hunt, screenshot each): (1) any Error in System log from "
                    "the last 7 days with Source and ID visible; (2) your top memory process; (3) startup "
                    "impact list; (4) Disk Management showing free space on C:.\n\n"
                    "COMMON MISTAKES: reading only the newest event instead of the FIRST error in the "
                    "chain; killing a process the user needed; ignoring Warnings that precede Errors."
                ),
                "outcomes": [
                    "Pull a relevant error from Event Viewer and interpret Source, ID, level, and time",
                    "Identify and safely restart a failing service; explain when not to kill a process",
                    "Use Task Manager and Disk Management to capture resource and volume evidence",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Command-Line Diagnostics",
                "lesson_order": 3,
                "estimated_minutes": 120,
                "summary": (
                    "The Windows support seven, and what their output MEANS:\n"
                    "ipconfig /all → your identity on the network. Read: IP (169.254.x.x = DHCP failed), "
                    "gateway (empty = no route out), DNS servers (wrong = 'internet down' with working IP).\n"
                    "ping → reachability. Ping the gateway (local net ok?), then 1.1.1.1 (internet ok?), "
                    "then a NAME (DNS ok?). This three-step splits any 'no internet' ticket.\n"
                    "tracert → WHERE the path dies.\n"
                    "nslookup → asks DNS directly; compare against a known resolver (nslookup site 1.1.1.1).\n"
                    "netstat -ano → who is talking; pair PID with Task Manager Details.\n"
                    "whoami /groups, gpresult /r → who Windows thinks you are and which policies applied.\n"
                    "sfc /scannow then DISM /Online /Cleanup-Image /RestoreHealth → system file repair "
                    "sequence (DISM repairs the store sfc repairs from).\n"
                    "chkdsk SAFETY: /f needs a reboot lock; NEVER on a mechanically clicking drive.\n\n"
                    "ACTIVITY: practice the toolkit on an approved Windows machine or training VM, and keep "
                    "notes on what each command's output tells you.\n\n"
                    "COMMON MISTAKES: running commands without reading output; pasting screenshots with no "
                    "sentence saying what they prove."
                ),
                "outcomes": [
                    "Run and interpret ipconfig /all, ping, tracert, nslookup, netstat -ano, whoami, gpresult /r",
                    "Execute the sfc → DISM repair sequence and read its outcomes",
                    "State chkdsk safety rules and when not to run it",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Windows Update and Defender Basics",
                "lesson_order": 4,
                "estimated_minutes": 60,
                "summary": (
                    "FAILED UPDATES: Settings → Windows Update → Update history gives the failing KB and "
                    "an error code — the code is searchable gold. The safe standard sequence: (1) run the "
                    "Windows Update troubleshooter; (2) restart the Windows Update service; (3) rename "
                    "C:\\Windows\\SoftwareDistribution (a cache — Windows rebuilds it) and retry. STOP "
                    "POINT: if the same KB fails after the sequence, document the code and escalate — "
                    "deeper servicing-stack repair is not a Week 3 change.\n\n"
                    "DEFENDER: run a Quick scan; know Full and Offline exist (Offline scan reboots into a "
                    "clean environment for stubborn malware). Protection history shows what was caught and "
                    "what action was taken. In Week 7 you learn the response procedure; for now: found "
                    "malware on a work machine = document, do not 'clean and close', escalate.\n\n"
                    "COMMON MISTAKES: deleting SoftwareDistribution instead of renaming; disabling Defender "
                    "to 'test something' and forgetting to re-enable."
                ),
                "outcomes": [
                    "Locate update history and extract the failing KB and error code",
                    "Execute the safe failed-update sequence and identify the escalation stop point",
                    "Run Defender scans and read protection history",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-004",
        "title": "Working the Queue",
        "description": "Prioritization, escalation, user communication, and Multi-Ticket Simulation 1. Week 4 — Gate 1 week.",
        "target_role": "Support Technician I",
        "difficulty_band": 1,
        "estimated_hours": 13,
        "module_order": 5,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Priority, Impact, and Not Making It Worse",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "PRIORITY = IMPACT × URGENCY. Impact: how many people / how core a process. Urgency: "
                    "how time-bound. A VIP's jammed printer FEELS urgent; a department share outage IS "
                    "urgent. Learn to defend the order out loud — that defense is graded in Simulation 1.\n\n"
                    "PRACTICAL ITIL VOCABULARY (Nexus original summary — enough to be dangerous):\n"
                    "- INCIDENT: something broke; restore service.\n"
                    "- SERVICE REQUEST: nothing broke; user needs a thing (access, install).\n"
                    "- CHANGE: planned modification with approval and a rollback plan.\n"
                    "- ESCALATION: functional (needs deeper skill) vs hierarchical (needs authority).\n\n"
                    "THE TICKET YOU DON'T TOUCH: change-freeze windows, requests requiring approval "
                    "(access to HR folders!), anything where your change could widen an outage. Knowing "
                    "when NOT to act is a graded anchor (safe_fix_or_escalation).\n\n"
                    "HANDOFF NOTES: next tech continues without re-asking the user: current state, what's "
                    "been ruled out (with evidence), exact next step you'd take, and any promise made to "
                    "the user (deadline, callback).\n\n"
                    "COMMON MISTAKES: first-in-first-out queue handling; touching a risky ticket to look "
                    "fast; handoffs that say 'see above'."
                ),
                "outcomes": [
                    "Rank a five-ticket queue by impact × urgency and defend the order in writing",
                    "Identify the ticket that must not be touched without approval",
                    "Write a handoff note the next technician can act on without re-contacting the user",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Talking to Humans",
                "lesson_order": 2,
                "estimated_minutes": 60,
                "summary": (
                    "DE-ESCALATION IN WRITING: acknowledge the impact ('I understand this is blocking your "
                    "deadline'), state what you're doing NOW, give a realistic next update time — and never "
                    "promise a fix time you can't control. Frustrated users calm down when they see motion "
                    "and honesty, not when they read 'per my last email'.\n\n"
                    "TRANSLATE, DON'T DUMB DOWN: 'Your computer was asking the wrong server for website "
                    "addresses; I pointed it at the right one and confirmed browsing works.' Accurate, "
                    "human, two sentences.\n\n"
                    "GET EVIDENCE, NOT OPINIONS: ask 'send me a screenshot of the exact message' and 'what "
                    "changed since it last worked?' — not 'did you try restarting?'\n\n"
                    "PRACTICE ('write the email', graded on the communication anchor):\n"
                    "1. An executive's laptop needs a part ordered — 2-day wait. Deliver the news.\n"
                    "2. A user is angry their 'simple request' took 3 days (it required security approval). "
                    "De-escalate without blaming security.\n"
                    "3. Explain to a nontechnical user why you need them to stop using the machine until "
                    "a malware scan finishes.\n\n"
                    "COMMON MISTAKES: apologizing for things that aren't wrong; jargon walls; promising "
                    "'this will never happen again'."
                ),
                "outcomes": [
                    "De-escalate a frustrated user in writing without over-promising",
                    "Translate a technical root cause into two user-facing sentences",
                    "Ask follow-up questions that produce evidence instead of opinions",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


def _q(text, a, b, c, d, correct, expl, multi=None):
    """Compact question builder. multi='A,C' makes it multi-select."""
    return {
        "question_text": text, "option_a": a, "option_b": b, "option_c": c,
        "option_d": d, "correct_answer": correct[0], "correct_answers": multi,
        "explanation": expl,
    }


QUIZZES = [
    {
        "title": "Ticket Writing Fundamentals",
        "week_number": 1, "domain_id": "5.0", "lesson_title": "Anatomy of a Good Ticket",
        "questions": [
            _q("An internal note reads: 'PC was broken, fixed it.' What is the FIRST thing missing?",
               "The technician who closed it", "The reported symptom", "The final ticket category", "The user's satisfaction rating",
               "B", "A note must let another technician continue the work. Record the reported symptom before the investigation and resolution details."),
            _q("Which sentence belongs in a USER-FACING resolution?",
               "Your profile was repaired and your files open normally.",
               "The ProfileImagePath value and .bak SID key were corrected.",
               "The user loaded a temporary profile after Event ID 1511.",
               "Tier 2 should review the User Profile Service event logs.",
               "A", "A user-facing resolution explains the outcome in plain language. Registry details, event IDs, and escalation instructions belong in internal notes."),
            _q("The next technician should be able to continue a ticket without doing what?",
               "Reviewing the documented evidence", "Repeating the same questions", "Confirming the affected asset", "Checking the ticket history",
               "B", "A complete handoff records the reported symptom, evidence, and work already performed so the user is not asked for the same information again."),
            _q("Which items belong in INTERNAL notes? (select all that apply)",
               "Exact command output proving the fix", "Event ID and source", "A friendly closing greeting", "What was ruled out and how",
               "A", "Evidence, IDs, and eliminations are for technicians; greetings are user-facing.", multi="A,B,D"),
            _q("A note says 'ran some commands, seems fine now.' Which grading anchor does this fail hardest?",
               "communication", "verification", "investigation", "root_cause",
               "B", "'Seems fine' claims success without proof; verification requires showing the problem is demonstrably gone."),
            _q("Why do MSPs care intensely about ticket notes?",
               "They support billing and auditability", "They replace endpoint monitoring alerts",
               "They publish technical details to customers", "They satisfy a Windows licensing requirement",
               "A", "MSPs use complete notes as evidence of work performed and as an audit trail for handoffs, billing, and disputes."),
            _q("A single remote user says that every website on one company laptop stopped loading five minutes ago. Other staff in the same office can browse normally. Before changing the laptop, which question best confirms the scope?",
               "Can nearby staff browse normally?", "What IP configuration does the laptop use?",
               "Can you restart the laptop?", "Can you reproduce it in another browser?",
               "D", "The report already limits the issue to one laptop, so testing another browser is the fastest safe way to distinguish a browser-specific problem from a device or network-path problem. Asking whether nearby staff are affected repeats information the scenario already gives; a restart or IP address is premature."),
            _q("Why should a ticket avoid saying that a user 'obviously deleted' a file?",
               "It is unproven and unprofessional", "It makes the ticket difficult to close",
               "It prevents the file from being restored", "It means the user cannot be contacted",
               "A", "Tickets are business records. State observable evidence and avoid assigning blame unless the facts support it."),
        ],
    },
    {
        "title": "Windows Accounts and Permissions",
        "week_number": 3, "domain_id": "3.0", "lesson_title": "Accounts, Profiles, and Permissions",
        "questions": [
            _q("A user logs in and their desktop is empty, documents 'gone', wallpaper default. Most likely:",
               "Ransomware encrypted the profile", "Windows loaded a temporary profile", "Storage failure blocked the profile", "The profile folder was deleted",
               "B", "A factory-fresh desktop is the classic temporary-profile signature; the user's files normally remain on disk in the original profile."),
            _q("Which Event Viewer events confirm a temp-profile logon?",
               "Security audit events 4624 and 4625", "User Profile Service events 1511 and 1515", "Service Control Manager events 7000 and 7001", "Power events 41 and 6008",
               "B", "User Profile Service events 1511/1515 record failure to load the profile and temp fallback."),
            _q("NTFS: a user is in GroupA (Modify ALLOW) and GroupB (Write DENY). Effective ability to save changes to a file?",
               "Can save; Allow wins", "Cannot save; Deny wins", "Can save after elevation", "Depends on the file size",
               "B", "Explicit Deny beats Allow in NTFS permission evaluation."),
            _q("Password reset paths differ MOST between which two account types?",
               "Administrator and standard accounts", "Local and Microsoft accounts", "Guest and standard accounts", "32-bit and 64-bit Windows",
               "B", "Local resets happen on the machine; Microsoft accounts reset through the cloud — completely different support flows."),
            _q("Which permissions are needed to open and read a file but NOT change it? (select all that apply)",
               "Read", "Read & Execute", "Modify", "Full Control",
               "A", "Read (and Read & Execute for programs) suffice; Modify/Full Control violate least privilege.", multi="A,B"),
            _q("Granting Full Control to 'make the error go away' primarily violates:",
               "Least privilege", "Data retention law", "The OSI model", "Licensing",
               "A", "It works — and grants far more than the task requires, which the safe_fix anchor penalizes."),
            _q("Permissions on C:\\Share\\Reports are inherited from:",
               "The domain controller policy", "The parent folder: C:\\Share", "The user's profile folder", "The share's network settings",
               "B", "NTFS permissions flow down from parent folders by default."),
            _q("Before demonstrating a permissions fix on a user's folder you should FIRST:",
               "Take ownership of the folder", "Plan the ACL rollback", "Disable permission inheritance", "Restart the workstation",
               "B", "Rollback thinking: know how to restore the previous ACL before changing permissions."),
            _q("A 'corrupt profile' usually means the user's files are:",
               "Encrypted by a user key", "Deleted during sign-in", "Still present on disk", "Moved to OneDrive cloud storage",
               "C", "The data is nearly always intact; the profile failed to load."),
            _q("Which tool shows the effective result of all group memberships on a folder for one user?",
               "Effective Access tab", "Task Manager process list", "Disk Management console", "System Configuration utility",
               "A", "Effective Access computes the group math for you."),
        ],
    },
    {
        "title": "The Investigator's Toolkit",
        "week_number": 3, "domain_id": "3.0", "lesson_title": "The Investigator's Toolkit",
        "questions": [
            _q("In an error chain spanning 20 minutes of events, which event matters most for root cause?",
               "The newest error", "The FIRST error in the chain", "The one with the longest text", "Any Warning",
               "B", "Later errors are usually consequences; the first one is closest to the cause."),
            _q("A service is set to Automatic but shows Stopped after boot. Best next step:",
               "Reinstall the operating system", "Review the System log",
               "Set the service to Manual", "Delete and recreate the service",
               "B", "The System log records why the service failed — evidence before action."),
            _q("Which pairs a network connection to the program that owns it?",
               "ipconfig /all adapter configuration", "netstat -ano with Details", "tracert route information", "gpresult /r policy results",
               "B", "netstat -ano lists PIDs; Details maps PID to executable."),
            _q("When should you NOT kill a process from Task Manager? (select all that apply)",
               "It holds unsaved user work", "It is a database/system process mid-write", "It is using 90% CPU", "It belongs to another logged-in user's session",
               "A", "High CPU alone is a symptom, not a license to kill; unsaved work, mid-write databases, and other users' sessions need graceful handling.", multi="A,B,D"),
            _q("Login takes 4 minutes. The fastest evidence source is:",
               "Task Manager startup impact", "Disk Management free-space view", "DNS lookup results", "Windows Update history",
               "A", "Startup impact ranks exactly what slows logon."),
            _q("Event Viewer 'Level' tells you:",
               "The event severity", "The responsible user", "The recommended fix", "The current CPU usage",
               "A", "Level is severity; Source and Event ID identify the component and condition."),
            _q("Windows is 'out of space' but the user 'deleted everything'. First evidence to collect:",
               "Measure disk use by folder",
               "Check IP configuration", "Review applied policy", "Check Windows Update cache size",
               "A", "Measure before acting: page files, shadow copies, update caches, and profiles hide space."),
            _q("Stopping vs killing: the correct way to restart a hung Automatic service is:",
               "End the service process tree", "Restart it through Services",
               "Rename the service executable", "Reboot immediately",
               "B", "Use the service control path so dependencies and cleanup run; killing is last resort."),
        ],
    },
    {
        "title": "Windows Command-Line Diagnostics",
        "week_number": 3, "domain_id": "2.0", "lesson_title": "Command-Line Diagnostics",
        "questions": [
            _q("ipconfig shows 169.254.23.7. This means:",
               "A static address was assigned", "DHCP failed; APIPA assigned", "DNS resolution failed", "The network adapter is disabled",
               "B", "169.254.x.x is APIPA — the machine asked DHCP and got no answer."),
            _q("ping 1.1.1.1 works; ping google.com fails. The layer at fault:",
               "Physical cabling", "DNS resolution", "The default gateway", "The firewall blocks all traffic",
               "B", "IP connectivity is proven; only name resolution is failing."),
            _q("Correct repair order for system file corruption:",
               "Run CHKDSK, then format", "Run DISM, then SFC",
               "Run SFC twice", "Defragment, then run SFC",
               "B", "DISM repairs the component store that sfc uses as its source."),
            _q("Which commands help diagnose 'no internet' on a workstation? (select all that apply)",
               "ipconfig /all", "ping (gateway, IP, name)", "nslookup", "gpresult /r",
               "A", "Identity, reachability, and resolution are the trio; gpresult is policy, not connectivity.", multi="A,B,C"),
            _q("You must NEVER run chkdsk /f on:",
               "Any solid-state drive", "A clicking hard drive", "The system drive", "A removable USB drive",
               "B", "Heavy repair writes can destroy the last readable data on a failing mechanical drive."),
            _q("gpresult /r answers which question?",
               "Which policies applied", "Which ports the firewall blocks",
               "Which updates failed", "Which DNS servers are configured",
               "A", "gpresult reports applied policy — essential for 'my drive mapping/setting is missing' tickets."),
        ],
    },
]

QUIZZES.append({
    "title": "Help-Desk Operations",
    "week_number": 4, "domain_id": "5.0", "lesson_title": "Priority, Impact, and Not Making It Worse",
    "questions": [
        _q("A VIP's personal printer is jammed; a 40-person department share is down; a password reset waits. Correct order:",
           "VIP printer, department outage, reset", "Department outage, password reset, VIP", "Password reset, VIP printer, department outage", "First come, first served",
           "B", "Impact × urgency: 40 people blocked beats one inconvenienced VIP; a reset is fast and unblocks one person — queue it second."),
        _q("Functional vs hierarchical escalation: needing deeper technical skill is _____; needing authority/approval is _____.",
           "hierarchical / functional", "functional / hierarchical", "both functional", "both hierarchical",
           "B", "Skill → functional; authority → hierarchical."),
        _q("Nothing is broken but a user needs access to a shared folder. This is a(n):",
           "Unplanned service interruption", "Service request", "Authorized configuration change", "Underlying cause of incidents",
           "B", "No broken service — it's a request for something new."),
        _q("A ticket asks you to grant a contractor access to the HR folder 'urgently'. Correct outcome:",
           "Grant urgent access now", "Obtain authorized approval",
           "Grant temporary read access", "Close the request",
           "B", "Sensitive-data access requires the approval path; urgency does not replace authorization."),
        _q("A good handoff note contains: (select all that apply)",
           "Current state and what's been ruled out with evidence", "The exact next step you would take",
           "Any promise made to the user", "'See above'",
           "A", "The next tech continues without re-asking anything; 'see above' is the anti-handoff.", multi="A,B,C"),
        _q("You promised the user an update by 3 PM but have no fix yet. At 3 PM you should:",
           "Wait for good news", "Send a status update",
           "Close and reopen the ticket", "Escalate without updating the user",
           "B", "Send the promised update with the current status, the work underway, and the next update time. Honest motion beats silence; missed updates destroy trust faster than slow fixes."),
    ],
})


def ANCHORS(inv, rc, fix, ver, com):
    return {
        "investigation": inv,
        "root_cause": rc,
        "safe_fix_or_escalation": fix,
        "verification": ver,
        "communication": com,
    }

NEW_TICKETS = [
    {
        "title": "Desktop won't turn on at all",
        "description": (
            "Front desk reports their desktop is completely dead this morning — 'not even a light'. "
            "It worked Friday. Cleaning crew was in over the weekend. The user has a deadline at noon "
            "and is anxious. You are remote; the user can follow instructions and send phone photos.\n\n"
            "NOTE: if your diagnosis points to internal component failure, the correct outcome is a "
            "complete diagnostic note and escalation to hardware depot — do NOT attempt board-level repair."
        ),
        "difficulty": 2, "week_number": 2, "category": "Hardware", "domain_id": "1.0",
        "root_cause": "Power strip switched off / unplugged at the wall by the cleaning crew; if parameters vary, PSU failure requiring depot escalation",
        "root_cause_type": "hardware_power",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Verify power at the wall and cable seating (photo evidence)", "required_mention": ["outlet", "wall", "cable", "power strip"], "weight": 0.3},
            {"id": 2, "step": "Check for any LEDs/fans/beeps when pressing power", "required_mention": ["led", "fan", "beep", "light"], "weight": 0.3},
            {"id": 3, "step": "Attempt a different outlet / known-good cable", "required_mention": ["different outlet", "another outlet", "known-good", "swap"], "weight": 0.2},
            {"id": 4, "step": "Decision: fixed at power path OR clean escalation to depot with findings", "required_mention": ["escalat", "depot", "resolved", "power strip"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Photo of outlet/power strip state and cable seating", "validation": {}},
            {"type": "screenshot", "description": "Ticket note showing diagnostic sequence and outcome", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = wall power, cable, and POST signs checked in order before any conclusion",
            "2 = power-path cause identified specifically (or PSU correctly implicated)",
            "2 = fixed at the power path with no parts swapped, OR escalated to depot with the full diagnostic note; board-level attempts = 0",
            "2 = machine boots and user confirms, OR escalation note lets depot start immediately",
            "2 = calm deadline-aware user message with a realistic next step",
        ),
        "model_answer": (
            "Ask the user for a photo of the rear power connection and the power strip. Verify the wall "
            "outlet works (lamp test) and the strip is on. Reseat the power cable. If still dead with zero "
            "LEDs, try a known-good outlet. If genuinely no power signs remain, record findings (no LEDs, "
            "no fans, outlet verified, cable reseated/swapped) and escalate to hardware depot for suspected "
            "PSU failure. User message: acknowledge the deadline, offer a loaner/hot-desk while hardware is "
            "handled."
        ),
        "hints": [
            "Start at the wall, not inside the case.",
            "Zero LEDs and zero fan movement points at the power path, not RAM or disk.",
            "Lamp-test the outlet, reseat the cable, then try a known-good outlet — in that order, with photos.",
            "If no power signs survive all of that: stop. Write the diagnostic note (what you verified, in order) and escalate to depot for suspected PSU failure. Offer the user an interim workspace.",
        ],
        "parameters": {"placeholders": {
            "DEPT": ["Front desk", "Accounts payable", "Reception", "Dispatch", "Records"],
        }},
    },
    {
        "title": "My desktop looks brand new and my files are gone",
        "description": (
            "{{USER}} calls in a panic: they logged in this morning and everything is gone — desktop "
            "empty, default wallpaper, browser has no bookmarks. 'Someone wiped my computer!' They have "
            "worked here four years. Machine: Windows 11, local profile."
        ),
        "difficulty": 2, "week_number": 3, "category": "Windows", "domain_id": "3.0",
        "root_cause": "Windows failed to load the user's profile and signed them into a temporary profile; original profile intact on disk",
        "root_cause_type": "temp_profile",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Calm the user and establish files are likely intact", "required_mention": ["temp", "temporary profile", "intact", "not deleted"], "weight": 0.2},
            {"id": 2, "step": "Confirm temp profile via Event Viewer 1511/1515 or C:\\Users listing", "required_mention": ["1511", "1515", "event", "c:\\users"], "weight": 0.3},
            {"id": 3, "step": "Verify original profile folder and its data exist", "required_mention": ["profile folder", "documents", "original profile"], "weight": 0.2},
            {"id": 4, "step": "Restore correct profile loading and verify at a fresh sign-in", "required_mention": ["sign out", "reboot", "logged in", "restored"], "weight": 0.3},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Event Viewer showing User Profile Service 1511/1515", "validation": {"must_contain_text": ["151"]}},
            {"type": "screenshot", "description": "User signed in with original desktop/files visible", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = temp-profile signature recognized and confirmed with Event Viewer/C:\\Users evidence before changes",
            "2 = profile-load failure identified (not 'files deleted', not malware)",
            "2 = minimal fix restoring original profile; recreating the profile from scratch without data verification = 0-1",
            "2 = fresh sign-in shows the user's real desktop and files; user confirms",
            "2 = panic de-escalated early with an honest 'files are safe' explanation",
        ),
        "model_answer": (
            "Recognize the temp-profile signature. Reassure the user their data is almost certainly intact. "
            "Confirm via Event Viewer (User Profile Service 1511/1515) and by listing C:\\Users — the "
            "original profile folder with Documents present. Fix profile loading (clear the .bak SID state "
            "per standard procedure / reboot), sign in fresh, verify the real desktop loads. Show the user "
            "their files. Document event IDs and the fix in internal notes."
        ),
        "hints": [
            "The 'brand-new desktop' pattern has a classic cause that does NOT involve data loss.",
            "Event Viewer → Windows Logs → Application: look for User Profile Service events.",
            "Events 1511/1515 confirm it. Check C:\\Users — is the original profile folder still there with the user's Documents?",
            "It's a temporary profile. Reassure the user, fix profile loading per standard procedure, then have them sign out/in and verify their real desktop returns before closing.",
        ],
        "parameters": {"placeholders": {
            "USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
        }},
    },
    {
        "title": "Windows Update keeps failing",
        "description": (
            "A user reports Windows Update has failed 'every day this week'. Update history shows the same "
            "KB failing repeatedly with error {{ERROR_CODE}}. The machine otherwise works. Management wants "
            "machines patched before the compliance audit next week."
        ),
        "difficulty": 2, "week_number": 3, "category": "Windows", "domain_id": "3.0",
        "root_cause": "Windows Update cache corruption; the safe sequence (troubleshooter, service restart, SoftwareDistribution rename) resolves it",
        "root_cause_type": "update_failure",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Capture failing KB and error code from Update history", "required_mention": ["kb", "error code", "history"], "weight": 0.25},
            {"id": 2, "step": "Run the Windows Update troubleshooter", "required_mention": ["troubleshooter"], "weight": 0.2},
            {"id": 3, "step": "Restart update services / rename SoftwareDistribution", "required_mention": ["softwaredistribution", "wuauserv", "service"], "weight": 0.3},
            {"id": 4, "step": "Retry, verify success or escalate with the documented code", "required_mention": ["retry", "installed", "escalat", "verified"], "weight": 0.25},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Update history showing the failing KB + error code", "validation": {}},
            {"type": "screenshot", "description": "Successful install after the fix (or escalation note)", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = KB + error code captured first and used to guide the sequence",
            "2 = cache corruption identified as the cause (or correctly ruled out)",
            "2 = the safe sequence in order, RENAMING SoftwareDistribution (deleting = 1); stopping at the stop-point and escalating if it still fails = 2",
            "2 = update shown installed in history, or a clean escalation with code documented",
            "2 = audit-deadline-aware note to the user/manager",
        ),
        "model_answer": (
            "Record the KB number and error code from Settings → Windows Update → Update history. Run the "
            "built-in troubleshooter. If it persists: stop the Windows Update service (net stop wuauserv), "
            "rename C:\\Windows\\SoftwareDistribution to SoftwareDistribution.old, start the service, retry. "
            "Verify the KB now shows Successfully installed. If the SAME KB still fails, do not improvise "
            "servicing-stack surgery — document the code and escalate."
        ),
        "hints": [
            "Update history contains two facts you need before touching anything.",
            "There is a standard safe sequence for repeated update failures — it starts with a built-in tool.",
            "Troubleshooter → restart the update service → rename (not delete) SoftwareDistribution → retry.",
            "If the same KB fails after the full sequence, that's the stop point: document KB + error code and escalate rather than digging into the servicing stack.",
        ],
        "parameters": {"placeholders": {
            "ERROR_CODE": ["0x80070002", "0x8024402F", "0x80073712", "0x800F0922", "0x80242016"],
        }},
    },
    {
        "title": "Strange pop-ups and the mouse moved by itself",
        "description": (
            "{{USER}} reports their PC showed 'weird antivirus pop-ups' yesterday and this morning they "
            "'watched the mouse move on its own for a few seconds'. They use this machine for invoicing "
            "and are still working on it right now.\n\n"
            "Your role scope: entry-level support. Security incidents beyond routine Defender detections "
            "must go to the security escalation path."
        ),
        "difficulty": 2, "week_number": 4, "category": "Security", "domain_id": "4.0",
        "root_cause": "Suspected active compromise (rogue remote access); correct outcome is isolation, evidence preservation, and security escalation — NOT remediation",
        "root_cause_type": "security_escalation",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Instruct user to stop using the machine; disconnect it from the network (do not power off)", "required_mention": ["disconnect", "network", "isolat", "unplug"], "weight": 0.3},
            {"id": 2, "step": "Preserve evidence: no scans/deletions/reboots that destroy volatile state", "required_mention": ["preserve", "evidence", "do not", "avoid reboot"], "weight": 0.25},
            {"id": 3, "step": "Document observations verbatim with times", "required_mention": ["document", "time", "observed"], "weight": 0.2},
            {"id": 4, "step": "Escalate to security with the full note; advise credential caution", "required_mention": ["escalat", "security", "password", "credential"], "weight": 0.25},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Escalation note with timeline of observations", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = symptoms recognized as possible active compromise; times and observations collected",
            "2 = 'suspected active remote access / compromise' named as the working cause",
            "2 = isolated from network, evidence preserved, escalated. ANY remediation attempt (scans that quarantine, deleting files, reimaging) or powering off = 0",
            "2 = handoff verified: security has what they need to act immediately",
            "2 = user calmly instructed without panic or blame; told what to do about passwords used on that machine",
        ),
        "model_answer": (
            "Treat as suspected active compromise. Have the user stop work immediately; disconnect the "
            "network cable / disable Wi-Fi but LEAVE THE MACHINE POWERED ON (volatile evidence). Do not run "
            "cleanup tools. Record the user's observations verbatim with times. Escalate to the security "
            "path with the timeline, machine name, and user account, and advise the user to change any "
            "passwords they used on that machine FROM A DIFFERENT DEVICE. This ticket is passed by a clean "
            "escalation — attempting removal fails it."
        ),
        "hints": [
            "'Mouse moving by itself' changes what kind of ticket this is.",
            "Two priorities beat 'fixing' here: stopping the bleeding and keeping evidence intact.",
            "Isolate from the network without powering off; document everything with times; touch nothing else.",
            "The correct resolution IS the escalation: network isolation, evidence preserved, timeline documented, security notified, user told to change passwords from another device.",
        ],
        "parameters": {"placeholders": {
            "USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
        }},
    },
    {
        "title": "Multi-Ticket Simulation 1 — three tickets, one afternoon",
        "description": (
            "It's 1:00 PM. Three tickets land within five minutes. First, submit your PRIORITY ORDER with "
            "a one-line justification for each; then work all three in your chosen order, documenting each.\n\n"
            "TICKET A ({{VIP}}, executive): 'My printer is jammed and I have a board pack to print for a "
            "meeting at 4.' Their personal desk printer.\n\n"
            "TICKET B (Facilities, 40 users): 'Nobody in our department can open the shared drive since "
            "lunch. We get \"\\\\FILES01\\Facilities is not accessible\".' \n\n"
            "TICKET C ({{USER2}}): 'The server is down!! I can't get to my files!' — On questioning, "
            "OTHER users can reach the same share fine; this user recently changed their password.\n\n"
            "One of these descriptions is misleading. Handle accordingly."
        ),
        "difficulty": 2, "week_number": 4, "category": "Simulation", "domain_id": "5.0",
        "root_cause": (
            "A: mechanical jam, quick clear with tray guidance. B: genuine outage — share/service issue on FILES01, "
            "highest impact, may require escalation if server-side. C: misleading — 'server down' is actually cached "
            "credentials after a password change; reconnect the mapped drive with new credentials."
        ),
        "root_cause_type": "multi_incident",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Priority order stated WITH justification (B first: impact×urgency)", "required_mention": ["priority", "impact", "urgency", "order"], "weight": 0.25},
            {"id": 2, "step": "Ticket B: scope confirmed (multiple users), server/share investigated or escalated with evidence", "required_mention": ["files01", "share", "multiple users", "escalat"], "weight": 0.3},
            {"id": 3, "step": "Ticket C: 'server down' claim tested and disproven; credential cause found", "required_mention": ["password", "credential", "mapped drive", "other users"], "weight": 0.25},
            {"id": 4, "step": "Ticket A: handled with realistic expectation-setting against the 4 PM deadline", "required_mention": ["printer", "jam", "4", "meeting"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Priority order + justifications (top of writeup)", "validation": {}},
            {"type": "screenshot", "description": "Per-ticket notes: investigation, outcome, user message", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = each ticket triaged before deep-diving any; C's claim tested against other users",
            "2 = all three root causes right, including recognizing C's misleading description",
            "2 = B prioritized first with justification; safe handling throughout; A not allowed to jump the queue on VIP pressure alone",
            "2 = each ticket verified with its user (B: share opens; C: drive reconnects; A: test page)",
            "2 = three distinct user-facing messages in the right tone, incl. de-escalating C without blame",
        ),
        "model_answer": (
            "Order: B (40 users, core process) → C (fast fix once diagnosed; user is loud but single) → A "
            "(single user, deadline at 4 leaves buffer; set expectations immediately). B: confirm scope with "
            "a second user, test \\\\FILES01 reachability, check the share/service state; if server-side "
            "beyond scope, escalate with evidence and notify the department with an ETA. C: other users "
            "unaffected disproves 'server down'; recent password change + mapped drive = stale cached "
            "credentials; reconnect drive with new credentials, verify access, explain kindly. A: guide the "
            "user through tray/jam clearing by phone with a photo; verify with a test page; if hardware "
            "fault, arrange printing via the shared floor printer before 4 PM. Three separate closure notes."
        ),
        "hints": [
            "Do not start with the loudest ticket. Rank first: who is blocked, how many, how core?",
            "Ticket C: before believing 'the server is down', check whether ANYONE ELSE is affected.",
            "C's giveaway is the recent password change — think about what still holds the old password.",
            "Order B→C→A. B: confirm scope, test the share, escalate with evidence if server-side. C: reconnect the mapped drive with new credentials. A: guided jam clearing + a fallback printer before 4.",
        ],
        "parameters": {"placeholders": {
            "VIP": ["CFO Daniels", "VP Alvarez", "Director Chen", "COO Brooks", "VP Okafor"],
            "USER2": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
        }},
    },
]

# Five-anchor + hint-ladder + parameter retrofits for the 8 original seed
# tickets (matched by title substring). CB-04 second half.
TICKET_RETROFITS = {
    "DNS resolution failing": {
        "scoring_anchors": ANCHORS(
            "2 = ping by IP vs name compared and ipconfig inspected before changes",
            "2 = wrong DNS server address identified specifically",
            "2 = only the DNS setting corrected; no stack resets/reboots",
            "2 = nslookup + browsing re-tested and confirmed with the user",
            "2 = plain-language explanation of what a DNS setting is"),
        "hints": [
            "Working ping to 8.8.8.8 with failing websites narrows this to one layer.",
            "Compare reaching things by IP address vs by name.",
            "ipconfig /all — look hard at the DNS server entries.",
            "The DNS server address is wrong. Correct it, ipconfig /flushdns, verify with nslookup and real browsing."],
        "parameters": {"placeholders": {"BAD_DNS": ["10.99.99.99", "192.168.250.1", "172.31.99.53", "10.0.99.8", "192.0.2.53"]}},
    },
    "locked out": {
        "scoring_anchors": ANCHORS(
            "2 = lockout cause investigated (bad attempts? stale credentials elsewhere?) not just cleared",
            "2 = repeated failed attempts identified as the trigger, incl. WHERE from if evidence allows",
            "2 = unlock performed with identity verified; no password given over an unverified channel",
            "2 = user logs in successfully after unlock",
            "2 = user told, kindly, what causes lockouts (saved old passwords on phone/other devices)"),
        "hints": [
            "Unlocking is one click — the ticket is about why it locked.",
            "Verify you're talking to the account owner before touching anything.",
            "Check for saved/stale credentials on other devices still retrying the old password.",
            "Unlock the account, have the user sign in while you watch it stay unlocked, and hunt the device retrying old credentials if it re-locks."],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"]}},
    },
    "printer": {
        "scoring_anchors": ANCHORS(
            "2 = queue, connectivity, and driver state checked in a sensible order",
            "2 = actual failure point named (spooler/queue/connectivity/driver), not 'printer fixed'",
            "2 = least-disruptive fix; no reinstalling everything by default",
            "2 = test page printed and user confirms their real document prints",
            "2 = user-facing note avoids blaming user error even if it was one"),
        "hints": [
            "Is the job leaving the computer at all? The queue answers that.",
            "A stuck queue points at the spooler; an empty queue points at connectivity or the wrong printer selected.",
            "Restart the Print Spooler service and clear stuck jobs, then retest.",
            "Spooler restart + queue clear, verify with a test page, then the user's actual document."],
    },
    "Wi-Fi": {
        "scoring_anchors": ANCHORS(
            "2 = signal, adapter state, and ipconfig checked before blaming 'the Wi-Fi'",
            "2 = specific failure identified (auth, DHCP on wireless, driver, or AP-side)",
            "2 = client-side fix scoped correctly; AP/controller issues escalated not guessed at",
            "2 = connection stable through a re-test (not just 'connected once')",
            "2 = user told what to try first next time in one sentence"),
        "hints": [
            "Separate 'connected with no internet' from 'cannot connect' — different problems.",
            "ipconfig on the wireless adapter: what address did it get?",
            "169.254.x.x on Wi-Fi = associated but DHCP failed; forget/rejoin the network and check the adapter driver.",
            "Forget the network, rejoin with correct credentials, confirm a real DHCP address, and verify with the three-step ping test."],
    },
    "slow": {
        "scoring_anchors": ANCHORS(
            "2 = Task Manager evidence gathered (top CPU/RAM/disk) before any cleanup ritual",
            "2 = the actual resource hog / cause named with numbers",
            "2 = targeted fix (offending process/startup item/disk issue), not blanket 'cleanup + reboot'",
            "2 = before/after resource numbers captured",
            "2 = honest user note about what was slow and what changed"),
        "hints": [
            "Measure first: which resource is pinned — CPU, RAM, or disk?",
            "Task Manager → Processes sorted by the pinned column; screenshot it.",
            "100% disk with a specific process on a HDD machine is a classic; also check Startup impact.",
            "Address the specific hog (service, startup item, or failing disk), then capture the after numbers to prove it."],
    },
    "External hard drive": {
        "scoring_anchors": ANCHORS(
            "2 = port/cable/another-machine isolation done before software changes",
            "2 = failure localized correctly (cable/port/enclosure/disk/letter-assignment)",
            "2 = data-safety-first choices; no format suggestions while data recovery matters",
            "2 = drive accessible and a real file opened, or honest data-risk escalation",
            "2 = user told the backup moral without a lecture"),
        "hints": [
            "Isolate: different port, different cable, different machine — which combination works?",
            "Disk Management: does the disk appear at all? With a letter?",
            "Appears without a letter = assign one. Doesn't appear anywhere = hardware path.",
            "If it's the disk itself and the data matters, stop and escalate for recovery — do not format, do not run repair writes."],
    },
    "SMTP": {
        "scoring_anchors": ANCHORS(
            "2 = exact error captured; send vs receive scoped; one user vs many checked",
            "2 = auth failure isolated to the actual credential/setting at fault",
            "2 = only the failing setting corrected; no profile rebuilds by default",
            "2 = test message sent AND received",
            "2 = user note explains in one line why sending broke"),
        "hints": [
            "Get the exact error text — SMTP errors are specific.",
            "Can they RECEIVE? Receive-works/send-fails narrows it to the outgoing path.",
            "Recent password change + saved SMTP credentials is a classic auth-failure pair.",
            "Update the stored credentials/settings for the outgoing server, send a test to yourself, and confirm a reply round-trips."],
    },
    "domain": {
        "scoring_anchors": ANCHORS(
            "2 = current domain/network state gathered (whoami, ipconfig, DNS to DC) before rejoining",
            "2 = trust/join failure cause identified (secure channel, DNS to DC, duplicate name)",
            "2 = least-drastic repair chosen; full unjoin/rejoin only when justified",
            "2 = domain sign-in verified with the user's own account",
            "2 = downtime expectations set before reboots"),
        "hints": [
            "Check DNS first — domain operations live and die by DNS to the DC.",
            "The trust relationship can be repaired without a full unjoin on modern systems.",
            "Test-ComputerSecureChannel -Repair (or the documented equivalent) beats unjoin/rejoin.",
            "Fix DNS to the DC if broken, repair the secure channel, reboot once, and verify a domain logon."],
    },
}


# --------------------------------------------------------------------- seeding

def seed_phase_a(db) -> dict:
    """Idempotent Phase A content seed. Returns counts for the seed summary."""
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Quiz
    from app.models.ticket import Ticket

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0,
              "tickets": 0, "retrofits": 0}

    # Modules + lessons (match module by code, lesson by module+order)
    prev_module = db.query(Module).filter(Module.code == "MOD-000").first()
    for spec in MODULES:
        module = db.query(Module).filter(Module.code == spec["code"]).first()
        fields = {k: spec[k] for k in ("title", "description", "target_role",
                  "difficulty_band", "estimated_hours", "module_order", "unlock_threshold")}
        if module is None:
            module = Module(code=spec["code"], **fields)
            db.add(module)
            counts["modules"] += 1
        else:
            for k, v in fields.items():
                setattr(module, k, v)
        if spec["code"] == "MOD-001":
            # Week 1 is gated by current Week 0 lesson + quiz progression, not
            # MOD-000 mastery. Do not restore the prerequisite removed by 0030.
            module.prerequisite_module_id = None
        elif prev_module is not None:
            module.prerequisite_module_id = prev_module.id if module.id != prev_module.id else None
        db.flush()
        for lspec in spec["lessons"]:
            lesson = (db.query(Lesson)
                      .filter(Lesson.module_id == module.id,
                              Lesson.lesson_order == lspec["lesson_order"]).first())
            lfields = {k: lspec.get(k) for k in ("title", "summary", "outcomes",
                       "estimated_minutes", "required_notes_template", "status",
                       "related_activity_stable_id")}
            if lesson is None:
                db.add(Lesson(module_id=module.id, lesson_order=lspec["lesson_order"], **lfields))
                counts["lessons"] += 1
            else:
                for k, v in lfields.items():
                    setattr(lesson, k, v)
        db.flush()
        prev_module = module

    from app.services.seed_question_sync import sync_seed_questions

    # Quizzes + questions. Authored questions update in place by seed_key so
    # existing attempt/review references keep their stable question IDs.
    for qspec in QUIZZES:
        quiz = db.query(Quiz).filter(Quiz.title == qspec["title"]).first()
        lesson = (db.query(Lesson)
                  .filter(Lesson.title == qspec["lesson_title"]).first())
        if quiz is None:
            quiz = Quiz(title=qspec["title"], week_number=qspec["week_number"],
                        domain_id=qspec["domain_id"], question_count=len(qspec["questions"]),
                        status=QUIZ_STATUS_PUBLISHED,
                        lesson_id=lesson.id if lesson else None)
            db.add(quiz)
            counts["quizzes"] += 1
            db.flush()
        else:
            quiz.week_number = qspec["week_number"]
            quiz.domain_id = qspec["domain_id"]
            quiz.question_count = len(qspec["questions"])
            quiz.status = QUIZ_STATUS_PUBLISHED
            quiz.lesson_id = lesson.id if lesson else quiz.lesson_id
        counts["questions"] += sync_seed_questions(db, quiz, qspec["questions"])
        db.flush()

    # New tickets (match by title)
    for tspec in NEW_TICKETS:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()

    # Retrofits (title substring match against original seed tickets)
    for needle, patch in TICKET_RETROFITS.items():
        ticket = db.query(Ticket).filter(Ticket.title.ilike(f"%{needle}%")).first()
        if ticket is None:
            continue
        ticket.scoring_anchors = patch["scoring_anchors"]
        ticket.hints = patch["hints"]
        if patch.get("parameters"):
            ticket.parameters = patch["parameters"]
        counts["retrofits"] += 1
    db.flush()
    return counts
