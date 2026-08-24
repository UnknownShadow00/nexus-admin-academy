"""Phase 4C.2 network, Linux, and cloud practical upgrades.

The phase owns seven existing LabTemplate rows, their existing activity role
metadata, and three Week 21 video requirement flags. It deliberately does not
create curriculum identities, shell execution, or another simulator.
"""

from copy import deepcopy

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.lab import LabTemplate
from app.models.training import TrainingWeek, TrainingWeekActivity


def _field(label: str, value: str) -> dict:
    return {"label": label, "value": value}


def _panel(panel_id: str, label: str, *fields: tuple[str, str]) -> dict:
    return {"id": panel_id, "label": label, "fields": [_field(*field) for field in fields]}


def _command(
    command: str,
    inspection_id: str | None,
    *output: str,
    aliases: tuple[str, ...] = (),
) -> dict:
    return {
        "command": command,
        "aliases": list(aliases),
        "inspection_id": inspection_id,
        "output": list(output),
    }


def _terminal_profile(
    profile_id: str,
    intro: str,
    help_topics: tuple[str, ...],
    commands: list[dict],
    prompt: str,
) -> dict:
    return {
        "id": profile_id,
        "intro": intro,
        "help_topics": list(help_topics),
        "commands": commands,
        "prompt": prompt,
        "unknown_command_message": (
            "That command is unavailable in this focused case. Use help to review tool categories."
        ),
    }


def _verification(label: str, description: str, *fields: tuple[str, str]) -> dict:
    return {"label": label, "description": description, "fields": [_field(*field) for field in fields]}


def _question(
    question_id: str,
    prompt: str,
    options: tuple[tuple[str, str], ...],
    correct: str,
    explanation: str,
    context: str = "",
) -> dict:
    return {
        "id": question_id,
        "prompt": prompt,
        "context": context,
        "type": "single_choice",
        "options": [{"id": option_id, "label": label} for option_id, label in options],
        "correct": [correct],
        "explanation": explanation,
    }


def _service_desk(key: str, ticket_id: str, label: str, note: str) -> dict:
    return {"key": key, "ticket_id": ticket_id, "label": label, "note": note}


NETWORK_LINUX_CLOUD_CASES: dict[int, dict] = {
    8: {
        "lab_id": 2,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 30,
        "title": "Diagnose the Client Network",
        "description": "Separate endpoint, addressing, gateway, DNS, upstream, connection-type, and VPN evidence in one client incident.",
        "setup_instructions": "Start from the complaint, choose relevant Windows network tools, isolate the failing layer, choose one safe correction, verify the original resource, and document the result.",
        "workbench": {
            "title": "Client network triage",
            "domain": "client_network",
            "guidance_level": "troubleshoot",
            "complaint": "Internet sites open, but internal company resources stopped opening after the laptop reconnected this morning.",
            "guidance": "Separate local link and addressing, local gateway, numeric upstream reachability, and name resolution. Compare connection scope before changing anything.",
            "required_inspections": ["terminal:addressing", "terminal:gateway", "terminal:dns", "scope"],
            "panels": [
                _panel("scope", "Connection scope", ("Affected", "OPS-LT-57 on Corporate Wi-Fi"), ("Wired peer", "Internal portal opens"), ("Nearby Wi-Fi peer", "Internal portal opens"), ("Public internet", "Working on OPS-LT-57")),
                _panel("vpn", "Remote-access state", ("Location", "North Campus"), ("VPN", "Disconnected by on-campus policy"), ("VPN gateway", "Healthy; no related alerts"), ("Private workspace", "Not required for the on-campus intranet")),
                _panel("change", "Client change record", ("Yesterday", "Temporary public DNS used during home troubleshooting"), ("Approval", "No permanent adapter override approved"), ("DHCP DNS", "10.40.0.10, 10.40.0.11")),
            ],
            "terminal_profile": _terminal_profile(
                "client-internal-resources-after-reconnect",
                "Focused Windows network case on OPS-LT-57. Inspect only the client path; commands never run on a real host.",
                ("Address and DHCP state", "Gateway and numeric reachability", "Name resolution", "Route path", "Interface scope"),
                [
                    _command("ipconfig /all", "terminal:addressing", "Windows IP Configuration", "Wireless LAN adapter Wi-Fi:", "   Description . . . . . . . . . . . : Nexus Wi-Fi 6E Adapter", "   DHCP Enabled. . . . . . . . . . . : Yes", "   IPv4 Address. . . . . . . . . . . : 10.40.8.57 (Preferred)", "   Subnet Mask . . . . . . . . . . . : 255.255.255.0", "   Default Gateway . . . . . . . . . : 10.40.8.1", "   DHCP Server . . . . . . . . . . . : 10.40.8.5", "   DNS Servers . . . . . . . . . . . : 1.1.1.1", aliases=("ipconfig",)),
                    _command("ping 10.40.8.1", "terminal:gateway", "Pinging 10.40.8.1 with 32 bytes of data:", "Reply from 10.40.8.1: bytes=32 time<1ms TTL=255", "Reply from 10.40.8.1: bytes=32 time<1ms TTL=255"),
                    _command("ping 1.1.1.1", None, "Pinging 1.1.1.1 with 32 bytes of data:", "Reply from 1.1.1.1: bytes=32 time=12ms TTL=56", "Reply from 1.1.1.1: bytes=32 time=11ms TTL=56"),
                    _command("nslookup intranet.nexus.internal", "terminal:dns", "Server:  one.one.one.one", "Address:  1.1.1.1", "*** one.one.one.one can't find intranet.nexus.internal: Non-existent domain", aliases=("nslookup intranet.nexus.internal 1.1.1.1",)),
                    _command("nslookup intranet.nexus.internal 10.40.0.10", None, "Server:  dns01.nexus.internal", "Address:  10.40.0.10", "Name:    intranet.nexus.internal", "Address:  10.40.16.20"),
                    _command("tracert intranet.nexus.internal", None, "Unable to resolve target system name intranet.nexus.internal."),
                    _command("tracert 10.40.16.20", None, "Tracing route to 10.40.16.20 over a maximum of 30 hops", "  1    <1 ms    <1 ms    <1 ms  10.40.8.1", "  2     2 ms     2 ms     2 ms  10.40.16.20", "Trace complete."),
                    _command("route print", None, "IPv4 Route Table", "Network Destination        Netmask          Gateway       Interface", "0.0.0.0                    0.0.0.0          10.40.8.1    10.40.8.57", "10.40.8.0             255.255.255.0        On-link      10.40.8.57"),
                ],
                "PS C:\\Users\\support> ",
            ),
            "verification": _verification("Client path verification", "The simulated after-state appears only after the server accepts the evidence-backed plan.", ("Adapter DNS", "10.40.0.10, 10.40.0.11 via approved DHCP configuration"), ("Gateway", "10.40.8.1 reachable"), ("Internal lookup", "intranet.nexus.internal → 10.40.16.20"), ("Original complaint", "Internal portal opens on Corporate Wi-Fi"), ("Public internet", "Still working")),
            "documentation_required": True,
            "reinforcement_scenarios": [
                _service_desk("inc2407", "INC2407", "Internal hostname failure", "Existing authoritative Service Desk DNS case."),
                _service_desk("inc2406", "INC2406", "Private workspace from home", "Existing remote-access scope case; it remains non-gating here."),
                _service_desk("inc2402", "INC2402", "Wi-Fi device isolation", "Existing wireless-scope case; it retains Service Desk grading."),
            ],
        },
        "questions": [
            _question("scope", "Which scope statement is best supported?", (("upstream", "The internet edge is down for the campus"), ("client", "One Wi-Fi client has a local resolver configuration mismatch"), ("vpn", "The on-campus VPN gateway is required and down"), ("wireless", "Corporate Wi-Fi is down for every user")), "client", "Peers work on both connection types, the client reaches its gateway and a numeric internet address, and only its configured resolver differs."),
            _question("layer", "Which evidence most directly isolates the failing layer?", (("route", "The default route uses 10.40.8.1"), ("wifi", "The adapter is connected to Corporate Wi-Fi"), ("dns", "The configured public resolver returns no internal record while the approved internal resolver returns 10.40.16.20"), ("vpn", "The VPN is disconnected on campus")), "dns", "The split lookup proves internal DNS resolution is the failing path while IP routing remains usable."),
            _question("action", "Choose the safe response.", (("gateway", "Replace the default gateway with an unmanaged address"), ("disable", "Disable the firewall and VPN client"), ("hosts", "Add a permanent hosts-file entry"), ("restore", "Remove the unapproved static DNS override, restore approved DHCP resolver settings, then repeat lookup and the original portal test")), "restore", "The narrow correction reverses the unsupported client override and includes layered verification."),
        ],
    },
    11: {
        "lab_id": 10,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 30,
        "title": "Trace the Network Service Failure",
        "description": "Use topology, client, SVI, route, DHCP, and change evidence to isolate a scoped network-service incident.",
        "setup_instructions": "You receive symptoms rather than a command recipe. Identify scope and the likely failing service path, choose the smallest authorized correction, verify reachability, and write a professional handoff.",
        "workbench": {
            "title": "Routing and network-services troubleshoot",
            "domain": "network_services",
            "guidance_level": "troubleshoot",
            "complaint": "New training-room laptops connect to their switch ports but cannot reach any company resource. Other floors are working.",
            "guidance": "Inspect scope across clients, the access/trunk path, gateway state, and the central service before deciding where the fault lives.",
            "required_inspections": ["clients", "topology", "gateway", "dhcp", "change"],
            "panels": [
                _panel("clients", "Client samples", ("TRN-LT-01", "169.254.32.18/16; no gateway"), ("TRN-LT-02", "169.254.77.41/16; no gateway"), ("Existing VLAN 20 client", "10.40.20.44/24; gateway 10.40.20.1; working")),
                _panel("topology", "Existing simulator-derived switch evidence", ("Training ports", "Access VLAN 30; connected"), ("Uplink", "802.1Q trunk; VLAN 30 allowed"), ("MAC learning", "Training laptops learned on expected access ports"), ("Access-layer change", "None required")),
                _panel("gateway", "Layer 3 gateway", ("Vlan30", "10.40.30.1/24; up/up"), ("Connected route", "10.40.30.0/24 present"), ("Other SVIs", "Up/up"), ("DHCP helper", "Not configured on Vlan30")),
                _panel("dhcp", "Central DHCP service", ("Server", "10.40.0.25 reachable from core"), ("Service", "Running"), ("VLAN 30 scope", "10.40.30.50–10.40.30.199; 0 active leases"), ("Other scopes", "Issuing leases normally")),
                _panel("change", "Approved change", ("Change", "Training VLAN 30 added yesterday"), ("Implementation", "VLAN, trunk, SVI, and scope recorded"), ("Relay step", "No evidence recorded"), ("Owner", "Network Operations")),
            ],
            "verification": _verification("VLAN 30 service-path verification", "The approved relay correction is simulated after the server verifies the plan.", ("Vlan30 helper", "10.40.0.25 configured under approved change"), ("Client lease", "10.40.30.51/24; gateway 10.40.30.1"), ("Gateway", "Reachable"), ("Internal DNS", "Resolves"), ("Original resource", "Training portal opens")),
            "documentation_required": True,
            "reinforcement_scenarios": [
                _service_desk("inc2503", "INC2503", "Desk network after move", "Existing access-port and physical-scope case."),
                _service_desk("inc2504", "INC2504", "Department printer path", "Existing client-to-network-printer isolation case."),
            ],
            "network_simulator_labs": [
                {
                    "id": "dev-sw-act-23",
                    "label": "Exam 2: Access Ports",
                    "note": "Existing stateful access-port fault isolation. This optional reinforcement retains its own hints, grading, and progress.",
                }
            ],
        },
        "questions": [
            _question("scope", "What scope is supported by the evidence?", (("server", "The DHCP server is down for every subnet"), ("client", "One laptop adapter failed"), ("vlan", "Lease delivery fails only for the new VLAN 30"), ("dns", "DNS alone is failing")), "vlan", "Multiple VLAN 30 clients use APIPA while existing scopes lease normally."),
            _question("fault", "Where is the most likely fault?", (("relay", "The VLAN 30 SVI is missing its DHCP relay/helper"), ("trunk", "VLAN 30 is absent from the trunk"), ("route", "The VLAN 30 connected route is absent"), ("scope", "The VLAN 30 DHCP scope does not exist")), "relay", "The access and routed interfaces are present and the scope is healthy, but broadcasts need relay to reach the central server."),
            _question("action", "Choose the safe correction and verification plan.", (("static", "Assign unmanaged static addresses to every laptop"), ("relay", "Have Network Operations add the documented helper to Vlan30 under the approved change, renew a lease, then test gateway, DNS, and the original resource"), ("broad", "Change helpers on every SVI"), ("restart", "Restart the central DHCP service during business hours")), "relay", "The scoped relay change addresses the missing path and proves service from lease through application."),
        ],
    },
    12: {
        "lab_id": 11,
        "role": "prove",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 30,
        "title": "Make the Safe Network Admin Decision",
        "description": "Independently evaluate a risky shared-network change, verify intended access, and hand off what exceeds junior authority.",
        "setup_instructions": "Review the access request, current evidence, and change scope. Do not weaken a broad control to make one test pass. Choose a safe response, verify the intended path, and prepare a concise escalation.",
        "workbench": {
            "title": "Secure network administration prove case",
            "domain": "secure_network",
            "guidance_level": "prove",
            "complaint": "A vendor support session cannot reach the maintenance portal after last night's approved restriction change.",
            "required_inspections": ["request", "acl", "logs", "change"],
            "panels": [
                _panel("request", "Access request", ("Application", "Maintenance portal TCP 443"), ("Approved source", "Vendor jump host 198.51.100.42/32"), ("Window", "10:00–12:00 UTC today"), ("Requested shortcut", "Allow Any to portal until testing finishes")),
                _panel("acl", "Effective edge policy", ("Permit", "203.0.113.64/27 → portal TCP 443"), ("Vendor host", "198.51.100.42 is outside permitted source"), ("Default", "Deny and log"), ("Other services", "No change indicated")),
                _panel("logs", "Denied-flow evidence", ("Source", "198.51.100.42"), ("Destination", "10.40.50.20:443"), ("Disposition", "Denied by EDGE-IN rule 120"), ("Portal health", "Healthy from internal support subnet")),
                _panel("change", "Change control", ("CHG", "CHG-4821 approved source restriction"), ("Implementation error", "Vendor /32 omitted from documented permit"), ("Rollback", "Restore last approved ACL version"), ("Owner", "Network Security; technician has read-only access")),
            ],
            "verification": _verification("Authorized access verification", "The owner-scoped correction is simulated only after the exact plan passes verification.", ("Effective permit", "198.51.100.42/32 → 10.40.50.20 TCP 443 for approved window"), ("Broad exposure", "No Any-source permit"), ("Vendor test", "Portal TLS connection succeeds"), ("Unrelated ports", "Remain denied"), ("Change record", "Owner update and expiry/removal recorded")),
            "documentation_required": True,
            "additional_note_fields": [{"id": "handoff", "label": "Handoff / escalation", "placeholder": "Name the owner, risk avoided, evidence, approved scope, and follow-up."}],
        },
        "questions": [
            _question("risk", "Which proposed action is unsafe?", (("rollback", "Ask the owner to compare against the approved change"), ("any", "Allow Any source to the portal until the vendor finishes"), ("preserve", "Preserve the deny log and effective rule"), ("verify", "Test only the intended port and source")), "any", "A broad temporary permit exceeds the approved source and creates unnecessary exposure."),
            _question("cause", "What best explains the failure without overclaiming?", (("portal", "The portal application is down"), ("vendor", "The vendor host is infected"), ("identity", "The vendor password expired"), ("scope", "The approved vendor /32 is absent from the effective permit after CHG-4821")), "scope", "The deny log and effective rule show a source-scope omission while internal portal health remains good."),
            _question("handoff", "What is the correct junior-scope response?", (("owner", "Escalate to Network Security with CHG-4821, the denied five-tuple, and the exact approved /32; request a time-bounded scoped correction and post-change tests"), ("edit", "Edit the shared ACL despite read-only authority"), ("telnet", "Enable an unencrypted management path"), ("disable", "Remove the default deny")), "owner", "The handoff preserves change control and gives the owner exact evidence and verification scope."),
        ],
    },
    18: {
        "lab_id": 16,
        "role": "practice",
        "lab_type": "structured_evidence_case",
        "difficulty": 1,
        "estimated_minutes": 30,
        "title": "Investigate the Linux Host",
        "description": "Navigate a small deterministic filesystem and interpret ownership, permissions, groups, processes, and basic network state.",
        "setup_instructions": "Use the guided Linux terminal to locate the service log, inspect its mode and ownership, compare the support account's groups, and choose the least-privilege resolution.",
        "workbench": {
            "title": "Linux fundamentals guided case",
            "domain": "linux_host",
            "guidance_level": "practice",
            "complaint": "A new support account can sign in to the application host but cannot read the orders service log needed for a ticket.",
            "guidance": "Start by locating yourself and the log path. Read owner, group, and mode; then compare the account's group membership. Basic process and network commands are available for orientation but may not explain this access symptom.",
            "required_inspections": ["terminal:path", "terminal:permissions", "terminal:identity", "access"],
            "panels": [
                _panel("access", "Access request", ("User", "samira"), ("Role", "New service-desk support technician"), ("Approved need", "Read orders service logs"), ("Write/change need", "None")),
                _panel("host", "Host record", ("Host", "lnx-app-18"), ("Service", "nexus-orders running"), ("Log path", "/var/log/nexus/orders.log"), ("Account login", "Successful")),
            ],
            "terminal_profile": _terminal_profile(
                "linux-log-access-fundamentals",
                "Guided Linux host on lnx-app-18 with a small simulated filesystem and deterministic account state.",
                ("Current directory", "Directory listing and navigation", "File ownership and permissions", "User and group membership", "Processes", "Basic network state"),
                [
                    _command("pwd", "terminal:path", "/home/samira"),
                    _command("ls", None, "notes  tickets"),
                    _command("ls -l", None, "drwxr-x--- 2 samira support 4096 Aug 24 08:10 notes", "drwx------ 2 samira samira  4096 Aug 24 08:12 tickets"),
                    _command("cd /var/log/nexus", None, "Directory changed to /var/log/nexus."),
                    _command("ls -l /var/log/nexus/orders.log", "terminal:permissions", "-rw-r----- nexusapp support 18432 Aug 24 08:17 /var/log/nexus/orders.log", aliases=("ls -l orders.log",)),
                    _command("cat /var/log/nexus/orders.log", None, "cat: /var/log/nexus/orders.log: Permission denied", aliases=("cat orders.log",)),
                    _command("id samira", "terminal:identity", "uid=1104(samira) gid=1104(samira) groups=1104(samira),100(users)", aliases=("id",)),
                    _command("getent group support", None, "support:x:1042:alex,jordan"),
                    _command("ps -ef", None, "UID          PID  PPID  C STIME TTY          TIME CMD", "nexusapp    1842     1  0 07:55 ?        00:00:02 /usr/local/bin/nexus-orders", "samira      2310  2309  0 08:14 pts/0    00:00:00 -bash", aliases=("ps", "ps aux")),
                    _command("ip addr", None, "2: ens18: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP", "    inet 10.40.18.16/24 brd 10.40.18.255 scope global ens18", aliases=("ip a",)),
                    _command("ip route", None, "default via 10.40.18.1 dev ens18", "10.40.18.0/24 dev ens18 proto kernel scope link src 10.40.18.16", aliases=("ip r",)),
                ],
                "samira@lnx-app-18:~$ ",
            ),
            "verification": _verification("Least-privilege access verification", "A simulated approved group-membership update creates the after-state.", ("samira groups", "samira, users, support after approval and fresh session"), ("Log mode", "-rw-r----- unchanged"), ("Log owner/group", "nexusapp:support unchanged"), ("Read test", "orders.log opens read-only"), ("Write test", "Still denied")),
            "documentation_required": True,
        },
        "questions": [
            _question("permission", "Who can currently read orders.log?", (("owner", "Only nexusapp"), ("group", "nexusapp and members of support"), ("all", "Every local user"), ("root", "Only root regardless of mode")), "group", "Owner has rw, group has r, and others have no access."),
            _question("cause", "Why is samira denied?", (("service", "The orders service is stopped"), ("network", "The host has no default route"), ("mode", "The file has no group-read bit"), ("membership", "The approved log group can read the file, but samira is not a member")), "membership", "The mode and group are already least-privilege compatible; the account lacks that approved group."),
            _question("action", "Choose the safe resolution.", (("group", "After approval, add samira to the existing support group, establish a fresh session, and verify read-only access"), ("777", "Run chmod 777 on the log"), ("root", "Give samira permanent root access"), ("owner", "Change the log owner to samira")), "group", "Approved group access preserves the existing service ownership and avoids broad write permission."),
        ],
    },
    19: {
        "lab_id": 17,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 35,
        "title": "Diagnose the Linux Service",
        "description": "Choose Linux service, journal, listener, process, route, DNS, and application evidence to diagnose a symptom-driven outage.",
        "setup_instructions": "The command order is not supplied. Choose tools that separate service state, port ownership, host networking, and application reachability; then select a controlled correction and verify it.",
        "workbench": {
            "title": "Linux service troubleshoot",
            "domain": "linux_service",
            "guidance_level": "troubleshoot",
            "complaint": "The branch status page stopped responding after this morning's reboot, although the Linux host itself is reachable.",
            "guidance": "Choose evidence categories that test service state, recent errors, listener ownership, network state, and application response; there is no required exact order.",
            "required_inspections": ["terminal:service", "terminal:journal", "terminal:listener", "scope"],
            "panels": [
                _panel("scope", "Incident scope", ("Host", "lnx-web-19 reachable by monitoring"), ("Application", "Branch status page unavailable"), ("Started", "Immediately after 07:00 reboot"), ("Other host services", "SSH and monitoring healthy")),
                _panel("change", "Change record", ("Yesterday", "Developer ran a temporary preview server for testing"), ("Expected expiry", "Before reboot"), ("Service owner", "Web Operations"), ("Production listener", "nginx on TCP 80")),
            ],
            "terminal_profile": _terminal_profile(
                "linux-nginx-port-conflict",
                "Focused Linux service case on lnx-web-19. Commands reveal only this incident's deterministic state.",
                ("Service state", "Recent service logs", "Listening ports and process ownership", "Host address and route", "DNS and application reachability"),
                [
                    _command("systemctl status nginx", "terminal:service", "× nginx.service - A high performance web server", "     Loaded: loaded (/lib/systemd/system/nginx.service; enabled)", "     Active: failed (Result: exit-code) since Mon 2026-08-24 07:00:14 UTC", "    Process: 812 ExecStartPre=/usr/sbin/nginx -t (code=exited, status=0/SUCCESS)", "    Process: 819 ExecStart=/usr/sbin/nginx (code=exited, status=1/FAILURE)", aliases=("systemctl status nginx --no-pager",)),
                    _command("journalctl -u nginx -n 20", "terminal:journal", "Aug 24 07:00:14 lnx-web-19 nginx[819]: bind() to 0.0.0.0:80 failed (98: Address already in use)", "Aug 24 07:00:14 lnx-web-19 nginx[819]: still could not bind()", "Aug 24 07:00:14 lnx-web-19 systemd[1]: nginx.service: Failed with result 'exit-code'.", aliases=("journalctl -u nginx", "journalctl -u nginx -e")),
                    _command("ss -lntp", "terminal:listener", "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process", "LISTEN 0      5            0.0.0.0:80        0.0.0.0:*     users:((\"python3\",pid=744,fd=3))", "LISTEN 0      128          0.0.0.0:22        0.0.0.0:*     users:((\"sshd\",pid=611,fd=3))", aliases=("ss -ltnp", "ss -lnt")),
                    _command("ps -fp 744", None, "UID       PID  PPID  C STIME TTY      TIME CMD", "devpreview 744     1  0 06:59 ?    00:00:00 python3 -m http.server 80 --directory /srv/preview", aliases=("ps -ef", "ps aux")),
                    _command("ip addr", None, "2: ens18: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP", "    inet 10.40.19.20/24 brd 10.40.19.255 scope global ens18", aliases=("ip a",)),
                    _command("ip route", None, "default via 10.40.19.1 dev ens18", "10.40.19.0/24 dev ens18 proto kernel scope link src 10.40.19.20", aliases=("ip r",)),
                    _command("dig status.branch.nexus.internal", None, ";; ANSWER SECTION:", "status.branch.nexus.internal. 300 IN A 10.40.19.20", aliases=("nslookup status.branch.nexus.internal",)),
                    _command("ping 10.40.19.1", None, "64 bytes from 10.40.19.1: icmp_seq=1 ttl=255 time=0.424 ms"),
                    _command("curl -I http://127.0.0.1", None, "HTTP/1.0 200 OK", "Server: SimpleHTTP/0.6 Python/3.12.3", aliases=("curl http://127.0.0.1",)),
                ],
                "support@lnx-web-19:~$ ",
            ),
            "verification": _verification("Production service verification", "The after-state follows the approved removal of the stale preview process and controlled nginx start.", ("Port 80 owner", "nginx master process"), ("nginx", "active (running)"), ("Local HTTP", "200 OK; Server: nginx"), ("Remote status page", "Loads from branch client"), ("Monitoring", "Healthy for 10 minutes")),
            "documentation_required": True,
        },
        "questions": [
            _question("layer", "Which layer is failing?", (("network", "Host addressing and routing"), ("dns", "Internal DNS"), ("service", "Production web-service startup and listener ownership"), ("firewall", "An upstream firewall")), "service", "The host and DNS paths are healthy; nginx failed because another process owns its required port."),
            _question("cause", "What is the most defensible cause?", (("config", "nginx syntax is invalid"), ("preview", "A stale preview process started at boot and bound TCP 80 before nginx"), ("disk", "The root filesystem is full"), ("ssh", "SSH is stopped")), "preview", "The journal reports address-in-use and ss maps TCP 80 to the preview process."),
            _question("action", "Choose the safe response.", (("reboot", "Reboot repeatedly until nginx wins the race"), ("port", "Move production nginx to an undocumented port"), ("killall", "Kill every Python process"), ("controlled", "Confirm the preview process is unauthorized/stale with its owner, disable only its boot path, stop it, start nginx, then verify listener, local HTTP, remote HTTP, and monitoring")), "controlled", "The scoped response preserves ownership and proves the production service rather than masking the conflict."),
        ],
    },
    20: {
        "lab_id": 18,
        "role": "prove",
        "lab_type": "structured_evidence_case",
        "difficulty": 3,
        "estimated_minutes": 40,
        "title": "Triage the Linux Production Alert",
        "description": "Independently investigate a Linux application outage across service, capacity, logs, listener, process, configuration, and firewall evidence.",
        "setup_instructions": "Start only from the symptom and environment. Choose commands, determine the actual issue among plausible signals, select a safe response within junior scope, verify recovery, and prepare the owner handoff.",
        "workbench": {
            "title": "Linux production prove case",
            "domain": "linux_production",
            "guidance_level": "prove",
            "complaint": "The web application is unavailable and monitoring reports host pressure on lnx-prod-20.",
            "required_inspections": ["terminal:capacity", "terminal:journal", "terminal:service", "monitoring"],
            "panels": [
                _panel("monitoring", "Monitoring", ("Application", "HTTP health check returns 503"), ("Host", "Reachable"), ("Pressure", "Root filesystem critical"), ("CPU", "22%"), ("Memory", "61%")),
                _panel("ownership", "Operational boundaries", ("Technician", "May gather evidence and run approved log-retention procedure"), ("Application owner", "Owns logging-level correction"), ("Change window", "Emergency capacity response approved"), ("Data", "No database corruption alert")),
                _panel("recent", "Recent change", ("Yesterday", "Debug logging enabled for checkout investigation"), ("Expiry", "Should have ended at 18:00"), ("Rollback", "Return checkout logger to INFO"), ("Owner", "Application Operations")),
            ],
            "terminal_profile": _terminal_profile(
                "linux-production-disk-pressure",
                "Focused Linux production case on lnx-prod-20. The simulator exposes incident state only and never executes host commands.",
                ("Service and application state", "Filesystem and path usage", "Relevant logs", "Listener/process state"),
                [
                    _command("df -h", "terminal:capacity", "Filesystem      Size  Used Avail Use% Mounted on", "/dev/mapper/os-root   20G   20G     0 100% /", "/dev/sdb1             80G   34G   42G  45% /srv/data"),
                    _command("du -sh /var/*", None, "12M     /var/cache", "1.2G    /var/lib", "17G     /var/log", "84M     /var/tmp"),
                    _command("du -sh /var/log/*", None, "16G     /var/log/nexus-checkout", "420M    /var/log/journal", "188M    /var/log/nginx", aliases=("du -sh /var/log/* | sort -h",)),
                    _command("journalctl -u nexus-web -n 30", "terminal:journal", "Aug 24 08:02:14 lnx-prod-20 nexus-web[1288]: checkout request failed: OSError: [Errno 28] No space left on device", "Aug 24 08:02:14 lnx-prod-20 nexus-web[1288]: health endpoint degraded: write-dependent check failed", aliases=("journalctl -u nexus-web", "journalctl -u nexus-web -e")),
                    _command("systemctl status nexus-web", "terminal:service", "● nexus-web.service - Nexus Web Application", "     Loaded: loaded (/etc/systemd/system/nexus-web.service; enabled)", "     Active: active (running) since Mon 2026-08-24 06:40:02 UTC", "   Main PID: 1288 (nexus-web)", aliases=("systemctl status nexus-web --no-pager",)),
                    _command("ss -lntp", None, "State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process", "LISTEN 0      511          0.0.0.0:443       0.0.0.0:*     users:((\"nginx\",pid=1210,fd=6))", "LISTEN 0      128        127.0.0.1:8080      0.0.0.0:*     users:((\"nexus-web\",pid=1288,fd=9))", aliases=("ss -ltnp",)),
                    _command("curl -sk -I https://127.0.0.1/health", None, "HTTP/1.1 503 Service Unavailable", "Server: nginx"),
                    _command("nginx -t", None, "nginx: the configuration file /etc/nginx/nginx.conf syntax is ok", "nginx: configuration file /etc/nginx/nginx.conf test is successful"),
                    _command("ufw status", None, "Status: active", "To                         Action      From", "443/tcp                    ALLOW       10.40.0.0/16", "22/tcp                     ALLOW       10.40.99.0/24"),
                    _command("ps -ef", None, "root      1210     1  0 06:39 ? 00:00:00 nginx: master process /usr/sbin/nginx", "nexusapp  1288     1  1 06:40 ? 00:01:18 /opt/nexus/bin/nexus-web", aliases=("ps aux",)),
                ],
                "support@lnx-prod-20:~$ ",
            ),
            "verification": _verification("Production recovery verification", "The simulated outcome follows the approved retention cleanup and logging correction.", ("Root filesystem", "63% used with 7.1 GB free"), ("Checkout logger", "INFO; debug override removed by owner"), ("nexus-web", "active (running)"), ("Health endpoint", "HTTP 200"), ("Remote application", "Checkout page loads and a test transaction succeeds"), ("Monitoring", "Healthy through 15-minute observation")),
            "documentation_required": True,
            "additional_note_fields": [{"id": "handoff", "label": "Handoff / escalation", "placeholder": "Record owner follow-up, prevention, and any work outside technician authority."}],
        },
        "questions": [
            _question("cause", "Which finding explains the outage?", (("firewall", "UFW blocks HTTPS"), ("config", "nginx configuration syntax is invalid"), ("capacity", "Runaway checkout debug logs filled the root filesystem and write-dependent health checks fail"), ("process", "The application process is stopped")), "capacity", "Disk and journal evidence align with the alert; the services, listeners, configuration, and firewall path are otherwise present."),
            _question("response", "What is the safest immediate response?", (("delete", "Delete random files under /var"), ("approved", "Preserve evidence, use the approved retention/rotation procedure on the identified log set, coordinate removal of the stale debug setting, and watch free space during recovery"), ("chmod", "Grant everyone write access to /var/log"), ("firewall", "Open every inbound firewall port")), "approved", "The response controls growth, follows retention authority, and avoids destructive guesses."),
            _question("proof", "What proves recovery before handoff?", (("df", "Free space increased"), ("service", "systemctl still says active"), ("curl", "One local HTTP request returns 200"), ("layered", "Capacity is stable, logging is corrected, local health is 200, a remote transaction works, and monitoring remains healthy")), "layered", "Production proof covers cause, service, user outcome, and observation rather than a single green signal."),
        ],
    },
    22: {
        "lab_id": 20,
        "role": "troubleshoot",
        "lab_type": "structured_evidence_case",
        "difficulty": 2,
        "estimated_minutes": 30,
        "title": "Diagnose the Azure Access Path",
        "description": "Inspect simulated Azure resource, network, health, activity, and access evidence to route an unreachable-application incident.",
        "setup_instructions": "No Azure tenant is required. Open only the evidence you need, separate control plane, guest OS, network, and identity layers, select the narrow next action or escalation, verify the original application path, and document the result.",
        "workbench": {
            "title": "Azure VM access troubleshoot",
            "domain": "azure",
            "guidance_level": "troubleshoot",
            "complaint": "Azure reports the VM as running, but support cannot reach the inventory application.",
            "guidance": "Compare resource state and boot health with endpoint addressing, effective NSG behavior, recent changes, and your own access scope before choosing a guest action.",
            "required_inspections": ["resource", "network", "health", "change", "identity"],
            "panels": [
                _panel("resource", "Resource", ("Tenant", "Nexus Training"), ("Subscription", "Nexus-Operations-Prod"), ("Resource group", "rg-inventory-prod"), ("Region", "UK South"), ("VM", "vm-inventory-22 — Running")),
                _panel("network", "Network", ("Private IP", "10.72.4.22 (static)"), ("Public IP", "None"), ("Approved support path", "Jump subnet 10.72.99.0/24 → TCP 443"), ("Effective NSG", "Deny 10.72.99.0/24 → TCP 443 at priority 210"), ("NIC/route", "Provisioned; VNet route effective")),
                _panel("health", "Health", ("Resource health", "Available"), ("Boot diagnostics", "Ubuntu login prompt; no boot error"), ("Guest agent", "Ready"), ("Application monitor", "Healthy locally at 10.72.4.22:443")),
                _panel("change", "Recent activity / change", ("09:02", "NSG rule Restrict-Inventory-HTTPS updated"), ("Change", "Source changed from 10.72.99.0/24 to 10.72.98.0/24"), ("Actor", "Cloud Network Automation"), ("Ticket", "CHG-4890 intended no support-path interruption")),
                _panel("identity", "Identity / access", ("Signed-in technician", "Cloud Support Reader"), ("Role result", "Read VM, NIC, NSG, health, and activity logs"), ("Write result", "Cannot modify NSG"), ("Owner", "Cloud Network Operations")),
            ],
            "verification": _verification("Azure application-path verification", "The simulated after-state follows the owner-applied, change-controlled source correction.", ("VM state", "Running"), ("Resource health", "Available"), ("Effective NSG", "Allow 10.72.99.0/24 → 10.72.4.22 TCP 443; deny remains for other sources"), ("Jump-host test", "TLS connection succeeds"), ("Application", "Inventory page loads"), ("Activity log", "CHG-4890 correction recorded")),
            "documentation_required": True,
        },
        "questions": [
            _question("layer", "Which layer best fits the evidence?", (("guest", "Guest OS or application failure"), ("network", "Azure network control plane policy on the effective NSG path"), ("identity", "Application-user identity failure"), ("platform", "Azure host-platform failure")), "network", "The VM, guest, and local application are healthy while the effective NSG denies the approved support subnet."),
            _question("evidence", "Which evidence most directly explains the timing?", (("state", "VM state is Running"), ("ip", "The VM has a static private IP"), ("role", "The technician has Reader access"), ("change", "The 09:02 activity changed the allowed source away from the documented jump subnet")), "change", "The recent rule update matches the start of the access failure and the effective deny."),
            _question("action", "Choose the correct next action at this technician's scope.", (("guest", "Restart the guest and reinstall the application"), ("any", "Ask for TCP 443 from Any source"), ("escalate", "Escalate to Cloud Network Operations with CHG-4890, the effective deny, approved 10.72.99.0/24 scope, and a narrow post-change TLS/application test"), ("role", "Grant yourself NSG Contributor")), "escalate", "Reader access is sufficient to diagnose but not change the NSG; the evidence supports a narrow owner-controlled correction."),
        ],
    },
}


WEEK_21_OPTIONAL_VIDEO_IDS = {"54", "55", "56"}


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


def _week_21_video_rows(db: Session) -> list[TrainingWeekActivity]:
    week = db.query(TrainingWeek).filter_by(week_number=21).first()
    if week is None:
        return []
    return (
        db.query(TrainingWeekActivity)
        .filter(
            TrainingWeekActivity.training_week_id == week.id,
            TrainingWeekActivity.activity_type == "video",
            TrainingWeekActivity.content_ref.in_(WEEK_21_OPTIONAL_VIDEO_IDS),
        )
        .all()
    )


def sync_network_linux_cloud_practical_upgrade(db: Session) -> dict:
    """Update only existing Phase 4C.2 targets and Week 21 flags."""
    if not inspect(db.get_bind()).has_table(TrainingWeekActivity.__tablename__):
        return {"updated_templates": 0, "updated_activities": 0, "skipped": True, "reason": "migration_not_applied"}

    targets = {
        week_number: (*_target_rows(db, week_number, case["lab_id"]), case)
        for week_number, case in NETWORK_LINUX_CLOUD_CASES.items()
    }
    missing_targets = [
        {"week_number": week_number, "lab_id": case["lab_id"]}
        for week_number, (lab, activity, case) in targets.items()
        if lab is None or activity is None
    ]
    cloud_rows = _week_21_video_rows(db)
    if missing_targets or len(cloud_rows) != len(WEEK_21_OPTIONAL_VIDEO_IDS):
        if len(missing_targets) == len(targets) and not cloud_rows:
            return {
                "updated_templates": 0,
                "updated_activities": 0,
                "missing_targets": missing_targets,
                "skipped": True,
                "reason": "curriculum_not_seeded",
            }
        raise RuntimeError(
            "Phase 4C.2 target set is incomplete; refusing a partial upgrade: "
            f"labs={missing_targets}, week_21_videos={sorted(row.content_ref for row in cloud_rows)}"
        )

    result = {"updated_templates": 0, "updated_activities": 0, "optionalized_videos": 0, "skipped": False}
    for week_number, (lab, activity, case) in targets.items():
        values = {
            "title": case["title"],
            "description": case["description"],
            "lab_type": case["lab_type"],
            "week_number": week_number,
            "difficulty": case["difficulty"],
            "estimated_minutes": case["estimated_minutes"],
            "is_published": True,
            "environment_requirements": {},
            "setup_instructions": case["setup_instructions"],
            "success_criteria": {
                "evidence_case_workbench": deepcopy(case["workbench"]),
                "questions": deepcopy(case["questions"]),
            },
            "required_evidence": {},
            "hints": {},
        }
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

    for row in cloud_rows:
        if row.is_required:
            row.is_required = False
            result["updated_activities"] += 1
            result["optionalized_videos"] += 1

    db.commit()
    return result


def restore_pre_4c2_practical_labs(db: Session) -> dict:
    """Restore the exact 0059-owned content and Week 21 requirement flags."""
    from app.services.training_curriculum_seed import (
        WEEKS_11_14_QUALITY,
        WEEKS_15_18_QUALITY,
        WEEKS_19_22_QUALITY,
        WEEKS_7_10_QUALITY,
    )

    legacy_specs = {
        8: deepcopy(WEEKS_7_10_QUALITY[8]["lab"]),
        11: deepcopy(WEEKS_11_14_QUALITY[11]["lab"]),
        12: deepcopy(WEEKS_11_14_QUALITY[12]["lab"]),
        18: deepcopy(WEEKS_15_18_QUALITY[18]["lab"]),
        19: deepcopy(WEEKS_19_22_QUALITY[19]["lab"]),
        20: deepcopy(WEEKS_19_22_QUALITY[20]["lab"]),
        22: deepcopy(WEEKS_19_22_QUALITY[22]["lab"]),
    }
    targets = {
        week_number: (*_target_rows(db, week_number, case["lab_id"]), case)
        for week_number, case in NETWORK_LINUX_CLOUD_CASES.items()
    }
    missing_targets = [
        {"week_number": week_number, "lab_id": case["lab_id"]}
        for week_number, (lab, activity, case) in targets.items()
        if lab is None or activity is None
    ]
    cloud_rows = _week_21_video_rows(db)
    if missing_targets or len(cloud_rows) != len(WEEK_21_OPTIONAL_VIDEO_IDS):
        if len(missing_targets) == len(targets) and not cloud_rows:
            return {"restored": 0, "skipped": True, "reason": "curriculum_not_seeded"}
        raise RuntimeError(
            "Phase 4C.2 target set is incomplete; refusing a partial downgrade: "
            f"labs={missing_targets}, week_21_videos={sorted(row.content_ref for row in cloud_rows)}"
        )

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

    for row in cloud_rows:
        row.is_required = True
    db.commit()
    return {"restored": restored, "required_videos": len(cloud_rows)}
