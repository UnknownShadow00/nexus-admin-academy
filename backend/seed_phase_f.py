"""Phase F (Weeks 21-22) curriculum content — Azure & Cloud Fundamentals.

HARD CONSTRAINT (master prompt): every activity has a ZERO-COST fallback —
Microsoft Learn free sandboxes, the always-free Azure tier, guided screenshot
walkthroughs, or mentor-led demos. NO promotion requirement depends on
spending money. Where the free path is time-limited (Learn sandboxes) or
requires a card (free-tier signup), the lesson says so honestly and gives the
no-card alternative.

Scope: AZ-900-level concepts applied through a support/admin lens — the goal
is a junior who can work cloud-touching tickets (Entra ID lockouts, VM
connectivity, storage access), not a cloud architect.

No new role gate here — Weeks 21-22 feed Gate 5's mixed-incident requirements
in Phase G.
"""

from seed_phase_a import ANCHORS, NOTES_TEMPLATE, _q

MODULES_F = [
    {
        "code": "MOD-021",
        "title": "Cloud Concepts and Entra ID",
        "description": "Cloud service models, Azure structure, Entra ID identity administration, hybrid identity awareness. Week 21.",
        "target_role": "Junior Infrastructure Administrator",
        "difficulty_band": 5,
        "estimated_hours": 15,
        "module_order": 22,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Cloud Concepts That Matter on the Job",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Cloud is someone else's datacenter with an API — the concepts a support tech actually "
                    "uses:\n\n"
                    "SERVICE MODELS as responsibility lines (who fixes what — this decides how you route "
                    "tickets):\n"
                    "- IaaS (a VM in Azure): the provider owns the hardware/hypervisor; YOU own the OS up "
                    "— patching, services, firewall. An Azure VM ticket is mostly a Windows/Linux ticket "
                    "(Weeks 3-20 skills) with a cloud wrapper.\n"
                    "- PaaS (a managed database/app service): provider owns the OS too; you own your app "
                    "and data. 'Restart the server' is often not even a thing — different playbook.\n"
                    "- SaaS (Microsoft 365): you own users, access, and configuration only. Most tickets "
                    "are identity and licensing.\n\n"
                    "AZURE'S STRUCTURE (so portal navigation makes sense): Tenant (your organization's "
                    "identity boundary, holds Entra ID) → Subscriptions (billing boundaries) → Resource "
                    "Groups (folders for related resources) → Resources (VMs, storage...). 'Which "
                    "subscription / resource group is it in?' is the cloud version of 'which server is it "
                    "on?'.\n\n"
                    "REGIONS & AVAILABILITY (awareness): resources live in regions; redundancy options "
                    "exist. Junior relevance: 'is there a regional outage?' is a legitimate triage check "
                    "(the Azure status page) before deep-diving a cloud ticket.\n\n"
                    "COST AWARENESS: cloud resources bill by existence and usage. A junior never creates "
                    "resources casually and flags orphaned ones. In THIS program you never need to spend: "
                    "all activities below have zero-cost paths.\n\n"
                    "ZERO-COST ACTIVITY: Microsoft Learn's AZ-900 'Describe cloud concepts' modules "
                    "(free, no signup needed to read; free sandbox where offered) + a mentor-led portal "
                    "tour on the mentor's tenant, screen-shared on Discord. No student spends anything.\n\n"
                    "COMMON MISTAKES: treating an IaaS VM ticket as exotic (it's a Windows/Linux box); "
                    "not knowing which service model owns the fix; creating billable resources to 'test "
                    "something'."
                ),
                "outcomes": [
                    "Use IaaS/PaaS/SaaS responsibility lines to decide who owns a fix and route tickets",
                    "Navigate the tenant → subscription → resource group → resource hierarchy conceptually",
                    "Apply cloud cost-awareness and regional-outage checks to triage",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Entra ID: Cloud Identity Administration",
                "lesson_order": 2,
                "estimated_minutes": 120,
                "summary": (
                    "Entra ID (formerly Azure AD) is the cloud identity system — the AD skills from Week "
                    "13, in the cloud, with some crucial differences. This is the highest-volume cloud "
                    "ticket source (Entra lockouts and MFA problems are bread-and-butter).\n\n"
                    "SAME IDEAS, NEW HOME: users, groups, and roles exist; group-based access still beats "
                    "individual grants; disabled accounts ('Block sign-in' in Entra) still mean 'find out "
                    "WHY before re-enabling'. Your Week 13 safety rails all apply.\n\n"
                    "KEY DIFFERENCES a junior must know:\n"
                    "- NO OUs — organization is by groups and administrative units; policy comes from "
                    "Conditional Access, not GPO.\n"
                    "- MFA is central: many 'can't log in' tickets are really 'lost phone / new phone / "
                    "MFA method broken'. The fix is re-registering authentication methods (with identity "
                    "verification FIRST — the Week 6 rail matters MORE here, since an attacker resetting "
                    "MFA owns the account).\n"
                    "- SIGN-IN LOGS are your evidence pane: Entra's sign-in log shows every attempt — "
                    "success/failure, WHY it failed (bad password? MFA denied? Conditional Access block? "
                    "'risky sign-in' lock?), from WHERE. This replaces guessing. A lockout ticket starts "
                    "at the sign-in log.\n"
                    "- SELF-SERVICE PASSWORD RESET (SSPR) exists; part of support is checking whether the "
                    "user can self-serve and why SSPR failed for them.\n\n"
                    "HYBRID IDENTITY (awareness): most real orgs sync on-prem AD to Entra (Entra Connect). "
                    "One human, two linked accounts. Junior relevance: know WHERE a password/account "
                    "change must happen (usually on-prem AD, which syncs up) — changing it in the wrong "
                    "place 'doesn't stick'. 'Password works on the laptop but not in the cloud' (or vice "
                    "versa) is a sync question: is Entra Connect healthy, when did it last sync?\n\n"
                    "ZERO-COST ACTIVITY: Microsoft Learn's Entra ID fundamentals modules (free) + "
                    "mentor-led walkthrough of the sign-in log and user administration on the mentor's "
                    "tenant (screen-shared; students drive verbally). A free Entra tenant can be created "
                    "without spend for those who want hands-on, but NO assessment requires it.\n\n"
                    "COMMON MISTAKES: resetting MFA without verifying identity (account-takeover risk); "
                    "guessing at lockout causes instead of reading the sign-in log; changing a synced "
                    "password in the cloud when the source is on-prem; re-enabling blocked sign-in "
                    "without asking why it was blocked."
                ),
                "outcomes": [
                    "Administer Entra users/groups with the same safety rails as on-prem AD",
                    "Investigate sign-in failures via the Entra sign-in log instead of guessing",
                    "Handle MFA-reset requests with strict identity verification, and reason about hybrid sync direction",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-022",
        "title": "Azure Infrastructure for Support",
        "description": "Azure VMs, NSGs, storage, cloud networking basics, cloud-vs-on-prem decisions. Week 22.",
        "target_role": "Junior Infrastructure Administrator",
        "difficulty_band": 5,
        "estimated_hours": 15,
        "module_order": 23,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Azure VMs and Network Security Groups",
                "lesson_order": 1,
                "estimated_minutes": 120,
                "summary": (
                    "An Azure VM is a Windows or Linux box you already know how to fix — wrapped in cloud "
                    "controls that add NEW failure points. The support model:\n\n"
                    "INSIDE the VM: everything from Weeks 3-20 applies unchanged — services, logs, disk, "
                    "permissions. RDP/SSH in and it's the same work.\n\n"
                    "AROUND the VM (the cloud-specific layer — where cloud tickets differ):\n"
                    "- VM STATE: is it running? Stopped (deallocated) VMs aren't reachable and their "
                    "dynamic public IPs CHANGE on restart — 'the IP I always use stopped working' after a "
                    "deallocation is a classic.\n"
                    "- NETWORK SECURITY GROUPS (NSGs): the cloud firewall, as rule lists on the VM's NIC "
                    "and/or subnet. 'Can't RDP/SSH to the VM' with the VM running = check the NSG rule "
                    "for 3389/22 — the ufw/Windows-firewall lesson (Weeks 7/20), cloud edition. Same "
                    "discipline: find/add the RULE, never open everything to the internet ('Any/Any' "
                    "inbound is the cloud's chmod 777).\n"
                    "- PUBLIC vs PRIVATE IPs: the VM sees its private IP; the public one is a mapping. "
                    "ipconfig inside won't show the public address — a confusion worth pre-empting.\n"
                    "- THE PORTAL'S DIAGNOSTICS: boot diagnostics (a console screenshot of a wedged VM!), "
                    "resource health, and the activity log ('who changed what, when' — the cloud's "
                    "show-logging).\n\n"
                    "THE CLOUD-VM TRIAGE (RDP/SSH unreachable): VM running? → NSG allows the port from "
                    "your source? → public IP correct/current? → THEN in-guest causes (the Week 7 RDP "
                    "gates). Outside-in, because the cloud layer is new and cheap to check.\n\n"
                    "ZERO-COST ACTIVITY: Microsoft Learn's 'Create a VM' sandbox modules give a REAL, "
                    "free, time-boxed Azure environment (no card, no spend) to create and inspect a VM "
                    "and its NSG. Fallback for sandbox-unavailable days: the mentor-led guided screenshot "
                    "walkthrough in the module resources. NO assessment requires a paid resource.\n\n"
                    "COMMON MISTAKES: opening RDP/SSH to 'Any' source; not checking VM state before deep "
                    "triage; expecting a stopped VM's dynamic IP to survive; treating in-guest and NSG "
                    "layers as one problem."
                ),
                "outcomes": [
                    "Triage an unreachable Azure VM outside-in: state → NSG → IP → in-guest",
                    "Read and reason about NSG rules with least-privilege discipline (no Any/Any)",
                    "Use boot diagnostics, resource health, and the activity log as cloud evidence sources",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Azure Storage and Cloud-vs-On-Prem Thinking",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "AZURE STORAGE for support: a storage account holds blobs (files/objects), file "
                    "shares (SMB shares in the cloud — mountable like \\\\server\\share!), and more. "
                    "Junior-relevant failure points:\n"
                    "- ACCESS: who can reach a blob/share is controlled by access keys, SAS tokens "
                    "(time-limited signed URLs — 'the link stopped working' often = an EXPIRED SAS token, "
                    "a wonderfully diagnosable ticket), and Entra-based RBAC roles. Least privilege "
                    "applies: a Reader role beats handing out account keys.\n"
                    "- NETWORK: storage accounts can restrict which networks may connect — 'works from "
                    "the office, fails from home' for a storage resource is often the storage firewall, "
                    "not the user.\n"
                    "- An Azure Files share mounted on Windows behaves like any mapped drive — including "
                    "the credential problems you already know from Week 6.\n\n"
                    "CLOUD-vs-ON-PREM DECISIONS (the thinking employers want juniors to follow): it's a "
                    "trade-off conversation, not a religion —\n"
                    "- Cloud favors: variable/spiky load, fast provisioning, no hardware ownership, "
                    "global access, OpEx.\n"
                    "- On-prem favors: steady predictable load (often cheaper long-run), data that must "
                    "stay local (regulation/latency), existing hardware investment, full control.\n"
                    "- HYBRID is the real world: identity synced (Week 21), some workloads in each place. "
                    "A junior's job is to know WHERE a resource lives so tickets route correctly, and to "
                    "articulate the trade-off when asked — not to make the call alone.\n\n"
                    "TIE-BACK TO NEXUS ITSELF: this program runs on Abdi's Proxmox — an on-prem choice "
                    "(owned hardware, zero marginal cost, full control, learning value). That's a live "
                    "case study of the trade-off.\n\n"
                    "ZERO-COST ACTIVITY: Microsoft Learn storage-fundamentals modules + sandbox where "
                    "offered; mentor-led demo of a SAS token expiring (create one with a 5-minute expiry, "
                    "watch it die) on the mentor's tenant. NO assessment requires paid resources.\n\n"
                    "COMMON MISTAKES: handing out account keys where a scoped SAS/RBAC role would do; "
                    "missing SAS expiry as a cause; forgetting the storage-side network rules; arguing "
                    "cloud-vs-on-prem as ideology instead of trade-offs."
                ),
                "outcomes": [
                    "Diagnose storage access failures across SAS expiry, RBAC/keys, and storage network rules",
                    "Treat Azure Files like the SMB share it is, reusing mapped-drive troubleshooting",
                    "Articulate cloud-vs-on-prem/hybrid trade-offs and route tickets by where resources live",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


QUIZZES_F = [
    {
        "title": "Cloud Concepts and Entra ID",
        "week_number": 21, "domain_id": "7.0", "lesson_title": "Entra ID: Cloud Identity Administration",
        "questions": [
            _q("A ticket concerns a broken OS service on an Azure IaaS VM. Who owns the fix?",
               "Microsoft — it's their cloud", "You/your org — IaaS means you own the OS and up",
               "The ISP", "Nobody",
               "B", "IaaS responsibility: provider owns hardware/hypervisor; the customer owns OS, services, patching."),
            _q("In Azure's hierarchy, resources are organized as:",
               "Tenant → Subscription → Resource Group → Resource", "Region → User → File",
               "Domain → OU → GPO", "Cluster → Node → Pod",
               "A", "Tenant (identity) → subscriptions (billing) → resource groups → resources."),
            _q("An Entra 'can't log in' ticket should START with:",
               "Resetting the password immediately", "Reading the user's sign-in log to see WHY attempts fail",
               "Re-enabling the account", "Reinstalling Office",
               "B", "The sign-in log shows the actual failure reason (bad password, MFA, CA block, risk lock) — evidence before action."),
            _q("A user lost their phone and asks you to reset their MFA. Before anything else you must:",
               "Reset it — they sound stressed", "Verify their identity through the defined process",
               "Disable MFA permanently", "Give them your phone",
               "B", "MFA reset without verification is the account-takeover playbook; the Week 6 rail applies doubly."),
            _q("In a hybrid (Entra Connect) setup, a synced user's password change usually must happen:",
               "In the cloud only", "In on-prem AD (the source), which then syncs to Entra",
               "On the user's phone", "Nowhere",
               "B", "Changes made in the wrong direction 'don't stick'; know the sync source."),
            _q("Entra ID differs from on-prem AD in that: (select all that apply)",
               "There are no OUs — organization is via groups/administrative units",
               "Policy comes from Conditional Access rather than GPO",
               "MFA and sign-in risk are first-class citizens", "Groups don't exist",
               "A", "No OUs, CA instead of GPO, and central MFA are the key differences; groups very much exist.", multi="A,B,C"),
            _q("'Password works on my laptop but not on webmail' in a hybrid org suggests:",
               "The user is wrong", "A sync question — check Entra Connect health and last sync",
               "A dead NIC", "A GPO problem",
               "B", "Split behavior between on-prem and cloud logons points at identity sync."),
            _q("An account shows 'Block sign-in' enabled. Correct move:",
               "Unblock it — that's the fix", "Find out WHY it was blocked (security/HR) before touching it",
               "Delete the account", "Reset MFA",
               "B", "Blocked sign-in is the cloud 'disabled account' — same Week 13 rail: reason before re-enable."),
        ],
    },
    {
        "title": "Azure VMs, NSGs, and Storage",
        "week_number": 22, "domain_id": "7.0", "lesson_title": "Azure VMs and Network Security Groups",
        "questions": [
            _q("You can't SSH to a running Azure Linux VM. The FIRST cloud-layer check is:",
               "Reinstall the VM", "The NSG — is port 22 allowed from your source?",
               "The user's keyboard", "DNS on your laptop",
               "B", "Outside-in: state (running ✓) → NSG rule → IP → then in-guest causes."),
            _q("A VM was stopped (deallocated) overnight; now 'its IP doesn't work'. Likely cause:",
               "Hackers", "Dynamic public IPs change on deallocation/restart",
               "The NSG deleted itself", "DNS poisoning",
               "B", "Deallocated VMs release dynamic public IPs; a new one is assigned at start."),
            _q("Opening RDP inbound from 'Any' source on an NSG is:",
               "Best practice", "The cloud equivalent of chmod 777 — exposes the VM to the whole internet",
               "Required by Azure", "Harmless",
               "B", "Scope inbound management ports to known sources; Any/Any invites attacks."),
            _q("A wedged Azure VM won't respond at all. A cloud evidence source for 'what's on its screen' is:",
               "The activity log", "Boot diagnostics (console screenshot)", "The storage firewall", "Entra sign-in logs",
               "B", "Boot diagnostics shows the console — like standing at a physical monitor."),
            _q("A shared blob link 'suddenly stopped working' for an external partner. A classic cause:",
               "The internet is down", "The SAS token expired", "The VM rebooted", "MFA",
               "B", "SAS tokens are time-limited by design; expiry is the first check."),
            _q("'Storage works from the office but not from home' most likely involves:",
               "The user's chair", "The storage account's network rules restricting allowed networks",
               "A full disk", "A GPO",
               "B", "Storage-side network restrictions produce exactly this location-dependent pattern."),
            _q("Which favor CLOUD in a cloud-vs-on-prem decision? (select all that apply)",
               "Spiky/variable load", "Fast provisioning without buying hardware",
               "Steady predictable load on owned hardware", "Global access needs",
               "A", "Spiky load, speed, and global access favor cloud; steady load on owned gear often favors on-prem.", multi="A,B,D"),
            _q("'Who changed this NSG rule and when?' is answered by:",
               "Boot diagnostics", "The Azure activity log", "ipconfig", "The VM's event viewer",
               "B", "The activity log is the audit trail of control-plane changes."),
        ],
    },
]


# Cloud tickets — including the Entra lockout from the real-world scenario list.
TICKETS_F = [
    {
        "title": "Entra ID: exec locked out of everything before a board call",
        "description": (
            "{{USER}}, an executive assistant, calls at 8:40: their Microsoft 365 sign-in fails "
            "everywhere ('your account is locked') and they prepare the 9:30 board pack. They got a new "
            "phone yesterday. The org is hybrid (on-prem AD synced via Entra Connect). You have Entra "
            "admin access and the sign-in logs."
        ),
        "difficulty": 4, "week_number": 21, "category": "Cloud", "domain_id": "7.0",
        "root_cause": "Sign-in logs show repeated MFA failures then a risk-based lock: the new phone never got the Authenticator re-registered, and the old registration keeps failing. Verify identity, clear the risk/unlock, re-register MFA methods for the new phone; password itself was never wrong",
        "root_cause_type": "entra_mfa_lockout",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Read the sign-in log FIRST: what is actually failing (password? MFA? risk lock?)", "required_mention": ["sign-in log", "mfa", "risk", "failure reason"], "weight": 0.3},
            {"id": 2, "step": "Connect the new-phone clue to the broken MFA registration", "required_mention": ["new phone", "authenticator", "registration", "method"], "weight": 0.25},
            {"id": 3, "step": "Verify identity through the defined process BEFORE any reset (exec = high-value target)", "required_mention": ["verify", "identity", "callback", "process"], "weight": 0.25},
            {"id": 4, "step": "Clear the lock, re-register MFA on the new phone, verify a full sign-in; no blanket MFA disable", "required_mention": ["unlock", "re-register", "verify sign-in", "not disable"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Sign-in log entries showing the MFA failures / risk lock", "validation": {}},
            {"type": "screenshot", "description": "Successful sign-in after MFA re-registration", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = sign-in log read before any action; new-phone clue connected",
            "2 = MFA re-registration gap + risk lock identified (not 'wrong password')",
            "2 = identity verified BEFORE reset (skipping this on an exec = 0); MFA re-registered, NOT disabled",
            "2 = end-to-end sign-in verified before the 9:30 deadline; risk state cleared properly",
            "2 = calm deadline-aware handling; user shown how to re-register next phone swap",
        ),
        "model_answer": (
            "Sign-in log: password succeeds, MFA fails repeatedly (old registration), then a risk-based "
            "lock. The new phone is the cause — Authenticator was never re-registered. VERIFY IDENTITY "
            "first (exec accounts are prime targets; use the callback/manager process). Then clear the "
            "lock/risk, delete the stale authentication method, re-register Authenticator on the new "
            "phone, and watch a full successful sign-in before 9:30. Do not disable MFA 'temporarily'. "
            "Close with a one-liner on self-service method management for next time."
        ),
        "hints": [
            "Don't guess at 'locked'. Entra records exactly WHY every attempt failed — where?",
            "The sign-in log shows the password is fine. What changed for this user yesterday?",
            "New phone = the old MFA registration is failing. And who might pretend to be a locked-out exec? Verify first.",
            "Verify identity via the process, clear the risk lock, re-register MFA on the new phone, and confirm a complete sign-in before the board call — never bypass or disable MFA as a shortcut.",
        ],
        "parameters": {"placeholders": {"USER": ["c.moreno", "j.whitfield", "a.osei", "l.tanaka", "p.novak"]}},
    },
    {
        "title": "Azure: can't RDP to the reporting VM since the weekend",
        "description": (
            "The finance team's Azure VM AZ-RPT01 (Windows, IaaS) is unreachable over RDP since Monday. "
            "The portal shows the VM 'Running'. Over the weekend, a cost-cleanup script deallocated and "
            "restarted several VMs, and a security review 'tightened some network rules'. Users connect "
            "by a saved IP address. You have portal access."
        ),
        "difficulty": 4, "week_number": 22, "category": "Cloud", "domain_id": "7.0",
        "root_cause": "Two compounding cloud-layer causes: the weekend deallocation changed the VM's dynamic public IP (users' saved IP is stale), AND the security review's NSG change restricted RDP to a source range that excludes the finance subnet. Fix: current IP (or better, a DNS name/static IP), plus a correct NSG allow rule — never Any/Any",
        "root_cause_type": "azure_vm_unreachable",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Outside-in triage: VM Running ✓ → check current public IP vs the saved one", "required_mention": ["public ip", "changed", "deallocat", "current"], "weight": 0.3},
            {"id": 2, "step": "Check the NSG: is 3389 allowed from the finance source after the review?", "required_mention": ["nsg", "3389", "rule", "source"], "weight": 0.3},
            {"id": 3, "step": "Fix both: correct/least-privilege NSG rule + current IP; recommend static IP or DNS name", "required_mention": ["allow", "least", "static", "dns name"], "weight": 0.25},
            {"id": 4, "step": "Verify RDP from the finance side; activity log confirms what changed and when", "required_mention": ["verify", "rdp", "activity log", "when"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Current public IP + the NSG rule before/after", "validation": {}},
            {"type": "screenshot", "description": "Successful RDP from a finance machine", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = outside-in walked (state → IP → NSG) with both weekend changes investigated; activity log used",
            "2 = BOTH causes found — stale dynamic IP AND the tightened NSG (finding only one = 1)",
            "2 = least-privilege NSG rule (finance source, not Any) + static-IP/DNS recommendation; Any/Any = 0",
            "2 = RDP verified from an actual finance machine",
            "2 = users given a durable way to connect (name/static IP) so the stale-IP class of ticket dies",
        ),
        "model_answer": (
            "VM Running, so the cloud layer: the weekend deallocation rotated the dynamic public IP — the "
            "saved IP is stale. AND the activity log shows the security review changed the NSG: RDP is now "
            "allowed only from a range excluding finance. Fix both: add a least-privilege 3389 allow from "
            "the finance source (never Any), give users the CURRENT IP, and fix the class of problem — "
            "assign a static public IP or a DNS name so deallocations stop breaking saved addresses. "
            "Verify RDP from a finance machine."
        ),
        "hints": [
            "The VM is 'Running', so go outside-in. Two different things changed this weekend — check both.",
            "What happens to a dynamic public IP when a VM is deallocated? Compare the current IP to the one users saved.",
            "Now the NSG: after the security review, from which sources is 3389 actually allowed?",
            "Stale dynamic IP + a tightened NSG. Add a least-privilege RDP rule for the finance source, hand out the current address, and make it durable with a static IP or DNS name. Verify from a finance machine.",
        ],
        "parameters": {"placeholders": {}},
    },
    {
        "title": "Azure: partner's download link died mid-project",
        "description": (
            "An external partner reports the download link {{TEAM}} shared for the project files "
            "(an Azure blob URL with a long token in it) 'worked all month and now gives an error about "
            "authentication'. The files are still in the storage account, unchanged. {{TEAM}} 'didn't "
            "touch anything'. You have portal access to the storage account."
        ),
        "difficulty": 3, "week_number": 22, "category": "Cloud", "domain_id": "7.0",
        "root_cause": "The link is a SAS URL and its token reached its expiry date — by design. Issue a new SAS with an appropriate (least-privilege, time-boxed) scope, or better, set up proper partner access; nothing is 'broken'",
        "root_cause_type": "sas_expiry",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Recognize the long-token URL as a SAS link; 'worked then stopped' = expiry pattern", "required_mention": ["sas", "token", "expir"], "weight": 0.35},
            {"id": 2, "step": "Confirm the files/account are intact — nothing is broken; access just lapsed", "required_mention": ["intact", "unchanged", "not broken", "files"], "weight": 0.2},
            {"id": 3, "step": "Issue a new SAS: least privilege (read-only), time-boxed to the project window", "required_mention": ["new sas", "read", "expiry", "least"], "weight": 0.3},
            {"id": 4, "step": "Verify the partner can download; note the expiry date in the ticket for next time", "required_mention": ["verify", "download", "note", "date"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The SAS creation with scope and expiry visible", "validation": {}},
            {"type": "screenshot", "description": "Partner-side (or simulated external) successful download", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = SAS-expiry pattern recognized from the URL shape and timeline; nothing chased as 'broken'",
            "2 = token expiry named precisely as the cause",
            "2 = replacement SAS is read-only and time-boxed; handing out account keys or a never-expiring token = 0-1",
            "2 = partner download verified; expiry date recorded so it's a calendar item, not a surprise",
            "2 = partner and {{TEAM}} given a plain explanation that expiry is a security feature",
        ),
        "model_answer": (
            "The URL's long token is a SAS signature; 'worked for a month then died with an auth error' is "
            "the expiry signature — by design, not a fault. Files verified intact. Generate a new SAS: "
            "read-only, scoped to the project container, expiring at the project end date (least "
            "privilege, time-boxed). Verify the partner can download. Record the new expiry in the ticket "
            "and suggest a calendar reminder — and explain kindly that the expiry is a security feature, "
            "not a glitch."
        ),
        "hints": [
            "Look at the SHAPE of that link — what's the long token after the '?', and what property do those tokens have?",
            "'Worked all month, then an authentication error, nothing changed' — what runs out on a schedule?",
            "The SAS token expired, exactly as designed. The files are fine.",
            "Issue a new read-only, time-boxed SAS for the project container, verify the partner's download, and log the expiry date. Don't 'fix' it with account keys or a token that never expires.",
        ],
        "parameters": {"placeholders": {"TEAM": ["Marketing", "Engineering", "Legal", "Design", "Finance"]}},
    },
]


def seed_phase_f(db) -> dict:
    """Idempotent Phase F seed — modules, lessons, quizzes, cloud tickets."""
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
    from app.models.ticket import Ticket

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0, "tickets": 0}
    prev_module = db.query(Module).filter(Module.code == "MOD-020").first()
    for spec in MODULES_F:
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

    for qspec in QUIZZES_F:
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
            db.query(Question).filter(Question.quiz_id == quiz.id).delete()
        for q in qspec["questions"]:
            db.add(Question(quiz_id=quiz.id, **q))
            counts["questions"] += 1
        db.flush()

    for tspec in TICKETS_F:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()
    return counts
