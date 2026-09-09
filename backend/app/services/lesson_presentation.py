"""Learner-facing structure for a small, reviewed set of legacy Core lessons.

The legacy lesson table intentionally stays unchanged.  This additive view model
lets reviewed lessons gain a beginner presentation without rewriting every old
lesson or requiring a content migration.
"""

from __future__ import annotations

from typing import Any


LESSON_PRESENTATIONS: dict[str, dict[str, Any]] = {
    "Anatomy of a Good Ticket": {
        "workplace_purpose": "Support teams rely on the ticket to continue work, communicate with the user, and verify what was actually resolved.",
        "mental_model": [
            "reported symptom",
            "checks and observations",
            "safe action",
            "verification",
            "clear handoff",
        ],
        "worked_example": {
            "symptom": "A user says, ‘My laptop cannot get online.’",
            "check": "Confirm the affected device, time, connection type, and what the user can still reach.",
            "observation": "The laptop reaches internal sites but not external names.",
            "suggests": "The scope is narrower than a total network outage and name resolution is worth checking.",
            "does_not_prove": "It does not yet prove the DNS server is down; the client setting or one application may be involved.",
            "next_check": "Capture IP configuration and compare a lookup through the configured resolver with an approved known resolver.",
        },
        "evidence_guidance": "A ticket records what was observed and verified. It should separate evidence from a suspected cause.",
        "understanding_prompt": "Can another technician tell what happened, what you checked, and what remains to do without contacting the user again?",
        "readiness": [
            "separate internal technical notes from user-facing language",
            "record symptoms, checks, observations, actions, and verification",
            "avoid presenting an unverified cause as fact",
        ],
    },
    "Storage: Symptoms Before Specs": {
        "workplace_purpose": "Storage faults can threaten user data, so a technician must recognize risk before running repairs or replacing parts.",
        "mental_model": [
            "component",
            "its role",
            "failure symptom",
            "supporting evidence",
            "protect data before replacement",
        ],
        "worked_example": {
            "symptom": "A laptop takes several minutes to boot and the drive clicks repeatedly.",
            "check": "Stop write-heavy troubleshooting and confirm the sound, backup status, and drive health information.",
            "observation": "The sound comes from the hard disk and the firmware reports a drive-health warning.",
            "suggests": "The mechanical drive may be failing and the data is at risk.",
            "does_not_prove": "Slow boot by itself would not prove a failed drive; startup software can also cause delay.",
            "next_check": "Follow the approved data-protection and escalation path before replacement or repair scans.",
        },
        "evidence_guidance": "A symptom points to a component only when corroborating evidence supports it. Protect irreplaceable data before destructive testing.",
        "understanding_prompt": "Which observation would make you stop routine troubleshooting and protect the user’s data first?",
        "readiness": [
            "describe the role of storage",
            "connect common symptoms to possible storage failure",
            "name evidence to gather before replacement",
        ],
    },
    "The Client-Side Network Triage Tree": {
        "workplace_purpose": "IP configuration quickly shows whether a workstation received the settings it needs before you blame the internet, DNS, or the network team.",
        "mental_model": [
            "device",
            "local IP configuration",
            "gateway",
            "DNS",
            "remote service",
        ],
        "worked_example": {
            "symptom": "One workstation cannot reach company services.",
            "check": "Run ipconfig /all and compare the result with a nearby working workstation.",
            "observation": "The affected PC has 169.254.40.7, no default gateway, and DHCP is enabled; the nearby PC has a normal lease.",
            "suggests": "The affected PC did not obtain normal IPv4 configuration through DHCP, and the fault is likely local to its path.",
            "does_not_prove": "It does not prove the DHCP server is down or identify whether the cable, switch port, adapter, or lease exchange failed.",
            "next_check": "Confirm link status and the physical or Wi-Fi connection, then renew the lease and compare the new output.",
        },
        "evidence_guidance": "A 169.254.x.x address narrows the issue to missing normal DHCP configuration. A failed ping means connectivity is not confirmed; ICMP may be blocked, so corroborate it with another relevant check.",
        "understanding_prompt": "What does an APIPA address tell you, and what must you check before naming the cause?",
        "readiness": [
            "explain what DHCP supplies",
            "recognize a 169.254.x.x APIPA address",
            "describe one next check without claiming an unsupported cause",
        ],
    },
    "Startup Failures and Recovery Options": {
        "workplace_purpose": "The point where startup fails helps a technician choose a focused, low-risk recovery step instead of reinstalling Windows blindly.",
        "mental_model": [
            "symptom",
            "startup-stage evidence",
            "least disruptive supported repair",
            "verification",
        ],
        "worked_example": {
            "symptom": "Windows hangs at the spinning dots after a driver update.",
            "check": "Test whether the device starts in Safe Mode and review the recent change and relevant events.",
            "observation": "Safe Mode starts and the normal boot began failing immediately after the driver update.",
            "suggests": "A driver or service loaded during normal startup is a strong suspect.",
            "does_not_prove": "Safe Mode success does not identify the exact driver or rule out every other startup component.",
            "next_check": "Inspect the changed driver and logs, then use the approved rollback and verify with two normal restarts.",
        },
        "evidence_guidance": "Recovery tools change the machine. Capture the failure stage and recent-change evidence before choosing the least disruptive supported action.",
        "understanding_prompt": "How does a successful Safe Mode boot narrow the investigation without naming the exact cause?",
        "readiness": [
            "locate the startup stage that fails",
            "use Safe Mode as evidence",
            "choose and verify a low-risk recovery step",
        ],
    },
    "Network Printing Without Tears": {
        "workplace_purpose": "Following the print path lets support fix the failed stage instead of repeatedly reinstalling a driver that may be healthy.",
        "mental_model": [
            "application",
            "print queue and spooler",
            "configured printer destination",
            "network",
            "printer",
        ],
        "worked_example": {
            "symptom": "Everyone can submit jobs, but one office printer remains offline after a network change.",
            "check": "Compare the queue’s configured port with the current IP on the printer panel or configuration page.",
            "observation": "The queue targets the old address while the printer panel shows a new address.",
            "suggests": "The configured destination is stale after the address change.",
            "does_not_prove": "A failed ping alone would not prove the printer or path is down because ICMP may be blocked.",
            "next_check": "Verify the printer through an approved service or its web page, correct the managed port if authorized, then send a test page.",
        },
        "evidence_guidance": "Queue state, configured destination, printer-panel status, and a test page each prove different parts of the print path.",
        "understanding_prompt": "Which evidence separates an application or queue problem from a stale destination or printer fault?",
        "readiness": [
            "trace a job through the print path",
            "compare the configured destination with the printer’s current address",
            "choose a next check before reinstalling",
        ],
    },
    "Account Lifecycle Support": {
        "workplace_purpose": "Identity tickets can expose company data, so support must verify the person and authorization before making even a simple account change.",
        "mental_model": [
            "request",
            "verified identity",
            "verified authorization",
            "least-privilege action",
            "audit evidence",
        ],
        "worked_example": {
            "symptom": "A caller urgently asks for a password reset before a meeting.",
            "check": "Use the organization’s approved identity-verification method and inspect the account state.",
            "observation": "The caller cannot complete verification through a channel already on file.",
            "suggests": "The reset must pause or follow the approved escalation path despite the urgency.",
            "does_not_prove": "A familiar voice, employee details, or an urgent story does not prove identity or authorization.",
            "next_check": "Contact the verified manager or identity team through the documented process and record the result.",
        },
        "evidence_guidance": "Identity evidence answers who is asking; authorization evidence answers whether the requested access is allowed. One does not substitute for the other.",
        "understanding_prompt": "Can you explain why urgency changes priority but never replaces identity and authorization checks?",
        "readiness": [
            "distinguish identity verification from authorization",
            "recognize when a reset or access request must pause",
            "record an auditable safe next action",
        ],
    },
    "Meet the Command Line": {
        "workplace_purpose": "A terminal gives technicians precise, copyable evidence when a graphical status is vague or remote access is limited.",
        "mental_model": [
            "terminal",
            "prompt",
            "command",
            "output",
            "interpretation before action",
        ],
        "worked_example": {
            "symptom": "A user says the network icon looks connected but websites do not open.",
            "check": "At the prompt, run the read-only command ipconfig and read the output before changing anything.",
            "observation": "IPv4 Address is 192.168.10.24 and Default Gateway is 192.168.10.1.",
            "suggests": "The workstation has local IPv4 settings and a configured route toward other networks.",
            "does_not_prove": "Those fields do not prove the gateway, DNS, or website is reachable.",
            "next_check": "Use the guided practice to test the next layer, then record the command and interpretation in the ticket.",
        },
        "evidence_guidance": "Start with read-only inspection. Command output is evidence of the fields shown, not proof of every service that depends on them.",
        "understanding_prompt": "In a simple terminal result, can you point out the prompt, command, output, and what the output does and does not establish?",
        "readiness": [
            "explain what a terminal and prompt are",
            "separate a command from its output",
            "interpret an IPv4 address and gateway before making changes",
        ],
    },
}


def presentation_for_lesson(title: str) -> dict[str, Any]:
    """Return a copy-safe learner presentation; unknown lessons fall back."""

    presentation = LESSON_PRESENTATIONS.get(title)
    if presentation is None:
        return {}
    return {
        **presentation,
        "mental_model": list(presentation["mental_model"]),
        "worked_example": dict(presentation["worked_example"]),
        "readiness": list(presentation["readiness"]),
    }


def learner_summary(title: str, summary: str | None) -> str | None:
    """Correct reviewed legacy text at read time as well as in fresh seeds."""

    if summary is None:
        return None
    corrections = {
        "Command-Line Diagnostics": (
            (
                "sfc /scannow then DISM /Online /Cleanup-Image /RestoreHealth → system file repair sequence (DISM repairs the store sfc repairs from).",
                "DISM /Online /Cleanup-Image /RestoreHealth then sfc /scannow → supported system file repair sequence (DISM repairs the component store first; SFC then checks and repairs protected files from it).",
            ),
            (
                "IP (169.254.x.x = DHCP failed)",
                "IP (169.254.x.x means normal DHCP configuration was not obtained)",
            ),
        ),
        "Meet the Command Line": (
            (
                "GUI status icons summarize; command output proves.",
                "GUI status icons summarize; command output provides precise evidence.",
            ),
            (
                "trusting 'it looks connected' over 'ping succeeded 4/4'",
                "treating either a status icon or one successful ping as proof that every network service works",
            ),
        ),
        "The Client-Side Network Triage Tree": (
            (
                "169.254.x.x → DHCP FAILED.",
                "169.254.x.x → normal DHCP configuration was not obtained.",
            ),
            (
                "Fail = local network/switch port/cable.",
                "Failure means reachability is not confirmed; ICMP may be blocked, so corroborate before naming the local path as the cause.",
            ),
        ),
    }
    for old, new in corrections.get(title, ()):
        summary = summary.replace(old, new)
    return summary


def learner_outcomes(title: str, outcomes: list[str]) -> list[str]:
    if title == "Command-Line Diagnostics":
        return [outcome.replace("sfc → DISM", "DISM → SFC") for outcome in outcomes]
    return outcomes
