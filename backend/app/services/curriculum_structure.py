"""Authoritative student-facing Stage -> Module curriculum metadata.

TrainingWeek remains the transitional storage and sequencing container.  This
module is the single presentation mapping from those containers to durable,
student-facing concepts.  Student progress remains attached to the underlying
activity/content identities, never to a stage/module label or array position.

IMPORTANT: Stage.display_order and Module.display_order only control how the
Learning Path groups and labels content (see training_service._build_stage_path).
They do NOT control the actual unlock/progression sequence a student
experiences week to week -- that sequence is driven independently by
TrainingWeek.display_order in the database (see training_service._active_weeks
and _build_state). Today, the two happen to be kept in lockstep (module
source_week_number order matches Stage/Module display_order), but relabeling
or regrouping Stage/Module metadata here does not move a module earlier or
later in the student's actual required path. Physically resequencing content
requires an authorized TrainingWeek.display_order data change, not just an
edit to this file. See docs/JOB_READY_CURRICULUM_BLUEPRINT.md for the
distinction between structural (safe, code-only) and sequence (data,
authorization-gated) reordering.
"""

from dataclasses import asdict, dataclass
import re


LEARNING_ROLES = {"learn", "check", "practice", "troubleshoot", "prove"}
DEFAULT_LEARNING_ROLE = {
    "lesson": "learn",
    "video": "learn",
    "quiz": "check",
    "review": "check",
    "guided_lab": "practice",
    "networking_lab": "practice",
    "command_exercise": "practice",
    "terminal_exercise": "practice",
    "support_ticket": "troubleshoot",
    "service_desk_scenario": "troubleshoot",
    "capstone": "prove",
}
_STABLE_ID_RE = re.compile(r"^(stage|module)\.[a-z0-9_]+(?:\.[a-z0-9_]+)*$")


@dataclass(frozen=True)
class StageDefinition:
    stable_id: str
    title: str
    description: str
    display_order: int


@dataclass(frozen=True)
class ModuleDefinition:
    stable_id: str
    stage_id: str
    title: str
    purpose: str
    display_order: int
    source_week_number: int


STAGES = (
    StageDefinition("stage.orientation", "Technician Orientation", "Learn how Nexus works and how support work is completed safely.", 0),
    StageDefinition("stage.endpoint_foundations", "Endpoint Foundations", "Build the support workflow and hardware foundation used throughout the path.", 1),
    StageDefinition("stage.windows_support", "Windows Support", "Diagnose and resolve common Windows, account, application, and endpoint-security problems.", 2),
    StageDefinition("stage.networking_support", "Networking for Support Technicians", "Trace client connectivity from addressing through name resolution the way a help-desk technician does.", 3),
    StageDefinition("stage.network_administration", "Network Administration & Infrastructure", "Go deeper into switching, routing, and network services administration. Role-dependent, later-career material.", 4),
    StageDefinition("stage.identity_access", "Identity & Access", "Support directory accounts, domain access, permissions, and policy safely.", 5),
    StageDefinition("stage.microsoft_workplace", "Microsoft 365, Entra & Endpoint Management", "Coming soon: Microsoft 365, Entra ID, Intune, and endpoint-management support work. Planned in Phase 4B; see docs/JOB_READY_CURRICULUM_BLUEPRINT.md.", 6),
    StageDefinition("stage.server_foundations", "Systems & Server Foundations", "Investigate and operate shared Windows services with evidence and rollback discipline.", 7),
    StageDefinition("stage.linux_support", "Linux Support", "Use Linux commands, services, logs, and network evidence to support production systems.", 8),
    StageDefinition("stage.cloud_infrastructure", "Cloud & Infrastructure Foundations", "Reason about cloud responsibility, identity, compute, storage, and access paths.", 9),
    StageDefinition("stage.integrated_support", "Integrated Support & Capstone", "Combine triage, troubleshooting, communication, and evidence in complete support shifts.", 10),
)


MODULES = (
    ModuleDefinition("module.orientation.nexus", "stage.orientation", "Nexus Orientation", "Understand the training workflow, evidence expectations, and first support checkpoint.", 0, 0),
    ModuleDefinition("module.endpoint.support_workflow", "stage.endpoint_foundations", "Support Workflow Essentials", "Record, communicate, and complete support work professionally.", 0, 1),
    ModuleDefinition("module.endpoint.pc_hardware", "stage.endpoint_foundations", "PC Hardware Foundations", "Recognize core components and isolate common hardware symptoms.", 1, 2),
    ModuleDefinition("module.windows.fundamentals", "stage.windows_support", "Windows Fundamentals & Diagnostics", "Use Windows tools and commands to gather evidence before changing the system.", 0, 3),
    ModuleDefinition("module.windows.queue_operations", "stage.windows_support", "Queue & Endpoint Operations", "Prioritize endpoint work and communicate safe, useful next steps.", 1, 4),
    ModuleDefinition("module.windows.troubleshooting", "stage.windows_support", "Windows Troubleshooting", "Isolate startup, application, storage, and device failures with low-risk tests.", 2, 5),
    ModuleDefinition("module.windows.accounts_permissions", "stage.windows_support", "Accounts & Permissions", "Resolve local account and access requests without bypassing verification or least privilege.", 3, 6),
    ModuleDefinition("module.windows.endpoint_security", "stage.windows_support", "Endpoint Security & Remote Support", "Contain endpoint risk, support users remotely, and escalate with useful evidence.", 4, 7),
    ModuleDefinition("module.networking.client_triage", "stage.networking_support", "Client Network Triage", "Separate local, upstream, and name-resolution failures on a client endpoint.", 0, 8),
    ModuleDefinition("module.networking.ip_addressing", "stage.networking_support", "IP Addressing & Packet Flow", "Reason about IPv4 addressing, subnets, gateways, ARP, and packet paths.", 1, 9),
    ModuleDefinition("module.networking.switching_vlans", "stage.network_administration", "Switching & VLANs", "Inspect switch state and safely correct access-port and VLAN problems.", 0, 10),
    ModuleDefinition("module.networking.routing_services", "stage.network_administration", "Routing & Network Services", "Trace failures across trunks, gateways, routing, DHCP, and DNS.", 1, 11),
    ModuleDefinition("module.networking.secure_admin", "stage.network_administration", "Secure Network Administration", "Troubleshoot shared network equipment safely and produce a usable handoff.", 2, 12),
    ModuleDefinition("module.identity.active_directory", "stage.identity_access", "Active Directory Foundations", "Handle common directory account and group requests with appropriate safeguards.", 0, 13),
    ModuleDefinition("module.identity.domain_access", "stage.identity_access", "Domain Operations & File Access", "Diagnose domain trust, computer-account, and group-based access failures.", 1, 14),
    ModuleDefinition("module.identity.group_policy", "stage.identity_access", "Group Policy", "Use resultant-policy evidence to diagnose scope and refresh issues.", 2, 15),
    ModuleDefinition("module.server.powershell_services", "stage.server_foundations", "Server Networking & PowerShell", "Inspect Windows services and support DNS, DHCP, and directory operations safely.", 0, 16),
    ModuleDefinition("module.server.operations_recovery", "stage.server_foundations", "Server Operations & Recovery", "Operate shared servers with logs, tested restores, rollback plans, and verification.", 1, 17),
    ModuleDefinition("module.linux.fundamentals", "stage.linux_support", "Linux Fundamentals", "Navigate Linux, interpret permissions, and gather host evidence safely.", 0, 18),
    ModuleDefinition("module.linux.services", "stage.linux_support", "Linux Services & Troubleshooting", "Use systemd, journals, network tools, DNS, and cron evidence to diagnose faults.", 1, 19),
    ModuleDefinition("module.linux.production", "stage.linux_support", "Linux Production & Security", "Triage web, remote-access, monitoring, capacity, and security concerns with evidence.", 2, 20),
    ModuleDefinition("module.cloud.identity", "stage.cloud_infrastructure", "Cloud Concepts & Identity", "Route cloud issues by responsibility and investigate cloud identity failures.", 0, 21),
    ModuleDefinition("module.cloud.azure_infrastructure", "stage.cloud_infrastructure", "Azure Infrastructure", "Separate control-plane and guest failures across compute, networking, and storage.", 1, 22),
    ModuleDefinition("module.integrated.operations", "stage.integrated_support", "Integrated Support Operations", "Prioritize mixed work and preserve evidence through incident communication and handoff.", 0, 23),
    ModuleDefinition("module.integrated.final_shift", "stage.integrated_support", "Final Support Shift", "Complete a realistic support shift from triage through diagnosis, action, escalation, and documentation.", 1, 24),
)


STAGE_BY_ID = {stage.stable_id: stage for stage in STAGES}
MODULE_BY_ID = {module.stable_id: module for module in MODULES}
MODULE_BY_WEEK = {module.source_week_number: module for module in MODULES}


def learning_role_for(activity_type: str, metadata: dict | None = None) -> str | None:
    """Return presentation metadata only; this is never competency evidence."""
    override = (metadata or {}).get("learning_role")
    return override or DEFAULT_LEARNING_ROLE.get(activity_type)


def module_for_week(week_number: int) -> ModuleDefinition | None:
    return MODULE_BY_WEEK.get(week_number)


def public_stage(stage: StageDefinition) -> dict:
    return asdict(stage)


def public_module(module: ModuleDefinition) -> dict:
    return {
        "stable_id": module.stable_id,
        "stage_id": module.stage_id,
        "title": module.title,
        "purpose": module.purpose,
        "display_order": module.display_order,
        "route": f"/training/module/{module.stable_id}",
    }


def structure_definition_issues(
    stages: tuple[StageDefinition, ...] = STAGES,
    modules: tuple[ModuleDefinition, ...] = MODULES,
) -> list[dict]:
    issues: list[dict] = []
    stage_ids = [stage.stable_id for stage in stages]
    module_ids = [module.stable_id for module in modules]
    for kind, stable_ids in (("stage", stage_ids), ("module", module_ids)):
        duplicates = sorted({stable_id for stable_id in stable_ids if stable_ids.count(stable_id) > 1})
        for stable_id in duplicates:
            issues.append({"code": f"DUPLICATE_{kind.upper()}_ID", "severity": "error", "stable_id": stable_id, "message": f"Duplicate {kind} stable ID."})
        for stable_id in stable_ids:
            if not _STABLE_ID_RE.fullmatch(stable_id):
                issues.append({"code": f"INVALID_{kind.upper()}_ID", "severity": "error", "stable_id": stable_id, "message": f"Invalid {kind} stable ID."})
    stage_orders = [stage.display_order for stage in stages]
    if len(stage_orders) != len(set(stage_orders)) or any(order < 0 for order in stage_orders):
        issues.append({"code": "INVALID_STAGE_ORDER", "severity": "error", "message": "Stage display orders must be unique and non-negative."})
    module_weeks = [module.source_week_number for module in modules]
    for week_number in sorted({week for week in module_weeks if module_weeks.count(week) > 1}):
        issues.append({"code": "DUPLICATE_MODULE_MAPPING", "severity": "error", "week_number": week_number, "message": "A storage week maps to multiple modules."})
    known_stage_ids = set(stage_ids)
    for module in modules:
        if module.stage_id not in known_stage_ids:
            issues.append({"code": "MISSING_STAGE", "severity": "error", "stable_id": module.stable_id, "message": "Module references a missing stage."})
        if module.display_order < 0:
            issues.append({"code": "INVALID_MODULE_ORDER", "severity": "error", "stable_id": module.stable_id, "message": "Module display order must be non-negative."})
    for stage in stages:
        orders = [module.display_order for module in modules if module.stage_id == stage.stable_id]
        if len(orders) != len(set(orders)):
            issues.append({"code": "INVALID_MODULE_ORDER", "severity": "error", "stable_id": stage.stable_id, "message": "Module display orders must be unique within a stage."})
    return issues
