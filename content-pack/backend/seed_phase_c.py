"""Phase C (Weeks 9-12) curriculum content — Network Support.

Role target: Network Support Technician (Gate 3, end of Week 12).
Same structured-seed pattern as Phase A/B. Idempotent.

Infrastructure honesty: CLI packs (meet-the-cli, network-foundations,
learn-switching) are fully client-side and ship now. Physical Catalyst 3650
activities are optional and always have a Packet Tracer / CLI-lab fallback —
NO Gate 3 requirement depends on physical hardware or the Proxmox pipeline.
Cisco Packet Tracer is free with a Cisco Skills for All account and is the
standing substitute for every switch activity.
"""

from seed_phase_a import ANCHORS, NOTES_TEMPLATE, _q

MODULES_C = [
    {
        "code": "MOD-009",
        "title": "Addressing and Packet Flow",
        "description": "IPv4, practical subnetting, ARP, gateway reasoning, MAC learning. Week 9.",
        "target_role": "Network Support Technician",
        "difficulty_band": 3,
        "estimated_hours": 16,
        "module_order": 10,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "IPv4 Addressing You Can Reason With",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "An IPv4 address is two parts: NETWORK and HOST, split by the subnet mask. Everything "
                    "in networking troubleshooting comes back to one question: are these two addresses on "
                    "the SAME network or not? Same network → they talk directly (via ARP + switch). "
                    "Different network → they must go through a router (the default gateway).\n\n"
                    "READING A MASK PRACTICALLY: /24 = 255.255.255.0 = first three octets are the network, "
                    "last octet is hosts (254 usable). /25 = 255.255.255.128 = splits that last octet in "
                    "half (two networks of 126 hosts). You do NOT need to convert binary in your head for "
                    "junior work — you need to answer 'same network?' and 'is this a valid host address or "
                    "the network/broadcast address?'\n\n"
                    "PRIVATE RANGES you'll see daily: 10.0.0.0/8, 172.16-31.0.0/12, 192.168.0.0/16. "
                    "169.254.x.x is APIPA (DHCP failed — you know this from Week 8). Public vs private and "
                    "why NAT exists is Week 11.\n\n"
                    "THE TROUBLESHOOTING PAYOFF: '192.168.1.50/24 with gateway 192.168.2.1' can NEVER work "
                    "— the gateway isn't on the host's network, so the host can't reach it to leave. You "
                    "spotted this in Week 8's triage tree; now you understand WHY. A wrong mask ('/16 "
                    "instead of /24') makes a host think remote machines are local, so it never sends "
                    "their traffic to the router — packets vanish.\n\n"
                    "COMMON MISTAKES: assuming /24 everywhere (VLANs and point-to-point links use others); "
                    "confusing the network address (.0) and broadcast (.255) for usable host addresses; "
                    "ignoring the mask because 'the IP looks right'."
                ),
                "outcomes": [
                    "Given an IP and mask, state the network, usable host range, and broadcast address",
                    "Determine whether two addresses are on the same network and therefore need a router",
                    "Diagnose wrong-mask and wrong-gateway misconfigurations by inspection",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Practical Subnetting for Support",
                "lesson_order": 2,
                "estimated_minutes": 120,
                "summary": (
                    "Junior subnetting is not exam arithmetic under time pressure — it's answering real "
                    "questions: 'is this host in the right subnet?', 'how many hosts fit here?', 'which "
                    "subnet is this address in?'.\n\n"
                    "THE FOUR NUMBERS PER MASK you actually use: hosts-per-subnet, block size (the "
                    "increment between subnets), and from those, each subnet's network and broadcast. "
                    "Example /26 (255.255.255.192): block size 64 → subnets .0, .64, .128, .192; each has "
                    "62 usable hosts. An address of .70 lives in the .64 subnet (network .64, broadcast "
                    ".127, gateway usually .65). You can answer 'is .70 reachable from .10 on this /26?' — "
                    "no, different subnets, needs routing.\n\n"
                    "THE METHOD (no binary gymnastics): from the mask, get the block size in the "
                    "'interesting octet' (256 − mask octet). Count up by that block to bracket the "
                    "address. Network = start of the bracket; broadcast = next bracket − 1; hosts = "
                    "in between.\n\n"
                    "WHY A JUNIOR NEEDS THIS: reading whether a static IP a colleague set is valid; "
                    "understanding VLAN-to-subnet mapping (Week 10); explaining why a device with the "
                    "wrong mask 'works locally but can't reach the server'.\n\n"
                    "PRACTICE: use the CLI labs' addressing drills and a subnet worksheet; you are NOT "
                    "expected to design a VLSM scheme — that's later, separate CCNA study.\n\n"
                    "COMMON MISTAKES: off-by-one on broadcast; forgetting network+broadcast aren't usable; "
                    "panicking at masks that aren't /24."
                ),
                "outcomes": [
                    "Compute block size, network, broadcast, and usable host range for common masks (/25-/30)",
                    "Determine which subnet an address belongs to and whether two hosts can talk without a router",
                    "Validate whether a manually-assigned IP/mask/gateway is correct for its subnet",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "ARP, MAC Learning, and Packet Flow",
                "lesson_order": 3,
                "estimated_minutes": 90,
                "summary": (
                    "Follow one packet and networking stops being magic. Host A (192.168.1.10) wants to "
                    "reach Host B (192.168.1.20), same /24 subnet:\n"
                    "1. A checks: same network? Yes. So talk directly — but A needs B's MAC address.\n"
                    "2. ARP: A broadcasts 'who has 192.168.1.20?' B replies with its MAC. A caches it "
                    "(arp -a shows the table).\n"
                    "3. A sends the frame to B's MAC. The SWITCH learns which port A is on (source MAC), "
                    "and forwards toward B's port (from its MAC table — show mac address-table).\n\n"
                    "NOW cross-network: A (192.168.1.10) to server (10.0.0.5), different networks:\n"
                    "1. A checks: same network? No. So send to the DEFAULT GATEWAY.\n"
                    "2. A ARPs for the GATEWAY's MAC (not the server's — A can't reach the server "
                    "directly). Frame goes to the gateway; the router takes it from there.\n"
                    "This is why a wrong gateway or a gateway not on your subnet breaks ALL remote traffic "
                    "but local traffic still works — the exact signature you'll diagnose.\n\n"
                    "SWITCH MAC LEARNING: switches build their MAC table by watching SOURCE addresses on "
                    "each port. Unknown destination → flood out all ports (that's normal, not broken). "
                    "You saw this in the CLI labs' simulated switch; show mac address-table on real gear "
                    "shows the same learning.\n\n"
                    "TROUBLESHOOTING PAYOFF: 'can ping local but not remote' = gateway/routing. 'can't "
                    "ping anything including local' = layer 1/2 (cable, port, VLAN). 'ping by IP works, "
                    "name fails' = DNS. You now have a layer for every symptom.\n\n"
                    "COMMON MISTAKES: expecting a host to ARP for a remote IP (it ARPs for the gateway); "
                    "thinking switch flooding is a fault; ignoring a stale ARP entry after an IP change."
                ),
                "outcomes": [
                    "Trace a packet's path for same-subnet vs cross-subnet destinations, including ARP targets",
                    "Explain how a switch learns MACs and why unknown-destination flooding is normal",
                    "Map 'local works, remote fails' and 'nothing works' symptoms to the correct layer",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-010",
        "title": "Switching, VLANs, and the CLI",
        "description": "Cisco CLI modes, show commands, interface status, VLANs, access ports, saving config. Week 10.",
        "target_role": "Network Support Technician",
        "difficulty_band": 3,
        "estimated_hours": 16,
        "module_order": 11,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Cisco CLI Modes and Verification",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "The Cisco CLI has MODES, and knowing which one you're in prevents most beginner "
                    "damage:\n"
                    "- User EXEC (Switch>): look but barely touch.\n"
                    "- Privileged EXEC (Switch#): full show/diagnostic commands, and 'enable' gets you "
                    "here. This is where you VERIFY.\n"
                    "- Global config (Switch(config)#): 'configure terminal' — where you CHANGE things.\n"
                    "- Interface config (Switch(config-if)#): changes to one port.\n"
                    "The prompt tells you where you are. 'exit' backs out one level; 'end' or Ctrl-Z jumps "
                    "to privileged EXEC.\n\n"
                    "THE VERIFICATION COMMANDS (a junior lives in these — all read-only, all safe):\n"
                    "- show running-config — the live config (what IS)\n"
                    "- show ip interface brief — every port, its IP, and up/down status at a glance\n"
                    "- show interfaces status — port, VLAN, duplex, speed, and connected/notconnect\n"
                    "- show vlan brief — VLANs and which ports are in them\n"
                    "- show mac address-table — learned MACs per port/VLAN\n"
                    "- show interfaces <x> — errors, drops, counters for one port\n\n"
                    "SAVING CONFIG — the mistake that eats a night's work: the running-config is in RAM. "
                    "A reboot loses everything unless you 'copy running-config startup-config' (or "
                    "'write memory'). ALWAYS verify a change with a show command, THEN save. Teaching "
                    "yourself 'change → verify → save' now prevents 'I fixed it, rebooted, and it's broken "
                    "again' later.\n\n"
                    "PRACTICE: the meet-the-cli and learn-switching CLI packs drill exactly these modes "
                    "and commands in a safe simulator — no gear required.\n\n"
                    "COMMON MISTAKES: configuring in the wrong mode; forgetting to save; changing without "
                    "a show before AND after; using 'no' commands without understanding what they remove."
                ),
                "outcomes": [
                    "Identify and move between Cisco CLI modes using the prompt",
                    "Verify switch and interface state with the core show commands",
                    "Apply change → verify → save discipline and explain why unsaved config is lost on reboot",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "VLANs and Access Ports",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "A VLAN is a broadcast domain you create in software — a way to split one physical "
                    "switch into several logical networks. Ports in VLAN 10 can't talk directly to ports "
                    "in VLAN 20 (that needs routing, Week 11). VLANs usually map one-to-one to subnets: "
                    "VLAN 10 = 192.168.10.0/24, VLAN 20 = 192.168.20.0/24. This is why a device in the "
                    "wrong VLAN gets the wrong subnet's DHCP (or none) and 'can't reach anything'.\n\n"
                    "ACCESS PORT: a switch port assigned to ONE VLAN, for one end device (PC, printer, "
                    "phone). Configured with:\n"
                    "  interface gigabitEthernet 1/0/5\n"
                    "   switchport mode access\n"
                    "   switchport access vlan 10\n"
                    "Verify: show vlan brief (is the port listed under VLAN 10?), show interfaces status "
                    "(does the port show VLAN 10 and connected?).\n\n"
                    "THE #1 REAL TICKET: 'this desk has no network / wrong network after a move'. Cause: "
                    "the port is in the wrong VLAN (or defaulted to VLAN 1 after a change). Fix: assign "
                    "the correct access VLAN, verify with show vlan brief, save. You diagnosed the "
                    "physical version (dead port) in Week 8; this is the logical version.\n\n"
                    "VLAN 1 CAUTION: the default VLAN. Leaving user ports in VLAN 1, or using it for "
                    "management, is a security smell — real deployments move management off VLAN 1.\n\n"
                    "PRACTICE: learn-switching CLI pack builds and verifies VLAN/access-port config in the "
                    "simulator. Physical Catalyst optional; Packet Tracer is the fallback.\n\n"
                    "COMMON MISTAKES: assigning a VLAN that doesn't exist yet; forgetting switchport mode "
                    "access (leaving it dynamic); not verifying with show vlan brief; not saving."
                ),
                "outcomes": [
                    "Explain what a VLAN is and how VLAN-to-subnet mapping causes 'wrong network' symptoms",
                    "Configure and verify an access port in a specific VLAN",
                    "Diagnose and fix a port assigned to the wrong VLAN",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Interface Status and Basic Port Troubleshooting",
                "lesson_order": 3,
                "estimated_minutes": 75,
                "summary": (
                    "'show interfaces status' and 'show ip interface brief' turn port problems into "
                    "one-line diagnoses. The states you must read:\n"
                    "- connected / up-up: link is good.\n"
                    "- notconnect: no link — cable, dead device, wrong port, or speed/duplex mismatch. "
                    "This is layer 1.\n"
                    "- err-disabled: the switch SHUT the port for a violation (port security, BPDU guard, "
                    "flapping). It won't come back on its own — you must find the cause and "
                    "'shutdown / no shutdown' to recover, or fix the trigger.\n"
                    "- administratively down: someone ran 'shutdown' on the port. Fix: 'no shutdown'. A "
                    "surprisingly common 'the port is dead' cause.\n\n"
                    "THE PORT TRIAGE: is it up? (show interfaces status). If administratively down → no "
                    "shutdown. If err-disabled → why? (show interfaces <x>, logs) then recover. If "
                    "notconnect → layer 1: reseat cable, try a known-good cable, confirm the far-end "
                    "device is on. Check errors/counters (CRC errors, input errors) for cable/duplex "
                    "problems.\n\n"
                    "DUPLEX/SPEED MISMATCH: a classic slow/erratic link. show interfaces shows late "
                    "collisions or errors; both ends should auto-negotiate or be set to match.\n\n"
                    "PRACTICE: CLI labs cover reading interface states; the Week 12 break-fix has you "
                    "recover a shut/err-disabled port. Physical Catalyst optional; Packet Tracer fallback.\n\n"
                    "COMMON MISTAKES: 'no shutdown' on an err-disabled port without fixing the cause (it "
                    "re-disables); ignoring error counters; assuming notconnect is always a cable."
                ),
                "outcomes": [
                    "Read interface status (connected/notconnect/err-disabled/admin-down) and map each to a cause class",
                    "Recover an administratively-down port and correctly handle an err-disabled port",
                    "Use interface counters to spot cable and duplex problems",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]

MODULES_C += [
    {
        "code": "MOD-011",
        "title": "Trunks, Routing, and Network Services",
        "description": "Trunks, native VLAN, inter-VLAN routing concepts, static routes, DHCP relay, NAT/firewall/VPN/wireless awareness. Week 11.",
        "target_role": "Network Support Technician",
        "difficulty_band": 3,
        "estimated_hours": 16,
        "module_order": 12,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Trunks and the Native VLAN",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "An ACCESS port carries one VLAN for an end device. A TRUNK port carries MANY VLANs "
                    "between switches (or to a router/firewall). Trunks tag frames with their VLAN id "
                    "(802.1Q) so the other end knows which VLAN each frame belongs to.\n\n"
                    "  interface gigabitEthernet 1/0/24\n"
                    "   switchport mode trunk\n"
                    "   switchport trunk allowed vlan 10,20,30\n"
                    "Verify: show interfaces trunk (which port is trunking, which VLANs are allowed and "
                    "active).\n\n"
                    "THE NATIVE VLAN: one VLAN on a trunk travels UNtagged (the native VLAN, default "
                    "VLAN 1). Both ends of a trunk MUST agree on the native VLAN. A NATIVE VLAN MISMATCH "
                    "(one end native 1, other native 99) is a classic ticket: some traffic leaks between "
                    "VLANs, the switch logs the mismatch, and connectivity is weird-but-not-dead. show "
                    "interfaces trunk and the logs reveal it.\n\n"
                    "TRUNK MISMATCH generally: one end trunk, other end access → the VLANs beyond the "
                    "access VLAN can't cross. 'Users in VLAN 20 on switch B can't reach anything, but "
                    "VLAN 10 works' after a switch was added = allowed-VLAN list or a trunk that's really "
                    "an access port. Diagnose with show interfaces trunk on BOTH ends.\n\n"
                    "PRACTICE: learn-switching CLI pack includes trunk config/verify; Week 12 break-fix "
                    "includes a trunk mismatch. Packet Tracer fallback for multi-switch topologies.\n\n"
                    "COMMON MISTAKES: forgetting to allow a VLAN across the trunk; native VLAN mismatch; "
                    "one end access + one end trunk; not checking BOTH ends."
                ),
                "outcomes": [
                    "Explain access vs trunk ports and how 802.1Q tagging carries multiple VLANs",
                    "Configure and verify a trunk with an allowed-VLAN list",
                    "Diagnose native-VLAN and trunk/access mismatches from show interfaces trunk on both ends",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Inter-VLAN Routing and Static Routes",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "VLANs are separate networks; separate networks need a ROUTER to talk. That's "
                    "inter-VLAN routing. Two common shapes (concept-level for a junior — you assist, you "
                    "don't design):\n"
                    "- Router-on-a-stick: one router link, trunked, with a subinterface per VLAN acting "
                    "as each VLAN's gateway.\n"
                    "- Layer-3 switch with SVIs: the switch itself routes, using a virtual interface "
                    "(interface vlan 10 with an IP) as each VLAN's gateway. show ip interface brief lists "
                    "the SVIs; show ip route shows what the device can reach.\n\n"
                    "THE GATEWAY CONNECTION: each VLAN's gateway IP is the router/SVI address for that "
                    "subnet. A host in VLAN 10 uses the VLAN 10 SVI as its default gateway. Wrong gateway "
                    "on the host, or a down SVI, = 'can reach my own VLAN but nothing else' — the "
                    "cross-network failure from Week 9, now at the infrastructure level.\n\n"
                    "STATIC ROUTES (awareness + reading): 'ip route 10.0.0.0 255.0.0.0 192.168.1.1' means "
                    "'to reach the 10.x network, send to 192.168.1.1'. show ip route reads the routing "
                    "table; a missing route explains 'this whole network is unreachable'. Juniors read "
                    "and report routing tables far more than they write routes — but you must interpret "
                    "'why can't VLAN 30 reach the server subnet' from show ip route.\n\n"
                    "SCOPE HONESTY: dynamic routing protocols (OSPF/EIGRP/BGP) are CCNA, not Nexus. You "
                    "learn to read a routing table, understand a static route, and recognize inter-VLAN "
                    "routing symptoms — enough to troubleshoot and escalate precisely.\n\n"
                    "COMMON MISTAKES: expecting VLANs to route without a router/SVI; host pointed at the "
                    "wrong gateway; assuming a routing problem when it's actually a down SVI or trunk."
                ),
                "outcomes": [
                    "Explain why inter-VLAN traffic needs a router/SVI and identify each VLAN's gateway",
                    "Read show ip route and a static route to determine what a device can reach",
                    "Distinguish inter-VLAN routing failures from VLAN/trunk/gateway misconfigurations",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "DHCP Relay, NAT, Firewall, VPN, and Wireless — Awareness",
                "lesson_order": 3,
                "estimated_minutes": 75,
                "summary": (
                    "The services a junior network tech must RECOGNIZE and reason about (not deeply "
                    "configure):\n\n"
                    "DHCP RELAY (ip helper-address): DHCP uses broadcasts, which don't cross routers/VLANs. "
                    "So a router interface for a client VLAN needs 'ip helper-address <dhcp-server>' to "
                    "forward requests to a central DHCP server. Symptom when missing: 'this whole new VLAN "
                    "gets no IP (APIPA), but the server-side scope is fine and other VLANs work'. A very "
                    "diagnosable ticket once you know relay exists.\n\n"
                    "NAT: translates private addresses to public for internet access. Awareness: why "
                    "internal hosts share one public IP, and that 'internet works but inbound doesn't' "
                    "often involves NAT/port-forwarding — usually escalated.\n\n"
                    "FIREWALL: rules allow/deny traffic by source/dest/port. Junior reasoning: 'the app "
                    "worked yesterday, now it's refused on port X' after a firewall change = find the "
                    "rule, don't disable the firewall (Week 7's lesson at network scale).\n\n"
                    "VPN: extends the corporate network over the internet. You met the DNS-over-tunnel "
                    "ticket in Week 8 — recognize 'connected but can't resolve internal names' and "
                    "split-tunnel basics.\n\n"
                    "WIRELESS: SSID, band (2.4/5 GHz), signal, and authentication. Junior triage: signal "
                    "strength, right SSID, DHCP on wireless, and 'associated but no internet' vs 'can't "
                    "associate'. AP/controller config is usually escalated.\n\n"
                    "COMMON MISTAKES: forgetting DHCP relay exists (chasing the DHCP server for a relay "
                    "problem); disabling firewalls as a 'fix'; assuming VPN is broken when it's DNS; "
                    "treating every Wi-Fi issue as the AP."
                ),
                "outcomes": [
                    "Recognize a missing DHCP relay from the 'whole VLAN gets no IP but server is fine' symptom",
                    "Reason about NAT, firewall rules, VPN, and wireless at a triage-and-escalate level",
                    "Decide what a junior fixes locally vs packages for network-team escalation",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
    {
        "code": "MOD-012",
        "title": "Network Troubleshooting and Secure Administration",
        "description": "Port security, SSH, config backup, logging, structured network troubleshooting, Gate 3. Week 12.",
        "target_role": "Network Support Technician",
        "difficulty_band": 3,
        "estimated_hours": 16,
        "module_order": 13,
        "unlock_threshold": 70,
        "lessons": [
            {
                "title": "Secure Switch Administration",
                "lesson_order": 1,
                "estimated_minutes": 90,
                "summary": (
                    "Managing a switch safely is a junior responsibility. The essentials:\n\n"
                    "SSH not Telnet: Telnet sends passwords in clear text. Switches should be managed over "
                    "SSH. Recognize 'is this device reachable over SSH' and why Telnet is unacceptable. "
                    "Verify with show ip ssh / the vty line config.\n\n"
                    "PORT SECURITY: limits which/how many MAC addresses a port accepts, so someone can't "
                    "unplug a PC and attach a rogue switch/device. A violation can err-disable the port "
                    "(the err-disabled state from Week 10!). Reading 'show port-security interface <x>' "
                    "tells you if a port shut due to a security violation vs a cable fault — a key "
                    "diagnostic distinction.\n\n"
                    "CONFIG BACKUP: 'copy running-config startup-config' saves across reboot; backing the "
                    "config off-device (to a TFTP/SCP server or even copy-paste into the runbook) means a "
                    "dead switch doesn't mean a lost configuration. A junior who says 'we have no backup "
                    "of this switch's config' has found a real risk worth escalating.\n\n"
                    "LOGGING: switches log events (link changes, security violations, mismatches). "
                    "'show logging' is an evidence source — the native-VLAN mismatch, the port-security "
                    "violation, the flapping interface all leave log entries. Reading logs turns 'the "
                    "network is weird' into 'port 1/0/7 err-disabled at 14:03 due to psecure-violation'.\n\n"
                    "DEVICE HARDENING (awareness): management off VLAN 1, strong enable secret, no unused "
                    "open services, banner warnings. You recognize these as good practice and their "
                    "absence as a finding.\n\n"
                    "COMMON MISTAKES: managing over Telnet; no config backup; ignoring logs; 'no shutdown' "
                    "on a port-security err-disable without addressing the rogue device."
                ),
                "outcomes": [
                    "Explain why SSH replaces Telnet and how to confirm secure management access",
                    "Read port-security status to distinguish a security violation from a cable fault",
                    "Use config backup and show logging as recovery and evidence tools",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
            {
                "title": "Structured Network Troubleshooting",
                "lesson_order": 2,
                "estimated_minutes": 90,
                "summary": (
                    "Bring it together: a repeatable method for any network complaint, layer by layer, "
                    "bottom-up (fastest for physical/config faults):\n\n"
                    "L1 PHYSICAL: is the link up? show interfaces status — connected? notconnect? "
                    "admin-down? err-disabled? Cable, port, power. (Week 10.)\n"
                    "L2 SWITCHING: right VLAN? show vlan brief. Trunk carrying the VLAN? show interfaces "
                    "trunk. MAC learned? show mac address-table. Native VLAN match? (Weeks 10-11.)\n"
                    "L3 ADDRESSING/ROUTING: correct IP/mask/gateway? (Week 9 — same subnet as gateway?). "
                    "Can it reach the gateway? Route to the destination? show ip route. DHCP relay for "
                    "the VLAN? (Week 11.)\n"
                    "L4+/SERVICES: DNS resolving? (Week 8 triage tree). Firewall rule? Application up?\n\n"
                    "THE DISCIPLINE: change ONE thing, verify with a show command, document what you saw, "
                    "and know how to undo it. On shared infrastructure a careless change is an OUTAGE — a "
                    "wrong VLAN or a saved bad config affects everyone on that switch. This is why network "
                    "changes get more caution, more verification, and more escalation than a single "
                    "desktop.\n\n"
                    "WHEN TO ESCALATE: routing changes, anything affecting multiple VLANs/users, config "
                    "you don't fully understand, or a fix that would require a change window. Package the "
                    "escalation with your show-command evidence — the network team can act immediately "
                    "on 'VLAN 30 SVI is down per show ip int brief, 60 users affected since 09:15'.\n\n"
                    "COMMON MISTAKES: starting at L3 when it's an L1 cable; changing multiple things; not "
                    "saving; making a switch-wide change to fix one port; no evidence in the escalation."
                ),
                "outcomes": [
                    "Apply a bottom-up L1-L4 network troubleshooting method with the matching show commands",
                    "Practice change safety on shared infrastructure: one change, verify, document, undo-plan",
                    "Escalate network issues with show-command evidence and correct scope",
                ],
                "required_notes_template": NOTES_TEMPLATE,
                "status": "published",
            },
        ],
    },
]


QUIZZES_C = [
    {
        "title": "IPv4 Addressing and Subnetting",
        "week_number": 9, "domain_id": "2.0", "lesson_title": "Practical Subnetting for Support",
        "questions": [
            _q("A host is 192.168.1.50/24 with gateway 192.168.2.1. Result:",
               "Works normally", "Cannot reach the gateway — it's on a different network, so no remote traffic",
               "Works only for local traffic", "Causes an IP conflict",
               "B", "The gateway must be within the host's own subnet; /24 puts .50 and .2.1 on different networks."),
            _q("On a /26 network, the address 192.168.1.70 belongs to which subnet?",
               "192.168.1.0", "192.168.1.64", "192.168.1.128", "192.168.1.192",
               "B", "/26 block size is 64: subnets .0/.64/.128/.192; .70 falls in the .64 subnet (hosts .65-.126)."),
            _q("How many usable hosts on a /28?",
               "16", "14", "30", "8",
               "B", "/28 = 16 addresses − network − broadcast = 14 usable."),
            _q("A PC has mask 255.255.0.0 (/16) instead of the correct /24. The likely symptom:",
               "No effect", "It treats some remote hosts as local, never sends their traffic to the router",
               "It can't get an IP", "DNS fails only",
               "B", "A too-broad mask makes remote networks look local, so the host ARPs for them instead of using the gateway."),
            _q("Which are private IPv4 ranges? (select all that apply)",
               "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
               "A", "10/8, 172.16/12, 192.168/16 are private; 169.254 is APIPA (link-local, not a usable private range).", multi="A,B,C"),
            _q("The broadcast address of the subnet containing 10.1.1.100/27 is:",
               "10.1.1.127", "10.1.1.95", "10.1.1.128", "10.1.1.255",
               "A", "/27 block size 32: .96 subnet? No — .100 is in .96/.127. Network .96, broadcast .127."),
            _q("Two hosts on the same subnet communicate by:",
               "Sending everything to the default gateway", "ARP for each other's MAC, then direct switching",
               "DNS lookups", "A static route",
               "B", "Same subnet = direct delivery via ARP + switch; the gateway is only for OTHER subnets."),
            _q("Network address vs broadcast address: which can be assigned to a host?",
               "Both", "Neither", "Only the network address", "Only the broadcast address",
               "B", "The all-zeros (network) and all-ones (broadcast) host addresses are reserved."),
        ],
    },
    {
        "title": "Packet Flow, ARP, and MAC Learning",
        "week_number": 9, "domain_id": "2.0", "lesson_title": "ARP, MAC Learning, and Packet Flow",
        "questions": [
            _q("Host A (192.168.1.10/24) sends to server 10.0.0.5. A ARPs for the MAC of:",
               "The server (10.0.0.5)", "Its default gateway", "The DNS server", "The broadcast address",
               "B", "Different subnet → A can't reach the server directly, so it ARPs for the gateway and sends the frame there."),
            _q("A user can ping local machines but nothing on other subnets. Most likely:",
               "DNS failure", "Default gateway wrong/unreachable or a routing problem", "Bad cable", "Switch is down",
               "B", "Local works = L1/L2 fine; only cross-subnet fails = gateway/routing."),
            _q("A switch receives a frame for a destination MAC not in its table. It:",
               "Drops the frame", "Floods it out all ports in that VLAN (normal behavior)", "Errors", "Reboots",
               "B", "Unknown-unicast flooding is normal; the switch learns the reply's source MAC and stops flooding."),
            _q("A switch learns which port a device is on by reading the frame's:",
               "Destination MAC", "Source MAC", "IP address", "VLAN tag",
               "B", "MAC tables are built from source addresses seen on each port."),
            _q("After a server's NIC was replaced, one client still can't reach it though others can. Suspect:",
               "The server is down", "A stale ARP entry on that client mapping the old MAC", "DNS", "Routing",
               "B", "A cached ARP entry with the old MAC misdelivers until it ages out or is cleared (arp -d)."),
            _q("A user can't ping ANYTHING, including devices on their own subnet. Layer to check first:",
               "DNS (L7)", "Physical/switching (L1/L2): cable, port, VLAN", "Routing (L3)", "Application",
               "B", "Total local failure points at the lowest layers before addressing or DNS."),
        ],
    },
    {
        "title": "Cisco CLI, VLANs, and Interfaces",
        "week_number": 10, "domain_id": "2.0", "lesson_title": "VLANs and Access Ports",
        "questions": [
            _q("You just changed a switch config and it works. Before rebooting you must:",
               "Nothing — changes are automatic", "copy running-config startup-config (save)",
               "Reload the switch", "Delete the VLAN database",
               "B", "Running-config is in RAM; without saving to startup-config the change is lost on reboot."),
            _q("A PC moved to a new port has no network; other PCs are fine. The port shows VLAN 1, should be VLAN 20. Fix:",
               "Replace the cable", "switchport access vlan 20 on that port, then verify with show vlan brief",
               "Reboot the switch", "Reinstall the NIC driver",
               "B", "Wrong access VLAN = wrong subnet/no DHCP; assign the correct VLAN and verify."),
            _q("Which command shows every port with its VLAN and connected/notconnect status?",
               "show running-config", "show interfaces status", "show ip route", "show mac address-table",
               "B", "show interfaces status is the at-a-glance port/VLAN/link view."),
            _q("A switch port shows 'administratively down'. To bring it up:",
               "Replace the switch", "Enter the interface and run 'no shutdown'", "Change the VLAN", "copy run start",
               "B", "'administratively down' means someone ran shutdown; 'no shutdown' re-enables it."),
            _q("Which CLI mode do you configure a single port in?",
               "User EXEC (>)", "Interface config (config-if)#", "Privileged EXEC (#)", "Global config (config)#",
               "B", "Per-port changes happen in interface config mode, reached via 'interface <x>'."),
            _q("Leaving user ports in VLAN 1 or using VLAN 1 for management is:",
               "Best practice", "A security smell — management should be moved off the default VLAN",
               "Required", "Impossible",
               "B", "VLAN 1 is the default; hardening moves management and user traffic off it."),
            _q("A port shows 'err-disabled'. Running 'no shutdown' without more:",
               "Fixes it permanently", "May re-disable it because the underlying trigger (e.g. port-security) remains",
               "Deletes the VLAN", "Is impossible",
               "B", "err-disabled needs the cause resolved; blindly re-enabling re-triggers the violation."),
        ],
    },
    {
        "title": "Trunks, Routing, and Network Services",
        "week_number": 11, "domain_id": "2.0", "lesson_title": "Trunks and the Native VLAN",
        "questions": [
            _q("A trunk port differs from an access port in that it:",
               "Carries one VLAN for a PC", "Carries multiple VLANs between switches using 802.1Q tags",
               "Is always faster", "Cannot be configured",
               "B", "Trunks tag frames to carry many VLANs; access ports carry one untagged VLAN for an end device."),
            _q("Users in VLAN 20 on a newly-added switch B can't reach anything; VLAN 10 works. First check:",
               "Replace switch B", "show interfaces trunk on both ends — is VLAN 20 allowed/active on the trunk?",
               "Reboot both switches", "Reinstall drivers",
               "B", "A trunk not carrying VLAN 20 (allowed-list or access/trunk mismatch) isolates VLAN 20."),
            _q("A native VLAN mismatch between two trunk ends causes:",
               "Total link failure", "Odd cross-VLAN leakage and logged mismatch warnings",
               "Faster throughput", "An IP conflict",
               "B", "Untagged native traffic lands in different VLANs on each end — weird behavior plus log messages."),
            _q("VLAN 10 and VLAN 20 hosts need to communicate. This requires:",
               "A bigger switch", "A router or layer-3 switch (SVI) to route between the VLANs",
               "The same cable", "Disabling VLANs",
               "B", "Separate VLANs are separate networks; inter-VLAN traffic must be routed."),
            _q("A whole new VLAN gets no IP (APIPA) but the DHCP server and other VLANs are fine. Likely cause:",
               "DHCP server down", "Missing ip helper-address (DHCP relay) on that VLAN's router interface",
               "Bad cables everywhere", "DNS",
               "B", "DHCP broadcasts don't cross routers; without a relay the new VLAN never reaches the server."),
            _q("show ip route is used to:",
               "See connected clients", "Determine what networks the device knows how to reach",
               "Configure VLANs", "Save the config",
               "B", "The routing table shows reachable networks; a missing route explains an unreachable subnet."),
            _q("A host reaches its own VLAN but no other network. Besides gateway config, suspect:",
               "DNS only", "A down SVI/router interface serving as that VLAN's gateway",
               "The cable", "Port security",
               "B", "If the VLAN's gateway (SVI/router subinterface) is down, all inter-VLAN traffic fails while local works."),
        ],
    },
    {
        "title": "Network Troubleshooting and Secure Admin",
        "week_number": 12, "domain_id": "2.0", "lesson_title": "Structured Network Troubleshooting",
        "questions": [
            _q("Why manage switches over SSH rather than Telnet?",
               "SSH is faster", "Telnet sends credentials in clear text; SSH encrypts the session",
               "Telnet is unavailable", "SSH uses less power",
               "B", "Telnet exposes passwords on the wire; SSH is the secure management standard."),
            _q("A port is err-disabled. show port-security shows a violation. The RIGHT recovery:",
               "no shutdown immediately", "Find/remove the rogue device or fix the trigger, THEN re-enable",
               "Delete the VLAN", "Replace the switch",
               "B", "Address the security cause first; otherwise the port re-disables on the next violation."),
            _q("Bottom-up troubleshooting: a user has no connectivity. You check FIRST:",
               "DNS resolution", "L1/L2: link status, VLAN, cabling", "The routing table", "The application",
               "B", "Bottom-up starts at physical/switching, the fastest place to find config/cable faults."),
            _q("Why do network changes demand more caution than a single desktop fix?",
               "They don't", "A wrong VLAN or saved bad config on shared gear can outage many users at once",
               "Switches are fragile", "Cisco requires it",
               "B", "Shared infrastructure means one careless change is a multi-user outage."),
            _q("Good practices for a junior handling switch config include: (select all that apply)",
               "copy running-config startup-config after verifying a change", "Keeping an off-device config backup",
               "Managing over Telnet to save time", "Reading show logging for evidence",
               "A", "Save, back up, and read logs; Telnet is the insecure anti-practice.", multi="A,B,D"),
            _q("The strongest network escalation note contains:",
               "'The network is broken'", "Scope + evidence: 'VLAN 30 SVI down per show ip int brief, 60 users since 09:15'",
               "A guess at the cause", "A request to reboot everything",
               "B", "Show-command evidence and scope let the network team act immediately."),
            _q("You save a switch's config off-device primarily so that:",
               "It runs faster", "A failed switch doesn't mean a lost, unrecoverable configuration",
               "VLANs work", "SSH is enabled",
               "B", "Off-device backups make hardware failure recoverable."),
        ],
    },
]


TICKETS_C = [
    {
        "title": "New static IP 'can reach the office but not the internet or servers'",
        "description": (
            "{{USER}} was given a static IP for a lab device by a colleague. It can ping other machines "
            "on its own floor but cannot reach any server or the internet. The colleague set: IP "
            "{{IP}}, mask {{MASK}}, gateway {{GW}}. You have the client and can read its config."
        ),
        "difficulty": 3, "week_number": 9, "category": "Networking", "domain_id": "2.0",
        "root_cause": "The gateway {{GW}} is not on the same subnet as the host given its mask {{MASK}}, so the host cannot reach its gateway and no traffic leaves the local network; correcting the mask/gateway to match fixes it",
        "root_cause_type": "addressing_mismatch",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Symptom = local works, remote fails → gateway/routing, not L1", "required_mention": ["local works", "remote", "gateway", "same subnet"], "weight": 0.3},
            {"id": 2, "step": "Check whether the gateway is within the host's subnet for the given mask", "required_mention": ["mask", "subnet", "gateway", "same network"], "weight": 0.3},
            {"id": 3, "step": "Correct the mask (or gateway) so host and gateway share a subnet", "required_mention": ["correct", "mask", "gateway", "fix"], "weight": 0.25},
            {"id": 4, "step": "Verify remote reachability (ping gateway, then internet/server)", "required_mention": ["ping", "verify", "reach", "internet"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "ipconfig showing the wrong IP/mask/gateway and the corrected values", "validation": {}},
            {"type": "screenshot", "description": "Successful ping to the gateway and a remote host after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = local-works/remote-fails reasoned to the gateway relationship, not blamed on cable/DNS",
            "2 = gateway-not-in-subnet identified using the mask (the actual arithmetic shown)",
            "2 = minimal correct fix (mask or gateway) so they share a subnet; no random reconfiguration",
            "2 = ping to gateway then a remote host verifies the fix",
            "2 = explained simply why the address was wrong; suggested DHCP/reservation to avoid repeats",
        ),
        "model_answer": (
            "Local works, remote fails = the host can't use its gateway. Check the math: with mask "
            "{{MASK}}, the host {{IP}} and gateway {{GW}} are NOT on the same subnet, so the host can't "
            "ARP/reach the gateway and nothing leaves the network. Correct the mask (or gateway) so they "
            "share a subnet, ping the gateway to confirm, then ping a remote host/internet. Recommend a "
            "DHCP reservation instead of hand-set statics to prevent repeats."
        ),
        "hints": [
            "It reaches its own floor but nothing beyond. What does a host use to leave its network, and what must be true about that address?",
            "Do the subnet math: given the mask, are the IP and the gateway actually on the same network?",
            "They're not on the same subnet — so the host can never reach its gateway.",
            "Fix the mask (or the gateway) so host and gateway share a subnet, ping the gateway to confirm, then a remote host. Suggest a DHCP reservation to stop hand-set mistakes.",
        ],
        "parameters": {"placeholders": {
            "USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
            "IP": ["192.168.1.50", "10.0.5.20", "192.168.20.15", "172.16.4.30", "10.10.1.60"],
            "MASK": ["255.255.255.0 (/24)", "255.255.255.0 (/24)", "255.255.255.128 (/25)", "255.255.255.0 (/24)", "255.255.255.192 (/26)"],
            "GW": ["192.168.2.1", "10.0.6.1", "192.168.20.200", "172.16.5.1", "10.10.1.200"],
        }},
    },
    {
        "title": "New desk on the wrong VLAN after office reshuffle",
        "description": (
            "{{USER}} was moved to a new desk. Their PC gets an IP in the {{WRONGNET}} range and can't "
            "reach the {{DEPT}} file server or printers, though the machine and cable are fine. The port "
            "they're on is switchport gi1/0/{{PORT}}. Their old neighbor (unchanged) works normally. You "
            "have SSH access to the switch."
        ),
        "difficulty": 3, "week_number": 10, "category": "Networking", "domain_id": "2.0",
        "root_cause": "The access port gi1/0/{{PORT}} is assigned to the wrong VLAN (defaulted to VLAN 1 / a neighbor VLAN) instead of the {{DEPT}} VLAN; reassigning the access VLAN and saving fixes it",
        "root_cause_type": "wrong_vlan",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Confirm symptom = wrong subnet, not L1 (cable/link ok, neighbor fine)", "required_mention": ["subnet", "vlan", "link", "connected"], "weight": 0.25},
            {"id": 2, "step": "show vlan brief / show interfaces status to see the port's current VLAN", "required_mention": ["show vlan", "show interfaces status", "access vlan"], "weight": 0.3},
            {"id": 3, "step": "Assign correct access VLAN; verify with show vlan brief", "required_mention": ["switchport access vlan", "verify", "show vlan"], "weight": 0.25},
            {"id": 4, "step": "Save config; confirm user gets correct subnet and reaches resources", "required_mention": ["copy running", "write mem", "save", "verified"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "show vlan brief / interfaces status before and after", "validation": {}},
            {"type": "screenshot", "description": "Client ipconfig showing correct subnet + reaching a resource", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = localized to VLAN/subnet (not cable) using switch show commands, neighbor clue used",
            "2 = wrong access-VLAN assignment identified specifically",
            "2 = correct VLAN assigned to that ONE port and saved; no switch-wide changes",
            "2 = client verified on the right subnet reaching the file server; config saved",
            "2 = user told plainly it was a port setting from the move, now fixed",
        ),
        "model_answer": (
            "Link is up and the neighbor works, so it's not L1 — the client's wrong subnet points at VLAN. "
            "show interfaces status / show vlan brief shows gi1/0/{{PORT}} in the wrong VLAN. In interface "
            "config: switchport mode access; switchport access vlan <DEPT VLAN>. Verify with show vlan "
            "brief, confirm the client now gets the right subnet and reaches the file server, then copy "
            "running-config startup-config."
        ),
        "hints": [
            "The link is up and the neighbor is fine — so this isn't a cable. What decides which subnet a port lands in?",
            "On the switch: show interfaces status and show vlan brief for that port.",
            "The port is in the wrong VLAN. Assign the correct access VLAN in interface config.",
            "switchport access vlan <correct>, verify with show vlan brief, confirm the client's subnet and reachability, then SAVE (copy run start) — don't touch other ports.",
        ],
        "parameters": {"placeholders": {
            "USER": ["mfields", "tnguyen", "rpatel", "kjohnson", "dlee"],
            "DEPT": ["Finance", "Engineering", "Sales", "Support", "Logistics"],
            "PORT": ["7", "11", "3", "18", "22"],
            "WRONGNET": ["192.168.1.x (default VLAN)", "192.168.99.x", "10.10.1.x", "192.168.50.x", "172.16.5.x"],
        }},
    },
    {
        "title": "Whole new VLAN gets no IP address",
        "description": (
            "The network team stood up a new VLAN {{VLAN}} for the {{DEPT}} team this week. Every device "
            "in it gets a 169.254.x.x address — no DHCP. The DHCP server is up, its scope for VLAN "
            "{{VLAN}} exists and looks correct, and every OTHER VLAN gets addresses normally. You can "
            "read the router and switch configs."
        ),
        "difficulty": 4, "week_number": 11, "category": "Networking", "domain_id": "2.0",
        "root_cause": "The router/SVI interface for VLAN {{VLAN}} is missing 'ip helper-address' (DHCP relay), so broadcast DHCP requests never reach the central server; adding the helper fixes the whole VLAN",
        "root_cause_type": "missing_dhcp_relay",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Scope: ALL of one new VLAN, server + scope fine, other VLANs fine → not the server", "required_mention": ["whole vlan", "server fine", "other vlans", "169.254"], "weight": 0.3},
            {"id": 2, "step": "Reason to DHCP relay: broadcasts don't cross the router to reach central DHCP", "required_mention": ["relay", "helper", "broadcast", "cross"], "weight": 0.3},
            {"id": 3, "step": "Identify missing ip helper-address on the VLAN's gateway interface", "required_mention": ["ip helper-address", "svi", "interface vlan", "gateway"], "weight": 0.25},
            {"id": 4, "step": "Verify (or escalate to add it) then confirm the VLAN leases addresses", "required_mention": ["verify", "lease", "escalat", "dhcp"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "Config of the VLAN's gateway interface showing missing/added helper", "validation": {}},
            {"type": "screenshot", "description": "A client in the VLAN receiving a real lease after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = scope correctly rules out the DHCP server (whole VLAN, others fine, scope exists)",
            "2 = missing DHCP relay named as the cause (not 'server problem')",
            "2 = ip helper-address on the SVI identified; if adding it needs change approval, packaged escalation counts full",
            "2 = VLAN confirmed leasing after the fix, or clean escalation with the exact interface + command",
            "2 = clear explanation of why a brand-new VLAN specifically hit this",
        ),
        "model_answer": (
            "Whole VLAN affected + server and scope fine + other VLANs fine = not the server. DHCP uses "
            "broadcasts, which don't cross the router into the central DHCP server — the VLAN {{VLAN}} "
            "gateway interface (interface vlan {{VLAN}} / the router subinterface) is missing "
            "'ip helper-address <dhcp-server>'. Add it (or escalate with the exact interface and command "
            "if a change window is required), then confirm clients in VLAN {{VLAN}} receive real leases."
        ),
        "hints": [
            "One entire new VLAN, but the server and every other VLAN are fine. Where is the boundary the requests can't cross?",
            "DHCP relies on broadcasts. What happens to a broadcast at a router?",
            "The VLAN's gateway interface needs something to FORWARD DHCP to the central server.",
            "It's a missing ip helper-address on the VLAN {{VLAN}} SVI/gateway. Add it (or escalate with the exact interface + command), then verify the VLAN leases addresses.",
        ],
        "parameters": {"placeholders": {
            "VLAN": ["40", "55", "70", "35", "60"],
            "DEPT": ["Marketing", "R&D", "Facilities", "Contractors", "Training"],
        }},
    },
    {
        "title": "Second-floor switch: half the VLANs unreachable after a switch swap",
        "description": (
            "IT swapped a failed access switch on floor 2 last night. Now devices in VLAN {{VLAN_OK}} "
            "work, but everyone in VLAN {{VLAN_BAD}} on that switch can't reach anything beyond the "
            "floor. The uplink to the core is gi1/0/24. Core-side config is unchanged and known-good. "
            "You have SSH to both switches."
        ),
        "difficulty": 4, "week_number": 11, "category": "Networking", "domain_id": "2.0",
        "root_cause": "The replacement switch's uplink gi1/0/24 is not trunking VLAN {{VLAN_BAD}} (either the allowed-VLAN list omits it, or the port came up as access instead of trunk); correcting the trunk restores the VLAN",
        "root_cause_type": "trunk_mismatch",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Scope: one VLAN broken on the swapped switch, core unchanged → uplink trunk", "required_mention": ["one vlan", "swap", "uplink", "trunk"], "weight": 0.25},
            {"id": 2, "step": "show interfaces trunk on the uplink (both ends) — allowed VLANs / mode", "required_mention": ["show interfaces trunk", "allowed vlan", "both ends"], "weight": 0.3},
            {"id": 3, "step": "Correct the trunk: add VLAN to allowed list / set trunk mode", "required_mention": ["switchport trunk allowed", "switchport mode trunk", "add vlan"], "weight": 0.25},
            {"id": 4, "step": "Verify VLAN {{VLAN_BAD}} now crosses; save config", "required_mention": ["verify", "reach", "save", "copy running"], "weight": 0.2},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "show interfaces trunk before/after on the uplink", "validation": {}},
            {"type": "screenshot", "description": "A VLAN {{VLAN_BAD}} client reaching a resource beyond the floor", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = scoped to the uplink trunk using the 'one VLAN, post-swap, core unchanged' clues",
            "2 = trunk allowed-list omission / mode mismatch identified precisely",
            "2 = minimal trunk correction on the uplink; no unrelated changes, saved",
            "2 = VLAN {{VLAN_BAD}} verified reaching beyond the floor; config saved",
            "2 = change explained with the swap as root cause; escalate if a change window is required",
        ),
        "model_answer": (
            "One VLAN broken only on the replaced switch, core unchanged = the new switch's uplink trunk. "
            "show interfaces trunk gi1/0/24 on both ends: the allowed-VLAN list omits VLAN {{VLAN_BAD}} "
            "(or the port came up access). Fix: switchport mode trunk; switchport trunk allowed vlan add "
            "{{VLAN_BAD}}. Verify VLAN {{VLAN_BAD}} crosses to the core and reaches resources, then save. "
            "The replacement switch didn't inherit the old trunk config."
        ),
        "hints": [
            "Only ONE VLAN is broken, only on the swapped switch, and the core is unchanged. What single link carries all VLANs between them?",
            "show interfaces trunk on the gi1/0/24 uplink — on BOTH ends.",
            "The uplink isn't carrying the broken VLAN (allowed-list omission, or it's access not trunk).",
            "Set the uplink to trunk and add VLAN {{VLAN_BAD}} to the allowed list, verify it reaches the core, and save. The new switch simply didn't inherit the old uplink config.",
        ],
        "parameters": {"placeholders": {
            "VLAN_OK": ["10", "20", "30", "15", "25"],
            "VLAN_BAD": ["20", "30", "40", "25", "35"],
        }},
    },
    {
        "title": "Switch port keeps shutting down on the shared lab bench",
        "description": (
            "The port for the shared lab bench (gi1/0/{{PORT}}) keeps going dark. Users say 'it works for "
            "a bit then dies'. show interfaces status shows it err-disabled. The bench has a small "
            "unmanaged switch someone plugged in to add more ports. You have SSH to the switch."
        ),
        "difficulty": 3, "week_number": 12, "category": "Networking", "domain_id": "2.0",
        "root_cause": "Port security on gi1/0/{{PORT}} err-disables the port when the unauthorized unmanaged switch introduces multiple/again unknown MAC addresses; the rogue switch is the trigger — not a cable",
        "root_cause_type": "port_security_violation",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Read err-disabled cause: show port-security interface / show logging (not assume cable)", "required_mention": ["err-disable", "port-security", "show logging", "violation"], "weight": 0.3},
            {"id": 2, "step": "Identify the unmanaged switch introducing extra MACs as the trigger", "required_mention": ["unmanaged switch", "multiple mac", "rogue", "extra"], "weight": 0.3},
            {"id": 3, "step": "Remove the unauthorized device / address the policy; then recover the port", "required_mention": ["remove", "unplug", "no shutdown", "recover"], "weight": 0.25},
            {"id": 4, "step": "Verify stable; document as a security finding, escalate policy question if needed", "required_mention": ["verify", "stable", "document", "escalat"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "show port-security interface / show logging showing the violation", "validation": {}},
            {"type": "screenshot", "description": "Port stable up after removing the trigger", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = err-disabled cause READ from port-security/logging, not assumed to be a cable",
            "2 = unauthorized unmanaged switch identified as the port-security trigger",
            "2 = trigger removed BEFORE/with recovery; a bare 'no shutdown' that re-disables = 1; ignoring the security aspect = 0",
            "2 = port verified stable; documented as a security finding",
            "2 = users told why the extra switch isn't allowed, without blame",
        ),
        "model_answer": (
            "err-disabled + a user-added unmanaged switch = port-security violation, not a cable. show "
            "port-security interface gi1/0/{{PORT}} and show logging confirm the psecure-violation. The "
            "unmanaged switch presents multiple MACs, tripping the limit. Remove the unauthorized switch "
            "(the correct fix), then recover the port (shutdown / no shutdown, or clear the violation). "
            "Verify it stays up. Document as a security finding and escalate the 'they need more ports' "
            "request to be solved properly."
        ),
        "hints": [
            "err-disabled isn't a cable fault. What made the switch shut the port ON PURPOSE?",
            "show port-security interface and show logging will name the violation.",
            "Something on that bench introduces extra MAC addresses. What did someone plug in?",
            "The unmanaged switch trips port security. Remove it (that's the fix), then recover the port — 'no shutdown' alone will just re-disable while the rogue switch is there. Document it as a security finding.",
        ],
        "parameters": {"placeholders": {"PORT": ["9", "14", "5", "19", "23"]}},
    },
    {
        "title": "Users in one VLAN can reach each other but nothing else",
        "description": (
            "Everyone in VLAN {{VLAN}} ({{SUBNET}}) can reach each other but cannot reach any other VLAN, "
            "the servers, or the internet since this morning. Other VLANs are completely fine. The layer-3 "
            "switch hosts the gateway for each VLAN on an SVI. You have SSH access."
        ),
        "difficulty": 4, "week_number": 11, "category": "Networking", "domain_id": "2.0",
        "root_cause": "The SVI (interface vlan {{VLAN}}) that serves as this VLAN's default gateway is administratively down or lost its IP, so intra-VLAN switching works but nothing routes out; restoring the SVI fixes it",
        "root_cause_type": "down_svi_gateway",
        "required_checkpoints": {"checkpoints": [
            {"id": 1, "step": "Symptom = intra-VLAN works, inter-VLAN fails → gateway/SVI, not L1/L2", "required_mention": ["own vlan works", "gateway", "svi", "inter-vlan"], "weight": 0.3},
            {"id": 2, "step": "show ip interface brief — is interface vlan {{VLAN}} up/up with the right IP?", "required_mention": ["show ip interface brief", "interface vlan", "up", "down"], "weight": 0.3},
            {"id": 3, "step": "Restore the SVI (no shutdown / correct IP)", "required_mention": ["no shutdown", "ip address", "svi", "restore"], "weight": 0.25},
            {"id": 4, "step": "Verify inter-VLAN + internet reachability; save", "required_mention": ["verify", "reach", "save", "ping"], "weight": 0.15},
        ]},
        "required_evidence": {"evidence_types": [
            {"type": "screenshot", "description": "show ip interface brief showing the SVI state before/after", "validation": {}},
            {"type": "screenshot", "description": "A VLAN {{VLAN}} client reaching another subnet after the fix", "validation": {}},
        ]},
        "scoring_anchors": ANCHORS(
            "2 = intra-vs-inter-VLAN split correctly points at the gateway/SVI",
            "2 = down/misconfigured SVI identified as the cause",
            "2 = SVI restored precisely; no unrelated routing changes, saved",
            "2 = inter-VLAN + internet verified for a VLAN {{VLAN}} client",
            "2 = scope and cause explained; escalate if the SVI change needs approval",
        ),
        "model_answer": (
            "Intra-VLAN works but nothing routes out = the VLAN's gateway. show ip interface brief shows "
            "interface vlan {{VLAN}} down (or missing its IP). Restore it: no shutdown and/or reapply the "
            "correct ip address {{SUBNET}} gateway. Verify a VLAN {{VLAN}} client now reaches other "
            "subnets and the internet, then save. Other VLANs were fine because only this SVI failed."
        ),
        "hints": [
            "They can reach each OWN VLAN fine — so switching works. What's the one thing needed to leave a VLAN?",
            "The gateway for a VLAN on a layer-3 switch is its SVI. Check show ip interface brief.",
            "interface vlan {{VLAN}} is down or lost its IP.",
            "Restore the SVI (no shutdown / correct IP), verify a client reaches other subnets and the internet, and save. Only this VLAN's gateway failed, which is why the rest were fine.",
        ],
        "parameters": {"placeholders": {
            "VLAN": ["30", "40", "50", "25", "60"],
            "SUBNET": ["192.168.30.1/24", "192.168.40.1/24", "10.0.50.1/24", "192.168.25.1/24", "172.16.60.1/24"],
        }},
    },
]


def seed_phase_c(db) -> dict:
    """Idempotent Phase C seed — same conventions as seed_phase_a/b()."""
    from app.models.learning import Lesson, Module
    from app.models.quiz import QUIZ_STATUS_PUBLISHED, Question, Quiz
    from app.models.ticket import Ticket

    counts = {"modules": 0, "lessons": 0, "quizzes": 0, "questions": 0, "tickets": 0}
    prev_module = db.query(Module).filter(Module.code == "MOD-008").first()
    for spec in MODULES_C:
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

    for qspec in QUIZZES_C:
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

    for tspec in TICKETS_C:
        ticket = db.query(Ticket).filter(Ticket.title == tspec["title"]).first()
        if ticket is None:
            db.add(Ticket(**tspec))
            counts["tickets"] += 1
        else:
            for k, v in tspec.items():
                setattr(ticket, k, v)
    db.flush()
    return counts
