---
lesson_key: lesson.aplus.core1.ip_configuration.windows_commands
title: Windows Network Troubleshooting Commands
certification_version: comptia_aplus_220-1201
domain: "2.0"
module: module.aplus.core1.ip_configuration
importance: job_critical
learning_relationship: new
objectives:
  - "5.7"
  - "5.1"
builds_on:
  - lesson.aplus.core1.ip_configuration.ipv4_basics
  - lesson.aplus.core1.ip_configuration.dhcp_and_apipa
  - lesson.aplus.core1.ip_configuration.default_gateway
  - lesson.aplus.core1.ip_configuration.dns_basics
estimated_minutes: 16
status: draft
source_name: "CompTIA A+ Certification Exam Objectives (Core 1, 220-1201), objectives 5.7 and 5.1"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

A small set of built-in Windows commands lets you see a machine's network
state and test each layer in order. For A+ connectivity work the core four
are **`ipconfig`**, **`ping`**, **`nslookup`**, and the address-renewal pair
**`ipconfig /release` and `ipconfig /renew`**.

This lesson also puts them inside CompTIA's **six-step troubleshooting
methodology** (objective 5.1), because running commands without a method just
produces noise.

## 2. Why does an IT worker care?

These commands are how you turn "the internet is broken" into a specific,
provable fault. They're on every Windows machine, they need no admin rights to
*view* configuration, and a technician who uses them in a sensible order looks
competent and closes tickets faster.

## 3. Watch / read

- **Professor Messer – "Network Troubleshooting" (220-1201)** – `ipconfig`,
  `ping`, and `nslookup` demonstrated together. *(required)*
- **Microsoft Learn – "ipconfig"** – official command reference with every
  switch. *(required)*
- **Microsoft Learn – "ping"** and **"nslookup"** – official references.
  *(optional)*

## 4. What you actually need to remember

The commands:

| Command | What it shows / does |
|---|---|
| `ipconfig` | IPv4 address, subnet mask, default gateway per adapter |
| `ipconfig /all` | adds DNS servers, DHCP enabled?, DHCP server, MAC address, lease times |
| `ipconfig /release` | drops the current DHCP (or APIPA) address |
| `ipconfig /renew` | requests a fresh DHCP lease |
| `ipconfig /flushdns` | clears the local DNS name cache |
| `ping <IP or name>` | tests if a host answers; 4 requests by default on Windows |
| `nslookup <name>` | asks DNS to resolve a name; shows which server replied |

Sensible order for a "can't connect" ticket:

1. `ipconfig /all` – is there a real address, correct mask, a gateway, and a
   sensible DNS server? `169.254.x.x` = DHCP failed; blank = link down.
2. `ping 127.0.0.1` then `ping <own IP>` – is TCP/IP and the adapter OK?
3. `ping <default gateway>` – can you reach the router? (local vs. upstream)
4. `ping 8.8.8.8` – can you reach the internet by IP? (skips DNS)
5. `ping <a name>` / `nslookup <a name>` – does name resolution work?
6. Fix the lowest layer that failed, then **re-run the same commands to
   verify**, and document what you changed.

The six-step methodology (5.1), applied here:

1. **Identify the problem** – ask what changed, reproduce it, read `ipconfig`.
2. **Establish a theory** – e.g. "APIPA address → DHCP not reachable."
3. **Test the theory** – `ipconfig /release` + `/renew`; compare a working
   neighbour.
4. **Plan and act** – re-enable the switch port / fix the adapter / escalate.
5. **Verify full functionality** – real address, `ping` gateway + internet +
   a name, user opens their resource.
6. **Document** – what was wrong, what you did, how you confirmed it.

## 5. Real workplace example

Ticket: "Can't get email or the web." You run `ipconfig /all`:

```
   IPv4 Address. . . . . . . . . . . : 169.254.211.9 (Preferred)
   Subnet Mask . . . . . . . . . . . : 255.255.0.0
   Default Gateway . . . . . . . . . :
   DHCP Enabled. . . . . . . . . . . : Yes
   DHCP Server . . . . . . . . . . . :
```

Theory: APIPA, so no DHCP reply. Test: `ipconfig /release` then
`ipconfig /renew` → "unable to contact your DHCP server." The link light is
on and a neighbour is fine, so it's this desk. Act: network team finds the
patch cable in the wrong panel port and moves it. Verify: `ipconfig /renew`
gives `192.168.1.73`, `ping 192.168.1.1` and `ping 8.8.8.8` reply, `nslookup
mail.company.com` resolves, user sends a test email. Document in the ticket.

## 6. Commands / tools

```
C:\> ipconfig /all
C:\> ipconfig /release
C:\> ipconfig /renew
C:\> ipconfig /flushdns
C:\> ping 127.0.0.1
C:\> ping 192.168.1.1
C:\> ping 8.8.8.8
C:\> ping mail.company.com
C:\> nslookup mail.company.com
```

Note: viewing config with `ipconfig` needs no special rights; `release`/`renew`
and `flushdns` may prompt for an administrator command prompt on locked-down
machines.

## 7. Interview / example question

**"Walk me through how you'd troubleshoot a Windows PC that 'has no
internet'."**

Model answer outline: start with `ipconfig /all` to see the real state —
address, mask, gateway, DNS, DHCP. Form a theory from what's wrong (APIPA →
DHCP; blank gateway → routing; IP works but names don't → DNS). Test it with
`ping` from loopback outward and `nslookup`, and compare a working machine.
Fix the lowest failing layer, then re-run the same commands to prove it's
working end to end, and write up what changed.

## 8. Quick Check

Quick Check questions for this lesson are tagged to objectives `5.7` and `5.1`
in the module question bank.
