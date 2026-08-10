"""Phase D (Weeks 13-17) curriculum content — Windows System Administration.

Role target: Junior Systems Technician (Gate 4, end of Week 17).
This is the largest and (per the master prompt) one of the strongest phases:
Active Directory is a major recurring component across labs and tickets.

Infrastructure honesty: this phase is where AUTO-VM (the Proxmox/Guacamole
pipeline) is the TARGET, but every lab has a MANUAL-VM path — the mentor hand-
clones a WS2022 DC + Win11 client and grants access over Headscale. NO Gate 4
requirement depends on automated provisioning. Templates needed: Windows Server
2022 (DC), Windows 11 Enterprise (domain client).
"""

from seed_phase_a import ANCHORS, NOTES_TEMPLATE, _q

MODULES_D = [
    {
        "code": "MOD-013",
        "title": "Windows Server and Active Directory Foundations",
        "description": "Server Manager, roles, AD DS, OUs, users, groups and scopes, first account tickets. Week 13.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 17,
        "module_order": 14,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Windows Server and Server Manager",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Windows Server is Windows built to provide SERVICES to many users, not to be someone's "
                    "desktop. What changes for a technician:\n"
                    "- SERVER MANAGER is the dashboard: it shows installed ROLES (the big jobs a server "
                    "does — Active Directory, DNS, DHCP, File Services) and FEATURES (smaller add-ons), "
                    "plus health and events across servers.\n"
                    "- A ROLE is added deliberately and changes what the server IS. 'Promoting' a server "
                    "to a Domain Controller (installing AD DS and running the promotion) is the classic "
                    "example — after it, that server holds the directory for the whole domain.\n"
                    "- Servers are managed REMOTELY as the norm (you rarely sit at the console): RDP for "
                    "the desktop, but increasingly PowerShell and admin consoles from a management "
                    "machine.\n\n"
                    "WHY A JUNIOR NEEDS THIS: you'll be asked to check a role's health, read a server's "
                    "events, confirm a service is running, or RDP in to look at something — before you "
                    "ever change anything. Knowing Server Manager and where roles live orients you.\n\n"
                    "SERVER CORE vs DESKTOP EXPERIENCE (awareness): many production servers have no GUI "
                    "(Server Core) — another reason PowerShell matters (Week 16).\n\n"
                    "SAFETY: a server serves many people. A careless change or reboot is an outage for "
                    "everyone who depends on that role. Servers get change windows, verification, and more "
                    "caution than a desktop — the same lesson as shared network gear, one level up.\n\n"
                    "COMMON MISTAKES: treating a server like a desktop (installing random software, "
                    "rebooting casually); adding/removing roles without understanding the impact; making "
                    "changes at the console that should go through proper channels."
                ),
                "outcomes": [
                    "Navigate Server Manager to find installed roles, features, health, and events",
                    "Explain what a role is and what promoting a server to a Domain Controller means",
                    "Apply server-grade change caution: many dependents, change windows, verify before/after",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Active Directory: Domains, OUs, Users, and Groups",
                "lesson_order": 2,
                "estimated_minutes": 120,
                "summary": (
                    "Active Directory (AD) is the central directory of an organization — the single place "
                    "that knows every user, computer, and group, and enforces who can log in and access "
                    "what. Almost every Windows-shop ticket eventually touches it. The structure:\n"
                    "- DOMAIN: the security boundary (e.g. corp.example.com). Domain Controllers (DCs) "
                    "hold it.\n"
                    "- ORGANIZATIONAL UNIT (OU): a folder for organizing users/computers/groups, and the "
                    "unit that Group Policy (Week 15) targets. OUs usually mirror the org (Departments, "
                    "Sites) or function (Servers, Workstations).\n"
                    "- USER ACCOUNT: a person's identity — logon name, password, group memberships, "
                    "enabled/disabled state.\n"
                    "- COMPUTER ACCOUNT: a machine's identity in the domain (created when it joins).\n"
                    "- GROUP: the mechanism for granting access to MANY users at once. You add users to a "
                    "group, and grant the GROUP access to resources — never individuals (the lesson from "
                    "Week 6, now at directory scale).\n\n"
                    "GROUP TYPES & SCOPE (the part everyone finds confusing, kept practical):\n"
                    "- SECURITY groups grant permissions; DISTRIBUTION groups are just email lists.\n"
                    "- SCOPE controls where a group can be used and who it can contain: DOMAIN LOCAL "
                    "(grant access to resources in this domain), GLOBAL (organize users of one domain), "
                    "UNIVERSAL (span domains in a forest). The classic best-practice pattern is "
                    "'A-G-DL-P': Accounts → Global groups → Domain Local groups → Permissions. A junior "
                    "recognizes the pattern and doesn't fight it.\n\n"
                    "TOOLS: Active Directory Users and Computers (ADUC) is the GUI you'll live in; "
                    "PowerShell (Week 16) does the same at scale.\n\n"
                    "COMMON MISTAKES: granting resource access to individual users instead of groups; "
                    "putting everything in the default Users container instead of proper OUs; confusing "
                    "security and distribution groups; ignoring scope and wondering why a group 'won't "
                    "work' across domains."
                ),
                "outcomes": [
                    "Explain the AD hierarchy: domain, OU, user, computer, and group, and what each is for",
                    "Distinguish security vs distribution groups and the three group scopes at a practical level",
                    "Locate and inspect users, groups, and OUs in Active Directory Users and Computers",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "The Core AD Account Tickets",
                "lesson_order": 3,
                "estimated_minutes": 90,
                "summary": (
                    "These four tickets are the daily bread of Windows administration. You did the "
                    "desktop versions in Week 6; here they're in AD, with the same safety rails:\n\n"
                    "PASSWORD RESET (in ADUC / PowerShell): right-click user → Reset Password, usually "
                    "with 'user must change at next logon'. RAIL: verify identity first (Week 6). In AD "
                    "you can see the account's status and last-set time.\n\n"
                    "ACCOUNT UNLOCK: a locked account (too many bad attempts) shows as locked in ADUC → "
                    "Unlock. RAIL: if it re-locks, hunt the stale-credential device (Week 6's pattern) — "
                    "in AD you can also check WHICH DC recorded the lockout and event logs for the source.\n\n"
                    "DISABLED ACCOUNT: disabled accounts can't log in (leavers, security holds). RAIL: "
                    "NEVER just re-enable — confirm with HR/manager why it was disabled. Re-enabling a "
                    "deliberately-disabled account is a security incident.\n\n"
                    "GROUP MEMBERSHIP (access requests): add the user to the correct GROUP (not a direct "
                    "resource grant), with approval documented. RAIL: least privilege; the user must sign "
                    "out/in for new group membership to take effect (the token-refresh lesson from Week 6, "
                    "still true for domain logons).\n\n"
                    "EVIDENCE IN AD: ADUC shows account status, group memberships, last logon, and "
                    "password age — screenshot these as your before/after evidence.\n\n"
                    "COMMON MISTAKES: resetting for an unverified caller; re-enabling disabled accounts to "
                    "be helpful; granting individual access instead of group membership; forgetting the "
                    "sign-out/in; not documenting the approver."
                ),
                "outcomes": [
                    "Perform password resets, unlocks, and group-membership changes in AD with the correct safety rails",
                    "Refuse-and-verify on disabled accounts rather than blindly re-enabling",
                    "Capture AD account status and membership as before/after ticket evidence",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-014",
        "title": "Domain Operations and File Services",
        "description": "Domain joins, computer accounts, group-based file access, NTFS vs share at domain scale. Week 14.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 17,
        "module_order": 15,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Domain Joins and Computer Accounts",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Joining a computer to the domain lets domain users log into it and lets policy and "
                    "central management reach it. The process and its failure points:\n"
                    "- PREREQUISITE: the client must be able to find a Domain Controller, which means DNS "
                    "must point at the domain's DNS (usually the DC). The #1 domain-join failure is DNS: "
                    "if the client's DNS is the home router or a public resolver, it can't locate the "
                    "domain. (Your Week 8 and Week 11 DNS lessons pay off here.)\n"
                    "- JOINING: System → Rename this PC (advanced) → Domain, enter the domain and "
                    "credentials with join rights. A COMPUTER ACCOUNT is created in AD; the machine gets a "
                    "secure channel (a machine password) with the domain.\n"
                    "- AFTER JOIN: reboot; now domain users can log in and the machine appears in AD "
                    "(usually in the Computers container or a target OU).\n\n"
                    "THE 'TRUST RELATIONSHIP FAILED' TICKET: 'The trust relationship between this "
                    "workstation and the primary domain failed.' The machine's secure channel with the "
                    "domain is broken (often after a restore-from-image, a long offline period, or a "
                    "computer-account reset). Modern fix: Test-ComputerSecureChannel -Repair (PowerShell) "
                    "or reset the computer account — NOT a full unjoin/rejoin, which is the old sledgehammer "
                    "and loses the account's history.\n\n"
                    "COMPUTER ACCOUNTS as objects: they can be disabled, reset, or moved between OUs (which "
                    "changes which policies apply). A disabled computer account = that machine can't "
                    "authenticate to the domain.\n\n"
                    "COMMON MISTAKES: joining with wrong DNS (the eternal cause); unjoin/rejoin when a "
                    "secure-channel repair would do; duplicate computer names; ignoring which OU the "
                    "computer lands in (policy implications)."
                ),
                "outcomes": [
                    "Join a client to the domain and explain why DNS-to-the-DC is the critical prerequisite",
                    "Diagnose and repair a broken trust relationship without a full unjoin/rejoin",
                    "Explain computer accounts as AD objects that can be disabled, reset, or moved between OUs",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Group-Based File Access at Domain Scale",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "Week 6 taught NTFS vs share permissions on one machine. In a domain, the same rules "
                    "apply but the ACCESS is driven by AD GROUPS, and getting the design right is what "
                    "separates a maintainable environment from a permissions swamp.\n\n"
                    "THE PATTERN (A-G-DL-P, made concrete): put USERS into a GLOBAL group (e.g. "
                    "'GG-Finance'), put that global group into a DOMAIN LOCAL group tied to the resource "
                    "(e.g. 'DL-Finance-Share-Modify'), and grant the DOMAIN LOCAL group the NTFS "
                    "PERMISSION on the folder. To give someone access, you add them to the global group — "
                    "one change, correct scope, auditable. A junior USES this pattern; recognizing it "
                    "prevents the instinct to grant a user directly.\n\n"
                    "THE ACCESS-DENIED INVESTIGATION (domain version):\n"
                    "1. Reproduce; is it share or NTFS? (console vs network test, Week 6.)\n"
                    "2. Effective Access on the folder for the user — what group grants (or should grant) "
                    "this?\n"
                    "3. Is the user in the right GROUP? (ADUC → user → Member Of, or the group's Members.)\n"
                    "4. Did they sign out/in after a membership change? (Token refresh.)\n"
                    "5. Fix at the GROUP level; document the approver.\n\n"
                    "MAPPED DRIVES in a domain are often deployed by Group Policy (Week 15) — 'my drive is "
                    "missing' can be a policy/processing issue, not a permissions one.\n\n"
                    "COMMON MISTAKES: granting the user directly (breaks the model, unmaintainable); "
                    "adding to too-broad a group; forgetting sign-out/in; disabling inheritance to force "
                    "access; not checking whether the drive is GPO-deployed."
                ),
                "outcomes": [
                    "Apply group-based (A-G-DL-P) access instead of granting individual users",
                    "Run the domain access-denied investigation from reproduction to group-level fix",
                    "Recognize GPO-deployed drive mappings as a distinct cause from permissions",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]

MODULES_D += [
    {
        "code": "MOD-015",
        "title": "Group Policy",
        "description": "GPOs, application order, gpresult/RSoP troubleshooting. Week 15.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 16,
        "module_order": 16,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Group Policy Fundamentals",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Group Policy is how you enforce settings across many machines and users centrally — "
                    "password rules, drive mappings, security settings, software, desktop config. A GROUP "
                    "POLICY OBJECT (GPO) is a bundle of settings, LINKED to a site, domain, or OU; every "
                    "user/computer under that link gets it.\n\n"
                    "TWO HALVES of a GPO: COMPUTER configuration (applies at boot, per machine) and USER "
                    "configuration (applies at logon, per user). Knowing which half a setting lives in "
                    "tells you when it applies and what to reboot/re-logon to test.\n\n"
                    "APPLICATION ORDER — 'LSDOU', the key to troubleshooting: Local → Site → Domain → OU, "
                    "with LATER winning on conflict (OU-linked policy beats domain-linked). Nested OUs "
                    "apply parent-then-child. So a setting can be set at the domain and OVERRIDDEN closer "
                    "to the object. Modifiers: 'Enforced' (forces a GPO to win regardless of order) and "
                    "'Block Inheritance' (an OU refuses inherited GPOs, except Enforced ones). Most "
                    "'why did the wrong setting win?' tickets are an LSDOU/precedence story.\n\n"
                    "REFRESH: policy applies at boot/logon and refreshes periodically (~90 min); "
                    "'gpupdate /force' applies now. Some settings (like drive maps or scripts) only take "
                    "effect at the next logon.\n\n"
                    "A JUNIOR'S ROLE: you rarely DESIGN GPOs; you troubleshoot why an expected setting "
                    "isn't applying and report precisely. That means reading precedence and gpresult "
                    "(next lesson), not editing domain-wide policy casually — a bad GPO edit is an "
                    "everyone-outage.\n\n"
                    "COMMON MISTAKES: editing a GPO without knowing its link scope (blast radius); "
                    "expecting a user-config setting to apply at boot; forgetting gpupdate/re-logon; "
                    "ignoring Enforced/Block Inheritance when precedence looks 'wrong'."
                ),
                "outcomes": [
                    "Explain GPOs, links, and the computer vs user configuration halves",
                    "Apply LSDOU precedence including Enforced and Block Inheritance to predict which setting wins",
                    "Describe policy refresh timing and when a re-logon or gpupdate is required",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Troubleshooting Group Policy with gpresult and RSoP",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "When a policy 'isn't working', you don't guess — you ask the machine what it actually "
                    "applied. The tools:\n\n"
                    "gpresult /r — a text summary for the current user/computer: which GPOs applied, which "
                    "were FILTERED OUT and why, the OU location, and last refresh time. gpresult "
                    "/h report.html — a rich HTML Resultant Set of Policy report (the same data, "
                    "readable). Run as admin for computer-side data.\n\n"
                    "THE INVESTIGATION:\n"
                    "1. Is the GPO in the APPLIED list? No → why filtered? Common reasons: the "
                    "user/computer is in the wrong OU (the GPO isn't linked where they are), a SECURITY "
                    "FILTER excludes them (GPOs apply to 'Authenticated Users' by default; a custom filter "
                    "may omit them), or a WMI filter didn't match.\n"
                    "2. Is it applied but OVERRIDDEN? Check precedence (LSDOU) — a closer GPO won. gpresult "
                    "shows the winning GPO per setting area.\n"
                    "3. Did it just not REFRESH? gpupdate /force, or re-logon for user settings / reboot "
                    "for computer settings, then re-check.\n"
                    "4. Wrong OU is the classic root cause: the object was moved, or never in the OU the "
                    "GPO targets. Moving the object to the correct OU (with approval) fixes it.\n\n"
                    "REPORTING: 'GPO X is not in the applied list for USER on PC; gpresult shows they're in "
                    "OU=Temp, but the GPO is linked to OU=Finance — the account is in the wrong OU' is an "
                    "actionable finding a junior can hand up or fix with approval.\n\n"
                    "COMMON MISTAKES: guessing instead of running gpresult; not running elevated for "
                    "computer policy; missing the OU-location clue; blaming the GPO when it's a refresh/"
                    "re-logon timing issue; editing the GPO when the fix is moving the object."
                ),
                "outcomes": [
                    "Use gpresult /r and /h to determine which GPOs applied, were filtered, or were overridden",
                    "Diagnose the common causes: wrong OU, security filtering, precedence, and refresh timing",
                    "Report a GPO problem as an actionable finding or fix it at the correct level with approval",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-016",
        "title": "Server Networking and PowerShell for Administration",
        "description": "DNS/DHCP server roles, scopes, reservations; PowerShell discovery, pipeline, AD queries, CSV. Week 16.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 17,
        "module_order": 17,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "DNS and DHCP Server Roles",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "You've troubleshot DNS and DHCP from the CLIENT side for weeks. Now the SERVER side, "
                    "because in a Windows domain the DCs usually ARE the DNS and DHCP servers, and AD "
                    "itself depends on DNS.\n\n"
                    "DNS SERVER: hosts the zones that map names to addresses. For AD, DNS is not optional — "
                    "clients FIND domain controllers via special DNS records (SRV records). Junior tasks: "
                    "read a zone, check whether a record exists/is correct (a wrong or missing A record = "
                    "'can't reach server-by-name'), understand forwarders (how the server resolves names "
                    "it doesn't host — the internet). The client-side nslookup skill now has a server side "
                    "to inspect.\n\n"
                    "DHCP SERVER: hands out addresses from SCOPES (a range per subnet/VLAN) with OPTIONS "
                    "(gateway, DNS servers) and RESERVATIONS (a fixed address tied to a MAC — the RIGHT "
                    "way to give a printer/server a stable address, versus a hand-set static that causes "
                    "conflicts). Junior tasks: read a scope, check for exhaustion ('scope is full' = the "
                    "'whole area gets no IP' ticket, server side), add/verify a reservation, confirm scope "
                    "options are correct.\n\n"
                    "THE TIE-BACK: the DHCP-relay ticket (Week 11), the printer-IP-drift ticket (Week 8), "
                    "and 'can't reach by name' (Week 8) all have a server-side view here — a reservation "
                    "would have prevented the printer drift; a scope option explains a wrong gateway "
                    "handed to every client.\n\n"
                    "SAFETY: DNS/DHCP serve everyone. A bad zone edit or scope change is a broad outage — "
                    "change window, verify, and often escalate.\n\n"
                    "COMMON MISTAKES: hand-set statics instead of reservations; editing zones without "
                    "understanding SRV/AD dependency; not checking scope exhaustion; wrong scope options "
                    "pushed to all clients."
                ),
                "outcomes": [
                    "Explain why AD depends on DNS and how clients locate DCs via DNS records",
                    "Read and reason about DNS zones/records and DHCP scopes, options, and reservations",
                    "Connect server-side DNS/DHCP config to the client-side symptoms from earlier weeks",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "PowerShell for Investigation and Administration",
                "lesson_order": 2,
                "estimated_minutes": 120,
                "summary": (
                    "PowerShell is how you investigate and administer Windows at scale — and it's an "
                    "investigation tool long before it's a scripting one. It is NOT a software-development "
                    "course; it's a technician's power tool.\n\n"
                    "OBJECTS, NOT TEXT: PowerShell commands (cmdlets, Verb-Noun like Get-Service) return "
                    "OBJECTS with properties, which is why you can filter and sort precisely. The trio you "
                    "build everything from:\n"
                    "- DISCOVER: Get-Command (find cmdlets), Get-Help <cmdlet> -Examples (how to use it), "
                    "Get-Member (what properties/methods an object has). You are never stuck — you can ASK "
                    "PowerShell.\n"
                    "- FILTER & SELECT: Where-Object (keep rows that match), Select-Object (pick columns), "
                    "Sort-Object.\n"
                    "- PIPELINE: send objects from one cmdlet to the next: "
                    "Get-Service | Where-Object Status -eq 'Stopped' | Sort-Object Name.\n\n"
                    "REAL TASKS a junior runs:\n"
                    "- Services/processes: Get-Service, Get-Process, Restart-Service.\n"
                    "- Event logs: Get-WinEvent / Get-EventLog to pull specific events fast.\n"
                    "- AD (with the AD module): Get-ADUser, Get-ADGroupMember, Search-ADAccount "
                    "-LockedOut / -AccountDisabled — the account tickets from Week 13, but across HUNDREDS "
                    "of users at once ('find every locked account', 'list everyone in this group').\n"
                    "- EXPORT: Export-Csv turns any result into a spreadsheet for a report or a manager.\n\n"
                    "SAFETY: read before you write. Run the Get-/Search- (read-only) version first and "
                    "eyeball the results BEFORE any Set-/Remove-/Disable- (changing) command — especially "
                    "anything piped to a bulk change. -WhatIf shows what a command WOULD do without doing "
                    "it. A piped bulk operation without -WhatIf is how a junior accidentally disables 400 "
                    "accounts.\n\n"
                    "COMMON MISTAKES: treating output as text instead of objects; running a changing "
                    "command before verifying the read; forgetting -WhatIf on bulk operations; not using "
                    "Get-Help/Get-Member when stuck and guessing instead."
                ),
                "outcomes": [
                    "Use Get-Command, Get-Help, and Get-Member to discover how to do any task",
                    "Build pipelines with Where-Object/Select-Object to filter services, events, and AD accounts",
                    "Export results to CSV and apply read-before-write and -WhatIf safety on any changing command",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-017",
        "title": "Server Operations, Backup, and PowerShell at Scale",
        "description": "Event logs, services, scheduled tasks, Windows Server Backup with a real restore, patching, PowerShell remoting and small scripts. Week 17 — Gate 4.",
        "target_role": "Junior Systems Technician",
        "difficulty_band": 4,
        "estimated_hours": 17,
        "module_order": 18,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Server Operations: Logs, Services, and Scheduled Tasks",
                "lesson_order": 1,
                "estimated_minutes": 75,
                "summary": (
                    "Keeping a server healthy is daily operational work:\n"
                    "EVENT LOGS at server scale: the same Event Viewer skills (Week 3), but now the events "
                    "are about roles — AD replication, DNS, DHCP, service failures. Get-WinEvent (Week 16) "
                    "pulls them fast. The FIRST error in a chain still matters most.\n"
                    "SERVICES: roles run as services; a stopped 'Automatic' service (e.g. DHCP Server, DNS "
                    "Server, a specific AD service) is often the whole ticket. Check status, read WHY it "
                    "stopped (log), restart properly, verify the role recovered.\n"
                    "SCHEDULED TASKS: automated jobs (backups, scripts, maintenance). 'The nightly report "
                    "didn't run' = check Task Scheduler: last run result, history, the account it runs as "
                    "(a task failing after a password change is the service-account version of the "
                    "stale-credential ticket). A disabled or wrongly-credentialed task is a common, "
                    "diagnosable cause.\n\n"
                    "THE OPERATIONAL MINDSET: verify with evidence, change one thing, know the blast "
                    "radius, and document. A server's 'small' service restart may drop active sessions — "
                    "know what depends on it.\n\n"
                    "COMMON MISTAKES: restarting a role's service during business hours without checking "
                    "dependents; ignoring the task's run-as account after a password change; reading only "
                    "the latest event; no verification that the role actually recovered."
                ),
                "outcomes": [
                    "Investigate server role failures via event logs and service status",
                    "Diagnose failed scheduled tasks including run-as-account credential issues",
                    "Restart roles/services safely with awareness of dependents and verification",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Windows Server Backup and a Real Restore",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "A backup you've never restored is a hope, not a backup. This lesson's whole point is "
                    "that you will actually RESTORE something, because restore is the skill that matters "
                    "when it's 2 a.m. and a file is gone.\n\n"
                    "BACKUP CONCEPTS: Windows Server Backup (the built-in role) does full/volume and "
                    "file-level backups on a schedule to disk or a network target. The 3-2-1 idea (three "
                    "copies, two media, one offsite) is the principle behind why one backup on the same "
                    "disk isn't enough. Know what's protected: files, system state (which includes AD on a "
                    "DC), full server.\n\n"
                    "THE REAL RESTORE (the graded exercise): given a backup, restore a specific deleted "
                    "file/folder to a location, and VERIFY it — open it, check it's the right version, "
                    "confirm permissions came back. On a DC, understand that restoring AD (system state) "
                    "is a bigger, careful operation (authoritative vs non-authoritative restore is "
                    "awareness-level — a junior assists, doesn't lead a DC restore).\n\n"
                    "VERIFICATION IS THE POINT: 'I restored it' without opening the file is the "
                    "verification-anchor failure you learned in Week 1, at its most important. Restore, "
                    "then PROVE the data is intact and usable.\n\n"
                    "RECOVERY THINKING: before any risky change on a server, ask 'what's the restore path "
                    "if this goes wrong?' — the rollback mindset from Week 1, now with real backups behind "
                    "it.\n\n"
                    "COMMON MISTAKES: never testing restores; restoring to the wrong location and "
                    "overwriting good data; not verifying the restored data opens/is correct; treating a "
                    "single same-disk backup as safe; leading a DC/system-state restore without senior "
                    "involvement."
                ),
                "outcomes": [
                    "Explain backup scope (files, system state, full server) and the 3-2-1 principle",
                    "Perform and VERIFY a real file/folder restore from Windows Server Backup",
                    "Apply recovery-path thinking before risky changes and know the limits of a junior's role in a DC restore",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Patching and PowerShell Remoting at Scale",
                "lesson_order": 3,
                "estimated_minutes": 90,
                "summary": (
                    "Two capabilities that make you useful across MANY servers instead of one:\n\n"
                    "PATCHING & ROLLBACK: servers need updates, but a bad patch on a server is a bigger "
                    "deal than on a desktop. Concepts: staged/scheduled patching in maintenance windows, "
                    "checking update history (the desktop skill from Week 3, server scale), and ROLLBACK — "
                    "uninstalling a problem update, and why a pre-patch backup/snapshot is standard. WSUS "
                    "or Windows Update for Business centralize this (awareness). The junior lesson: patches "
                    "go in windows, with a rollback plan, verified after.\n\n"
                    "POWERSHELL REMOTING: run commands on remote servers without RDPing to each. "
                    "Enter-PSSession <server> for an interactive remote session; Invoke-Command -ComputerName "
                    "server1,server2 { Get-Service DNS } to run the SAME command across many servers and "
                    "get objects back. This is how you answer 'is this service running on all ten DCs?' in "
                    "one command. Read-before-write and -WhatIf (Week 16) matter MORE remotely — a bulk "
                    "remote change hits every target at once.\n\n"
                    "SMALL REPEATABLE SCRIPTS (not development): saving a verified pipeline as a .ps1 with "
                    "a clear name, a comment saying what it does, and basic safety (a -WhatIf pass, a "
                    "confirmation for changes). E.g. a script that finds locked accounts and reports them, "
                    "or restarts a named service on a list of servers with logging. Keep it small, "
                    "readable, and safe.\n\n"
                    "COMMON MISTAKES: patching without a window or rollback plan; bulk remote changes "
                    "without -WhatIf; scripts with no comment/logging that no one can trust later; running "
                    "a changing script you didn't read line-by-line."
                ),
                "outcomes": [
                    "Describe safe patching: maintenance windows, rollback plans, and post-patch verification",
                    "Use Enter-PSSession and Invoke-Command to investigate/administer many servers at once, safely",
                    "Write a small, commented, safe repeatable script for a real administrative task",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


QUIZZES_D = [
    {
        "title": "Active Directory Foundations",
        "week_number": 13, "domain_id": "3.0", "lesson_title": "Active Directory: Domains, OUs, Users, and Groups",
        "questions": [
            _q("What is an Organizational Unit (OU) primarily used for?",
               "Configuring DHCP client IP address assignments", "Organizing objects and applying GPOs",
               "Storing account passwords", "Routing traffic between VLANs",
               "B", "OUs organize users/computers/groups and are the unit GPOs target."),
            _q("Best practice for granting five users access to a folder is to:",
               "Grant each user folder rights", "Use a security group",
               "Make every user an administrator", "Share the folder with Everyone",
               "B", "Group-based access is maintainable and auditable; individual grants are not."),
            _q("A DISTRIBUTION group differs from a SECURITY group in that it:",
               "Grants NTFS permissions", "Cannot grant permissions",
               "Spans multiple AD forests", "Processes mail more quickly",
               "B", "Only security groups grant permissions; distribution groups are for email."),
            _q("A user reports their account is disabled. The correct first action is:",
               "Re-enable the account immediately", "Review why it was disabled",
               "Reset the account password", "Delete and recreate the account",
               "B", "Disabled accounts are disabled by process; blind re-enable can be a security incident."),
            _q("After adding a user to a new security group, they still can't access the resource. Missing step:",
               "Restart the domain controller service", "Refresh the user's sign-in token",
               "Reset the user's password", "Disable folder inheritance",
               "B", "Group membership is stamped into the logon token; a fresh logon is required."),
            _q("Which are valid AD group SCOPES? (select all that apply)",
               "Domain Local", "Global", "Universal", "Distribution",
               "A", "Domain Local/Global/Universal are scopes; Distribution is a group TYPE, not a scope.", multi="A,B,C"),
            _q("The A-G-DL-P best practice means:",
               "Accounts to groups to permissions",
               "Administrators get direct local permissions", "Assign groups directly to permissions",
               "All groups delete local passwords",
               "A", "Users into global groups, global into domain-local, domain-local gets the permission."),
            _q("To reset a user's password in AD you should also typically:",
               "Delete the associated user profile", "Verify identity and require a change",
               "Disable the user account", "Remove all assigned group memberships",
               "B", "Force a change at next logon, and always verify the requester's identity."),
        ],
    },
    {
        "title": "Domain Joins and File Access",
        "week_number": 14, "domain_id": "3.0", "lesson_title": "Domain Joins and Computer Accounts",
        "questions": [
            _q("The #1 reason a computer fails to join the domain is:",
               "Incorrect time-zone setting", "Wrong domain DNS server",
               "Insufficient system memory", "An enabled host firewall",
               "B", "Clients locate DCs via DNS SRV records; wrong DNS = can't find the domain."),
            _q("'The trust relationship between this workstation and the primary domain failed.' Best fix:",
               "Reinstall the operating system", "Repair the secure channel",
               "Change the user's password", "Always unjoin and rejoin first",
               "B", "Repair the secure channel; full unjoin/rejoin is the outdated sledgehammer."),
            _q("A disabled COMPUTER account in AD means:",
               "The user cannot sign in anywhere", "The machine cannot authenticate",
               "The entire domain is unavailable", "All Group Policy is disabled",
               "B", "A disabled computer account blocks that machine's domain authentication."),
            _q("In the A-G-DL-P model, to give a user access to the Finance share you:",
               "Grant the user direct NTFS rights", "Add the user to the Finance group",
               "Add the user to Domain Admins", "Share the folder with Everyone",
               "B", "Add the user to the appropriate global group; the permission chain does the rest."),
            _q("A user is in the correct group but still gets Access Denied. You should check: (select all that apply)",
               "Whether they signed out/in after the membership change", "Effective Access on the folder",
               "Whether it's a share vs NTFS restriction", "Whether the domain controller needs reinstalling",
               "A", "Token refresh, effective access, and share-vs-NTFS are the real checks; DC reinstall is not.", multi="A,B,C"),
            _q("Moving a computer account to a different OU can change:",
               "Its assigned network interface address", "Its applicable Group Policies", "Its hardware MAC address", "Its configured hostname",
               "B", "GPOs link to OUs; moving the object changes which policies it receives."),
            _q("'My mapped drive is missing' in a domain is often caused by:",
               "A failed local hard drive", "A Group Policy drive-map failure",
               "A workstation virus infection", "An incorrect DNS resolution setting",
               "B", "Domain drive maps are frequently GPO-deployed; a policy-processing issue removes them."),
        ],
    },
    {
        "title": "Group Policy Troubleshooting",
        "week_number": 15, "domain_id": "3.0", "lesson_title": "Troubleshooting Group Policy with gpresult and RSoP",
        "questions": [
            _q("Group Policy application order is:",
               "OU, Domain, Site, Local", "Local, Site, Domain, OU",
               "A random processing order", "Domain policies only",
               "B", "LSDOU; the closest link (OU) wins conflicts unless Enforced changes that."),
            _q("A setting expected from a domain GPO is being overridden. Most likely:",
               "A policy service is unavailable", "A closer GPO takes precedence",
               "DNS resolution failed", "The user's password expired",
               "B", "LSDOU precedence: an OU-linked GPO overrides the domain-linked one."),
            _q("To see exactly which GPOs applied to a user/computer, run:",
               "ipconfig /all", "gpresult /r", "nslookup query", "sfc /scannow",
               "B", "gpresult reports applied, filtered, and overridden policy."),
            _q("gpresult shows the GPO is NOT applied and was filtered. A common cause:",
               "A failed network cable", "Wrong OU placement or security filtering",
               "A powered-off monitor", "Slow DNS resolution",
               "B", "Wrong OU or a security filter excluding the object are classic filtering causes."),
            _q("'Enforced' on a GPO does what?",
               "Disables the linked GPO", "Overrides normal inheritance", "Applies only to computers", "Deletes conflicting policies",
               "B", "Enforced makes a GPO take precedence and pass through Block Inheritance."),
            _q("A user-configuration policy setting takes effect:",
               "At computer boot", "At the next user logon", "Never under any condition", "Only after a DC reboot",
               "B", "User config applies at logon; computer config at boot."),
            _q("The fix when gpresult shows the object is simply in the wrong OU is usually to:",
               "Edit the GPO settings", "Move it to the correct OU",
               "Reinstall the operating system", "Reset the user password",
               "B", "Correct the object's OU placement; don't edit the GPO for a placement problem."),
        ],
    },
    {
        "title": "Server DNS/DHCP and PowerShell",
        "week_number": 16, "domain_id": "3.0", "lesson_title": "PowerShell for Investigation and Administration",
        "questions": [
            _q("Why does Active Directory depend on DNS?",
               "It improves public internet response times", "Clients locate domain controllers",
               "It stores user passwords", "It has no AD role",
               "B", "Without correct DNS, clients can't find DCs and the domain 'doesn't work'."),
            _q("The RIGHT way to give a printer a stable address via DHCP is:",
               "Set a manual static address", "Create a DHCP reservation",
               "Turn off the DHCP service", "Assign the gateway address",
               "B", "Reservations give stable addresses without the conflict risk of manual statics."),
            _q("PowerShell cmdlets return ______, which is why you can filter on properties.",
               "Plain text", "Objects", "Images", "Nothing",
               "B", "Object output is what makes Where-Object/Select-Object precise."),
            _q("Which cmdlet finds all locked-out accounts?",
               "Get-Process", "Search-ADAccount -LockedOut", "Restart-Service", "Get-Help for Active Directory account commands",
               "B", "Search-ADAccount -LockedOut returns locked accounts across the directory."),
            _q("Before running a bulk CHANGING command against many objects, you should:",
               "Run it against all targets first", "Use -WhatIf first",
               "Restart the target server", "Disable audit logging first",
               "B", "Read-before-write and -WhatIf prevent mass-change accidents."),
            _q("Which cmdlets help you DISCOVER how to do something? (select all that apply)",
               "Get-Command", "Get-Help", "Get-Member", "Remove-Item",
               "A", "Get-Command/Get-Help/Get-Member are discovery; Remove-Item deletes things.", multi="A,B,C"),
            _q("To turn a query's results into a spreadsheet for a manager, pipe to:",
               "Format-List", "Export-Csv", "Out-Null", "Stop-Service",
               "B", "Export-Csv writes objects to a CSV file."),
            _q("A DHCP scope 'is full' and new devices in that subnet get no address. This is:",
               "A DNS resolution problem", "DHCP scope exhaustion",
               "A shared cable fault", "An account password issue",
               "B", "An exhausted scope hands out no more leases; the client sees APIPA."),
        ],
    },
    {
        "title": "Server Operations, Backup, and Remoting",
        "week_number": 17, "domain_id": "3.0", "lesson_title": "Windows Server Backup and a Real Restore",
        "questions": [
            _q("The single most important thing about a backup is:",
               "Its storage capacity", "A tested restore",
               "Its descriptive file name", "Its midnight schedule",
               "B", "An untested backup is a hope; restore is the skill that counts."),
            _q("After restoring a deleted file, you must:",
               "Close the ticket after notifying user", "Verify the file and permissions",
               "Delete the backup copy", "Restart the file server",
               "B", "Restore without verification is the verification-anchor failure."),
            _q("The 3-2-1 backup principle means:",
               "Three production servers and two admins", "Three copies, two media, one offsite",
               "Three backups each day", "Three gigabytes minimum",
               "B", "Three copies, two media, one offsite — why a single same-disk backup isn't enough."),
            _q("A nightly scheduled task stopped working right after a password change. Likely cause:",
               "The disk is full", "Stale run-as credentials",
               "A DNS resolution failure", "High processor utilization",
               "B", "Tasks run as an account; a changed password breaks the stored credential."),
            _q("Invoke-Command -ComputerName s1,s2 { Get-Service DNS } does what?",
               "Installs DNS on multiple named servers", "Runs a command on both servers",
               "Deletes the DNS service", "Restarts all named remote servers",
               "B", "It runs a command across many machines at once — read-only here."),
            _q("Before applying a patch to a production server, standard practice includes:",
               "No special preparation", "Plan, roll back, and verify",
               "Disable the server firewall", "Delete historical log files",
               "B", "Windows, rollback plans, and verification make server patching safe."),
            _q("A junior tech's role in a full Domain Controller / AD system-state restore is to:",
               "Lead the restore alone", "Assist a senior technician",
               "Refuse to participate", "Reinstall the domain controller",
               "B", "DC/AD restores are high-stakes; a junior assists rather than leads."),
        ],
    },
]


# The recurring Active Directory ticket family (master prompt: "a major recurring
# component"). Weeks 13-17, mixing account admin, domain ops, GPO, and server ops.
TICKETS_D = [
    {
        "title": "Bulk onboarding: five new hires need accounts and access by Monday",
        "description": (
            "HR sends five new {{DEPT}} hires starting Monday. Each needs an AD account in the correct "
            "OU, membership in the {{DEPT}} groups for file access, and the account set to change password "
            "at first logon. Manager approval for standard {{DEPT}} access is attached. You have ADUC and "
            "PowerShell on the DC."
        ),
        "difficulty": 3, "week_number": 13, "category": "Active Directory", "domain_id": "3.0",
        "root_cause": "Service request (not an incident): create accounts in the right OU, add to the correct GROUPS (not direct grants), enforce change-at-logon, document the approver",
        "root_cause_type": "account_provisioning",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Create accounts in the correct {{DEPT}} OU (not the default Users container)", "required_mention": ["ou", "create", "correct", "organizational unit"], "weight": 0.25},
            {"id": 2, "step": "Add to the correct {{DEPT}} GROUPS for access, not individual grants", "required_mention": ["group", "member", "add"], "weight": 0.3},
            {"id": 3, "step": "Set change-password-at-next-logon; verify enabled state", "required_mention": ["change at next logon", "must change", "enabled"], "weight": 0.2},
            {"id": 4, "step": "Document the approver; verify one account can log in and reach resources", "required_mention": ["approver", "approval", "verify", "logon"], "weight": 0.25},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "New accounts in the correct OU with group memberships", "validation": {}},
            {"type": "screenshot", "description": "One account's successful logon / resource access", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = correct OU chosen and standard onboarding steps followed methodically",
            "2 = access granted via the correct GROUPS (A-G-DL-P), not individual permissions",
            "2 = safe defaults (change-at-logon, least privilege); no over-broad group adds",
            "2 = at least one account verified logging in and reaching {{DEPT}} resources",
            "2 = approver documented; clear handoff note listing what was created",
        ),
        "model_answer": (
            "This is a service request. In the {{DEPT}} OU, create the five accounts (ADUC or New-ADUser "
            "in PowerShell for speed), set 'must change password at next logon', ensure enabled. Add each "
            "to the {{DEPT}} global group(s) that carry file access — never grant folders to the users "
            "directly. Document HR's approval. Verify by logging in as one account (or Search-ADAccount to "
            "confirm state) and confirming {{DEPT}} share access. Hand off a list of created accounts."
        ),
        "hints": [
            "This isn't a break/fix — it's provisioning. Where should the accounts LIVE, and how should access be granted?",
            "Access goes through groups, not folder-by-folder grants. Which OU and which groups are the {{DEPT}} standard?",
            "Create in the {{DEPT}} OU, add to the {{DEPT}} group(s), set change-at-next-logon, keep enabled.",
            "Accounts in the correct OU, membership in the correct {{DEPT}} groups (A-G-DL-P), change-at-logon set, approver documented, and verify one account logs in and reaches the share.",
        ],
        "parameters": {"placeholders": {"DEPT": ["Finance", "Marketing", "Operations", "Support", "Engineering"]}},
    },
    {
        "title": "'Trust relationship failed' on a restored laptop",
        "description": (
            "{{USER}}'s laptop was restored from an image after a disk failure. Now domain logon fails "
            "with 'The trust relationship between this workstation and the primary domain failed.' A local "
            "admin account still works. The machine is on the network and can reach the DC. You have local "
            "access and domain rights."
        ),
        "difficulty": 3, "week_number": 14, "category": "Active Directory", "domain_id": "3.0",
        "root_cause": "The restored image has a stale machine password; its secure channel with the domain is broken. Repairing the secure channel (or resetting the computer account) fixes it — full unjoin/rejoin is unnecessary",
        "root_cause_type": "broken_secure_channel",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Recognize the secure-channel/machine-password cause (esp. after image restore)", "required_mention": ["secure channel", "machine password", "trust", "restored"], "weight": 0.3},
            {"id": 2, "step": "Confirm connectivity/DNS to the DC is fine (rules out join prerequisites)", "required_mention": ["dns", "reach", "dc", "connectivity"], "weight": 0.2},
            {"id": 3, "step": "Repair the secure channel (Test-ComputerSecureChannel -Repair) / reset computer account", "required_mention": ["test-computersecurechannel", "repair", "reset computer account"], "weight": 0.3},
            {"id": 4, "step": "Verify domain logon works; avoid needless unjoin/rejoin", "required_mention": ["verify", "domain logon", "avoid unjoin", "logs in"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The repair command output / computer-account reset", "validation": {}},
            {"type": "screenshot", "description": "Successful domain logon after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = cause reasoned from the image-restore clue to a stale secure channel",
            "2 = broken secure channel identified (not 'reinstall Windows', not 'DNS')",
            "2 = secure-channel repair / computer-account reset used; needless unjoin/rejoin = 1",
            "2 = domain logon verified after the repair",
            "2 = user told plainly what happened and that no reinstall was needed",
        ),
        "model_answer": (
            "Image restore left a stale machine password, breaking the secure channel — the trust error. "
            "Connectivity/DNS to the DC is fine, so it's not a join prerequisite. Repair it: "
            "Test-ComputerSecureChannel -Repair (with domain credentials), or reset the computer account "
            "in AD and re-establish — NOT a full unjoin/rejoin. Reboot if needed, verify a domain logon "
            "succeeds. Explain to the user it was a post-restore trust issue, quickly repaired."
        ),
        "hints": [
            "The exact error names the problem. What kind of 'trust' does a domain-joined machine hold?",
            "It happened right after an IMAGE RESTORE. What does a machine store that an old image would make stale?",
            "The secure channel (machine password) is broken. There's a repair for that short of rejoining.",
            "Test-ComputerSecureChannel -Repair (or reset the computer account), then verify a domain logon. Skip the unjoin/rejoin sledgehammer.",
        ],
        "parameters": {"placeholders": {"USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"]}},
    },
    {
        "title": "New policy setting isn't reaching one department",
        "description": (
            "IT linked a GPO to enforce {{SETTING}} for the {{DEPT}} team. It works for everyone else, but "
            "{{DEPT}} users don't get it. Someone 'moved some accounts around' during a recent reorg. You "
            "have a {{DEPT}} test account, a domain-joined PC, and rights to run gpresult and read AD."
        ),
        "difficulty": 4, "week_number": 15, "category": "Active Directory", "domain_id": "3.0",
        "root_cause": "The {{DEPT}} user accounts were moved to the wrong OU during the reorg, so the GPO linked to the {{DEPT}} OU no longer applies to them; moving them back (or correcting the link) fixes it",
        "root_cause_type": "gpo_wrong_ou",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Run gpresult /r or /h for a {{DEPT}} user — is the GPO applied or filtered?", "required_mention": ["gpresult", "applied", "filtered", "report"], "weight": 0.3},
            {"id": 2, "step": "Read the object's OU location from gpresult / ADUC", "required_mention": ["ou", "location", "wrong ou", "moved"], "weight": 0.3},
            {"id": 3, "step": "Tie it to the reorg move; the account is outside the GPO's linked OU", "required_mention": ["reorg", "moved", "not linked", "outside"], "weight": 0.2},
            {"id": 4, "step": "Fix: move accounts to the correct OU (with approval), gpupdate/re-logon, verify", "required_mention": ["move", "correct ou", "gpupdate", "verify"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "gpresult showing the GPO filtered + the object's OU", "validation": {}},
            {"type": "screenshot", "description": "The setting applied after moving the account + gpupdate", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = gpresult run first (asked the machine) instead of guessing; OU location read",
            "2 = wrong-OU (outside the GPO's link) identified as the cause, tied to the reorg",
            "2 = fixed at the correct level (move object with approval); did NOT hack the GPO or grant elsewhere",
            "2 = setting verified applied after gpupdate/re-logon for a {{DEPT}} user",
            "2 = reported as an actionable finding: which accounts, which OU, why",
        ),
        "model_answer": (
            "Don't guess — run gpresult /r (or /h) for a {{DEPT}} user: the GPO is NOT in the applied list "
            "(filtered) and the report shows the account sitting in the wrong OU after the reorg. The GPO "
            "is linked to the {{DEPT}} OU, but these accounts were moved out of it. Fix: move the affected "
            "accounts back to the {{DEPT}} OU (with approval), run gpupdate /force and re-logon, verify "
            "{{SETTING}} now applies. Report which accounts and OUs were involved."
        ),
        "hints": [
            "Don't theorize about the GPO — ask the machine what it actually applied.",
            "gpresult /r or /h for a {{DEPT}} user. Is the GPO applied or filtered — and what OU is the account in?",
            "Someone 'moved accounts around'. A GPO only reaches objects UNDER its link. Where did the accounts land?",
            "The accounts are in the wrong OU, outside the GPO's link. Move them back (with approval), gpupdate/re-logon, and verify — don't edit the GPO for a placement problem.",
        ],
        "parameters": {"placeholders": {
            "DEPT": ["Finance", "Legal", "Sales", "HR", "Support"],
            "SETTING": ["a mapped drive", "the screen-lock timeout", "a security baseline", "a printer deployment", "a software restriction"],
        }},
    },
    {
        "title": "Find and report every locked and stale account before the audit",
        "description": (
            "Security asks for a report before Friday's audit: every currently LOCKED account, and every "
            "account that hasn't logged in for 90+ days (possible stale/leaver accounts). They want it as "
            "a spreadsheet. There are ~400 users. You have PowerShell with the AD module on the DC."
        ),
        "difficulty": 3, "week_number": 16, "category": "Active Directory", "domain_id": "3.0",
        "root_cause": "A reporting/investigation task best done with PowerShell: Search-ADAccount -LockedOut and Get-ADUser with a lastLogon filter, exported to CSV — done READ-ONLY, no changes without security's direction",
        "root_cause_type": "powershell_reporting",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Use PowerShell (not manual ADUC clicking through 400 users)", "required_mention": ["powershell", "search-adaccount", "get-aduser"], "weight": 0.3},
            {"id": 2, "step": "Locked accounts via Search-ADAccount -LockedOut", "required_mention": ["-lockedout", "locked"], "weight": 0.25},
            {"id": 3, "step": "Stale accounts via a lastLogon/lastLogonDate filter (90+ days)", "required_mention": ["lastlogon", "90", "stale", "filter"], "weight": 0.25},
            {"id": 4, "step": "Export-Csv; make NO changes (read-only report) unless security directs", "required_mention": ["export-csv", "read-only", "no changes", "report"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The PowerShell commands used and their output", "validation": {}},
            {"type": "screenshot", "description": "The exported CSV opened, showing the two lists", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = PowerShell chosen for scale; read-only approach stated up front",
            "2 = correct cmdlets/filters for locked and stale accounts",
            "2 = NO account changes made (report only); disabling/deleting without security's word = 0",
            "2 = accurate CSV produced and spot-verified against a known account",
            "2 = clear handoff: what the report contains and the recommendation to let security decide actions",
        ),
        "model_answer": (
            "Scale + spreadsheet = PowerShell, read-only. Locked: Search-ADAccount -LockedOut | "
            "Select-Object Name,SamAccountName,LockedOut | Export-Csv locked.csv. Stale: Get-ADUser "
            "-Filter * -Properties LastLogonDate | Where-Object { $_.LastLogonDate -lt (Get-Date).AddDays(-90) } "
            "| Select-Object Name,SamAccountName,LastLogonDate | Export-Csv stale.csv. Make NO changes — "
            "hand the report to security and let them decide on disables/removals. Spot-check one known "
            "account to confirm accuracy."
        ),
        "hints": [
            "400 users by hand in ADUC is a mistake. What tool does this in two commands?",
            "There's a cmdlet specifically for locked accounts, and a property for last logon you can filter on.",
            "Search-ADAccount -LockedOut for locked; Get-ADUser -Properties LastLogonDate + a Where-Object date filter for stale.",
            "Two read-only PowerShell queries piped to Export-Csv. Make NO account changes — this is a report; security decides the actions. Spot-check one entry.",
        ],
        "parameters": {"placeholders": {}},
    },
    {
        "title": "Restore the deleted quarterly folder from last night's backup",
        "description": (
            "The {{DEPT}} shared folder '\\\\FILES01\\{{DEPT}}\\Quarterly' was deleted this morning — a user "
            "thinks it was an accident during cleanup. Last night's Windows Server Backup completed "
            "successfully. {{DEPT}} needs it back for a report due this afternoon. You have access to the "
            "file server and its backups."
        ),
        "difficulty": 3, "week_number": 17, "category": "Active Directory", "domain_id": "3.0",
        "root_cause": "Accidental deletion; recover the folder from last night's Windows Server Backup to the correct location and VERIFY contents and permissions — restore is only done when verified",
        "root_cause_type": "backup_restore",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Confirm the loss and that a good backup exists before acting", "required_mention": ["backup", "last night", "deleted", "confirm"], "weight": 0.2},
            {"id": 2, "step": "Restore the specific folder to the CORRECT location (not overwriting other data)", "required_mention": ["restore", "correct location", "recover", "windows server backup"], "weight": 0.3},
            {"id": 3, "step": "VERIFY: contents present, right version, permissions intact", "required_mention": ["verify", "open", "permissions", "contents"], "weight": 0.3},
            {"id": 4, "step": "Confirm with the user; note what was restored and from when", "required_mention": ["confirm", "user", "restored from", "document"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The restore operation from Windows Server Backup", "validation": {}},
            {"type": "screenshot", "description": "The restored folder with contents and permissions verified", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = confirmed a good backup exists and the exact scope of loss before restoring",
            "2 = correct cause (accidental deletion) and correct recovery source identified",
            "2 = restored to the right location without overwriting good data; no risky improvisation",
            "2 = VERIFIED contents, version, and permissions — restore without verification scores 0 here",
            "2 = user confirmation obtained; note records what was restored and from when",
        ),
        "model_answer": (
            "Confirm the folder's gone and last night's backup is good. In Windows Server Backup → Recover "
            "→ select last night's backup → restore the '\\\\FILES01\\{{DEPT}}\\Quarterly' folder to its "
            "original location (or a staging path if you must avoid overwriting, then move). VERIFY: the "
            "expected files are present, it's last night's version, and permissions (the {{DEPT}} group "
            "access) came back. Confirm with a {{DEPT}} user that the report data is there. Document what "
            "was restored and the backup date."
        ),
        "hints": [
            "You have a good backup from last night — but what must you do AFTER restoring to actually close this well?",
            "Windows Server Backup → Recover. Restore the specific folder; be careful WHERE you restore it.",
            "Restore to the correct location without clobbering other data, then verify contents AND permissions.",
            "Recover the folder from last night's backup, verify the files, version, and {{DEPT}} permissions are intact, and confirm with the user before closing. 'Restored' without opening it doesn't count.",
        ],
        "parameters": {"placeholders": {"DEPT": ["Finance", "Sales", "Operations", "Legal", "Marketing"]}},
    },
]


# One VM-backed AD lab (MANUAL-VM viable; AUTO-VM target). Break-fix on a DC +
# client. Idempotent by title in seed_phase_d().
AD_LABS = [
    {
        "title": "AD Break-Fix: locked and misplaced account on a live domain",
        "lesson_id": None,
        "lab_type": "break_fix",
        "difficulty": 4,
        "week_number": 15,
        "estimated_minutes": 60,
        "is_published": True,
        "environment_requirements": {
            "vms": [
                {"role": "domain_controller", "template": "WS2022-DC", "notes": "AD DS + DNS + DHCP"},
                {"role": "client", "template": "Win11-Enterprise", "notes": "domain-joined"},
            ],
            "manual_vm_ok": True,
            "auto_vm_target": True,
        },
        "setup_instructions": (
            "MANUAL-VM PATH (works today): clone the WS2022-DC and Win11 client templates, ensure the "
            "client's DNS points at the DC, and confirm a baseline domain logon works. Grant the student "
            "RDP to the client and (read-mostly) access to the DC over Headscale. AUTO-VM path: the same, "
            "provisioned by the pipeline once its P0s pass a real smoke test — not required for this lab."
        ),
        "break_script": (
            "Per-student parametrized break (mentor applies one variant): (1) lock the test user's account "
            "by exceeding bad-password attempts OR set it locked; (2) move the test user OUT of the OU that "
            "carries a visible GPO setting (e.g. a mapped drive) into a Temp OU. Student must both unlock "
            "the account AND restore the missing policy by returning the account to the correct OU."
        ),
        "success_criteria": {
            "criteria": [
                "Test user account is unlocked and can log on",
                "Account is back in the correct OU",
                "The GPO-delivered setting (e.g. mapped drive) is present after gpupdate/re-logon",
                "Student used gpresult to diagnose the policy gap rather than guessing",
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "Account unlocked in ADUC", "validation": {}},
                {"type": "screenshot", "description": "gpresult showing the GPO now applied + correct OU", "validation": {}},
                {"type": "screenshot", "description": "Successful client logon with the policy setting present", "validation": {}},
            ]
        },
        "hints": {
            "hints": [
                "Two things are wrong: the account state and where the account lives. Check both.",
                "Unlock is easy; for the missing setting, run gpresult and read the OU.",
                "The account is in the wrong OU, so the GPO doesn't reach it. Move it back.",
                "Unlock the account, move it to the correct OU, gpupdate/re-logon, and verify both logon and the policy setting.",
            ]
        },
        "model_solution": (
            "ADUC → find the test user → Unlock. Run gpresult /r for the user: the expected GPO is filtered "
            "and the account is in the Temp OU. Move the account back to the correct OU (with approval), "
            "gpupdate /force, re-logon on the client, verify the mapped drive / setting returns and the "
            "user can log in. Document both fixes.\n\nRESET: mentor re-locks and re-moves per the break "
            "script for the next student; nothing destructive persists."
        ),
        "proxmox_template_vmid": None,
    },
]


def seed_phase_d(db) -> dict:
    """Idempotent Phase D seed — modules, lessons, quizzes, AD tickets, and one AD lab."""
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
    from app.models.ticket import Ticket
    from app.services.seed_question_sync import sync_seed_questions
    from app.models.lab import LabTemplate

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0, "tickets": 0, "labs": 0}
    prev_module = db.query(Module).filter(Module.code == "MOD-012").first()
    for spec in MODULES_D:
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

    for qspec in QUIZZES_D:
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

    for tspec in TICKETS_D:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()

    for lspec in AD_LABS:
        lab = db.query(LabTemplate).filter(LabTemplate.title == lspec["title"]).first()
        if lab is None:
            db.add(LabTemplate(**lspec))
            counts["labs"] += 1
        else:
            for k, v in lspec.items():
                setattr(lab, k, v)
    db.flush()
    return counts
