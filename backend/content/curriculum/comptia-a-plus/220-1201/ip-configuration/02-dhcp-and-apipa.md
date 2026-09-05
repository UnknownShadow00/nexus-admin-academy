---
lesson_key: lesson.aplus.core1.ip_configuration.dhcp_and_apipa
title: DHCP and APIPA
certification_version: comptia_aplus_220-1201
domain: "2.0"
module: module.aplus.core1.ip_configuration
importance: job_critical
learning_relationship: new
objectives:
  - "2.4"
  - "2.6"
  - "5.5"
builds_on:
  - lesson.aplus.core1.ip_configuration.ipv4_basics
estimated_minutes: 14
status: published
source_name: "CompTIA A+ Certification Exam Objectives (Core 1, 220-1201), objectives 2.4, 2.6, and 5.5"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

**DHCP** (Dynamic Host Configuration Protocol) is the service that hands out IP
settings automatically. When a PC joins the network, it broadcasts a request;
a DHCP server (usually the router in a small office, or a Windows server in a
company) replies with an **IP address, subnet mask, default gateway, and DNS
server**, leased for a set time.

**APIPA** (Automatic Private IP Addressing) is Windows' fallback. If a PC is
set to get its address automatically but **gets no answer from any DHCP
server**, Windows selects a link-local address from **`169.254.0.0/16`** with
mask `255.255.0.0` (the first and last /24 blocks are reserved). APIPA itself
does not supply a default gateway or DNS server. Two link-local hosts on the
same local segment may communicate, but the client normally cannot reach the
internet or routed company resources.

**Seeing `169.254.x.x` almost always means: "I asked for an address and nobody
answered."**

## 2. Why does an IT worker care?

"No internet" tickets very often come down to DHCP. If you can look at an
address and instantly recognise `169.254.x.x` as *"DHCP failed"*, you have
already narrowed the problem to: the cable/Wi-Fi link, the switch port, or the
DHCP server itself — not the browser, not DNS, not the user's account.

## 3. Watch / read

- **Professor Messer – "Dynamic Host Configuration Protocol (DHCP)"
  (220-1201)** – how the lease process works, at A+ depth. *(required)*
- **Professor Messer – "APIPA and Link-Local Addresses" (220-1201)** – what a
  `169.254` address means and why you get one. *(optional)*

## 4. What you actually need to remember

- **DHCP gives out**: IP address, subnet mask, default gateway, DNS server(s) —
  for a limited **lease** time, then renews.
- The client-side switch is "Obtain an IP address automatically" (dynamic). If
  that is off and someone typed a bad static address, DHCP can't help.
- **APIPA = `169.254.x.x`, mask `255.255.0.0`; it supplies no gateway or DNS.**
- `169.254.x.x` on a DHCP-enabled adapter = the PC never got a DHCP reply.
  Common causes include a bad or intermittent link, a switch/VLAN path that
  cannot reach DHCP, or a DHCP service with no available lease.
- **Media disconnected** or an absent adapter points directly to the physical
  link or adapter state. An all-zero address by itself can also appear while a
  client is still waiting for configuration, so do not treat it as proof of a
  cable fault.
- First moves for an APIPA address: confirm the physical/Wi-Fi link, then try
  `ipconfig /release` followed by `ipconfig /renew`. If a renew still gives
  `169.254`, the problem is upstream (switch port or DHCP server).

## 5. Real workplace example

A user reports "internet is down." You remote in — no, you can't, they're
offline — so you walk over. `ipconfig` shows:

```
IPv4 Address. . . . . . . . . . . : 169.254.88.17
Subnet Mask . . . . . . . . . . . : 255.255.0.0
Default Gateway . . . . . . . . . :
```

APIPA. The Ethernet cable is seated, and the link light is on. You run
`ipconfig /release` then `ipconfig /renew` — still `169.254`. A colleague at
the next desk is fine, so the DHCP server is up. You check the wall port label
and the patch panel: this desk's cable is patched to a switch port that was
disabled during last week's move. Network team re-enables the port, you
`ipconfig /renew`, and the PC gets `192.168.1.60`. Verified: the user can open
the shared drive and a website.

## 6. Commands / tools

```
C:\> ipconfig /all          # is "DHCP Enabled" Yes? what's the "DHCP Server"?
C:\> ipconfig /release      # give up the current (or APIPA) address
C:\> ipconfig /renew        # ask DHCP again
```

Read the top of `ipconfig /all` first: **DHCP Enabled: Yes** with a `169.254`
address is the real APIPA case (asked DHCP, no reply). **DHCP Enabled: No**
means the adapter has a **manual (static)** config — DHCP isn't involved, so
check the typed-in IPv4 properties instead.

## 7. Interview / example question

**"A user's Windows PC has a `169.254.x.x` address and can't reach the company
network. What does that tell you, and what do you check?"**

Model answer outline: that address is APIPA, which means the PC asked for a
DHCP lease and got no response. I'd check the physical link (cable/port or
Wi-Fi), then `ipconfig /release` and `/renew`. If it still self-assigns, I
compare with a working neighbour to decide whether it's this desk's port or a
wider DHCP outage, then escalate the switch port or DHCP server. Finally I
verify the PC gets a real address and can reach a resource.

## 8. Quick Check

Quick Check questions for this lesson are tagged to objectives `2.4`, `2.6`, and `5.5`
in the module question bank.
