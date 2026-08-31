---
lesson_key: lesson.aplus.network.ports_protocols
title: Ports, Protocols & What Services Are Listening
certification_version: comptia_aplus_220-1201
domain: '2.0'
module: module.aplus.core1.network_services_troubleshooting
lesson_order: 1
importance: working_knowledge
learning_relationship: new
objectives:
- '2.1'
estimated_minutes: 35
status: published
summary: Connect common ports to the services technicians troubleshoot, with TCP/UDP
  context rather than pure memorization.
quick_check:
  title: "Quick Check \u2014 Ports, Protocols & What Services Are Listening"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M7Q001
  - M7Q002
  - M7Q004
  - M7Q005
---

# 1. What is this?
A **port** is a logical service number used with TCP or UDP so one host can run many network applications at the same IP address. The port does not identify the computer; it helps identify the application/service conversation on that computer.

For A+ you should recognize the common defaults: FTP 20/21, SSH 22, Telnet 23, SMTP 25, DNS 53, DHCP 67/68, HTTP 80, POP3 110, IMAP 143, NetBIOS 137–139, LDAP 389, HTTPS 443, SMB/CIFS 445, and RDP 3389.

# 2. Why does an IT worker care?
Port knowledge helps you read firewall rules, interpret "the site works but remote desktop does not," and ask whether the **service** is unavailable rather than declaring the whole network down.

# 3. Watch / Read
**Required:** Professor Messer — *Common Ports (220-1201)*.

# 4. What you actually need to remember
- **TCP** is connection-oriented and emphasizes reliable, ordered delivery.
- **UDP** has less overhead and does not establish the same reliable session.
- Start with the service name and purpose; the number becomes easier to retain.
- A default port is a convention, not proof that a service is running or reachable.
- HTTPS 443 protects web traffic with TLS; SSH 22 is the common secure remote shell; RDP 3389 is common Windows graphical remote access.

# 5. At work
A user can browse secure websites but cannot reach an approved RDP host. That evidence says basic IP connectivity and HTTPS may be fine. You now investigate RDP/service/firewall policy rather than "restarting the internet."

# 6. Commands / Tools
Use service tests only when approved. `netstat` can show listening/established connections on a client; Module 11 will deepen Windows CLI administration.

# 7. Interview / Explain
Explain why "I can ping it" does **not** prove a specific application service is working.

# 8. Quick Check
Use Module 7 Quick Check 1: Q001, Q002, Q004, Q005.
