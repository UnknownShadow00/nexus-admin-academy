---
lesson_key: lesson.aplus.network.wireless
title: Wireless Networks, Bands & Interference
certification_version: comptia_aplus_220-1201
domain: '2.0'
module: module.aplus.core1.network_services_troubleshooting
lesson_order: 2
importance: job_critical
learning_relationship: deep_dive
objectives:
- '2.2'
- '5.5'
estimated_minutes: 40
status: published
summary: Use band, channel, range, interference, and radio-specific evidence to troubleshoot
  wireless rather than guessing.
quick_check:
  title: "Quick Check \u2014 Wireless Networks, Bands & Interference"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M7Q006
  - M7Q007
  - M7Q008
  - M7Q009
---

# 1. What is this?
Wi-Fi uses radio spectrum instead of a cable. A+ expects practical awareness of **2.4 GHz, 5 GHz, and 6 GHz**, channel selection/width, regulatory considerations, and nearby wireless technologies such as Bluetooth, NFC, and RFID.

# 2. Why does an IT worker care?
Wireless tickets are often intermittent. A device may show "connected" while users experience latency, jitter, poor VoIP, congestion, or roaming problems. Support work is about proving whether the failure follows the device, location, band, access point, or network service.

# 3. Watch / Read
**Required:** Professor Messer — *Wireless Network Technologies (220-1201)*.

# 4. What you actually need to remember
- **2.4 GHz:** longer practical range and broad compatibility, but more congestion/interference and fewer clean channel choices.
- **5 GHz:** more channel capacity and typically less 2.4-GHz interference, but generally shorter range through obstacles.
- **6 GHz:** newer spectrum with more clean capacity, but requires compatible equipment and is subject to local regulatory rules.
- **Bluetooth:** short-range peripheral/personal-device networking.
- **NFC:** very short-range tap/proximity use.
- **RFID:** identification/tracking using radio tags/readers.
- Wider channels can increase throughput but consume more spectrum; channel/band choice should be evidence-driven.

# 5. At work
Warehouse handhelds disconnect only near two loading lanes while wired stations stay stable. Rebooting every scanner is weak evidence. Compare affected APs, signal/quality, band/channel conditions, and a known-good scanner.

# 6. Commands / Tools
A Wi-Fi analyzer can show nearby SSIDs, channels, band usage, and signal information. Do not treat one signal-strength number as the full diagnosis.

# 7. Interview / Explain
Explain why moving a client from 2.4 GHz to 5/6 GHz can help congestion but may reduce usable range.

# 8. Quick Check
Use Module 7 Quick Check 2: Q006, Q007, Q008, Q009.
