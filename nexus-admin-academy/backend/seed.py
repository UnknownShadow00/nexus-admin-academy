from datetime import datetime, timezone

from app.config import load_env
from app.database import SessionLocal
from app.models.command_reference import CommandReference
from app.models.learning import Lesson, Module
from app.models.progression import MethodologyFramework, PromotionGate, Role
from app.models.student import Student
from app.models.ticket import Ticket

load_env()

STUDENTS = [
    ("Alex", "alex@nexus.local"),
    ("Jordan", "jordan@nexus.local"),
    ("Sam", "sam@nexus.local"),
    ("Taylor", "taylor@nexus.local"),
    ("Riley", "riley@nexus.local"),
]

ROLES = [
    {"name": "L1 Help Desk", "rank_order": 1, "description": "Entry support analyst"},
    {"name": "L2 Help Desk", "rank_order": 2, "description": "Escalation support analyst"},
    {"name": "Junior SysAdmin", "rank_order": 3, "description": "Junior systems administrator"},
    {"name": "SysAdmin", "rank_order": 4, "description": "Systems administrator"},
    {"name": "Network Admin", "rank_order": 5, "description": "Network administrator"},
]

PROMOTION_GATES = [
    {
        "role": "L2 Help Desk",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"1": 10, "2": 8, "3": 5}},
    },
    {
        "role": "L2 Help Desk",
        "requirement_type": "min_mastery_by_domain",
        "config": {"thresholds": {"hardware": 70, "networking": 70}},
    },
    {
        "role": "Junior SysAdmin",
        "requirement_type": "min_verified_tickets_by_difficulty",
        "config": {"thresholds": {"2": 10, "3": 8, "4": 5}},
    },
]

MODULE_0 = {
    "code": "MOD-000",
    "title": "Troubleshooting Methodology",
    "description": "Learn systematic IT problem-solving and disciplined incident handling.",
    "difficulty_band": 1,
    "estimated_hours": 4,
    "unlock_threshold": 0,
    "module_order": 0,
    "lessons": [
        {
            "title": "CompTIA 6-Step Process",
            "summary": "Define, theorize, test, plan, verify, and document.",
            "outcomes": ["Can identify symptoms", "Can test theories", "Can verify fixes"],
            "lesson_order": 1,
            "estimated_minutes": 45,
        }
    ],
}

FRAMEWORK_STEPS = {
    "steps": [
        "Identify the problem",
        "Establish a theory of probable cause",
        "Test the theory",
        "Establish a plan of action and implement",
        "Verify functionality and implement preventive measures",
        "Document findings, actions, and outcomes",
    ]
}

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

COMMANDS = [
    # Networking (12)
    {"command": "ping", "category": "Networking", "syntax": "ping <host>", "description": "Test connectivity to a host.", "example": "ping 8.8.8.8"},
    {"command": "tracert", "category": "Networking", "syntax": "tracert <host>", "description": "Trace route hops to destination.", "example": "tracert google.com"},
    {"command": "ipconfig", "category": "Networking", "syntax": "ipconfig /all", "description": "Show Windows network configuration.", "example": "ipconfig /all"},
    {"command": "ifconfig", "category": "Networking", "syntax": "ifconfig", "description": "Show interface config on Unix systems.", "example": "ifconfig eth0"},
    {"command": "netstat", "category": "Networking", "syntax": "netstat -ano", "description": "Show sockets and connections.", "example": "netstat -ano"},
    {"command": "nslookup", "category": "Networking", "syntax": "nslookup <domain>", "description": "Query DNS records.", "example": "nslookup microsoft.com"},
    {"command": "dig", "category": "Networking", "syntax": "dig <domain>", "description": "Detailed DNS lookup tool.", "example": "dig example.com"},
    {"command": "arp", "category": "Networking", "syntax": "arp -a", "description": "Inspect ARP cache entries.", "example": "arp -a"},
    {"command": "nmap", "category": "Networking", "syntax": "nmap <target>", "description": "Scan hosts and open ports.", "example": "nmap 192.168.1.0/24"},
    {"command": "ssh", "category": "Networking", "syntax": "ssh user@host", "description": "Open remote secure shell session.", "example": "ssh admin@server01"},
    {"command": "curl", "category": "Networking", "syntax": "curl <url>", "description": "HTTP request from command line.", "example": "curl https://example.com"},
    {"command": "wget", "category": "Networking", "syntax": "wget <url>", "description": "Download files over HTTP/HTTPS.", "example": "wget https://example.com/file.zip"},
    # File System (10)
    {"command": "ls", "category": "File System", "syntax": "ls -la", "description": "List directory contents.", "example": "ls -la /var/log"},
    {"command": "dir", "category": "File System", "syntax": "dir", "description": "List directory contents on Windows.", "example": "dir C:\\Users"},
    {"command": "cd", "category": "File System", "syntax": "cd <path>", "description": "Change current directory.", "example": "cd /etc"},
    {"command": "cp", "category": "File System", "syntax": "cp <src> <dst>", "description": "Copy files/directories.", "example": "cp app.conf app.conf.bak"},
    {"command": "mv", "category": "File System", "syntax": "mv <src> <dst>", "description": "Move or rename files.", "example": "mv old.log archive/"},
    {"command": "rm", "category": "File System", "syntax": "rm -rf <path>", "description": "Delete files/directories.", "example": "rm temp.txt"},
    {"command": "mkdir", "category": "File System", "syntax": "mkdir <dir>", "description": "Create a directory.", "example": "mkdir backups"},
    {"command": "find", "category": "File System", "syntax": "find <path> -name <pattern>", "description": "Search for files by criteria.", "example": "find . -name *.log"},
    {"command": "grep", "category": "File System", "syntax": "grep -R <pattern> <path>", "description": "Search text in files.", "example": "grep -R ERROR /var/log"},
    {"command": "cat", "category": "File System", "syntax": "cat <file>", "description": "Print file content.", "example": "cat hosts"},
    # Users & Permissions (8)
    {"command": "whoami", "category": "Users", "syntax": "whoami", "description": "Show current user identity.", "example": "whoami"},
    {"command": "id", "category": "Users", "syntax": "id <user>", "description": "Show user and group IDs.", "example": "id admin"},
    {"command": "passwd", "category": "Users", "syntax": "passwd <user>", "description": "Change user password.", "example": "passwd student"},
    {"command": "useradd", "category": "Users", "syntax": "useradd <user>", "description": "Create new local user.", "example": "useradd trainee1"},
    {"command": "usermod", "category": "Users", "syntax": "usermod [options] <user>", "description": "Modify local user account.", "example": "usermod -aG wheel trainee1"},
    {"command": "sudo", "category": "Users", "syntax": "sudo <command>", "description": "Run command with elevated rights.", "example": "sudo systemctl restart sshd"},
    {"command": "chown", "category": "Users", "syntax": "chown <owner>:<group> <file>", "description": "Change file ownership.", "example": "chown root:root /etc/ssh/sshd_config"},
    {"command": "last", "category": "Users", "syntax": "last", "description": "Show recent login history.", "example": "last -n 20"},
    # Services & Processes (10)
    {"command": "systemctl", "category": "Services", "syntax": "systemctl <action> <service>", "description": "Manage systemd services.", "example": "systemctl status nginx"},
    {"command": "ps", "category": "Services", "syntax": "ps aux", "description": "List running processes.", "example": "ps aux | grep python"},
    {"command": "top", "category": "Services", "syntax": "top", "description": "Live process resource view.", "example": "top"},
    {"command": "kill", "category": "Services", "syntax": "kill [-9] <pid>", "description": "Terminate a process.", "example": "kill -9 1234"},
    {"command": "journalctl", "category": "Services", "syntax": "journalctl -u <service>", "description": "Read systemd journal logs.", "example": "journalctl -u sshd"},
    {"command": "df", "category": "Services", "syntax": "df -h", "description": "Show filesystem disk usage.", "example": "df -h"},
    {"command": "du", "category": "Services", "syntax": "du -sh <path>", "description": "Show directory size usage.", "example": "du -sh /var/log"},
    {"command": "free", "category": "Services", "syntax": "free -m", "description": "Display memory usage.", "example": "free -m"},
    {"command": "uptime", "category": "Services", "syntax": "uptime", "description": "Show system uptime and load.", "example": "uptime"},
    {"command": "dmesg", "category": "Services", "syntax": "dmesg", "description": "Kernel ring buffer messages.", "example": "dmesg | tail"},
    # Diagnostics (6)
    {"command": "lsof", "category": "Diagnostics", "syntax": "lsof -i", "description": "List open files and sockets.", "example": "lsof -i :443"},
    {"command": "tcpdump", "category": "Diagnostics", "syntax": "tcpdump -i <iface>", "description": "Capture network packets.", "example": "tcpdump -i eth0 port 53"},
    {"command": "netcat", "category": "Diagnostics", "syntax": "nc <host> <port>", "description": "Read/write network connections.", "example": "nc -vz server01 443"},
    {"command": "openssl", "category": "Diagnostics", "syntax": "openssl <subcommand>", "description": "SSL/TLS and cert diagnostics.", "example": "openssl s_client -connect example.com:443"},
    {"command": "strace", "category": "Diagnostics", "syntax": "strace <command>", "description": "Trace system calls.", "example": "strace -p 1234"},
    {"command": "ss", "category": "Diagnostics", "syntax": "ss -tulpen", "description": "Socket statistics and listeners.", "example": "ss -tulpen"},
    # Windows-specific (4 additional, total list = 50)
    {"command": "netsh", "category": "Windows", "syntax": "netsh interface ip show config", "description": "Configure and inspect network settings.", "example": "netsh interface ip show config"},
    {"command": "sc", "category": "Windows", "syntax": "sc query <service>", "description": "Service control manager utility.", "example": "sc query wuauserv"},
    {"command": "tasklist", "category": "Windows", "syntax": "tasklist", "description": "List Windows running processes.", "example": "tasklist /fi \"imagename eq notepad.exe\""},
    {"command": "taskkill", "category": "Windows", "syntax": "taskkill /PID <pid> /F", "description": "Force-stop Windows process.", "example": "taskkill /PID 4321 /F"},
]


def seed_students(db):
    existing = {row.email for row in db.query(Student).all()}
    for name, email in STUDENTS:
        if email in existing:
            continue
        db.add(Student(name=name, email=email, total_xp=0))


def seed_roles(db):
    for role in ROLES:
        exists = db.query(Role).filter(Role.name == role["name"]).first()
        if not exists:
            db.add(Role(**role))
    db.flush()


def seed_default_student_roles(db):
    first_role = db.query(Role).filter(Role.rank_order == 1).first()
    if not first_role:
        return
    for student in db.query(Student).all():
        if student.current_role_id is None:
            student.current_role_id = first_role.id
            student.role_since = datetime.now(timezone.utc)


def seed_promotion_gates(db):
    for gate in PROMOTION_GATES:
        role = db.query(Role).filter(Role.name == gate["role"]).first()
        if not role:
            continue
        exists = db.query(PromotionGate).filter(PromotionGate.role_id == role.id, PromotionGate.requirement_type == gate["requirement_type"]).first()
        if exists:
            exists.requirement_config = gate["config"]
        else:
            db.add(PromotionGate(role_id=role.id, requirement_type=gate["requirement_type"], requirement_config=gate["config"]))


def seed_module0_and_methodology(db):
    module = db.query(Module).filter(Module.code == MODULE_0["code"]).first()
    if module is None:
        module = Module(
            code=MODULE_0["code"],
            title=MODULE_0["title"],
            description=MODULE_0["description"],
            difficulty_band=MODULE_0["difficulty_band"],
            estimated_hours=MODULE_0["estimated_hours"],
            unlock_threshold=MODULE_0["unlock_threshold"],
            module_order=MODULE_0["module_order"],
            active=True,
        )
        db.add(module)
        db.flush()

    for lesson_data in MODULE_0["lessons"]:
        lesson = db.query(Lesson).filter(Lesson.module_id == module.id, Lesson.lesson_order == lesson_data["lesson_order"]).first()
        if lesson:
            continue
        db.add(
            Lesson(
                module_id=module.id,
                title=lesson_data["title"],
                summary=lesson_data["summary"],
                lesson_order=lesson_data["lesson_order"],
                outcomes=lesson_data["outcomes"],
                estimated_minutes=lesson_data["estimated_minutes"],
                status="published",
            )
        )

    l1 = db.query(Role).filter(Role.rank_order == 1).first()
    framework = db.query(MethodologyFramework).filter(MethodologyFramework.name == "CompTIA 6-Step").first()
    if framework is None:
        db.add(
            MethodologyFramework(
                name="CompTIA 6-Step",
                description="Structured troubleshooting for support professionals",
                steps=FRAMEWORK_STEPS,
                required_for_role=l1.id if l1 else None,
            )
        )


def seed_answer_keys(db, limit: int = 10):
    tickets = db.query(Ticket).limit(limit).all()
    for ticket in tickets:
        title = (ticket.title or "").lower()
        matched = ANSWER_KEYS[0]
        for template in ANSWER_KEYS:
            if template["match"] in title:
                matched = template
                break
        ticket.root_cause = matched["root_cause"]
        ticket.root_cause_type = matched["root_cause_type"]
        ticket.required_checkpoints = matched["required_checkpoints"]
        ticket.required_evidence = matched["required_evidence"]
        ticket.scoring_anchors = matched["scoring_anchors"]
        ticket.model_answer = "Document symptom, confirm diagnosis, apply fix, and verify restoration."


def seed_commands(db):
    if len(COMMANDS) != 50:
        raise RuntimeError(f"Expected 50 command seeds, found {len(COMMANDS)}")

    allowed = {item["command"].lower() for item in COMMANDS}
    existing_rows = db.query(CommandReference).all()
    by_command = {c.command.lower(): c for c in existing_rows}
    for row in existing_rows:
        if row.command.lower() not in allowed:
            db.delete(row)

    for item in COMMANDS:
        key = item["command"].lower()
        row = by_command.get(key)
        if row is None:
            db.add(
                CommandReference(
                    command=item["command"],
                    description=item["description"],
                    syntax=item["syntax"],
                    example=item["example"],
                    category=item["category"],
                    os="windows" if item["category"] == "Windows" else "mixed",
                )
            )
        else:
            row.description = item["description"]
            row.syntax = item["syntax"]
            row.example = item["example"]
            row.category = item["category"]
            row.os = "windows" if item["category"] == "Windows" else "mixed"


def run_seed() -> None:
    db = SessionLocal()
    try:
        seed_students(db)
        db.flush()
        seed_roles(db)
        seed_default_student_roles(db)
        seed_promotion_gates(db)
        seed_module0_and_methodology(db)
        seed_answer_keys(db, limit=10)
        seed_commands(db)
        db.commit()
        print("Seed complete: students, roles, promotion gates, module0, methodology, answer keys, commands(50)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
