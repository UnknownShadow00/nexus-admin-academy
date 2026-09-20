---
lesson_key: lesson.aplus.network.host_services
title: Network Host Services & Appliances
certification_version: comptia_aplus_220-1201
domain: '2.0'
module: module.aplus.core1.network_services_troubleshooting
lesson_order: 3
importance: working_knowledge
learning_relationship: new
objectives:
- '2.3'
estimated_minutes: 40
status: published
summary: Recognize common network services/appliances so symptoms can be routed to
  the right dependency and team.
quick_check:
  title: "Quick Check \u2014 Network Host Services & Appliances"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M7Q010
  - M7Q011
  - M7Q012
  - M7Q013
---

# 1. What is this?
Organizations depend on services such as DNS, DHCP, file/print, mail, web, database, AAA/authentication, NTP, and Syslog. They may also use proxies, spam gateways, unified security appliances, and load balancers. Embedded/IoT and industrial/SCADA systems can be networked too.

# 2. Why does an IT worker care?
A desktop technician rarely administers every server, but must identify **which dependency is likely failing**. "The network is down" may actually be a name-resolution, authentication, file-share, time, or print-service problem.

# 3. Watch / Read
**Required:** Professor Messer — *Network Services (220-1201)*.

# 4. What you actually need to remember
- DNS resolves names; DHCP leases client configuration.
- NTP keeps system time synchronized; bad time can break authentication/certificates.
- Syslog centralizes device/service logs.
- AAA services support authentication, authorization, and accounting.
- A proxy intermediates client requests; a load balancer distributes service requests.
- UTM/security appliances combine multiple security/network functions.
- IoT/embedded/SCADA devices may have strict vendor/change windows—do not treat them like disposable home gadgets.

# 5. At work
If users can reach a server by IP but not name, the dependency points toward DNS—not the physical switch. If only authentication fails across many services at the same time, think identity/AAA before replacing client NICs.

# 6. Commands / Tools
Combine user scope, timestamps, and client evidence with service-status/log evidence available to your role. Escalate with a dependency hypothesis, not just "server problem."

# 7. Interview / Explain
Explain the difference between DNS, DHCP, and NTP in one sentence each.

# 8. Quick Check
Use Module 7 Quick Check 3: Q010, Q011, Q012, Q013.
