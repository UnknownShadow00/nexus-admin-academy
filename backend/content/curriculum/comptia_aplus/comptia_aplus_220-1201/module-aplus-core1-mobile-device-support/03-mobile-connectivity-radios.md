---
lesson_key: lesson.aplus.mobile.connectivity_radios
title: Wi-Fi, Cellular, SIM/eSIM, Hotspots & Bluetooth
certification_version: comptia_aplus_220-1201
domain: '1.0'
module: module.aplus.core1.mobile_device_support
lesson_order: 3
importance: job_critical
learning_relationship: deep_dive
objectives:
- '1.3'
estimated_minutes: 40
status: ready
summary: Configure and isolate Wi-Fi, cellular, SIM/eSIM, hotspot, Bluetooth, and
  location-service connectivity.
quick_check:
  title: "Quick Check \u2014 Wi-Fi, Cellular, SIM/eSIM, Hotspots & Bluetooth"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - Q015
  - Q016
  - Q017
  - Q019
---

# Lesson 3 — Wi-Fi, Cellular, SIM/eSIM, Hotspots & Bluetooth

## 1. What is this?
A phone or tablet can have several independent radio/network paths: **Wi-Fi, cellular data, Bluetooth, hotspot/tethering, and location services**. A strong technician tests them separately instead of treating “my phone has no internet” as one undivided problem.

This lesson builds on Module 1's habit of changing one variable at a time.

## 2. Why does an IT worker care?
Mobile users move between home Wi-Fi, corporate Wi-Fi, cellular networks, hotspots, vehicles, and Bluetooth accessories all day. The first job is to determine **which path is failing**.

## 3. Watch / Read
**Required:** Professor Messer — *Mobile Device Networks (220-1201)* — 10:14  
https://www.professormesser.com/free-a-plus-training/220-1201/220-1201-video/mobile-device-networks-220-1201/

**Optional:** Android Help — *Share a mobile connection by hotspot or tethering*  
https://support.google.com/android/answer/9059108?hl=en

## 4. What you actually need to remember
- **3G/4G/5G:** generations of cellular network service.
- **Wi-Fi:** local wireless network access, separate from cellular data.
- **SIM:** removable subscriber-identity card for cellular service.
- **eSIM:** electronically provisioned subscriber identity; no removable card is required.
- **Hotspot/tethering:** shares a device's connection with another device. Carrier plan, data caps, and company policy may matter.
- **Bluetooth pairing:** enable Bluetooth → enable/enter pairing mode → find/select device → enter/confirm PIN if required → test connectivity.
- **Location services:** may use GPS plus cellular/Wi-Fi-derived location; app permission must also allow access.

Isolation examples:
- Wi-Fi fails, cellular works → investigate the Wi-Fi path.
- Cellular fails, Wi-Fi works → investigate service/SIM/eSIM/carrier/configuration.
- Both fail → broaden the investigation to device settings, airplane mode, OS state, policy, or a wider outage.

Do not “fix” one path by permanently disabling security or management controls.

## 5. At work
A phone cannot open the company portal while on office Wi-Fi. The technician disables Wi-Fi temporarily (policy permitting) and tests the same site over cellular data. It works. That evidence does not prove exactly what is wrong, but it strongly narrows the fault to the Wi-Fi path instead of the entire phone.

## 6. Commands / Tools
Mobile devices are usually settings-driven rather than CLI-driven:
- Wi-Fi network details
- cellular/data settings
- SIM/eSIM status
- Bluetooth device list
- hotspot settings
- airplane mode status
- location permissions
- carrier/status information

## 7. Interview / Explain
**Prompt:** “A user's phone works on cellular but not Wi-Fi. What does that tell you?”

A strong answer says the successful path is useful evidence and the investigation should focus on Wi-Fi configuration/network conditions rather than replacing unrelated hardware.

## 8. Quick Check
Use bank questions: **Q015, Q016, Q017, Q019**.
