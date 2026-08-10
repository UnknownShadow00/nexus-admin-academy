"""Phase B (Weeks 5-8) curriculum content — Workplace Help Desk.

Same structured-seed pattern as seed_phase_a.py. Idempotent. Gate 2 references
MOD-005..MOD-008; seeding this file makes Gate 2 satisfiable.

Infrastructure honesty: every lab here runs on the student's own Windows
machine or a mentor-cloned manual VM (MANUAL-VM). Nothing depends on the
automated Proxmox/Guacamole pipeline, whose P0s remain open.
"""

from seed_phase_a import ANCHORS, NOTES_TEMPLATE, _q

MODULES_B = [
    {
        "code": "MOD-005",
        "title": "Windows Deep Troubleshooting",
        "description": "Startup failures, application crashes, Event Viewer forensics, disk-space incidents. Week 5.",
        "target_role": "Support Technician II",
        "difficulty_band": 2,
        "estimated_hours": 15,
        "module_order": 6,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Startup Failures and Recovery Options",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Map WHERE boot dies to WHAT to try:\n"
                    "- Before the Windows logo → firmware/disk/bootloader territory (Week 2 skills).\n"
                    "- Spinning dots forever → driver or service hang; Safe Mode is the diagnostic fork: "
                    "boots in Safe Mode = a third-party driver/service is the suspect; fails in Safe Mode "
                    "too = deeper corruption.\n"
                    "- Automatic Repair loop → use the Windows Recovery Environment (WinRE) menu "
                    "deliberately: Startup Repair once, then Command Prompt for evidence (sfc /scannow "
                    "/offbootdir), NOT repeated blind repair attempts.\n"
                    "- Login fine, desktop takes minutes → not a boot problem: startup apps and profile "
                    "loading (Task Manager → Startup; Event 6005/6006 timestamps bracket boot time).\n\n"
                    "SAFE MODE PROPERLY: Settings → Recovery → Advanced startup, or interrupt boot 3x for "
                    "WinRE. In Safe Mode: msconfig for selective startup, Event Viewer for the last errors "
                    "before hang, Device Manager for recently-changed drivers.\n\n"
                    "ROLLBACK THINKING: System Restore points and 'uninstall latest quality update' in "
                    "WinRE are your undo buttons — check what restore points exist BEFORE making changes.\n\n"
                    "VERIFICATION HABIT: after any startup fix, reboot TWICE. Once proves it can boot; "
                    "twice proves it boots reliably.\n\n"
                    "COMMON MISTAKES: reinstalling Windows as a second step; running Startup Repair five "
                    "times hoping for different results; fixing the symptom (slow login) with hardware "
                    "blame when Startup shows a 40-second updater."
                ),
                "outcomes": [
                    "Localize a startup failure to firmware/bootloader, driver/service hang, or login-time slowness",
                    "Use Safe Mode as a diagnostic fork and WinRE tools deliberately",
                    "Identify rollback options (restore points, update uninstall) before changing anything",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Application Crashes and Hangs",
                "lesson_order": 2,
                "estimated_minutes": 75,
                "summary": (
                    "CRASH vs HANG vs WON'T START — three different investigations:\n"
                    "CRASH (closes with/without error): Event Viewer → Application log → Event 1000 "
                    "(Application Error) names the faulting MODULE. Faulting module = the app's own exe "
                    "→ app problem (repair/reinstall/update). Faulting module = a DLL from something else "
                    "(an add-in, a graphics driver) → THAT is your suspect.\n"
                    "HANG (white window, 'Not Responding'): Event 1002 logs it. Ask WHAT it was doing — "
                    "opening a huge file, waiting on a network path? A hang on 'File → Open' with a dead "
                    "mapped drive is a NETWORK ticket wearing an app costume.\n"
                    "WON'T START: silent failure → try starting from an elevated prompt to see the error; "
                    "check antivirus quarantine; corrupted per-user config → test with a DIFFERENT Windows "
                    "user: works there = user-profile-level config, not the app.\n\n"
                    "THE REPAIR LADDER (least → most destructive): restart app → repair install (Apps → "
                    "Modify/Repair) → clear per-user app config → reinstall → escalate to app vendor. Each "
                    "step: note what you did so the next tech doesn't repeat it.\n\n"
                    "COMMON MISTAKES: reinstalling first (destroys evidence, often doesn't fix per-user "
                    "config causes); ignoring 'what changed' (updates, new add-ins, new file server)."
                ),
                "outcomes": [
                    "Differentiate crash, hang, and won't-start failures and pick the matching investigation",
                    "Read Event 1000/1002 and use the faulting module to assign blame correctly",
                    "Apply the repair ladder least-destructive-first with documentation at each step",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Disk-Space Incidents",
                "lesson_order": 3,
                "estimated_minutes": 60,
                "summary": (
                    "'Disk full' tickets are measurement problems. MEASURE FIRST: Settings → Storage "
                    "breaks down categories; for truth use a folder-size view (built-in: `dir /s` "
                    "summaries, or the Storage settings per-folder view). The usual suspects, in order:\n"
                    "1. User data hoards (Downloads, video files) — a conversation, not a deletion spree.\n"
                    "2. Windows Update caches and old update files → Disk Cleanup as admin ('Clean up "
                    "system files') is the SAFE removal path.\n"
                    "3. Temp files that never got cleaned (%TEMP%).\n"
                    "4. Shadow copies / restore points ballooning (vssadmin list shadowstorage to see).\n"
                    "5. A runaway log file from one application — find it, and fix the APP, not just the "
                    "file, or it returns next month.\n\n"
                    "WHAT YOU DO NOT DELETE: anything in another user's profile without approval; "
                    "hiberfil.sys/pagefile.sys by hand (there are settings for those); anything you can't "
                    "name. 'I freed space by deleting a folder I didn't recognize' is a résumé-updating "
                    "event.\n\n"
                    "VERIFICATION: before/after free-space screenshots, and WHAT consumed the space in the "
                    "note — the pattern matters for recurrence.\n\n"
                    "COMMON MISTAKES: compressing C:\\ as a fix; deleting the Windows.old the user's files "
                    "were about to be recovered from; freeing 2 GB when 200 MB/day is being written by a "
                    "broken app."
                ),
                "outcomes": [
                    "Measure what actually consumes disk space before deleting anything",
                    "Free space via the safe paths (Disk Cleanup system files, temp, update cache) and know the do-not-delete list",
                    "Identify recurring growth (runaway logs) and address the source, not the symptom",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-006",
        "title": "Accounts, Profiles, and Permissions in Practice",
        "description": "Password resets, profile recovery, NTFS vs share permissions, mapped drives, access-denied incidents. Week 6.",
        "target_role": "Support Technician II",
        "difficulty_band": 2,
        "estimated_hours": 15,
        "module_order": 7,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Account Lifecycle Support",
                "lesson_order": 1,
                "estimated_minutes": 75,
                "summary": (
                    "The four account tickets you will handle weekly, and the safety rail on each:\n"
                    "PASSWORD RESET: the safety rail is IDENTITY VERIFICATION — callback to a number on "
                    "file, manager confirmation, or the org's defined process. Social engineers' #1 attack "
                    "is a phone call to the help desk. Never read a new password over an unverified "
                    "channel; use one-time links or force change-at-next-logon.\n"
                    "LOCKOUT: unlocking is trivial; the ticket is WHY. Repeated re-locks = a stale saved "
                    "credential (phone mail app, mapped drive, scheduled task) still replaying the old "
                    "password. Find the device, not just the symptom.\n"
                    "DISABLED ACCOUNT: 'my account is disabled' — do NOT just re-enable. Accounts get "
                    "disabled BY PROCESS (leave, security hold, HR action). Verify with the account's "
                    "owner-of-record (manager/HR) before touching. Wrong re-enable = security incident.\n"
                    "NEW ACCOUNT / ACCESS REQUEST: a service request with an approval chain. Your job is "
                    "routing and least-privilege defaults, not creativity.\n\n"
                    "PROFILE RECOVERY (continuing Week 3): temp-profile fix sequence, and when a profile "
                    "is truly corrupt: create fresh profile, MIGRATE data (Desktop/Documents/etc.) with "
                    "the user watching, verify counts, THEN retire the old folder — never delete it same-day.\n\n"
                    "COMMON MISTAKES: resetting a password for a caller you didn't verify; re-enabling a "
                    "disabled account to be 'helpful'; 'fixing' recurring lockouts by asking the user to "
                    "stop typing wrong."
                ),
                "outcomes": [
                    "Execute password resets with identity verification and safe delivery",
                    "Trace recurring lockouts to the stale-credential device",
                    "Refuse-and-route correctly on disabled accounts and access requests",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "NTFS vs Share Permissions, For Real",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "Access to \\\\SERVER\\Share\\Folder passes TWO gates:\n"
                    "SHARE permissions (the door to the share, only over the network) and NTFS permissions "
                    "(the filesystem itself, always). Effective remote access = the MOST RESTRICTIVE of "
                    "the two. Classic confusions this explains:\n"
                    "- 'I can open it at the server console but not over the network' → share perms.\n"
                    "- 'I got the share open but the folder inside denies me' → NTFS.\n"
                    "- 'I'm in the right group but still denied' → group membership needs a fresh LOGON "
                    "token: sign out/in (the #1 forgotten step in access tickets).\n\n"
                    "STANDARD PRACTICE you'll meet on the job: share = Authenticated Users/Everyone "
                    "Full Control or Change, and do ALL real control with NTFS — one permission system to "
                    "reason about instead of two.\n\n"
                    "READING EFFECTIVE ACCESS: folder → Properties → Security → Advanced → Effective "
                    "Access → pick the user: Windows computes the group math for you. Screenshot = ticket "
                    "evidence.\n\n"
                    "MAPPED DRIVES: a mapped letter is a bookmark WITH SAVED CREDENTIALS. After password "
                    "changes: 'the server is down!' = the drive replaying old credentials (Simulation 1 "
                    "veterans know). net use shows current mappings and their state.\n\n"
                    "COMMON MISTAKES: granting the USER instead of the correct GROUP (unmaintainable); "
                    "Full Control where Modify suffices; forgetting sign-out after membership changes; "
                    "'fixing' by disabling inheritance without understanding what was inherited."
                ),
                "outcomes": [
                    "Predict effective remote access from combined share + NTFS permissions",
                    "Use Effective Access to prove why a user is denied and capture it as evidence",
                    "Resolve mapped-drive credential and group-token issues without shotgun fixes",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Access Requests and the Escalation Rail",
                "lesson_order": 3,
                "estimated_minutes": 45,
                "summary": (
                    "Some access tickets are traps for helpful technicians. The rail:\n"
                    "GRANTABLE AT YOUR LEVEL: access that matches the user's role and has an existing "
                    "group for it, with manager approval on record → add to group, document approver, "
                    "sign-out/in, verify.\n"
                    "NOT GRANTABLE AT YOUR LEVEL: HR/payroll/finance/executive folders, anything "
                    "personnel-sensitive, cross-department data, 'temporary' admin rights, contractor "
                    "access. Correct outcome = escalate WITH the request packaged: who, what, business "
                    "reason, requested duration, approver named. A clean escalation note IS the resolution "
                    "and scores 2/2 on safe_fix_or_escalation.\n\n"
                    "URGENCY IS NOT AUTHORIZATION. 'The CFO needs it in an hour' changes the escalation's "
                    "priority, not its necessity. You escalate FAST — you don't skip it.\n\n"
                    "LEAST PRIVILEGE IN PRACTICE: read-only unless write is stated; time-boxed when the "
                    "need is time-boxed; groups over individuals; document everything — access grants are "
                    "audited.\n\n"
                    "COMMON MISTAKES: granting 'just read-only' to sensitive data as a compromise (still "
                    "unauthorized); adding to a broader group than requested because it was easier."
                ),
                "outcomes": [
                    "Classify an access request as grantable-with-approval or escalate-only",
                    "Package an escalation so the approver can decide immediately",
                    "Apply least-privilege defaults (read-only, time-boxed, groups) when granting",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]

MODULES_B += [
    {
        "code": "MOD-007",
        "title": "Endpoint Security and Remote Support",
        "description": "Defender, firewall, malware response, phishing triage, RDP and remote-support practice. Week 7.",
        "target_role": "Support Technician II",
        "difficulty_band": 2,
        "estimated_hours": 15,
        "module_order": 8,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Defender and the Windows Firewall",
                "lesson_order": 1,
                "estimated_minutes": 75,
                "summary": (
                    "DEFENDER'S THREE SCANS and when each is right: QUICK (memory + common locations — "
                    "routine checks, 'is something obviously wrong'), FULL (every file — after a detection, "
                    "before declaring clean), OFFLINE (reboots into a trusted environment — for rootkit-"
                    "class suspicions where running-Windows can't be trusted to scan itself).\n"
                    "PROTECTION HISTORY is your evidence pane: what was detected, when, what action "
                    "Defender took (quarantined/removed/allowed). Screenshot it before touching anything — "
                    "detections can age out of the UI.\n\n"
                    "WINDOWS FIREWALL for support work: three profiles (Domain/Private/Public) and which "
                    "one is ACTIVE right now explains most 'it works at the office, fails at home' "
                    "mysteries. Reading inbound rules answers 'why can't anyone ping/RDP/reach the share "
                    "on this machine'. Diagnostic discipline: if you suspect the firewall, find the "
                    "BLOCKING RULE — 'I turned the firewall off and it worked' is a finding, never a fix; "
                    "turning it off and walking away fails the safe_fix anchor to 0.\n\n"
                    "SCOPE RAIL (this is Week 7's spine): entry-level role = detect, document, contain, "
                    "escalate. Defender auto-quarantined a common PUP and the machine is otherwise clean? "
                    "Document and note it. ANY sign of active compromise, repeated detections, or "
                    "credential theft indicators? That's Week 4's escalation ticket pattern — isolate and "
                    "hand to security. You are not the malware-removal team.\n\n"
                    "COMMON MISTAKES: disabling Defender/firewall 'to test' and forgetting; deleting "
                    "quarantine (destroys the security team's sample); declaring 'clean' off a quick scan."
                ),
                "outcomes": [
                    "Choose the correct Defender scan type for the situation and read Protection history as evidence",
                    "Identify the active firewall profile and locate a blocking rule instead of disabling the firewall",
                    "Apply the entry-level scope rail: detect, document, contain, escalate",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Malware Response and Phishing Triage",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "THE MALWARE-RESPONSE PROCEDURE (entry-level version, in order):\n"
                    "1. STOP the spread: disconnect network (cable out / Wi-Fi off). Leave power ON — "
                    "volatile evidence dies with a shutdown.\n"
                    "2. PRESERVE: no cleanup tools yet, no deleting, no reboot. Screenshot what the user "
                    "saw; note times verbatim.\n"
                    "3. ASSESS scope: what did the user DO (opened attachment? enabled macros? entered "
                    "credentials?) — this decides severity more than the malware name does.\n"
                    "4. ESCALATE with the timeline. If credentials were entered ANYWHERE suspicious: "
                    "passwords change NOW, from a DIFFERENT device, and MFA sessions get revoked.\n"
                    "5. REMEDIATE only what policy allows at your level (often: nothing beyond Defender's "
                    "own quarantine until security clears it).\n\n"
                    "PHISHING TRIAGE — the 60-second read: sender address vs display name (the classic "
                    "mismatch), urgency + authority + unusual channel ('CEO' asking for gift cards), "
                    "hover-don't-click link targets, unexpected attachments (esp. macro-enabled Office "
                    "files, .html, .iso/.zip chains). USER REPORTS A PHISH: thank them genuinely (you "
                    "want a culture where reporting is rewarded), get the original as an attachment if "
                    "possible (forwarding strips headers), check whether they clicked/entered anything, "
                    "report per procedure, and if credentials went in → step 4 above, immediately.\n\n"
                    "COMMON MISTAKES: powering off an infected machine; testing the suspicious link "
                    "'to see'; shaming the user (guarantees the next incident goes unreported); "
                    "remediating beyond your scope because the fix seemed obvious."
                ),
                "outcomes": [
                    "Execute the five-step malware response: stop, preserve, assess, escalate, bounded remediation",
                    "Triage a reported email for phishing indicators in under two minutes",
                    "Handle entered-credentials cases with immediate, correctly-sequenced containment",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Remote Desktop and Remote Support",
                "lesson_order": 3,
                "estimated_minutes": 75,
                "summary": (
                    "RDP TROUBLESHOOTING LADDER — 'can't RDP to X' walks four gates in order:\n"
                    "1. NETWORK: can you ping/reach the host at all? (No → Week 8's networking, not RDP.)\n"
                    "2. SERVICE: is Remote Desktop ENABLED on the target (Settings → System → Remote "
                    "Desktop)? Is the machine awake (power/sleep policies kill more RDP than firewalls)?\n"
                    "3. FIREWALL: is the Remote Desktop inbound rule enabled for the ACTIVE profile? "
                    "(Port 3389 by default.)\n"
                    "4. PERMISSION: is the user in Remote Desktop Users (or an admin) ON THE TARGET? "
                    "'Access denied' after a connection attempt = gate 4, not gates 1-3.\n"
                    "The error message tells you which gate: timeout = 1/2, instant refusal = 3, "
                    "credential/denied errors = 4.\n\n"
                    "REMOTE SUPPORT ETIQUETTE (graded on communication): ASK before connecting, every "
                    "time — consent is not a formality; announce what you're about to do before doing it; "
                    "no reading personal files/messages beyond the task; if you must reboot, warn and let "
                    "them save; close the session in front of them and say so. Quick Assist (built-in) vs "
                    "RDP: Quick Assist SHARES the user's session (they watch you work — ideal for "
                    "support); RDP TAKES a session (Windows client OSes log the user out — fine for "
                    "servers/unattended, rude mid-workday).\n\n"
                    "COMMON MISTAKES: blaming 'the VPN' without walking the gates; connecting unannounced "
                    "('the mouse moved by itself' — remember Week 4's ticket? Don't be the cause); "
                    "leaving remote sessions open."
                ),
                "outcomes": [
                    "Walk the four-gate RDP ladder and map error types to the failing gate",
                    "Choose Quick Assist vs RDP appropriately and explain the session difference",
                    "Conduct a remote session with consent, narration, and clean closure",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-008",
        "title": "Client Networking and the Workplace Simulation",
        "description": "DHCP/DNS/gateway triage, network printing, multi-ticket operations, Gate 2. Week 8.",
        "target_role": "Support Technician II",
        "difficulty_band": 2,
        "estimated_hours": 16,
        "module_order": 9,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "The Client-Side Network Triage Tree",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "One tree resolves 90% of 'no internet' tickets. Run it in order, capture output at "
                    "each node:\n"
                    "1. ipconfig /all — WHAT AM I?\n"
                    "   • 169.254.x.x → DHCP FAILED. Branch: is it just me (port/cable/NIC) or everyone "
                    "(DHCP server/scope — escalate with evidence)? ipconfig /release + /renew retests "
                    "after any fix.\n"
                    "   • Real IP, empty/wrong gateway → local config or DHCP scope options problem.\n"
                    "   • Real IP + gateway + DNS listed → continue.\n"
                    "2. ping <gateway> — CAN I LEAVE THE ROOM? Fail = local network/switch port/cable.\n"
                    "3. ping 1.1.1.1 — CAN I REACH THE INTERNET? Gateway ok but this fails = "
                    "router/upstream — escalate with both ping outputs.\n"
                    "4. nslookup google.com — CAN I RESOLVE NAMES? IP ping works, names fail = DNS. "
                    "Compare against a known resolver (nslookup google.com 1.1.1.1): configured-DNS fails "
                    "but 1.1.1.1 works = the DNS SERVER (or the client's DNS setting), not 'the internet'.\n"
                    "This tree turns 'internet down!!' into a one-line diagnosis with evidence attached — "
                    "and tells you exactly what to ESCALATE when the fault is beyond the client "
                    "(DHCP scope, router, DNS server) versus what you fix locally.\n\n"
                    "GATEWAY SANITY: the gateway must be ON THE SAME SUBNET as the IP. 192.168.1.50/24 "
                    "with gateway 192.168.2.1 can never work — a misconfiguration you can SEE in "
                    "ipconfig if you check.\n\n"
                    "COMMON MISTAKES: starting at step 4 (rebooting the router) before step 1; 'DNS is "
                    "down' when one machine's DNS SETTING is wrong; fixing DHCP failure by setting a "
                    "static IP and creating next month's address-conflict ticket."
                ),
                "outcomes": [
                    "Run the four-step triage tree and diagnose DHCP, gateway, upstream, and DNS failures from output",
                    "Decide fix-locally vs escalate-with-evidence at each branch",
                    "Spot subnet-mismatched gateway configs by inspection",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Network Printing Without Tears",
                "lesson_order": 2,
                "estimated_minutes": 60,
                "summary": (
                    "A network print job crosses four hops; failures live at exactly one:\n"
                    "1. APP → LOCAL QUEUE: wrong printer selected (the eternal 'printing but nothing "
                    "comes out' when jobs pile into 'Microsoft Print to PDF'), or spooler stuck (Week 3 "
                    "fix: restart Print Spooler, clear stuck jobs).\n"
                    "2. QUEUE → PRINTER over the network: can you PING the printer's IP? (Find it on the "
                    "printer's own panel/config page.) Printer asleep, re-IP'd by DHCP, or moved VLANs — "
                    "all live here. A printer that got a NEW IP while the port config points at the OLD "
                    "one is the classic office mystery: fix the PORT, don't reinstall the world.\n"
                    "3. PRINTER ITSELF: panel errors, jam, toner — the printer's own display and config "
                    "page are evidence sources, not just user rumor.\n"
                    "4. DRIVER: garbage characters or one app failing = driver/format territory; "
                    "reinstall the DRIVER then, not before.\n"
                    "Diagnose by hop: 'is the job in the queue? can I ping the printer? what does the "
                    "panel say?' beats reinstalling drivers as a ritual.\n\n"
                    "SHARED/DEPLOYED PRINTERS (preview of Week 13+): office printers often arrive via a "
                    "print SERVER share or Group Policy — 'the printer vanished' after a profile or "
                    "policy hiccup is a deployment issue, and mass outages of one printer for EVERYONE "
                    "point at the server queue, not twenty broken PCs.\n\n"
                    "COMMON MISTAKES: reinstalling drivers as step 1; ignoring the printer's own panel; "
                    "not checking WHICH printer the app targets."
                ),
                "outcomes": [
                    "Localize print failures to app/queue, network path, printer hardware, or driver",
                    "Diagnose stale printer-IP port configurations and fix the port rather than reinstalling",
                    "Recognize server-side deployment symptoms vs single-client issues",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Running a Real Queue",
                "lesson_order": 3,
                "estimated_minutes": 60,
                "summary": (
                    "Week 4 taught prioritization with three tickets. Real desks run six-plus with "
                    "interrupts. What changes at scale:\n"
                    "TRIAGE PASS FIRST (5 minutes, all tickets): read everything before working anything. "
                    "Tag each: quick win (<10 min), investigation, escalation-likely, security-drop-"
                    "everything. THEN order: security/major impact → quick wins that unblock people → "
                    "investigations → deferred with communication.\n"
                    "COMMUNICATION DEBT: every ticket you DON'T start owes its user a note — 'received, "
                    "here's where you are in the queue, next update by X.' Two minutes of expectation-"
                    "setting prevents the angriest follow-ups. Missed your promised update time? Update "
                    "anyway with status (Week 4's lesson, now under load).\n"
                    "HANDOFFS UNDER LOAD: your shift ends mid-investigation — the handoff note (state, "
                    "ruled-out-with-evidence, exact next step, promises made) is now a graded survival "
                    "skill, not a nicety.\n"
                    "INTERRUPT DISCIPLINE: a new 'URGENT!!' arrival gets a 60-second triage read, not an "
                    "automatic queue-jump. Loud ≠ priority (Simulation 1 veterans know). Security "
                    "indicators are the exception: they DO jump the queue.\n"
                    "KNOWING YOUR EXIT: any single ticket eating >30-45 min without progress in a loaded "
                    "queue is an escalation/timebox candidate — heroics on one ticket while five wait is "
                    "a net loss.\n\n"
                    "This lesson is the direct preparation for Multi-Ticket Simulation 2, the Gate 2 "
                    "practical checkpoint: six tickets, mixed priorities, one misleading, one security, "
                    "one escalation-correct."
                ),
                "outcomes": [
                    "Run a triage-first pass and produce a defensible working order for six-plus tickets",
                    "Pay communication debt: hold notes and expectation-setting for untouched tickets",
                    "Apply interrupt discipline and timeboxing under load",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


QUIZZES_B = [
    {
        "title": "Windows Deep Troubleshooting",
        "week_number": 5, "domain_id": "3.0", "lesson_title": "Startup Failures and Recovery Options",
        "questions": [
            _q("Windows hangs on spinning dots, but boots fine in Safe Mode. The strongest conclusion:",
               "The disk is failing", "A third-party driver or service is hanging normal boot",
               "The bootloader is corrupt", "RAM is faulty",
               "B", "Safe Mode loads a minimal set; success there points at something excluded from it — third-party drivers/services."),
            _q("Automatic Repair has failed twice in a loop. Best next move:",
               "Run Startup Repair five more times", "Use WinRE Command Prompt to gather evidence (e.g., offline sfc) and check restore points",
               "Reinstall Windows", "Clear CMOS",
               "B", "Repeating a failed automatic tool adds nothing; WinRE gives you deliberate diagnostics and rollback options."),
            _q("Event 1000 shows Faulting module: outlookaddin.dll for a crashing Outlook. Blame goes to:",
               "Outlook itself", "The add-in that owns that DLL", "Windows Update", "The user's profile",
               "B", "The faulting module names the code that crashed — an add-in DLL indicts the add-in, not the host app."),
            _q("An app hangs only when opening files from P:\\ (a mapped drive). This is most likely:",
               "An application bug", "A network/mapped-drive problem wearing an app costume", "A GPU issue", "Malware",
               "B", "Hangs on file operations against dead network paths are network tickets; the app is just the messenger."),
            _q("The repair ladder for a broken app, least destructive first:",
               "Reinstall → repair → restart", "Restart app → repair install → clear per-user config → reinstall → vendor escalation",
               "Reboot Windows → reinstall Windows", "Clear config → reinstall → restart",
               "B", "Each rung preserves more evidence and user config than the one below it."),
            _q("Before any startup fix is trusted, you should:",
               "Reboot twice and confirm both boots succeed", "Run Disk Cleanup", "Update the BIOS", "Defragment",
               "A", "Once proves it can boot; twice proves it does so reliably."),
            _q("Which are SAFE disk-space recovery paths? (select all that apply)",
               "Disk Cleanup with 'Clean up system files'", "Clearing %TEMP%",
               "Manually deleting pagefile.sys", "Deleting unrecognized folders in another user's profile",
               "A", "Cleanup tools and temp are safe; page files have settings, and other users' data needs approval.", multi="A,B"),
            _q("C: fills up again every week after cleanup. The real fix is:",
               "Weekly cleanup schedule", "Find what is WRITING the space (e.g., a runaway app log) and fix the source",
               "Compress the drive", "Bigger disk immediately",
               "B", "Recurring growth means an active writer; removing output without fixing the source just resets the timer."),
        ],
    },
    {
        "title": "Accounts and Permissions in Practice",
        "week_number": 6, "domain_id": "4.0", "lesson_title": "NTFS vs Share Permissions, For Real",
        "questions": [
            _q("Share permission: Everyone Change. NTFS on the folder: user has Read. Over the network the user can:",
               "Read and write", "Read only — most restrictive of the two gates wins", "Nothing", "Full control",
               "B", "Remote access = most restrictive of share vs NTFS."),
            _q("A user opens files fine AT the server console but is denied over the network. The gate at fault:",
               "NTFS", "Share permissions", "Group Policy", "The firewall",
               "B", "Console access bypasses share permissions; network access doesn't."),
            _q("You added a user to the right group but they're still denied. Most common missing step:",
               "Reboot the file server", "Have the user sign out and back in to refresh their group token",
               "Disable inheritance", "Grant Full Control",
               "B", "Group membership is stamped into the logon token at sign-in."),
            _q("After a password change, a user gets 'the server is down' opening their mapped P: drive. Likely cause:",
               "The server is down", "The mapped drive is replaying saved OLD credentials",
               "DNS failure", "The share was deleted",
               "B", "Mapped drives cache credentials; stale ones fail after password changes — Simulation 1's misleading ticket."),
            _q("A caller asks for a password reset 'urgently'. Before resetting you must:",
               "Ask their favorite color", "Verify identity via the defined process (callback/manager/etc.)",
               "Reset immediately — urgency first", "Email the new password to any address they give",
               "B", "Help-desk resets are social engineering's front door; verification is the rail."),
            _q("A user reports their account is disabled. Correct first move:",
               "Re-enable it — that's the fix", "Check WHY it was disabled (HR/security/process) before touching it",
               "Delete and recreate the account", "Reset the password",
               "B", "Accounts are disabled by process; blind re-enable can be a security incident."),
            _q("The request: contractor wants access to the Finance share 'for one urgent report'. Correct outcome:",
               "Grant read-only as a compromise", "Escalate with a packaged request: who, what, why, duration, approver",
               "Grant it and remove it tomorrow", "Refuse and close",
               "B", "Sensitive access needs the approval chain; urgency raises escalation priority, not your authority."),
            _q("Best-practice access design uses: (select all that apply)",
               "Groups rather than individual user grants", "Read-only unless write is stated",
               "Full Control to reduce future tickets", "Time-boxed access for time-boxed needs",
               "A", "Groups, minimal rights, and expiry are least-privilege practice; blanket Full Control is its opposite.", multi="A,B,D"),
            _q("Recurring lockouts every ~30 minutes for one user usually mean:",
               "Brute-force attack", "A device or service replaying stale saved credentials",
               "Weak password", "Domain controller failure",
               "B", "Phones, mapped drives, and scheduled tasks retry old passwords on a timer — find the device."),
        ],
    },
    {
        "title": "Endpoint Security and Remote Support",
        "week_number": 7, "domain_id": "4.0", "lesson_title": "Malware Response and Phishing Triage",
        "questions": [
            _q("Defender detected and quarantined a trojan on a work PC that also shows odd outbound activity. Your move:",
               "Delete the quarantine and run cleanups", "Isolate from network (power ON), preserve evidence, escalate",
               "Full scan and close if clean", "Reimage immediately",
               "B", "Signs beyond a routine auto-quarantine mean containment + escalation, not entry-level remediation."),
            _q("Why keep an infected machine POWERED ON while isolating it?",
               "To finish the scan", "Volatile evidence (memory, active connections) is destroyed by shutdown",
               "Windows requires it", "To keep the user working",
               "B", "Security teams need the live state; network isolation stops spread without destroying it."),
            _q("A user entered their credentials on a fake login page an hour ago. The FIRST action:",
               "Full Defender scan", "Change the password NOW from a DIFFERENT device and revoke sessions/MFA",
               "Delete the email", "Reboot their PC",
               "B", "Stolen credentials are being used or sold now; the machine can wait, the account cannot."),
            _q("Which are phishing red flags? (select all that apply)",
               "Display name doesn't match the sender address", "Urgency + authority + unusual request (gift cards)",
               "Hovered link target differs from the shown text", "The email has a company logo",
               "A", "Mismatch, pressure, and deceptive links are the classic trio; logos are trivially copied.", multi="A,B,C"),
            _q("A user REPORTS a phishing email they didn't click. Your response includes:",
               "Telling them to be more careful", "Thanking them, getting the original as an attachment, reporting per procedure",
               "Deleting it and closing", "Clicking the link to verify it's malicious",
               "B", "Reward reporting, preserve headers (attachment, not forward), never detonate links."),
            _q("'I turned the firewall off and the app worked.' As a resolution this is:",
               "Acceptable if documented", "A diagnostic finding only — the fix is identifying/adjusting the blocking rule",
               "Best practice", "A driver issue",
               "B", "Disabling protection converts a symptom into a vulnerability; find the rule."),
            _q("RDP to a workstation times out entirely (no error prompt). The four-gate ladder says start with:",
               "Remote Desktop Users membership", "Network reachability and whether the machine is awake",
               "The RDP firewall rule", "Reinstalling the RDP client",
               "B", "Timeouts are gates 1-2 (network/service); instant refusals are 3; denied errors are 4."),
            _q("For live support on a user's Windows 11 session while they watch, prefer:",
               "RDP (takes over the session, logs them out)", "Quick Assist (shares their session with consent)",
               "TeamViewer from a random download", "PowerShell remoting",
               "B", "Quick Assist shares; client-OS RDP takes. Consent and visibility make it the support default."),
        ],
    },
    {
        "title": "Client Network Triage",
        "week_number": 8, "domain_id": "2.0", "lesson_title": "The Client-Side Network Triage Tree",
        "questions": [
            _q("ipconfig shows 169.254.40.7 on ONE machine; neighbors are fine. Most likely fault domain:",
               "DHCP server scope exhausted", "This machine's port/cable/NIC or its DHCP conversation",
               "DNS", "The default gateway",
               "B", "One APIPA victim = local path; MANY victims = server/scope."),
            _q("IP, gateway, DNS all look right; ping <gateway> ok; ping 1.1.1.1 fails. Escalate as:",
               "DNS outage", "Upstream/router problem beyond the gateway, with both ping outputs attached",
               "DHCP failure", "Cable fault",
               "B", "The path dies after the gateway — that's router/ISP territory with clean evidence."),
            _q("nslookup google.com fails; nslookup google.com 1.1.1.1 succeeds. Conclusion:",
               "The internet is down", "The configured DNS server (or the client's DNS setting) is the problem",
               "The site is blocked", "ARP failure",
               "B", "A known-good resolver answering proves resolution works; the configured one is at fault."),
            _q("IP 192.168.1.50/24 with gateway 192.168.2.1 will:",
               "Work fine", "Never reach the gateway — it's on a different subnet",
               "Work only for HTTPS", "Cause an IP conflict",
               "B", "The gateway must be inside the host's own subnet to be reachable."),
            _q("'Fixing' a DHCP failure by assigning a static IP from the pool risks:",
               "Nothing — it's standard", "A future address conflict when DHCP hands that IP to someone else",
               "Slower internet", "DNS loops",
               "B", "Static addresses inside a dynamic pool are time bombs; fix DHCP or reserve properly."),
            _q("Jobs pile up in the queue; the printer's own panel shows a new IP since yesterday. The fix:",
               "Reinstall the driver", "Update the printer PORT to the new IP (or fix the reservation)",
               "Reboot the user's PC", "Replace the printer",
               "B", "The queue targets the old address; correct the port/reservation instead of reinstalling."),
            _q("Garbage characters print from one app only. The suspect layer:",
               "Network path", "Driver/print format", "The spooler service", "The share",
               "B", "Garbled output is render/driver territory — NOW a driver reinstall is justified."),
            _q("Six tickets land at once. Your first five minutes go to:",
               "The oldest ticket", "A triage read of ALL tickets, tagging quick wins/investigations/escalations/security",
               "The loudest user", "The easiest ticket",
               "B", "Order the queue before working it; loud ≠ priority, security is the only auto-jump."),
        ],
    },
]


TICKETS_B = [
    # ---------------- Week 5: deep Windows ----------------
    {
        "title": "Laptop stuck on spinning dots after Tuesday's updates",
        "description": (
            "{{USER}}'s laptop has hung on the Windows loading spinner for 20+ minutes, twice. It worked "
            "fine before Tuesday. They need it for a client call this afternoon. You can guide them by "
            "phone and they can follow careful instructions."
        ),
        "difficulty": 3, "week_number": 5, "category": "Windows", "domain_id": "3.0",
        "root_cause": "A driver update from Tuesday hangs normal boot; Safe Mode works; rolling back the driver (or uninstalling the latest quality update) restores normal boot",
        "root_cause_type": "startup_failure",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Establish where boot dies and what changed (Tuesday updates)", "required_mention": ["update", "tuesday", "spinner", "changed"], "weight": 0.2},
            {"id": 2, "step": "Reach Safe Mode / WinRE (3x interrupt) as the diagnostic fork", "required_mention": ["safe mode", "winre", "recovery"], "weight": 0.3},
            {"id": 3, "step": "Roll back the offending driver or uninstall latest quality update — one change", "required_mention": ["roll back", "rollback", "uninstall update", "driver"], "weight": 0.3},
            {"id": 4, "step": "Verify with TWO clean normal boots", "required_mention": ["twice", "two", "reboot", "normal boot"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Safe Mode reached / WinRE menu, and the rollback action", "validation": {}},
            {"type": "screenshot", "description": "Normal desktop after second clean boot", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = 'what changed' anchored to Tuesday and Safe Mode used as the fork before changes",
            "2 = update/driver from Tuesday identified as the boot blocker",
            "2 = single targeted rollback; reinstalling Windows or blind repeated Startup Repair = 0-1",
            "2 = two consecutive normal boots demonstrated",
            "2 = user kept informed against their afternoon deadline",
        ),
        "model_answer": (
            "Boot dies post-logo after Tuesday's updates → driver/service hang. Interrupt boot 3x to WinRE, "
            "boot Safe Mode (works → third-party driver confirmed). Roll back the Tuesday driver in Device "
            "Manager (or WinRE → Uninstall latest quality update). Reboot normally twice, verify. Note the "
            "held update for follow-up so it doesn't reinstall silently."
        ),
        "hints": [
            "The user told you exactly what changed — start there.",
            "There's a boot mode that loads almost nothing; whether it works splits this problem in half.",
            "Safe Mode boots fine. What arrived Tuesday that normal boot loads and Safe Mode doesn't?",
            "Roll back the Tuesday driver (Device Manager → driver → Roll Back) or WinRE → Uninstall latest quality update. Then two clean normal boots before you call it fixed.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"]}},
    },
    {
        "title": "Excel crashes the moment it opens",
        "description": (
            "{{USER}} reports Excel closes instantly at launch since this morning — no error, just gone. "
            "Word and Outlook are fine. They swear they installed nothing. Event Viewer is available."
        ),
        "difficulty": 3, "week_number": 5, "category": "Applications", "domain_id": "3.0",
        "root_cause": "Event 1000 shows the faulting module is a third-party Excel add-in DLL ({{ADDIN}}); starting Excel in safe mode (excel /safe) works; disabling the add-in resolves it",
        "root_cause_type": "application_crash",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Pull Event 1000 and read the faulting module", "required_mention": ["1000", "faulting module", "event"], "weight": 0.3},
            {"id": 2, "step": "Confirm with excel /safe (add-ins excluded)", "required_mention": ["/safe", "safe mode"], "weight": 0.25},
            {"id": 3, "step": "Disable the offending add-in only", "required_mention": ["add-in", "addin", "disable"], "weight": 0.25},
            {"id": 4, "step": "Verify normal launch and a real file opening", "required_mention": ["verify", "opens", "launch"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Event 1000 with faulting module visible", "validation": {"must_contain_text": ["1000"]}},
            {"type": "screenshot", "description": "Excel open normally after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = Event Viewer consulted BEFORE any reinstall; faulting module read",
            "2 = specific add-in named as the crasher (not 'Excel is broken')",
            "2 = only the add-in disabled; Office reinstall as first move = 0-1",
            "2 = normal launch + real workbook verified",
            "2 = user told plainly which add-in and why it was disabled",
        ),
        "model_answer": (
            "Application log → Event 1000 for EXCEL.EXE: faulting module is the add-in DLL, not Excel. "
            "Confirm via excel /safe (launches fine). File → Options → Add-ins → disable the culprit. "
            "Launch normally, open the user's actual workbook. Note the add-in vendor for a version-update "
            "follow-up."
        ),
        "hints": [
            "No error on screen doesn't mean no error was recorded.",
            "Application log, Event ID 1000 — the crash names its own culprit.",
            "The faulting module isn't Excel's own code. What loads INTO Excel at startup?",
            "Run excel /safe to confirm, then disable the named add-in in File → Options → Add-ins, and verify a real workbook opens normally.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "ADDIN": ["DataLinker", "PivotPro", "SheetSync", "FormulaFox", "GridWorks"]}},
    },
    {
        "title": "C: drive full — 'but I deleted everything!'",
        "description": (
            "{{USER}}'s PC warns 'Low disk space on C:'. They insist they've deleted all their old files "
            "and 'there's nothing left to remove'. The machine has a 256 GB drive. This is the second "
            "time this month the same machine has filled up."
        ),
        "difficulty": 2, "week_number": 5, "category": "Windows", "domain_id": "3.0",
        "root_cause": "An application ({{APP}}) writes a runaway log file gigabytes in size; cleanup alone recurs — the app's logging must be fixed/rotated",
        "root_cause_type": "disk_space",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Measure what consumes space (Storage settings / folder sizes) before deleting", "required_mention": ["storage", "measure", "folder size", "what is using"], "weight": 0.3},
            {"id": 2, "step": "Identify the runaway log and its owning application", "required_mention": ["log", "growing", "application"], "weight": 0.3},
            {"id": 3, "step": "Safe cleanup (Disk Cleanup system files / temp) + address the SOURCE", "required_mention": ["disk cleanup", "temp", "rotation", "source", "fix the app"], "weight": 0.25},
            {"id": 4, "step": "Before/after free space captured; recurrence noted", "required_mention": ["before", "after", "recurr", "second time"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Space breakdown showing the offender BEFORE cleanup", "validation": {}},
            {"type": "screenshot", "description": "Free space after, with the source fix noted", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = measured first; the 'second time this month' clue chased",
            "2 = runaway log + owning app identified (not 'user files')",
            "2 = safe cleanup paths only, and the SOURCE addressed; deleting unknowns = 0",
            "2 = before/after numbers captured",
            "2 = user cleared of blame gracefully — they were right, it wasn't their files",
        ),
        "model_answer": (
            "Measure: Settings → Storage + folder-size review shows a multi-GB log under the app's data "
            "folder. The recurrence clue means an active writer. Free space safely (Disk Cleanup as admin, "
            "%TEMP%), then fix the source: cap/rotate the app's logging (or escalate to the app owner with "
            "the path and growth rate). Before/after screenshots; note the growth rate in the ticket."
        ),
        "hints": [
            "'Second time this month' is the most important sentence in the ticket.",
            "Measure before deleting — what does Storage settings say is actually big?",
            "Something is WRITING gigabytes. Find the file, then find its owner.",
            "It's a runaway application log. Clean safely, then cap/rotate the app's logging or escalate to its owner — otherwise you'll be back in two weeks.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "APP": ["LabelPrint Pro", "SyncAgent", "InventoryScan", "BadgeWorks", "TimeClock Plus"]}},
    },
    # ---------------- Week 6: accounts / permissions ----------------
    {
        "title": "New team member can't open the department share",
        "description": (
            "{{USER}} joined the {{DEPT}} team Monday. They can open \\\\FILES01\\{{DEPT}} but get "
            "'Access denied' on the Projects folder inside it, which the whole team uses. Their manager "
            "already emailed approval for standard team access. Screenshots and Effective Access are "
            "available to you."
        ),
        "difficulty": 2, "week_number": 6, "category": "Permissions", "domain_id": "4.0",
        "root_cause": "User was never added to the {{DEPT}}-Projects security group; after adding (approval on record) they must sign out/in to refresh the token",
        "root_cause_type": "ntfs_group_membership",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Reproduce and localize: share opens, NTFS on subfolder denies", "required_mention": ["access denied", "ntfs", "folder", "share opens"], "weight": 0.2},
            {"id": 2, "step": "Effective Access / group comparison vs a working teammate", "required_mention": ["effective access", "group", "member"], "weight": 0.3},
            {"id": 3, "step": "Add to the correct GROUP with approval documented (not a direct user grant)", "required_mention": ["group", "approval", "manager"], "weight": 0.3},
            {"id": 4, "step": "Sign out/in and verify the folder opens", "required_mention": ["sign out", "log off", "token", "verify"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Effective Access before (denied) with group evidence", "validation": {}},
            {"type": "screenshot", "description": "Folder open after group add + fresh sign-in", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = localized to NTFS on the subfolder and compared against a working teammate",
            "2 = missing group membership named as the cause",
            "2 = group-based grant with approval recorded; direct user grant or Full Control = 1",
            "2 = fresh-token sign-in performed and folder verified open",
            "2 = user told what was missing and that the manager's approval was recorded",
        ),
        "model_answer": (
            "Share opens (share perms fine) but Projects denies → NTFS. Effective Access for the user shows "
            "no rights; a teammate has them via {{DEPT}}-Projects group. Manager approval is on record → "
            "add the user to that group, document approver in the ticket, have them sign out/in (token "
            "refresh), verify Projects opens. Least privilege preserved: the standard team group, nothing "
            "broader."
        ),
        "hints": [
            "The share opened — so which of the two permission gates is doing the denying?",
            "Compare the new hire to a teammate who CAN open it. What's different?",
            "Effective Access will show the gap; look at group memberships.",
            "Add them to the team's Projects group (approval is on record), then sign-out/sign-in — new group memberships only apply to a fresh logon token.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "DEPT": ["Facilities", "Marketing", "Logistics", "Engineering", "Purchasing"]}},
    },
    {
        "title": "Executive assistant requests access to the salary review folder",
        "description": (
            "{{USER}}, assistant to a VP, submits: 'I need access to \\\\FILES01\\HR\\SalaryReview to "
            "prepare documents for my VP's meetings. This is urgent — the reviews start Monday.' No "
            "approval is attached. Your account has the technical ability to grant this."
        ),
        "difficulty": 3, "week_number": 6, "category": "Permissions", "domain_id": "4.0",
        "root_cause": "Sensitive HR data — correct outcome is a packaged escalation to HR data owner / approval chain, regardless of urgency; granting anything is a failure",
        "root_cause_type": "access_escalation",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Classify the data (HR/salary = sensitive) before considering the grant", "required_mention": ["sensitive", "hr", "salary", "classif"], "weight": 0.25},
            {"id": 2, "step": "Recognize urgency ≠ authorization", "required_mention": ["urgen", "authoriz", "approval"], "weight": 0.25},
            {"id": 3, "step": "Package the escalation: who/what/why/duration/needed approver", "required_mention": ["escalat", "package", "approver", "duration"], "weight": 0.3},
            {"id": 4, "step": "Respond to the user with the path and expected timing — helpful, not stonewalling", "required_mention": ["respond", "monday", "timeline", "path"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The escalation note as sent (who/what/why/duration/approver)", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = data sensitivity identified before any action; requester's role noted",
            "2 = 'needs HR-owner approval' named as the actual requirement",
            "2 = clean escalation, NOTHING granted. Granting read-only 'as a compromise' = 0",
            "2 = escalation contains everything the approver needs to decide same-day",
            "2 = user response is fast, kind, and gives a concrete path before Monday",
        ),
        "model_answer": (
            "Salary data is sensitive-by-default. Ability ≠ authority: escalate to the HR data owner with "
            "the request packaged — requester, exact folder, business reason (VP meeting prep), requested "
            "duration (review period), and the named approver required. Flag the Monday deadline so the "
            "approval moves today. Tell the assistant exactly this, warmly: not a no — the required yes "
            "has to come from HR, and you've already routed it with the deadline attached."
        ),
        "hints": [
            "Look at WHAT is being requested before HOW urgently.",
            "You can grant it. Should you? Whose data is it?",
            "Urgency changes how fast the request moves — not who gets to approve it.",
            "Escalate to the HR data owner with a complete package (who/what/why/duration/approver) flagged for the Monday deadline, and tell the assistant the path. Granting anything yourself — even read-only — fails this ticket.",
        ],
        "parameters": {"placeholders": {"USER": ["c.moreno", "j.whitfield", "a.osei", "l.tanaka", "p.novak"]}},
    },
    {
        "title": "Locked out again — third time this week",
        "description": (
            "{{USER}} is locked out again — third lockout this week. Each time the desk unlocks it, it "
            "re-locks within the hour. They changed their password last Friday per the expiry policy. "
            "They log in fine at their desk, and swear they're not mistyping anything."
        ),
        "difficulty": 3, "week_number": 6, "category": "Accounts", "domain_id": "4.0",
        "root_cause": "The user's {{DEVICE}} still holds the pre-Friday password and retries it on a schedule, tripping the lockout threshold; updating the stored credential ends the cycle",
        "root_cause_type": "stale_credentials",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Pattern recognized: re-locks on a timer after a password change = replaying device", "required_mention": ["password change", "friday", "pattern", "replay", "stale"], "weight": 0.3},
            {"id": 2, "step": "Inventory where the old password could live (phone mail, mapped drives, saved sessions, scheduled tasks)", "required_mention": ["phone", "mapped", "saved", "device", "where"], "weight": 0.3},
            {"id": 3, "step": "Update/remove the stale credential on the culprit device", "required_mention": ["update", "remove", "credential", "re-enter"], "weight": 0.2},
            {"id": 4, "step": "Unlock once more and verify NO re-lock over a full interval", "required_mention": ["unlock", "verify", "no re-lock", "hour"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Notes identifying the replaying device and the credential update", "validation": {}},
            {"type": "screenshot", "description": "Account status remaining unlocked past the previous re-lock interval", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = timer pattern + Friday change connected; not treated as user error",
            "2 = the specific replaying device/service identified",
            "2 = credential updated at the source; 'unlock and hope' or raising the lockout threshold = 0-1",
            "2 = verified unlocked beyond the prior re-lock window",
            "2 = user vindicated kindly — they were right, it wasn't their typing",
        ),
        "model_answer": (
            "Re-lock on a ~hourly timer right after a password change is the stale-credential signature. "
            "Inventory the user's other credential holders: phone mail profile, mapped drives, saved RDP, "
            "scheduled tasks. The {{DEVICE}} still has the pre-Friday password — update it there, unlock "
            "the account, and verify it stays unlocked past the old interval. Close with a note explaining "
            "the pattern for future desks."
        ),
        "hints": [
            "Three lockouts on a schedule is a pattern, not bad luck. What changed Friday?",
            "The user types fine at their desk. What ELSE knows their password?",
            "Something is retrying the OLD password automatically — phones and mapped drives are the usual suspects.",
            "Find the device with the saved pre-Friday credential (check their phone's mail account first), update it, unlock once more, and confirm it survives past the hour mark.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "DEVICE": ["personal iPhone mail profile", "Android mail app", "tablet's saved mail account", "home laptop's mapped drive", "saved RDP session on their second PC"]}},
    },
]

TICKETS_B += [
    # ---------------- Week 7: security / remote ----------------
    {
        "title": "Defender caught something — user asking if they're 'okay now'",
        "description": (
            "{{USER}} reports Defender popped a 'Threats found' notification an hour ago after they opened "
            "a downloaded 'invoice viewer' tool. Protection history shows a trojan, action: Quarantined. "
            "The machine seems fine now, and the user asks if they can just keep working."
        ),
        "difficulty": 3, "week_number": 7, "category": "Security", "domain_id": "4.0",
        "root_cause": "Trojan executed by the user before quarantine — cannot be assumed contained; correct outcome: isolate, preserve (incl. quarantine sample), assess what the user did, escalate to security; not entry-level remediation",
        "root_cause_type": "security_escalation",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Protection history read and captured; note the user RAN the file", "required_mention": ["protection history", "quarantin", "ran", "opened", "executed"], "weight": 0.25},
            {"id": 2, "step": "Isolate from network, power ON; user stops working on it", "required_mention": ["isolat", "disconnect", "network", "power on"], "weight": 0.3},
            {"id": 3, "step": "Assess exposure: what was entered/opened since; quarantine sample preserved", "required_mention": ["assess", "preserve", "sample", "credentials", "since"], "weight": 0.25},
            {"id": 4, "step": "Escalate with timeline; honest answer to the user: not 'okay' until security clears it", "required_mention": ["escalat", "security", "timeline", "not cleared"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Protection history entry (name, action, time)", "validation": {}},
            {"type": "screenshot", "description": "Escalation note with timeline and exposure assessment", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = history read, execution-before-quarantine recognized as the key fact",
            "2 = 'executed trojan, containment unverifiable at this level' as the working cause",
            "2 = isolate + preserve + escalate; 'ran a full scan, looks clean, closed' = 0; deleting quarantine = 0",
            "2 = security handoff lets them act immediately; machine state preserved",
            "2 = user answered honestly and kindly: paused, not punished; loaner path offered",
        ),
        "model_answer": (
            "Quarantined AFTER execution means the trojan ran — a quick 'seems fine' proves nothing. "
            "Isolate from network (power on), have the user pause work, capture Protection history, keep "
            "the quarantine sample. Assess: what did they enter/open since running it? Escalate to security "
            "with the timeline. Tell the user: not in trouble, machine is paused for a professional check, "
            "here's a loaner/hot-desk meanwhile."
        ),
        "hints": [
            "Read the order of events: when did they RUN it vs when did Defender act?",
            "Quarantine after execution is a very different situation from quarantine on download.",
            "Contain first: network off, power on, evidence intact — including the quarantine itself.",
            "This escalates: isolate, preserve the sample and timeline, assess what the user entered since, hand to security. 'It seems fine now' is not a clearance.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"]}},
    },
    {
        "title": "'Payroll update' email — user entered their password, then got suspicious",
        "description": (
            "{{USER}} forwards an email: 'Payroll portal update — verify your account before Friday' with "
            "a link. They admit they clicked it and typed their username and password before the page "
            "'looked off' and they closed it. That was about 20 minutes ago. They feel terrible."
        ),
        "difficulty": 3, "week_number": 7, "category": "Security", "domain_id": "4.0",
        "root_cause": "Credential phishing — credentials are compromised NOW; immediate password change from a different device + session/MFA revocation + security report; timing beats everything else",
        "root_cause_type": "credential_compromise",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Severity triage: credentials ENTERED = live compromise, clock running", "required_mention": ["entered", "compromise", "20 minutes", "immediate"], "weight": 0.3},
            {"id": 2, "step": "Password changed NOW from a DIFFERENT device; sessions/MFA revoked", "required_mention": ["different device", "change password", "revoke", "session"], "weight": 0.3},
            {"id": 3, "step": "Report per procedure with the ORIGINAL email preserved (attachment, not forward)", "required_mention": ["report", "original", "attachment", "header"], "weight": 0.2},
            {"id": 4, "step": "User treated well — reporting rewarded, no shaming; watch-items explained", "required_mention": ["thank", "not in trouble", "watch", "reported"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Notes showing the immediate-containment sequence with times", "validation": {}},
            {"type": "screenshot", "description": "Security report submitted with the preserved original", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = 'entered credentials 20 min ago' correctly ranked above everything, incl. the machine",
            "2 = live credential compromise named; not treated as a mere 'suspicious email' report",
            "2 = password change from another device + revocation FIRST; scanning the PC first = 1",
            "2 = change + revocation confirmed done; security has the original with headers",
            "2 = user thanked for reporting; clear watch-list (odd logins, MFA prompts) given",
        ),
        "model_answer": (
            "Credentials entered = compromised now. From a DIFFERENT device: change the password "
            "immediately and revoke active sessions/MFA tokens. Then report to security with the original "
            "email attached (forwarding strips headers). The machine likely only served a phishing page — "
            "note it for security but don't let a scan delay the credential response. Thank the user "
            "explicitly for reporting; tell them what to watch for."
        ),
        "hints": [
            "Two assets might be harmed here: the machine and something else. Which is definitely harmed?",
            "Twenty minutes. What is an attacker doing with a fresh password right now?",
            "The response starts on a DIFFERENT device than the one that visited the page.",
            "Change the password now from another device, revoke sessions/MFA, then report with the original email as an attachment. The PC scan comes after — credentials don't wait.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"]}},
    },
    {
        "title": "Can't RDP to the shared lab workstation",
        "description": (
            "{{USER}} needs the shared lab workstation LAB-{{NUM}} for month-end processing. RDP fails "
            "instantly with 'The remote computer refused the connection'. They could connect last month. "
            "The machine responds to ping and a teammate connected successfully yesterday."
        ),
        "difficulty": 2, "week_number": 7, "category": "Remote Support", "domain_id": "2.0",
        "root_cause": "Instant refusal + ping OK + others connect = gate 3/4 territory; the user was removed from Remote Desktop Users during a group cleanup — re-add (with approval noted) and verify",
        "root_cause_type": "rdp_permission",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Walk the four gates with the evidence given (ping OK, teammate OK, instant refusal)", "required_mention": ["ping", "gate", "refus", "teammate"], "weight": 0.3},
            {"id": 2, "step": "Compare the user vs the working teammate on the TARGET's RDP permissions", "required_mention": ["remote desktop users", "member", "compare", "permission"], "weight": 0.3},
            {"id": 3, "step": "Restore membership with approval/reason documented", "required_mention": ["re-add", "add", "approval", "documented"], "weight": 0.2},
            {"id": 4, "step": "User connects successfully; note why membership was lost", "required_mention": ["connect", "verified", "why", "cleanup"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Evidence of the permission gap (before) on LAB-{{NUM}}", "validation": {}},
            {"type": "screenshot", "description": "Successful RDP session after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = gates walked in order; given facts used to skip to 3/4 with reasoning shown",
            "2 = missing Remote Desktop Users membership identified (not 'firewall', not 'reinstall')",
            "2 = targeted re-add with reason; making the user a local admin instead = 0",
            "2 = live successful connection verified by the user",
            "2 = user told what happened and that it's fixed at the source",
        ),
        "model_answer": (
            "Ping OK (gate 1 clear), instant refusal with a teammate connecting fine — service and firewall "
            "are up (gates 2-3), pointing at gate 4: permission. On LAB-{{NUM}}, Remote Desktop Users no "
            "longer contains this user (recent group cleanup). Re-add with the reason documented, have the "
            "user connect, and note the cleanup as the cause so it doesn't repeat."
        ),
        "hints": [
            "The error type matters: timeout, instant refusal, or credential error?",
            "A teammate connects fine — which gates does that clear for you?",
            "Compare the two users AS THE TARGET MACHINE sees them.",
            "The user fell out of Remote Desktop Users on the target. Re-add (document why), verify a live connection — and don't 'fix' it with local admin.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "NUM": ["07", "12", "03", "21", "15"]}},
    },
    # ---------------- Week 8: network triage ----------------
    {
        "title": "One desk has no network after the office move",
        "description": (
            "After this weekend's desk moves, {{USER}} has no network at their new desk. ipconfig shows "
            "169.254.88.{{OCTET}}. The person at the NEXT desk is fine. The wall has two ports; only one "
            "is labeled. Facilities says 'we just moved the PCs, we didn't touch the network'."
        ),
        "difficulty": 2, "week_number": 8, "category": "Networking", "domain_id": "2.0",
        "root_cause": "PC was plugged into the dead/unpatched second wall port during the move; moving the cable to the live port restores DHCP",
        "root_cause_type": "dhcp_failure",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "APIPA recognized; scope narrowed to THIS desk (neighbor fine)", "required_mention": ["169.254", "apipa", "dhcp", "neighbor", "one machine"], "weight": 0.3},
            {"id": 2, "step": "Physical path checked first given the move: wall port, cable seating", "required_mention": ["wall port", "cable", "port", "moved", "physical"], "weight": 0.3},
            {"id": 3, "step": "Cable moved to the live port; /release /renew to retest", "required_mention": ["release", "renew", "other port", "swap"], "weight": 0.2},
            {"id": 4, "step": "Real DHCP address verified + triage-tree pings; dead port reported to facilities/network", "required_mention": ["verified", "ping", "report", "dead port"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "ipconfig before (APIPA) and after (real lease)", "validation": {"must_contain_text": ["169.254"]}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = APIPA read correctly and the move used as the primary clue; scope confirmed local",
            "2 = dead wall port identified (not 'DHCP server down', not 'bad NIC')",
            "2 = physical fix + proper DHCP retest; setting a static IP = 0",
            "2 = full triage-tree verification after the lease; dead port reported for patching",
            "2 = user working again with a simple explanation; follow-up for the unlabeled port noted",
        ),
        "model_answer": (
            "169.254 on one machine after a physical move = start physical. Two wall ports, one unlabeled: "
            "the PC landed in the unpatched one. Move to the live port, ipconfig /release && /renew, confirm "
            "a real lease, run gateway/8.8.8.8/nslookup checks. Report the dead port so facilities patches "
            "or labels it — the next move victim thanks you."
        ),
        "hints": [
            "What does 169.254.x.x tell you, and what does the happy neighbor rule out?",
            "The environment changed physically this weekend. Check physical before logical.",
            "Two wall ports, one label. Which one is the PC actually in?",
            "Move the cable to the live port, /release /renew, verify a real lease and the ping tree. Do NOT set a static IP — and report the dead port.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "OCTET": ["23", "41", "7", "112", "88"]}},
    },
    {
        "title": "Whole floor printer down since the DHCP change",
        "description": (
            "Since this morning, every user on floor {{FLOOR}} gets 'Printer offline' for the shared "
            "printer PRN-{{FLOOR}}A. Jobs sit in queues on every machine. The network team mentions they "
            "'re-organized DHCP reservations' last night. The printer's panel shows it is on and 'Ready'."
        ),
        "difficulty": 3, "week_number": 8, "category": "Networking", "domain_id": "2.0",
        "root_cause": "The printer received a NEW IP after the reservation change; every client's printer port still targets the old IP — fix at the source (restore reservation or update the shared queue/port), not twenty PCs",
        "root_cause_type": "printer_ip_change",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Scope read: EVERYONE + printer 'Ready' = path/addressing, not printer or PCs", "required_mention": ["everyone", "all users", "ready", "scope"], "weight": 0.25},
            {"id": 2, "step": "Printer's CURRENT IP pulled from its panel/config page and compared to the port target", "required_mention": ["panel", "config page", "current ip", "port"], "weight": 0.3},
            {"id": 3, "step": "Fix at the source: reservation restored or shared queue port updated once", "required_mention": ["reservation", "port", "source", "queue"], "weight": 0.25},
            {"id": 4, "step": "Verified from TWO different machines; cause tied to last night's change in the note", "required_mention": ["two", "verified", "change", "last night"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Printer's current IP vs the port's configured IP", "validation": {}},
            {"type": "screenshot", "description": "Successful test page from a second machine after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = floor-wide scope + 'Ready' panel + last night's change connected before touching any PC",
            "2 = IP drift from the reservation change identified precisely",
            "2 = ONE fix at the source; visiting twenty PCs to re-add the printer = 1; driver reinstalls = 0",
            "2 = verified from at least two clients; queues drain",
            "2 = floor notified with cause and status; network team looped in on the reservation",
        ),
        "model_answer": (
            "All users + printer Ready = addressing, and the DHCP work is the smoking gun. Panel/config "
            "page shows the printer's NEW IP; the shared queue's port still points at the old one. Restore "
            "the reservation (coordinate with the network team) or update the shared queue's port once. "
            "Test from two machines, watch queues drain, notify the floor with the cause."
        ),
        "hints": [
            "Twenty broken PCs at once is almost never twenty problems.",
            "The printer says Ready. So where do the jobs die between PC and paper?",
            "What did the network team change last night, and what does the printer's OWN panel say its address is now?",
            "The printer's IP moved; the queue's port didn't. Fix it once at the source (reservation or shared-queue port), verify from two machines — don't tour the floor reinstalling drivers.",
        ],
        "parameters": {"placeholders": {"FLOOR": ["3", "2", "5", "4", "6"]}},
    },
    {
        "title": "'The VPN is broken' — remote worker can't reach anything by name",
        "description": (
            "{{USER}} works from home and reports 'the VPN is broken — I can't reach any company systems'. "
            "The VPN client shows Connected. They can ping the file server's IP address successfully over "
            "the tunnel, but \\\\FILES01 and the intranet by NAME both fail."
        ),
        "difficulty": 3, "week_number": 8, "category": "Networking", "domain_id": "2.0",
        "root_cause": "VPN tunnel is fine; the client's DNS points at the home router ({{HOMEDNS}}) instead of corporate DNS, so internal names don't resolve — misleading symptom ('VPN broken')",
        "root_cause_type": "dns_misconfiguration",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "The user's framing tested: Connected + IP-ping works = tunnel is UP", "required_mention": ["connected", "ping", "ip works", "tunnel"], "weight": 0.3},
            {"id": 2, "step": "Name vs IP split identified as DNS; nslookup against corporate DNS compared", "required_mention": ["nslookup", "dns", "name", "resolve"], "weight": 0.3},
            {"id": 3, "step": "Client DNS corrected to corporate resolver for the tunnel (per VPN profile guidance)", "required_mention": ["corporate dns", "adapter", "profile", "setting"], "weight": 0.2},
            {"id": 4, "step": "Named access verified (\\\\FILES01 opens, intranet loads); user's mental model fixed kindly", "required_mention": ["files01", "verified", "explain"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "IP-ping success + name failure side by side", "validation": {}},
            {"type": "screenshot", "description": "nslookup via corporate DNS resolving; share open by name", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = 'VPN broken' claim tested against evidence instead of accepted; IP/name split found",
            "2 = DNS-over-tunnel misdirection named specifically (home router answering)",
            "2 = DNS corrected per the VPN profile; hosts-file hacks or tunnel reinstalls = 1",
            "2 = named access demonstrated end-to-end",
            "2 = user shown why 'VPN broken' was reasonable but wrong — no condescension",
        ),
        "model_answer": (
            "Connected + IP-ping over the tunnel = the VPN works; the misleading symptom is names. "
            "nslookup shows queries going to the home router instead of corporate DNS. Correct the DNS "
            "for the tunnel per the VPN profile (adapter DNS / profile setting), verify \\\\FILES01 and "
            "the intranet by name, and explain the IP-vs-name distinction so next time the ticket writes "
            "itself."
        ),
        "hints": [
            "One thing in the report proves the VPN is actually working. Find it.",
            "Reaching by IP but not by NAME — you've split this exact problem before.",
            "Where are name queries going? nslookup will show which server answers.",
            "The tunnel's DNS points at the home router. Set corporate DNS for the VPN connection per the profile, verify by name, and gently correct the 'VPN is broken' diagnosis in your user message.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
                                          "HOMEDNS": ["192.168.1.1", "192.168.0.1", "10.0.0.1", "192.168.50.1", "172.16.0.1"]}},
    },
]

TICKETS_B.append({
    "title": "Multi-Ticket Simulation 2 — six tickets, ninety minutes",
    "description": (
        "Friday, 2:00 PM. Six tickets are open. First submit your TRIAGE: tag each ticket "
        "(quick win / investigation / escalate / security) and give your working order with one-line "
        "justifications. Then work them, documenting each. Untouched tickets still owe their user a "
        "hold note.\n\n"
        "T1 ({{USER1}}): 'My monitor is sideways since this morning, I can't work like this!' (loud, "
        "repeated calls)\n\n"
        "T2 (Reception, walk-in kiosk): 'The visitor kiosk shows THREATS FOUND from Defender and a "
        "toolbar nobody installed. Visitors used a USB stick on it yesterday.'\n\n"
        "T3 ({{USER2}}, Finance): 'I urgently need write access to \\\\FILES01\\Finance\\YearEnd — "
        "the controller is out sick and close is Monday.' No approval attached.\n\n"
        "T4 (Ops team, 12 people): 'Since about 1:30 nobody can reach the intranet OR the file server "
        "by name. Internet sites work fine.'\n\n"
        "T5 ({{USER3}}): 'The network is down for me' — attached screenshot shows their laptop on "
        "airplane mode.\n\n"
        "T6 ({{USER4}}): 'Excel takes 5+ minutes to open one specific workbook from the P: drive; "
        "other files open fast. Started after the file moved folders last week.'\n\n"
        "One description is misleading. One must be escalated, not solved. One is a genuine security "
        "matter. Manage your ninety minutes."
    ),
    "difficulty": 3, "week_number": 8, "category": "Simulation", "domain_id": "5.0",
    "root_cause": (
        "T1: rotated display hotkey/setting — quick win. T2: kiosk malware after USB use — isolate, "
        "preserve, ESCALATE to security (drop-everything). T3: sensitive finance access without approval "
        "— packaged escalation, expedited for Monday, nothing granted. T4: internal DNS failure affecting "
        "12 (internet names fine, internal names dead) — evidence-packaged escalation to the network/DNS "
        "owner with scope+onset, highest operational impact. T5: airplane mode — the misleading 'network "
        "down', 60-second fix. T6: multi-step — workbook links/lookup paths pointing at the old folder "
        "location cause open-time timeouts; repair the references/path."
    ),
    "root_cause_type": "multi_incident",
    "required_checkpoints": {"checkpoints": [
        {"id": 1, "step": "Triage submitted FIRST: all six tagged + order justified", "required_mention": ["triage", "order", "tag", "priority"], "weight": 0.25},
        {"id": 2, "step": "T2 handled as security: isolated (power on), preserved, escalated near the top", "required_mention": ["kiosk", "isolat", "preserve", "escalat"], "weight": 0.25},
        {"id": 3, "step": "T4 scoped (internal-only names, 12 users, onset 1:30) and escalated with evidence; T3 escalated packaged, nothing granted", "required_mention": ["dns", "scope", "onset", "approval", "packaged"], "weight": 0.25},
        {"id": 4, "step": "T5's claim disproven from the screenshot; T1 quick-won; T6 multi-step path documented; hold notes for anything untouched", "required_mention": ["airplane", "rotate", "links", "hold note"], "weight": 0.25},
    ]},
    "required_evidence": {"evidence_types": [
        {"type": "screenshot", "description": "Triage table: six tags, order, one-line justifications", "validation": {}},
        {"type": "screenshot", "description": "Per-ticket notes incl. T2 isolation/escalation and T4 evidence package", "validation": {}},
    ]},
    "scoring_anchors": ANCHORS(
        "2 = triage-first pass on all six; T5's screenshot actually read; T4's scope established with two data points",
        "2 = all six causes right, incl. T5 misleading (airplane mode) and T6's moved-path links",
        "2 = T2 isolated+escalated without remediation; T3 escalated with NOTHING granted; T1/T5 fixed; no queue-jump for T1's volume",
        "2 = each worked ticket verified with its user; untouched tickets carry hold notes with next-update times",
        "2 = six distinct, tone-appropriate user messages; T5 corrected without embarrassment; T3 given a real path for Monday",
    ),
    "model_answer": (
        "Triage: T2 security (drop-everything: isolate kiosk from network, power on, preserve, escalate) → "
        "T4 highest impact (12 users; internet-names-OK/internal-names-dead + 1:30 onset = internal DNS; "
        "escalate to DNS owner with evidence) → T5 quick win (airplane mode off, verify, kind note) → T1 "
        "quick win (display rotation setting/hotkey, verify) → T3 escalation (package who/what/why/duration/"
        "approver, expedite for Monday close, grant nothing) → T6 investigation (workbook's external "
        "links/lookups still point at the pre-move path; repair links, verify open time). Hold notes go "
        "out at triage time for everything not being worked immediately. Loud (T1) never outranks "
        "security (T2) or scope (T4)."
    ),
    "hints": [
        "Triage all six before touching any. Which one is a drop-everything category?",
        "T4: internet names work, internal names don't — what service does that isolate, and how many people prove it?",
        "T5: the evidence contradicting the user's claim is already attached. T3: what did Week 6 teach about urgency vs authorization?",
        "Order: T2 (isolate+escalate) → T4 (evidence-packaged DNS escalation) → T5 (airplane mode) → T1 (rotation) → T3 (packaged approval escalation, nothing granted) → T6 (repair the moved-path links). Hold notes at triage time for the queue's tail.",
    ],
    "parameters": {"placeholders": {
        "USER1": ["gharris", "bfoster", "mruiz", "cchen", "tadams"],
        "USER2": ["j.whitfield", "c.moreno", "a.osei", "l.tanaka", "p.novak"],
        "USER3": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
        "USER4": ["swalsh", "dkim", "rnair", "lbrown", "efarah"],
    }},
})


def seed_phase_b(db) -> dict:
    """Idempotent Phase B seed — same conventions as seed_phase_a()."""
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
    from app.models.ticket import Ticket
    from app.services.seed_question_sync import sync_seed_questions

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0, "tickets": 0}
    prev_module = db.query(Module).filter(Module.code == "MOD-004").first()
    for spec in MODULES_B:
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
        if prev_module is not None:
            module.prerequisite_module_id = prev_module.id if module.id != prev_module.id else None
        db.flush()
        for lspec in spec["lessons"]:
            lesson = (db.query(Lesson)
                      .filter(Lesson.module_id == module.id,
                              Lesson.lesson_order == lspec["lesson_order"]).first())
            lfields = {k: lspec[k] for k in ("title", "summary", "outcomes",
                       "estimated_minutes", "required_notes_template", "status")}
            if lesson is None:
                db.add(Lesson(module_id=module.id, lesson_order=lspec["lesson_order"], **lfields))
                counts["lessons"] += 1
            else:
                for k, v in lfields.items():
                    setattr(lesson, k, v)
        db.flush()
        prev_module = module

    for qspec in QUIZZES_B:
        quiz = db.query(Quiz).filter(Quiz.title == qspec["title"]).first()
        lesson = db.query(Lesson).filter(Lesson.title == qspec["lesson_title"]).first()
        if quiz is None:
            quiz = Quiz(title=qspec["title"], week_number=qspec["week_number"],
                        domain_id=qspec["domain_id"], question_count=len(qspec["questions"]),
                        status=QUIZ_STATUS_PUBLISHED, lesson_id=lesson.id if lesson else None)
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

    for tspec in TICKETS_B:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()
    return counts
