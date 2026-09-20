---
lesson_key: lesson.aplus.network.devices_poe
title: Routers, Switches, Access Points, Firewalls & PoE
certification_version: comptia_aplus_220-1201
domain: '2.0'
module: module.aplus.core1.network_services_troubleshooting
lesson_order: 5
importance: job_critical
learning_relationship: new
objectives:
- '2.5'
estimated_minutes: 40
status: published
summary: Identify network-device roles and PoE/access-layer components from what they
  actually do.
quick_check:
  title: "Quick Check \u2014 Routers, Switches, Access Points, Firewalls & PoE"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M7Q020
  - M7Q021
  - M7Q022
  - M7Q023
---

# 1. What is this?
Networks combine devices with different jobs: routers move traffic between networks, switches connect devices inside LANs, access points bridge wireless clients to the LAN, firewalls enforce traffic policy, and patch panels organize permanent cabling.

# 2. Why does an IT worker care?
Support technicians constantly trace a path: client NIC → cable/Wi-Fi → switch/AP → router/firewall → ISP/remote service. Misidentifying a device leads to bad tests and bad escalations.

# 3. Watch / Read
**Required:** Professor Messer — *Network Devices (220-1201)*.

# 4. What you actually need to remember
- **Router:** moves traffic between IP networks and often provides gateway/NAT functions in SOHO equipment.
- **Managed switch:** supports configurable features such as VLANs; unmanaged switches provide basic switching without that management plane.
- **Access point:** provides Wi-Fi access to a wired LAN.
- **Firewall:** allows/blocks traffic according to policy.
- **Patch panel:** passive termination/organization—not a switch.
- **PoE switch/injector:** supplies power over compatible Ethernet links to devices such as APs/phones/cameras.
- **Cable/DSL modem / ONT:** terminates different ISP access technologies.
- **NIC:** endpoint network interface; **MAC address** identifies a network interface at the local-link layer.

# 5. At work
An AP powers off after being moved to a different switch port. Before replacing the AP, verify whether the new port supplies compatible PoE and whether the cable/link is good.

# 6. Commands / Tools
Use switch/AP indicators and management data only if your role permits. A passive patch panel will not have a management interface or switch-port configuration.

# 7. Interview / Explain
Explain router vs switch vs access point in plain language.

# 8. Quick Check
Use Module 7 Quick Check 5: Q020, Q021, Q022, Q023.
