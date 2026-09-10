# Hybrid Labs Phase 0 — Network and Trust Design

## Current network

The Nexus VM has `192.168.0.101/24` on `ens18` with default gateway `192.168.0.1`. Proxmox management answers on `192.168.0.50:8006`, and `ip route get` shows it is directly connected through `ens18`. Several household/private-LAN neighbors are visible on the same `/24`.

Inside the Nexus VM, Docker uses:

- `172.17.0.0/16` (`bridge`), containing `nexus-frontend`;
- `172.19.0.0/16` (`nexus-production`), containing frontend and Service Desk;
- inactive `172.18.0.0/16` and `172.20.0.0/16` bridges.

UFW is active and enabled on the Nexus VM, but its rules require elevated access and could not be read. Proxmox bridges, physical NIC mapping, VLAN-aware settings, host routes, datacenter/node firewall enablement, security groups, and upstream-router ACLs are **UNKNOWN**. Guacamole is neither configured nor running on the Nexus VM.

## Isolation verdict

**UNSAFE FOR STUDENT LABS TODAY.** A hypothetical student-admin VM attached to the same production bridge/subnet would have a direct Layer-2 path toward Proxmox management, Nexus, host SSH endpoints, household devices, and other private systems. Nothing observed proves a deny-by-default student boundary. Local administrator rights inside Windows do not defeat a correctly designed external firewall, but that external boundary has not been demonstrated here.

## Proposed future lab network

Addressing proposal only; no bridge, VLAN, route, or rule was created:

| Purpose | Proposed value |
|---|---|
| Lab subnet | `10.26.19.0/24` |
| Firewall/router interface | `10.26.19.1` |
| Optional trusted evidence gateway | `10.26.19.2` |
| Windows workstation | `10.26.19.10` (`NX-2504`, static lease per attempt) |
| Stale/nonexistent printer target | `10.26.19.80` (must remain a black hole for this scenario) |
| Real isolated print endpoint | `10.26.19.94` (`ENG-COPIER`) |
| VLAN ID / Proxmox bridge name | **TBD after collision and topology review**; do not assume an unused VLAN |

The segment should be a dedicated VLAN/bridge behind a stateful firewall, not a subinterface that silently inherits access to management networks. Each learner attempt should be separately isolated when concurrency is introduced—prefer per-attempt VLAN/VRF or an equivalent microsegmented policy over a shared student broadcast domain.

### Deny-by-default policy intent

From the Windows lab segment:

- deny Proxmox management on every address/port, including `192.168.0.50:8006`, `192.168.100.2`, SSH, corosync, migration, storage, and console networks;
- deny Nexus production subnets and Docker networks except one explicit evidence API through a trusted gateway if later required;
- deny RFC1918, link-local, metadata, household/personal LAN, and other student attempt ranges by default;
- deny direct DNS except an approved resolver and deny arbitrary routing/proxying;
- allow Windows to `10.26.19.94` only on the selected print protocol plus minimal scenario dependencies;
- allow Guacamole/guacd **to** Windows TCP 3389; the Windows VM does not need to initiate a connection to Guacamole;
- allow narrow NTP/DNS/update destinations only if the lab requires them and through controlled egress;
- prevent east-west student traffic, spoofing, rogue DHCP/router advertisements, MAC changes where supported, and IPv6 bypasses;
- log deny events and permitted evidence-relevant flows outside the student VM.

The Proxmox API token belongs only on a trusted Nexus worker network. Neither the lab VM nor Guacamole client session should be able to route to the PVE API.

## Future access path and trust boundaries

```text
Student browser
  |  TB1: Internet/user device -> Nexus TLS/authentication
  v
Nexus authenticated session
  |  TB2: student identity -> server-side lab/run authorization
  v
Open Workstation -> Nexus lab assignment
  |  TB3: Nexus API -> durable provisioning worker
  |       (restricted PVE token, template/pool/network allowlists)
  v
Guacamole connection broker
  |  TB4: one temporary Guacamole identity -> one connection READ permission
  |  TB5: trusted gateway -> isolated lab RDP only
  v
NX-2504 on per-attempt lab segment
  |  TB6: untrusted student-admin VM -> external firewall/evidence plane
  v
ENG-COPIER at 10.26.19.94
```

Additional trust boundaries are the browser iframe, token-bearing Guacamole URL, Nexus-to-Guacamole administrator API, Nexus-to-Proxmox API, database/ledger, and evidence gateway-to-printer receipt channel.

## Existing code protections

Source references: [labs router](../../../backend/app/routers/labs.py), [Proxmox service](../../../backend/app/services/proxmox_service.py), [Guacamole service](../../../backend/app/services/guacamole_service.py), [VM assignment model](../../../backend/app/models/vm_assignment.py), and [Lab page](../../../frontend/src/pages/LabPage.jsx).

Already present:

- students must authenticate and lab/run lookup is scoped to the current student;
- one assignment is unique per lab run, reducing duplicate launch records;
- PVE credentials remain server-side and are never intentionally returned;
- Guacamole creates a random temporary account and grants only `READ` on one connection;
- refreshing access deletes the previous temporary Guacamole user;
- the browser embeds the scoped URL and also offers a new-tab link;
- TTL is persisted and expired access is rejected when status/access is requested;
- submission queues connection/user/VM cleanup.

Missing or insufficient:

- no live Proxmox or Guacamole configuration exists;
- no verified network isolation exists;
- the student VMID and IP are serialized to the client unnecessarily (knowledge is not authority, but minimize it);
- no resource pool, bridge, VLAN, firewall, or template allowlist is enforced in the Proxmox call;
- the API token's real ACL scope is unknown;
- Guacamole RDP accepts any security mode and ignores the RDP certificate;
- token-bearing URLs exist in frontend memory/history contexts; CSP, referrer behavior, logging redaction, and token revocation need an end-to-end test;
- no session recording/audit configuration was found;
- there is no SSH connection constructor even though SSH is a future hybrid-lab goal;
- no proof exists that one student's network can never reach another student's connection or VM; application ownership checks alone are not a network boundary.

## Required pre-Phase-1 network proof

An operator must collect `ip -br link`, `ip -br addr`, `ip route`, `/etc/network/interfaces`, `pve-firewall status`, datacenter/node/VM firewall configuration, and upstream ACL/NAT data on PVE without changing them. The design must then be reviewed with packet-level negative tests from a disposable non-production probe: management, Nexus internals, household LAN, other attempts, IPv6, DNS tunneling, and arbitrary RFC1918 must all fail. Those active tests belong to an authorized later staging phase, not Phase 0.
