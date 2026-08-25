"""Phase 4C.3 integrated support final shift.

Converts the two existing required Week 23/24 guided_lab activities
(LabTemplate 21 and 22) into a small incident-queue exercise: a student picks
what to work first from three simultaneous support issues, investigates each
with existing evidence-panel patterns, chooses a safe action, gets a
server-verified after-state, documents the outcome, and files a final
handoff. Week 23 is a moderately-guided rehearsal (role troubleshoot,
non-gating). Week 24 is the minimally-guided assessed version (role prove)
and becomes an exact graduation requirement via a new PromotionGate row.

No new curriculum identities are created and no schema changes are made.
Case content lives in LabTemplate.success_criteria["final_shift"]; grading
reads it in final_shift_grading.py and per-run progress is tracked in
LabRun.structured_feedback (see app/routers/final_shift.py).
"""

from copy import deepcopy

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.lab import LabTemplate
from app.models.progression import PromotionGate, Role
from app.models.training import TrainingWeek, TrainingWeekActivity

FINAL_SHIFT_GRADED_LAB_ID = 22
FINAL_SHIFT_GATE_ROLE_NAME = "Junior Infrastructure Administrator"
FINAL_SHIFT_MIN_SCORE_PCT = 80


def _field(label: str, value: str) -> dict:
    return {"label": label, "value": value}


def _panel(panel_id: str, label: str, *fields: tuple[str, str]) -> dict:
    return {"id": panel_id, "label": label, "fields": [_field(*field) for field in fields]}


def _action(action_id: str, label: str, *, safe: bool) -> dict:
    return {"id": action_id, "label": label, "safe": safe}


def _incident(
    key: str,
    *,
    requester: str,
    reported_at: str,
    complaint: str,
    impact_clue: str,
    skill_area: str,
    expected_priority_rank: int,
    priority_reason: str,
    panels: list[dict],
    required_inspections: list[str],
    diagnosis_options: tuple[tuple[str, str], ...],
    correct_diagnosis: str,
    diagnosis_explanation: str,
    actions: list[dict],
    correct_action_id: str,
    action_explanation: str,
    verification_label: str,
    verification_fields: list[tuple[str, str]],
    requires_user_update: bool,
    requires_escalation: bool,
) -> dict:
    return {
        "key": key,
        "requester": requester,
        "reported_at": reported_at,
        "complaint": complaint,
        "impact_clue": impact_clue,
        "skill_area": skill_area,
        "expected_priority_rank": expected_priority_rank,
        "priority_reason": priority_reason,
        "panels": panels,
        "required_inspections": required_inspections,
        "diagnosis": {
            "id": "diagnosis",
            "options": [{"id": option_id, "label": label} for option_id, label in diagnosis_options],
            "correct": correct_diagnosis,
            "explanation": diagnosis_explanation,
        },
        "actions": actions,
        "correct_action_id": correct_action_id,
        "action_explanation": action_explanation,
        "verification": {
            "label": verification_label,
            "fields": [_field(*field) for field in verification_fields],
        },
        "requires_user_update": requires_user_update,
        "requires_escalation": requires_escalation,
    }


# ---------------------------------------------------------------------------
# Week 24 — Final Support Shift (LabTemplate 22, role=prove, minimal guidance)
# ---------------------------------------------------------------------------

WEEK_24_INCIDENTS = [
    _incident(
        "incident_a",
        requester="Priya Shah — Finance",
        reported_at="08:12",
        complaint="I can sign into my laptop fine, but I can't open the shared Finance Reports folder anymore. It worked yesterday.",
        impact_clue="Single user affected. She has a read-only copy from yesterday, but today is monthly close.",
        skill_area="windows_identity",
        expected_priority_rank=2,
        priority_reason="Single user with a partial workaround, but a same-day deadline.",
        panels=[
            _panel("account", "Account state", ("Account", "priya.shah — enabled, not locked"), ("Last sign-in", "Today, 08:05, successful"), ("Password", "Not expired")),
            _panel("access", "Resource access requirement", ("Resource", "\\\\fs01\\FinanceReports"), ("Required group", "Finance-Reports-RW"), ("Priya's current groups", "Finance-Read, AllStaff")),
            _panel("change", "Change record", ("Yesterday 17:40", "HR ran a group-cleanup script during the Finance/Sales re-org"), ("Effect", "Script over-removed several users from Finance-Reports-RW, including Priya"), ("Approval", "Cleanup was approved; the over-removal was not")),
        ],
        required_inspections=["account", "access", "change"],
        diagnosis_options=(
            ("password", "Her password expired and needs a reset"),
            ("moved", "The Finance Reports folder was moved"),
            ("group", "Yesterday's group-cleanup script removed her from the required Finance-Reports-RW group"),
            ("locked", "Her account is locked"),
        ),
        correct_diagnosis="group",
        diagnosis_explanation="The account is healthy and the folder path is unchanged; the change record shows the cleanup script removed her from the required group.",
        actions=[
            _action("readd", "Request the approved re-add of Priya to Finance-Reports-RW, have her sign out and back in, then verify access", safe=True),
            _action("domain_admin", "Add Priya as a Domain Admin so nothing can block her again", safe=False),
            _action("everyone", "Grant Everyone Full Control on the Finance Reports folder to unblock her immediately", safe=False),
            _action("disable_group", "Disable the Finance-Reports-RW group entirely", safe=False),
        ],
        correct_action_id="readd",
        action_explanation="Restoring the specific membership the cleanup script incorrectly removed fixes the exact cause without granting anything new.",
        verification_label="Access restored",
        verification_fields=[
            ("Priya's groups", "Finance-Read, AllStaff, Finance-Reports-RW"),
            ("Fresh sign-in", "\\\\fs01\\FinanceReports opens read-write"),
            ("Other grants", "None added"),
        ],
        requires_user_update=True,
        requires_escalation=False,
    ),
    _incident(
        "incident_b",
        requester="Marcus Webb — Sales",
        reported_at="08:20",
        complaint="Outlook and Teams stopped getting new messages on my laptop this morning. My phone is fine. I have a client call in 30 minutes.",
        impact_clue="Single user affected, has a phone as a workaround, but is time-pressured.",
        skill_area="m365_endpoint",
        expected_priority_rank=3,
        priority_reason="Single user with a working full alternative (phone), less urgent than a deadline or a broad outage.",
        panels=[
            _panel("identity", "Sign-in activity", ("Phone", "Signed in successfully this morning"), ("Laptop", "Repeated token-refresh failures since 07:50"), ("Password", "Not expired; not locked")),
            _panel("device", "Endpoint compliance", ("Device", "Marcus-Laptop-14"), ("Compliance state", "Noncompliant as of 07:48"), ("Reason", "Disk encryption check failed after this morning's update")),
            _panel("policy", "Conditional access", ("Policy", "Block Exchange/Teams from noncompliant devices"), ("Browser OWA", "Not blocked by this policy"), ("Scope", "Applies company-wide")),
        ],
        required_inspections=["identity", "device", "policy"],
        diagnosis_options=(
            ("account", "His account was locked"),
            ("license", "His mailbox license was removed"),
            ("dns", "A DNS problem is blocking his laptop"),
            ("compliance", "The laptop fell out of compliance, so conditional access is blocking Outlook and Teams"),
        ),
        correct_diagnosis="compliance",
        diagnosis_explanation="Sign-in works from the phone and the account is healthy; only the noncompliant laptop is blocked by the conditional access policy.",
        actions=[
            _action("fix_compliance", "Have him re-check disk encryption to clear compliance, use OWA in a browser for the call meanwhile, and verify Outlook/Teams resume once compliant", safe=True),
            _action("exempt", "Add a permanent conditional-access exemption for his laptop", safe=False),
            _action("disable_policy", "Disable the conditional access policy company-wide so this can't happen again", safe=False),
            _action("reset_license", "Remove and reassign his whole M365 license to force a resync", safe=False),
        ],
        correct_action_id="fix_compliance",
        action_explanation="Fixing the actual compliance failure (and using the safe browser workaround for the call) resolves the cause without weakening a company-wide control.",
        verification_label="Sync restored",
        verification_fields=[
            ("Device compliance", "Compliant"),
            ("Outlook/Teams", "Syncing on the laptop"),
            ("Interim workaround", "OWA use during the call recorded"),
        ],
        requires_user_update=True,
        requires_escalation=False,
    ),
    _incident(
        "incident_c",
        requester="Branch monitoring alert — Riverside Branch",
        reported_at="07:55",
        complaint="The branch time-clock kiosk app shows 'connection refused' for all staff since early this morning. No one can clock in.",
        impact_clue="Affects the whole branch (12 staff) and today's payroll process.",
        skill_area="network_server_linux",
        expected_priority_rank=1,
        priority_reason="Broad outage tied to a business process (payroll), not a single user.",
        panels=[
            _panel("client", "Kiosk client evidence", ("Kiosk PCs", "Valid IP, gateway, DNS"), ("Ping to app server", "Successful from every kiosk"), ("Conclusion so far", "Client networking path is healthy")),
            _panel("server", "Application server (lnx-kiosk-01)", ("Service", "kiosk-api"), ("Status", "inactive (dead), crash-looping"), ("Access", "Monitoring/read-only evidence only — no technician shell access to this production host")),
            _panel("logs", "Monitoring log excerpt", ("06:00", "Scheduled OS security patch applied host-wide, host rebooted"), ("06:02", "kiosk-api failed to start: permission denied reading /etc/kiosk-api/config.yml"), ("Cause note", "The patch's file-ownership fix changed that config file's owner")),
        ],
        required_inspections=["client", "server", "logs"],
        diagnosis_options=(
            ("dns", "Company-wide DNS is down"),
            ("internet", "The branch internet connection is down"),
            ("kiosk_config", "Every kiosk PC is misconfigured"),
            ("config_perms", "This morning's OS patch changed ownership on kiosk-api's config file, so the service can't start"),
        ),
        correct_diagnosis="config_perms",
        diagnosis_explanation="Kiosks reach the server fine over the network; the server-side log shows the service crash-looping on a permissions error introduced by the patch.",
        actions=[
            _action("escalate", "Escalate to Server Operations with the service status, the exact error, and the config path — restarting/repairing this production host is outside technician scope", safe=True),
            _action("remote_chmod", "Remote into the production server and chmod 777 the config file to force it to start", safe=False),
            _action("hard_reboot", "Reboot the physical server again with no further evidence", safe=False),
            _action("phones", "Tell branch staff to permanently clock in from personal phones instead", safe=False),
        ],
        correct_action_id="escalate",
        action_explanation="Repairing file ownership on a production Linux host is outside a junior technician's authorized scope; the safe move is a well-evidenced escalation.",
        verification_label="Escalation accepted",
        verification_fields=[
            ("Server Operations", "Accepted the escalation with the evidence provided"),
            ("kiosk-api", "Restored to active (running) by the owning team"),
            ("Branch confirmation", "Kiosk clock-in works again"),
        ],
        requires_user_update=False,
        requires_escalation=True,
    ),
]

WEEK_24_CASE: dict = {
    "lab_id": FINAL_SHIFT_GRADED_LAB_ID,
    "role": "prove",
    "lab_type": "structured_final_shift",
    "difficulty": 3,
    "estimated_minutes": 45,
    "title": "Final Support Shift",
    "description": "Triage three simultaneous support issues, investigate each with real evidence, act safely, verify the outcome, communicate appropriately, and hand off the shift.",
    "setup_instructions": "You are starting a support shift with three open issues. Decide what to work first, investigate before you conclude anything, choose a safe action, get it verified, document the result, and file a final handoff. No exact command list or sequence is provided.",
    "final_shift": {
        "guidance_level": "minimal",
        "queue_intro": "Three issues are waiting. Nothing here tells you which to work first — decide from what you know at a glance.",
        "incidents": deepcopy(WEEK_24_INCIDENTS),
        "handoff_fields": ["resolved", "escalated", "watch_items"],
    },
}


# ---------------------------------------------------------------------------
# Week 23 — guided rehearsal (LabTemplate 21, role=troubleshoot, moderate
# guidance). Related skill families, different specifics, so the rehearsal
# cannot hand the student the Week 24 answers.
# ---------------------------------------------------------------------------

WEEK_23_INCIDENTS = [
    _incident(
        "incident_a2",
        requester="Devon Ortiz — Reception",
        reported_at="09:05",
        complaint="I reset my password this morning like IT asked, and now I can't print to the front-desk printer anymore.",
        impact_clue="Single user; the reset itself worked fine, the printer is the only broken piece.",
        skill_area="windows_identity",
        expected_priority_rank=2,
        priority_reason="Single user, low business risk, but blocks a daily task.",
        panels=[
            _panel("account", "Account state", ("Account", "devon.ortiz — enabled, password reset succeeded 08:58"), ("Sign-in", "Working normally")),
            _panel("printer", "Mapped printer", ("Printer", "\\\\print01\\Frontdesk"), ("Connection type", "Mapped using saved credentials"), ("Saved credentials", "Still hold the OLD password")),
        ],
        required_inspections=["account", "printer"],
        diagnosis_options=(
            ("locked", "Her account is locked"),
            ("stale_creds", "The mapped printer connection is still using her old saved credentials"),
            ("driver", "The printer driver is missing"),
            ("offline", "The printer itself is offline"),
        ),
        correct_diagnosis="stale_creds",
        diagnosis_explanation="The account and sign-in are fine; the printer mapping still holds the password from before the reset.",
        actions=[
            _action("remap", "Have her remove and re-add the printer connection so it re-prompts for the current password", safe=True),
            _action("admin_creds", "Save your own admin credentials into her printer mapping so it always works", safe=False),
            _action("disable_auth", "Turn off authentication on the print share for everyone", safe=False),
        ],
        correct_action_id="remap",
        action_explanation="Refreshing the saved credential on her own mapping fixes the exact stale-password cause without touching shared print security.",
        verification_label="Printing restored",
        verification_fields=[("Printer mapping", "Re-authenticated with current password"), ("Test print", "Succeeds")],
        requires_user_update=True,
        requires_escalation=False,
    ),
    _incident(
        "incident_b2",
        requester="Alicia Reyes — Marketing",
        reported_at="09:10",
        complaint="My OneDrive files stopped syncing this morning. I still have everything from yesterday, just nothing new.",
        impact_clue="Single user, has yesterday's files locally as a partial workaround.",
        skill_area="m365_endpoint",
        expected_priority_rank=3,
        priority_reason="Single user with a partial local workaround; lowest immediate pressure of the three.",
        panels=[
            _panel("device", "Endpoint compliance", ("Device", "Alicia-Laptop-08"), ("Compliance state", "Noncompliant since 08:40"), ("Reason", "Antivirus definitions out of date")),
            _panel("sync", "OneDrive client", ("Status", "Paused"), ("Last successful sync", "Yesterday 17:20")),
        ],
        required_inspections=["device", "sync"],
        diagnosis_options=(
            ("quota", "Her OneDrive storage quota is full"),
            ("compliance", "The device fell out of compliance (stale antivirus definitions), pausing managed sync"),
            ("license", "Her license was removed"),
            ("network", "Her laptop has no internet connection"),
        ),
        correct_diagnosis="compliance",
        diagnosis_explanation="Sync paused exactly when the device went noncompliant for an antivirus reason unrelated to storage or licensing.",
        actions=[
            _action("update_av", "Have her update antivirus definitions to clear compliance, then confirm sync resumes", safe=True),
            _action("exempt_device", "Exempt her device from compliance checks permanently", safe=False),
            _action("reinstall_everything", "Wipe and reinstall OneDrive and Windows to be thorough", safe=False),
        ],
        correct_action_id="update_av",
        action_explanation="Fixing the actual compliance gap is the narrow, safe correction; a permanent exemption or a full reinstall is unnecessary and riskier.",
        verification_label="Sync resumed",
        verification_fields=[("Device compliance", "Compliant"), ("OneDrive", "Syncing; today's files present")],
        requires_user_update=True,
        requires_escalation=False,
    ),
    _incident(
        "incident_c2",
        requester="Break-room monitoring alert",
        reported_at="08:50",
        complaint="The break-room printer keeps dropping off the network and a laptop nearby also lost its connection this morning.",
        impact_clue="A small shared area, not a single user, but not the whole office either.",
        skill_area="network_server_linux",
        expected_priority_rank=1,
        priority_reason="Shared-area outage affecting more than one person, so it goes first even though it's small.",
        panels=[
            _panel("leases", "DHCP lease evidence", ("Printer's usual address", "10.20.4.55, leased to the printer's MAC"), ("Conflict", "A visiting laptop was also assigned 10.20.4.55 this morning by a rogue access point in the break room")),
            _panel("scope", "Network scope", ("Only affected", "Devices near the break-room rogue AP"), ("Rest of office", "Unaffected")),
        ],
        required_inspections=["leases", "scope"],
        diagnosis_options=(
            ("server_down", "The whole company DHCP server is down"),
            ("ip_conflict", "A rogue access point handed out a duplicate IP that conflicts with the printer's address"),
            ("cable", "The printer's network cable is unplugged"),
            ("firmware", "The printer needs a firmware update"),
        ),
        correct_diagnosis="ip_conflict",
        diagnosis_explanation="Only the break-room area is affected and the evidence shows a duplicate-address conflict from an unauthorized access point, not a company-wide DHCP failure.",
        actions=[
            _action("escalate_rogue", "Escalate to Network Operations to locate and remove the rogue access point — that authority is outside technician scope", safe=True),
            _action("static_ip", "Manually assign a permanent static IP outside the DHCP scope to work around it", safe=False),
            _action("disable_wifi", "Disable Wi-Fi for the entire building until it's found", safe=False),
        ],
        correct_action_id="escalate_rogue",
        action_explanation="Locating and removing unauthorized network hardware is outside a junior technician's scope; a well-evidenced escalation is the safe response — this is the same escalation pattern Week 24 will expect you to use independently.",
        verification_label="Escalation accepted",
        verification_fields=[("Network Operations", "Accepted the escalation with the lease evidence"), ("Rogue AP", "Removed"), ("Printer and laptop", "Reconnect normally")],
        requires_user_update=False,
        requires_escalation=True,
    ),
]

WEEK_23_CASE: dict = {
    "lab_id": 21,
    "role": "troubleshoot",
    "lab_type": "structured_final_shift",
    "difficulty": 2,
    "estimated_minutes": 35,
    "title": "Work the Mixed Support Queue",
    "description": "Rehearse working a small queue of simultaneous issues: choose what matters first, investigate, act safely, verify, document, and hand off — the same mechanics Week 24 will assess independently.",
    "setup_instructions": "Three issues are open at once. This rehearsal explains how to read the queue, pick an issue, gather evidence, and return to the queue — but you still have to reason through each case yourself.",
    "final_shift": {
        "guidance_level": "guided",
        "queue_intro": "Here is how a shift starts: several issues are open at once and nothing is pre-sorted for you. Glance at who is affected and how urgent it looks, then choose one to open.",
        "incidents": deepcopy(WEEK_23_INCIDENTS),
        "handoff_fields": ["resolved", "escalated", "watch_items"],
        "guidance_notes": [
            "Open an issue from the queue to see its full complaint and evidence.",
            "Inspect every evidence panel before you commit to a diagnosis — guessing early is how real technicians make it worse.",
            "Choose the action you could defend in a ticket. If it isn't yours to fix, the safe action is a clear escalation.",
            "Verification only appears after your plan is accepted — an unsafe or wrong plan never shows a fake success.",
            "Return to the queue after each issue; nothing is graded until the final handoff.",
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


def _lab_values(case: dict, week_number: int) -> dict:
    return {
        "title": case["title"],
        "description": case["description"],
        "lab_type": case["lab_type"],
        "week_number": week_number,
        "difficulty": case["difficulty"],
        "estimated_minutes": case["estimated_minutes"],
        "is_published": True,
        "environment_requirements": {},
        "setup_instructions": case["setup_instructions"],
        "success_criteria": {"final_shift": deepcopy(case["final_shift"])},
        "required_evidence": {},
        "hints": {},
    }


def _ensure_final_shift_gate(db: Session) -> bool:
    final_role = db.query(Role).filter_by(name=FINAL_SHIFT_GATE_ROLE_NAME).first()
    if final_role is None:
        return False
    existing = (
        db.query(PromotionGate)
        .filter_by(role_id=final_role.id, requirement_type="required_lab_pass")
        .first()
    )
    if existing is not None:
        return False
    db.add(
        PromotionGate(
            role_id=final_role.id,
            requirement_type="required_lab_pass",
            requirement_config={"lab_id": FINAL_SHIFT_GRADED_LAB_ID, "min_score_pct": FINAL_SHIFT_MIN_SCORE_PCT},
        )
    )
    return True


def _remove_final_shift_gate(db: Session) -> bool:
    final_role = db.query(Role).filter_by(name=FINAL_SHIFT_GATE_ROLE_NAME).first()
    if final_role is None:
        return False
    existing = (
        db.query(PromotionGate)
        .filter_by(role_id=final_role.id, requirement_type="required_lab_pass")
        .first()
    )
    if existing is None:
        return False
    db.delete(existing)
    return True


def sync_integrated_support_final_shift_upgrade(db: Session) -> dict:
    """Convert Week 23/24 in place and add the Gate 5 graduation requirement."""
    if not inspect(db.get_bind()).has_table(TrainingWeekActivity.__tablename__):
        return {"updated_templates": 0, "updated_activities": 0, "gate_added": False, "skipped": True, "reason": "migration_not_applied"}

    targets = {
        23: (*_target_rows(db, 23, 21), WEEK_23_CASE),
        24: (*_target_rows(db, 24, FINAL_SHIFT_GRADED_LAB_ID), WEEK_24_CASE),
    }
    missing_targets = [
        {"week_number": week_number, "lab_id": case["lab_id"]}
        for week_number, (lab, activity, case) in targets.items()
        if lab is None or activity is None
    ]
    if missing_targets:
        if len(missing_targets) == len(targets):
            return {"updated_templates": 0, "updated_activities": 0, "gate_added": False, "skipped": True, "reason": "curriculum_not_seeded"}
        raise RuntimeError(f"Phase 4C.3 target set is incomplete; refusing a partial upgrade: {missing_targets}")

    result = {"updated_templates": 0, "updated_activities": 0, "gate_added": False, "skipped": False}
    for week_number, (lab, activity, case) in targets.items():
        values = _lab_values(case, week_number)
        if any(getattr(lab, field) != value for field, value in values.items()):
            for field, value in values.items():
                setattr(lab, field, value)
            result["updated_templates"] += 1

        metadata = dict(activity.metadata_json or {})
        if case["role"] == "practice":
            metadata.pop("learning_role", None)
        else:
            metadata["learning_role"] = case["role"]
        if activity.metadata_json != metadata or activity.estimated_minutes != case["estimated_minutes"]:
            activity.metadata_json = metadata
            activity.estimated_minutes = case["estimated_minutes"]
            result["updated_activities"] += 1

    result["gate_added"] = _ensure_final_shift_gate(db)
    db.commit()
    return result


def restore_pre_4c3_final_shift(db: Session) -> dict:
    """Restore the exact pre-Phase-4C.3 Week 23/24 lab content and remove the added gate."""
    from app.services.training_curriculum_seed import WEEKS_23_24_QUALITY

    targets = {
        23: (*_target_rows(db, 23, 21), None),
        24: (*_target_rows(db, 24, FINAL_SHIFT_GRADED_LAB_ID), None),
    }
    missing_targets = [
        {"week_number": week_number, "lab_id": lab_id}
        for week_number, lab_id in ((23, 21), (24, FINAL_SHIFT_GRADED_LAB_ID))
        for lab, activity, _ in [targets[week_number]]
        if lab is None or activity is None
    ]
    if missing_targets:
        if len(missing_targets) == len(targets):
            return {"restored": 0, "gate_removed": False, "skipped": True, "reason": "curriculum_not_seeded"}
        raise RuntimeError(f"Phase 4C.3 target set is incomplete; refusing a partial downgrade: {missing_targets}")

    legacy_specs = {
        23: deepcopy(WEEKS_23_24_QUALITY[23]["lab"]),
        24: deepcopy(WEEKS_23_24_QUALITY[24]["lab"]),
    }
    restored = 0
    for week_number, (lab, activity, _case) in targets.items():
        legacy = legacy_specs[week_number]
        values = {
            "title": legacy.get("new_title", legacy["title"]),
            "description": legacy.get(
                "description",
                "Work through realistic evidence and choose the safest support action before moving to an independent case.",
            ),
            "lab_type": legacy["lab_type"],
            "week_number": week_number,
            "difficulty": 1,
            "estimated_minutes": legacy.get("estimated_minutes", 20),
            "is_published": True,
            "environment_requirements": {},
            "setup_instructions": legacy.get(
                "setup_instructions",
                "Read each symptom and evidence block. Choose the action you could defend in a support ticket.",
            ),
            "success_criteria": {
                "questions": deepcopy(legacy["questions"]),
                **({"required_commands": deepcopy(legacy["required_commands"])} if legacy.get("required_commands") else {}),
                **({"terminal_profile": legacy["terminal_profile"]} if legacy.get("terminal_profile") else {}),
            },
            "required_evidence": {},
            "hints": {},
        }
        for field, value in values.items():
            setattr(lab, field, value)
        metadata = dict(activity.metadata_json or {})
        metadata.pop("learning_role", None)
        activity.metadata_json = metadata
        activity.estimated_minutes = values["estimated_minutes"]
        restored += 1

    gate_removed = _remove_final_shift_gate(db)
    db.commit()
    return {"restored": restored, "gate_removed": gate_removed}
