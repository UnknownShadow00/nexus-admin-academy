from app.database import SessionLocal
from app.models.ticket import Ticket

ANSWER_KEYS = [
    {
        "match": "dns",
        "root_cause": "DNS server misconfiguration on client NIC",
        "root_cause_type": "dns_misconfiguration",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Verify network connectivity", "commands": ["ping 8.8.8.8", "ipconfig"], "weight": 0.2},
                {"id": 2, "step": "Check DNS resolution", "commands": ["nslookup"], "weight": 0.3},
                {"id": 3, "step": "Identify root cause", "required_mention": ["dns server", "incorrect"], "weight": 0.3},
                {"id": 4, "step": "Verify fix", "commands": ["ping internal"], "weight": 0.2},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "ipconfig /all DNS values", "validation": {"must_contain_text": ["DNS"]}},
                {"type": "screenshot", "description": "after-fix resolution test", "validation": {}},
            ]
        },
        "scoring_anchors": {
            "6": "Basic troubleshooting with missing verification detail",
            "8": "Systematic triage and clear verification",
            "10": "Root cause proven, validated, and documented professionally",
        },
    },
    {
        "match": "locked",
        "root_cause": "Account lockout due to repeated failed authentication attempts",
        "root_cause_type": "expired_credential",
        "required_checkpoints": {
            "checkpoints": [
                {"id": 1, "step": "Confirm lockout status", "commands": ["Active Directory Users and Computers"], "weight": 0.3},
                {"id": 2, "step": "Investigate source", "required_mention": ["event viewer", "failed logon"], "weight": 0.4},
                {"id": 3, "step": "Verify user can sign in", "required_mention": ["test login"], "weight": 0.3},
            ]
        },
        "required_evidence": {
            "evidence_types": [
                {"type": "screenshot", "description": "account lockout state before unlock", "validation": {}},
                {"type": "screenshot", "description": "successful login after resolution", "validation": {}},
            ]
        },
        "scoring_anchors": {
            "6": "Unlocked account but weak root-cause analysis",
            "8": "Investigated lock source with verification",
            "10": "Resolved, validated, and prevented recurrence",
        },
    },
]


def seed_answer_keys(limit: int = 10) -> None:
    db = SessionLocal()
    try:
        tickets = db.query(Ticket).limit(limit).all()
        for ticket in tickets:
            title = (ticket.title or "").lower()
            match = None
            for template in ANSWER_KEYS:
                if template["match"] in title:
                    match = template
                    break
            if not match:
                match = ANSWER_KEYS[0]

            ticket.root_cause = match["root_cause"]
            ticket.root_cause_type = match["root_cause_type"]
            ticket.required_checkpoints = match["required_checkpoints"]
            ticket.required_evidence = match["required_evidence"]
            ticket.scoring_anchors = match["scoring_anchors"]
            ticket.model_answer = "Document symptom, confirm diagnosis, apply fix, and verify restoration."

        db.commit()
        print(f"Seeded answer keys for up to {limit} tickets")
    finally:
        db.close()


if __name__ == "__main__":
    seed_answer_keys()

