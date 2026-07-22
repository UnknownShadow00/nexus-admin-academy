"""Phase G (Weeks 23-24) — Integrated Operations, Simulation 3, and the
"Take Over Maple & Finch Co." graduation capstone (Gate 5).

Blueprint: NEXUS_CURRICULUM_MASTER.md §F. The capstone reuses the existing
CapstoneTemplate model (matched by title, idempotent). The mixed-incident
queue and Simulation 3 are the Gate 5 practical checkpoints; Linux (Phase E)
and cloud (Phase F) competence are assessed here via the mixed tickets.

Infrastructure honesty: the capstone's full-environment version targets the
manual-VM path (mentor-cloned DC + client + Ubuntu box over Headscale) — the
same footprint as the Phase D/E labs, nothing new to build. The paper+platform
version (tickets, interviews, documented runbooks against the simulated
environment) is fully sufficient for Gate 5 if VMs are unavailable that week.
"""

from seed_phase_a import ANCHORS, NOTES_TEMPLATE, _q

MODULES_G = [
    {
        "code": "MOD-023",
        "title": "Integrated Operations",
        "description": "Mixed-incident queues across Windows/Linux/network/cloud, incident communication, Simulation 3. Week 23.",
        "target_role": "Junior Infrastructure Administrator",
        "difficulty_band": 5,
        "estimated_hours": 16,
        "module_order": 24,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Working a Mixed Queue",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Real infrastructure jobs don't sort tickets by technology. A Tuesday queue holds an "
                    "Entra lockout, a Linux disk alert, a VLAN problem, and a GPO question at once. What "
                    "changes when the queue is MIXED:\n\n"
                    "CLASSIFY BY LAYER AND OWNER FIRST: for each ticket, name (a) the technology domain, "
                    "(b) the layer the symptom points at, and (c) who owns the fix (you, network team, "
                    "security, the cloud provider — the IaaS/PaaS/SaaS lines from Week 21). Three tags per "
                    "ticket, thirty seconds each — the triage pass from Week 8, matured.\n\n"
                    "YOUR METHOD IS PORTABLE — trust it: 'local works, remote fails' means gateway/"
                    "routing whether it's a Windows PC (Week 8), a Linux box (Week 19), or an Azure VM's "
                    "NSG (Week 22). 'Service down' starts at status+logs whether it's services.msc, "
                    "systemctl, or a portal resource-health blade. The transfer IS the skill this week "
                    "grades.\n\n"
                    "CONTEXT-SWITCHING DISCIPLINE: mixed queues punish half-finished work. Finish a "
                    "verifiable unit (or write the handoff note) before switching; keep per-ticket notes "
                    "AS YOU GO, not from memory at 5 PM. The communication debt rule (Week 8) still holds: "
                    "every waiting ticket owes its user a status.\n\n"
                    "KNOW YOUR ESCALATION MAP: by now you know precisely what a junior fixes vs packages — "
                    "sensitive access (Weeks 6/13), security incidents (Weeks 4/7), routing/change-window "
                    "work (Week 12), DC restores (Week 17), risky Entra changes (Week 21). Escalating "
                    "correctly and fast is senior behavior, not weakness.\n\n"
                    "COMMON MISTAKES: deep-diving ticket #1 while five wait; re-learning a method you "
                    "already own because the OS changed; notes written at end-of-day from memory; solo "
                    "heroics on something the escalation map routes elsewhere."
                ),
                "outcomes": [
                    "Triage a mixed queue with domain/layer/owner tags and a defensible order",
                    "Transfer the layered troubleshooting method across Windows, Linux, network, and cloud tickets",
                    "Apply context-switching discipline: verifiable units, live notes, communication debt paid",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Incident Communication and the Post-Incident Note",
                "lesson_order": 2,
                "estimated_minutes": 75,
                "summary": (
                    "When something big breaks, the communication IS half the job. The skills Simulation 3 "
                    "and the capstone grade:\n\n"
                    "DURING an incident:\n"
                    "- The first status goes out EARLY, before you fully understand it: what's affected, "
                    "that it's being worked, when the next update comes. Silence breeds duplicate tickets "
                    "and panic.\n"
                    "- Updates on the promised cadence even when the update is 'still investigating' "
                    "(Week 4's lesson at incident scale).\n"
                    "- One writer: in a team incident, one person owns comms so users get one consistent "
                    "story.\n\n"
                    "SEVERITY HONESTY: don't inflate (crying wolf burns trust) or deflate (surprising "
                    "leadership burns more). '40 users cannot access the file server since 09:15; "
                    "workaround: none; ETA: investigating' is complete and honest.\n\n"
                    "THE POST-INCIDENT NOTE (mini-RCA — the graduation-level writing skill): after "
                    "resolution, a short blameless write-up: TIMELINE (first symptom → detection → "
                    "diagnosis → fix → verification, with times), ROOT CAUSE (the actual one, not the "
                    "symptom), IMPACT (who/what/how long), WHAT FIXED IT, and PREVENTION (the rebuild-"
                    "checklist/log-rotation/reservation class of fix — you've written these all program). "
                    "Blameless means systems and process, not people: 'the rebuild checklist lacked a "
                    "firewall step', never 'Dave forgot'.\n\n"
                    "COMMON MISTAKES: going silent while heads-down; first update sent only after the fix; "
                    "RCAs that name a person instead of a process gap; prevention sections that say 'be "
                    "more careful'."
                ),
                "outcomes": [
                    "Send early, honest, cadenced incident updates with impact and next-update times",
                    "Write a blameless post-incident note: timeline, root cause, impact, fix, prevention",
                    "Calibrate severity honestly — neither inflated nor deflated",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-024",
        "title": "The Capstone: Take Over Maple & Finch Co.",
        "description": "The graduation exercise — inherit, stabilize, operate, and hand over a small company's IT. Week 24 — Gate 5.",
        "target_role": "Junior Infrastructure Administrator",
        "difficulty_band": 5,
        "estimated_hours": 20,
        "module_order": 25,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Capstone Briefing: Your First Week at Maple & Finch",
                "lesson_order": 1,
                "estimated_minutes": 60,
                "summary": (
                    "THE SCENARIO: Maple & Finch Co. (a ~60-person furniture design firm) just lost its "
                    "only IT person with two days' notice. You are the incoming junior infrastructure "
                    "administrator. The environment: a Windows domain (one DC: AD, DNS, DHCP), a file "
                    "server, an Ubuntu box running the intranet wiki and nightly jobs, managed switches, "
                    "Microsoft 365 with hybrid identity, and monitoring that 'someone set up once'. "
                    "Documentation: one out-of-date network diagram and a sticky note with two passwords.\n\n"
                    "YOUR FOUR STAGES (each graded, mentor plays every human role):\n"
                    "1. DISCOVER & DOCUMENT: inventory what exists — servers, roles, shares and their "
                    "groups, VLANs, scheduled jobs, monitoring, backup state. Deliverable: a runbook a "
                    "stranger could operate from (the Week 1 ticket-notes principle, environment-sized).\n"
                    "2. STABILIZE: work the audit findings you WILL discover — an unverified backup, a "
                    "port-security landmine, a debug log filling a disk, accounts that should be "
                    "disabled. Fix what's yours; package what isn't (some findings are escalation-"
                    "correct even here).\n"
                    "3. OPERATE: a live mixed week — the mentor feeds tickets, an alert or two, an access "
                    "request with a trap in it, and one MAJOR INCIDENT worked with proper comms and a "
                    "blameless post-incident note.\n"
                    "4. HAND OVER: your successor arrives (the mentor). Walk them through the runbook, "
                    "the open items, and the promises made to users. If they can operate from your "
                    "documentation, you graduate.\n\n"
                    "TWO DELIVERY MODES (both fully valid for Gate 5): FULL-ENVIRONMENT (mentor-cloned "
                    "DC + client + Ubuntu VMs over Headscale — the Phase D/E lab footprint) or "
                    "PLATFORM (the same stages driven through tickets, interviews, and documents against "
                    "the described environment). The grading rubric is identical.\n\n"
                    "WHAT GRADUATION MEANS: passing the capstone plus the standing Gate 5 requirements "
                    "promotes you to Junior Infrastructure Administrator — the program's statement that "
                    "you can walk into a junior sysadmin interview and back every line on your resume."
                ),
                "outcomes": [
                    "Explain the four capstone stages and their deliverables",
                    "Plan a discovery pass over an unknown environment using the whole program's toolkit",
                    "Understand the two delivery modes and that grading is identical in both",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


QUIZZES_G = [
    {
        "title": "Integrated Operations Readiness",
        "week_number": 23, "domain_id": "5.0", "lesson_title": "Working a Mixed Queue",
        "questions": [
            _q("A mixed queue's triage pass tags each ticket with:",
               "A random number", "Technology domain, symptom layer, and fix owner",
               "The user's mood", "Font color",
               "B", "Domain/layer/owner classification routes work correctly in thirty seconds per ticket."),
            _q("'Local works, remote fails' on an Azure VM, a Linux server, and a Windows PC points at:",
               "Three unrelated methods", "The same gateway/routing/NSG layer — the method transfers",
               "DNS in all cases", "Reinstalling",
               "B", "The layered method is portable; only the commands change."),
            _q("During a major incident, your FIRST user communication goes out:",
               "After the fix, with full details", "Early — affected scope, being worked, next-update time",
               "Never", "Only if asked",
               "B", "Early honest status prevents duplicate tickets and panic; details follow."),
            _q("A blameless post-incident note attributes cause to:",
               "The person who made the mistake", "Process/system gaps (e.g. a checklist missing a step)",
               "Bad luck", "The vendor, always",
               "B", "Blameless RCA fixes systems; naming people teaches hiding."),
            _q("The prevention section of a good RCA says:",
               "'Be more careful next time'", "A concrete systemic fix (rotation rule, checklist step, reservation, alert)",
               "Nothing", "'Users should stop breaking things'",
               "B", "Prevention must be actionable and systemic — the class-of-problem fix."),
            _q("Mid-investigation, your shift ends. Before leaving you: (select all that apply)",
               "Write the handoff: state, ruled-out-with-evidence, next step, promises made",
               "Update the waiting user with status and next-update time",
               "Keep it all in your head for tomorrow", "Mark it resolved to clean the queue",
               "A", "Handoff + communication debt paid; memory and fake-resolves are the anti-patterns.", multi="A,B"),
        ],
    },
]


# Simulation 3 — the Gate 5 practical checkpoint: a mixed Windows/Linux/network/
# cloud queue with a live major incident.
TICKETS_G = [
    {
        "title": "Maple & Finch: the Friday outage (capstone major incident)",
        "description": (
            "CAPSTONE STAGE 3 DELIVERABLE — submit your major-incident work here.\n\n"
            "Friday of your operate-week at Maple & Finch, 10:10 AM: the design team (25 people) reports "
            "the file server unreachable AND the intranet wiki down simultaneously. Your monitoring shows "
            "LNX-WEB healthy but the {{SUBNET}} subnet's checks all failing since 10:05. The mentor (as "
            "the panicking office manager) is calling. Work it as a real major incident: comms first and "
            "throughout, diagnosis with evidence, fix or coordinated escalation, verification with real "
            "users, and a blameless post-incident note. Your submission is the complete incident record."
        ),
        "difficulty": 5, "week_number": 24, "category": "Capstone", "domain_id": "5.0",
        "root_cause": (
            "Mentor-selected per run (the environment defines it): typically the {{SUBNET}} VLAN's gateway "
            "SVI down, or the uplink trunk dropped after a change — the point is the PROCESS: early comms, "
            "layered diagnosis crossing Windows/Linux/network, evidence, verification with users, and a "
            "complete blameless post-incident note. Graded on the incident record, not on guessing the "
            "mentor's break."
        ),
        "root_cause_type": "capstone_major_incident",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "First status to affected users within minutes; cadence promised and kept", "required_mention": ["status", "update", "comms", "minutes"], "weight": 0.25},
            {"id": 2, "step": "Layered diagnosis with evidence (scope: two services, one subnet, monitoring correlation)", "required_mention": ["scope", "subnet", "evidence", "diagnos"], "weight": 0.3},
            {"id": 3, "step": "Fix within scope or coordinated escalation per change control; verification with real users", "required_mention": ["fix", "escalat", "verif", "users"], "weight": 0.25},
            {"id": 4, "step": "Blameless post-incident note: timeline, root cause, impact, fix, systemic prevention", "required_mention": ["post-incident", "timeline", "prevention", "blameless"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "The comms thread (first status + updates + all-clear)", "validation": {}},
            {"type": "screenshot", "description": "Diagnostic evidence trail (commands/portal output)", "validation": {}},
            {"type": "screenshot", "description": "The post-incident note", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = scope established fast (which users, which services, since when) and monitoring correlated before deep-diving",
            "2 = actual root cause found with evidence, crossing domains as needed",
            "2 = fix minimal/verified or escalation coordinated properly; change control respected mid-incident",
            "2 = restoration verified WITH affected users; monitoring confirmed green; note complete",
            "2 = comms early, cadenced, honest; post-incident note blameless with a systemic prevention",
        ),
        "model_answer": (
            "Send the first status immediately ('design team file/wiki access down since ~10:05, "
            "investigating, next update 10:30'). Correlate: LNX-WEB healthy + one subnet's checks all red "
            "= the subnet's path, not the servers. Walk the layers (Week 12/23): gateway SVI state, uplink "
            "trunk, recent changes. Fix within scope or coordinate the network-level change, verify with "
            "design-team users AND monitoring, send the all-clear, then write the blameless post-incident "
            "note with a systemic prevention (checklist/monitoring/alert improvement). The record of HOW "
            "you worked it is the deliverable."
        ),
        "hints": [
            "Comms before diagnosis: what do 25 blocked people need from you in the first five minutes?",
            "Two 'down' services but the server itself is healthy, and exactly one subnet's checks failed together. What does that scope tell you?",
            "The failure is on the subnet's path — gateway/SVI/trunk territory you've owned since Week 11-12. Bring evidence, respect change control.",
            "Status out fast → correlate monitoring → layered path diagnosis (SVI/trunk) → fix or coordinated escalation → verify with users AND monitoring → all-clear → blameless post-incident note with systemic prevention.",
        ],
        "parameters": {"placeholders": {"SUBNET": ["design-floor", "second-floor", "studio", "east-wing", "annex"]}},
    },
    {
        "title": "Multi-Ticket Simulation 3 — the infrastructure shift",
        "description": (
            "Wednesday, 08:55. You're the on-shift infrastructure tech. Submit your TRIAGE (domain/layer/"
            "owner tags + working order + one-line justifications), then work the queue. Communication "
            "debt applies. At some point one of these becomes a MAJOR INCIDENT requiring proper comms and "
            "a post-incident note.\n\n"
            "T1 ({{USER1}}): 'Locked out of Microsoft 365 again — I got a new phone Monday.' (Hybrid "
            "identity org.)\n\n"
            "T2 (Netdata alert, 08:40): LNX-APP root filesystem 91% and climbing ~1%/hour.\n\n"
            "T3 (Facilities, 35 users, 09:05 — ESCALATING): 'The whole floor lost the file server AND "
            "printers ten minutes ago. Internet still works.' The floor's access switch was replaced "
            "last night.\n\n"
            "T4 ({{USER2}}, Finance): 'I need the payroll export from the old system — just add me to "
            "whatever group has it, the deadline is today.' No approval attached.\n\n"
            "T5 (Azure): the reporting VM AZ-RPT01 shows 'Running' but the morning batch job errored "
            "with 'connection refused' to it since last night's 'security tightening'.\n\n"
            "T6 ({{USER3}}): 'My Excel is slow.' (No other details; user is patient.)\n\n"
            "T3 is your major incident. One ticket is a trap. Manage the shift."
        ),
        "difficulty": 5, "week_number": 23, "category": "Simulation", "domain_id": "5.0",
        "root_cause": (
            "T1: Entra MFA re-registration after phone swap (verify identity first). T2: runaway log — "
            "measured, safely truncated, source fixed, alert cleared (proactive: fix BEFORE it's an "
            "outage). T3 MAJOR INCIDENT: replaced switch's uplink not trunking the floor's server/printer "
            "VLAN (internet VLAN unaffected) — Week 11's trunk-mismatch at incident scale, with comms + "
            "post-incident note; escalate/coordinate if change control requires. T4: the trap — payroll "
            "data access without approval = packaged escalation, nothing granted, deadline expedites the "
            "escalation not the grant. T5: NSG tightened to exclude the batch server's source; "
            "least-privilege rule fix. T6: lowest priority; polite hold note, basic triage when time "
            "allows."
        ),
        "root_cause_type": "multi_incident",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Triage first: 6 tickets tagged domain/layer/owner, ordered, justified; T3 recognized as the major incident", "required_mention": ["triage", "order", "major incident", "owner"], "weight": 0.25},
            {"id": 2, "step": "T3 worked as an incident: early user comms, trunk/VLAN diagnosis on the new switch, fix or coordinated escalation, post-incident note (timeline/cause/impact/prevention)", "required_mention": ["trunk", "vlan", "comms", "post-incident", "timeline"], "weight": 0.3},
            {"id": 3, "step": "T4 trap handled: NOTHING granted, packaged escalation with deadline flagged; T1 identity verified before MFA reset", "required_mention": ["escalat", "approval", "verify", "mfa"], "weight": 0.25},
            {"id": 4, "step": "T2 fixed at source before outage; T5 NSG least-privilege fix; T6 hold note; per-ticket notes throughout", "required_mention": ["truncate", "nsg", "hold note", "source"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Triage table with tags, order, justifications", "validation": {}},
            {"type": "screenshot", "description": "T3 incident comms (first status + updates) and the post-incident note", "validation": {}},
            {"type": "screenshot", "description": "Per-ticket resolution notes for the remainder", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = full triage before work; T3's scope (35 users, two services, internet fine) read correctly; T2's slope treated proactively",
            "2 = all six causes right across four domains, incl. the T4 trap and T3's trunk mismatch on the swapped switch",
            "2 = T4 nothing granted + clean escalation; T1 verified before reset; T5 least-privilege NSG (no Any/Any); T3 change-control respected",
            "2 = every worked ticket verified (T3 floor confirmed restored from a user; T2 alert cleared; T5 batch reruns clean); post-incident note complete",
            "2 = incident comms early and cadenced; six distinct user messages; T6's patient user not forgotten",
        ),
        "model_answer": (
            "Triage: T3 major incident (35 users, two services — start comms NOW) → T2 proactive (fix "
            "before it becomes incident #2) → T1 (verify identity, MFA re-register) → T5 (NSG rule) → T4 "
            "(packaged escalation, nothing granted) → T6 (hold note; triage later). T3: first status to "
            "the floor within minutes; new switch + internet-works/servers-don't = a VLAN missing from "
            "the uplink trunk (show interfaces trunk both ends); fix or coordinate per change control; "
            "verify with floor users; blameless post-incident note with a rebuild-checklist prevention. "
            "T2: df/du → runaway log → safe truncate + source fix + rotation; alert clears. T1: sign-in "
            "log → MFA failures post-phone-swap → verify identity → re-register. T5: activity log shows "
            "the tightening; add least-privilege allow for the batch source; rerun verifies. T4: payroll "
            "data + no approval = escalate packaged with the deadline flagged; granting anything fails. "
            "T6: courteous hold note, then standard slow-app triage when the queue allows."
        ),
        "hints": [
            "Six tickets, four domains, one major incident. Tag and order everything before touching anything — which one is burning?",
            "T3: internet works but servers/printers died floor-wide right after a switch swap. You solved this exact pattern in Week 11 — at what link?",
            "T4 is the trap (what data is that, and where's the approval?). T2 is a slope, not yet a fire — what does fixing it BEFORE it's an outage look like?",
            "Order T3 (incident: comms + uplink trunk fix + post-incident note) → T2 (truncate + source + rotation) → T1 (verify, re-register MFA) → T5 (least-privilege NSG) → T4 (escalate, grant nothing) → T6 (hold note). Verification and communication carry half your anchors.",
        ],
        "parameters": {"placeholders": {
            "USER1": ["c.moreno", "j.whitfield", "a.osei", "l.tanaka", "p.novak"],
            "USER2": ["gharris", "bfoster", "mruiz", "cchen", "tadams"],
            "USER3": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
        }},
    },
]


# The graduation capstone (CapstoneTemplate, matched by title).
CAPSTONE_G = {
    "title": "Take Over Maple & Finch Co.",
    "description": (
        "The graduation exercise: inherit a ~60-person company's IT with almost no documentation, then "
        "DISCOVER & DOCUMENT (produce the runbook), STABILIZE (work the audit findings, escalate the "
        "escalation-correct ones), OPERATE (a live mixed week including one major incident with full "
        "comms and a blameless post-incident note), and HAND OVER (your successor operates from your "
        "runbook). Mentor plays all human roles. Delivered full-environment (mentor-cloned DC + client + "
        "Ubuntu over Headscale) or platform-only — identical rubric either way."
    ),
    "week_number": 24,
    "is_published": True,
    "estimated_hours": 20,
    "requirements": {
        "stages": [
            {"id": 1, "name": "Discover & Document", "deliverable": "Environment runbook a stranger could operate from: inventory, roles, shares+groups, VLANs, jobs, monitoring, backup state"},
            {"id": 2, "name": "Stabilize", "deliverable": "Audit-findings log: what was found, fixed-with-verification, or escalated-with-package (some findings are escalation-correct)"},
            {"id": 3, "name": "Operate", "deliverable": "One week of worked mixed tickets + the major incident: comms artifacts and a blameless post-incident note (timeline, root cause, impact, fix, prevention)"},
            {"id": 4, "name": "Hand Over", "deliverable": "Successful successor walkthrough: open items, promises made, runbook navigation — successor (mentor) can operate unaided"},
        ],
        "prerequisites": ["Gate 4 passed", "Multi-Ticket Simulation 3 passed (max 1 hint, score ≥ 7)"],
        "delivery_modes": ["full_environment_manual_vm", "platform_only"],
    },
    "deliverables": {
        "artifacts": [
            "Runbook (markdown/doc)",
            "Findings log with fix/escalation evidence",
            "Incident comms thread + post-incident note",
            "Handover checklist signed by the 'successor'",
        ]
    },
    "rubric": {
        "anchors": {
            "investigation": "2 = discovery is systematic and evidenced; the runbook reflects what IS, not guesses",
            "root_cause": "2 = audit findings and the major incident traced to real causes",
            "safe_fix_or_escalation": "2 = fixes are minimal and verified; sensitive/out-of-scope findings escalated packaged — including during the incident",
            "verification": "2 = every fix proven; backup RESTORED not just observed; successor operates from the runbook unaided",
            "communication": "2 = incident comms early/cadenced/honest; post-incident note blameless with systemic prevention; handover complete",
        },
        "pass_rule": "Sum ≥ 8 of 10, no anchor at 0, all four stages delivered",
    },
}


def seed_phase_g(db) -> dict:
    """Idempotent Phase G seed — modules, lessons, quiz, Simulation 3, capstone, Gate 5 support."""
    from app.models.capstone import CapstoneTemplate
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
    from app.models.progression import Role
    from app.models.ticket import Ticket

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0, "tickets": 0, "capstones": 0}
    prev_module = db.query(Module).filter(Module.code == "MOD-022").first()
    for spec in MODULES_G:
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

    for qspec in QUIZZES_G:
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

    for tspec in TICKETS_G:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()

    capstone_role = (
        db.query(Role)
        .filter(Role.name == "Junior Systems Technician", Role.rank_order == 5)
        .one()
    )
    capstone_fields = {**CAPSTONE_G, "role_level": capstone_role.id}
    cap = db.query(CapstoneTemplate).filter(CapstoneTemplate.title == CAPSTONE_G["title"]).first()
    if cap is None:
        db.add(CapstoneTemplate(**capstone_fields))
        counts["capstones"] += 1
    else:
        for k, v in capstone_fields.items():
            setattr(cap, k, v)
    db.flush()
    return counts
