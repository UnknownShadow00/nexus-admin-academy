---
lesson_key: lesson.aplus.network.troubleshooting
title: Evidence-First Network Troubleshooting
certification_version: comptia_aplus_220-1201
domain: '2.0'
module: module.aplus.core1.network_services_troubleshooting
lesson_order: 7
importance: job_critical
learning_relationship: deep_dive
objectives:
- '5.5'
- '2.2'
- '2.6'
- '2.8'
estimated_minutes: 45
status: published
summary: Diagnose limited connectivity, intermittent Wi-Fi, latency/jitter, port flapping,
  interference, and authentication failures using evidence.
quick_check:
  title: "Quick Check \u2014 Evidence-First Network Troubleshooting"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M7Q031
  - M7Q032
  - M7Q033
  - M7Q037
---

# 1. What is this?
Network troubleshooting is not a list of magic resets. It is controlled isolation: decide whether the failure is physical link, radio, addressing, name resolution, authentication, path quality, or the destination service.

# 2. Why does an IT worker care?
Intermittent problems create expensive tickets because the symptom can disappear before the technician arrives. Good evidence—scope, timestamps, AP/link state, address config, latency/jitter, and repeatable tests—turns "random Wi-Fi" into something another team can act on.

# 3. Watch / Read
**Required:** Professor Messer — *Troubleshooting Networks (220-1201)*.

# 4. What you actually need to remember
- **Limited connectivity / APIPA:** investigate DHCP/link path before DNS.
- **Intermittent wireless:** compare location, AP, band/channel, interference, device scope, and time pattern.
- **High latency:** response delay; **jitter:** variation in delay—especially harmful to real-time voice/video.
- **Port flapping:** a switch interface repeatedly transitions up/down; investigate cabling, endpoint, power, and port evidence.
- **Authentication failure:** distinguish "cannot join/authenticate" from "joined but cannot reach a service."
- Change one variable at a time, retest the **original symptom**, and document evidence.

# 5. At work
VoIP becomes robotic every afternoon in one area. A successful speed test does not close the case. Gather latency/jitter/packet-quality evidence and compare wireless/channel use during the affected period.

# 6. Commands / Tools
Review `ipconfig`, `ping`, `nslookup`, and path tests from Module 1; pair them with a Wi-Fi analyzer, cable tester, link indicators, and infrastructure evidence available to your role.

# 7. Interview / Explain
Walk through how you would isolate "Wi-Fi says connected but calls are choppy."

# 8. Quick Check
Use Module 7 Quick Check 7: Q031, Q032, Q033, Q037.
