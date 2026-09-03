"""First-class escalation as a terminal Service Desk outcome.

Escalation metadata is server-owned and keyed by the scenario ``stable_key``.
It rides on the already-published ``definition_json`` (id, priority, title,
hints), so it needs **no Alembic migration and no new scenario version**.

The converted priority scenarios (``inc2506``/``inc2508``) are built by
``backend/seed.py``'s ``_converted_service_desk_ticket`` whose requester has no
``directoryUserId`` and whose only tool vocabulary is
``remote_desktop.perform_scenario_step``.  Escalation prerequisites and
containment are therefore expressed in *that* vocabulary via
``service_desk_objectives._remote``.  Directory / session-revocation fidelity
is deferred to the realism sprint (see ``service-desk-app/docs/WORKSPACE.md``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.service_desk_objectives import EvidenceRule, _remote


# Fixed taxonomy.  The frontend mirrors this in packages/shared/src.
ESCALATION_REASONS: frozenset[str] = frozenset(
    {
        "permissions-access",
        "security-incident",
        "policy-authorization",
        "change-approval-required",
        "hardware-replacement",
        "unknown-root-cause",
        "other-team-owns-system",
    }
)


@dataclass(frozen=True)
class EscalationProfile:
    """Per-scenario escalation grading contract."""

    expected: bool
    route: str
    accepted_reasons: tuple[str, ...]
    # Trusted successful events that must also be present for a resolved
    # escalation (e.g. contain-then-hand-off).  Empty => escalation alone.
    required_containment: tuple[EvidenceRule, ...] = ()
    # Any trusted successful match here is a safety breach: critical_failure,
    # cannot pass, regardless of anything else.
    prohibited: tuple[EvidenceRule, ...] = ()
    # Debrief copy (Group 4).  Never surfaced while the attempt is in progress.
    rationale: str = ""
    no_escalation_rationale: str = ""
    _reserved: tuple[str, ...] = field(default=(), repr=False)

    @property
    def verification_applicable(self) -> bool:
        """Escalation-only outcomes have no student-performed verification."""
        return bool(self.required_containment)


ESCALATION_PROFILES: dict[str, EscalationProfile] = {
    # Restricted payroll / salary records.  The technician must NOT grant the
    # access themselves; the correct outcome is to hand off to the data owner.
    "inc2506": EscalationProfile(
        expected=True,
        route="Identity & Access",
        accepted_reasons=("policy-authorization", "permissions-access"),
        required_containment=(),
        prohibited=(_remote("INC2506", "NX-2506", "scenario.apply-safe-remediation"),),
        rationale=(
            "Restricted payroll and salary records are governed data. Granting "
            "access needs authorization from the data owner via Identity & "
            "Access - a help-desk technician cannot approve it, so the correct "
            "outcome is to escalate with the request and evidence."
        ),
        no_escalation_rationale=(
            "Closing this yourself - or applying an access change - would be "
            "acting outside a help-desk technician's authority."
        ),
    ),
    # Phishing: the requester entered credentials on a fake page.  Contain with
    # the permitted safe-remediation step, THEN hand off to Information Security.
    "inc2508": EscalationProfile(
        expected=True,
        route="Information Security",
        accepted_reasons=("security-incident",),
        required_containment=(
            _remote("INC2508", "NX-2508", "scenario.apply-safe-remediation"),
        ),
        prohibited=(),
        rationale=(
            "Credentials entered on a phishing page is a security incident. "
            "Perform the permitted containment step first, then escalate to "
            "Information Security for credential and session response."
        ),
        no_escalation_rationale=(
            "Containment alone does not close a suspected account compromise - "
            "Information Security must own the follow-up."
        ),
    ),
}


def escalation_profile(stable_key: str) -> EscalationProfile | None:
    """Return the escalation contract for a scenario, or None if it has none."""
    if not stable_key:
        return None
    return ESCALATION_PROFILES.get(stable_key.lower())
