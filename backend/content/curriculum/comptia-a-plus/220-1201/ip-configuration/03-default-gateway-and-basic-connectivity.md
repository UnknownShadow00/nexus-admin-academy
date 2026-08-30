---
lesson_key: lesson.aplus.core1.ip_configuration.default_gateway
title: Default Gateway and Basic Connectivity
certification_version: comptia_aplus_220-1201
domain: "2.0"
module: module.aplus.core1.ip_configuration
importance: job_critical
learning_relationship: new
objectives:
  - "2.5"
  - "5.7"
builds_on:
  - lesson.aplus.core1.ip_configuration.ipv4_basics
estimated_minutes: 13
status: draft
source_name: "CompTIA A+ Certification Exam Objectives (Core 1, 220-1201), objectives 2.5 and 5.7"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

The **default gateway** is the address the computer sends traffic to when the
destination is **not on the local network**. It is almost always the local
router.

The subnet mask decides "local or not":

- Destination on the **same** local network → the PC talks to it directly.
- Destination **anywhere else** (another office subnet, the internet) → the PC
  hands the packet to the **default gateway**, which forwards it on.

So the gateway must be **present** and must be **on the same subnet** as the
PC. A PC with address `192.168.1.42` / mask `255.255.255.0` needs a gateway
like `192.168.1.1`. A gateway of `10.0.0.1` on that PC is unreachable and
nothing outside the local network will work.

**Connectivity** is usually tested with `ping`, which sends a small "are you
there?" packet and waits for a reply.

## 2. Why does an IT worker care?

A missing or wrong gateway produces a very specific symptom: **local things
work, everything else fails.** The user can reach the printer next to them but
not the internet or head-office systems. Recognising that pattern points you
straight at the gateway instead of blaming DNS or the application.

## 3. Watch / read

- **Professor Messer – "Configuring a SOHO Network" (220-1201)** – covers IP,
  mask, gateway, and how a client uses them. *(required)*
- **Professor Messer – "Network Troubleshooting" (220-1201)** – the "local
  works, remote doesn't" pattern and using `ping`. *(optional)*

## 4. What you actually need to remember

- The default gateway is the **way out** of the local network. No gateway (or a
  wrong one) = no access to anything remote.
- The gateway address must be **on the same subnet** as the PC.
- Quick test order with `ping`:
  1. `ping 127.0.0.1` – the PC's own TCP/IP stack ("loopback"). Fails only if
     TCP/IP itself is broken.
  2. `ping <your own IP>` – confirms the adapter is configured.
  3. `ping <default gateway>` – can you reach the router? If this fails, the
     problem is local: cable, switch, wrong subnet, or the router.
  4. `ping 8.8.8.8` (a known internet IP) – can you get *out*? If gateway ping
     works but this fails, look upstream of the router.
  5. `ping <a name>` e.g. `ping google.com` – if IPs work but names don't, it's
     **DNS** (next lesson), not connectivity.
- A ping that "times out" isn't always a real outage — some devices and
  firewalls are set to ignore ping. Use it as one clue, not proof.

## 5. Real workplace example

A user can print to the copier down the hall but no websites load and Outlook
can't connect. `ipconfig` shows a valid `192.168.1.55 / 255.255.255.0` but the
**Default Gateway line is blank**. Local devices work because they're on the
same subnet; nothing else does because there's no way out. The adapter had a
half-entered static config. You set it back to "Obtain automatically",
`ipconfig /renew`, confirm the gateway is now `192.168.1.1`, `ping` the gateway
and `8.8.8.8` successfully, and the user is back online.

## 6. Commands / tools

```
C:\> ping 192.168.1.1        # the default gateway
C:\> ping 8.8.8.8            # a known internet IP (skips DNS)
C:\> ping -n 4 10.0.0.5      # send 4 pings (Windows default is already 4)
```

`ping` uses names too (`ping intranet.company.com`), but for connectivity
testing, **ping an IP first** so a DNS problem doesn't look like an outage.

## 7. Interview / example question

**"A user can reach devices on their own floor but nothing on the internet or
at head office. Where do you look first?"**

Model answer outline: that pattern says local network is fine but there's no
route off it — I check the **default gateway**. Is it present, on the right
subnet, and can the PC `ping` it? If the gateway is missing or wrong, fix the
IP config (usually switch back to DHCP and renew). If the gateway pings but the
internet doesn't, the issue is past the router and I escalate.

## 8. Quick Check

Quick Check questions for this lesson are tagged to objectives `2.5` and `5.7`
in the module question bank.
