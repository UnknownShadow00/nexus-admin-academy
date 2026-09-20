---
lesson_key: lesson.aplus.core1.networking_fundamentals.tcp_udp_ports
title: TCP vs UDP and the Ports You Must Know
certification_version: comptia_aplus_220-1201
domain: "2.0"
module: module.aplus.core1.networking_fundamentals
importance: job_critical
learning_relationship: new
objectives:
  - "2.1"
estimated_minutes: 12
status: draft
source_name: "CompTIA A+ Certification Exam Objectives (Core 1, 220-1201)"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

TCP and UDP are the two transport protocols that carry almost all network
traffic. TCP sets up a connection, checks that every piece arrives, and
resends anything lost. UDP just sends and hopes — no setup, no delivery
guarantee, less overhead.

A *port* is a number that tells the receiving computer which program the
traffic is for. Web traffic goes to port 443, email submission to 587, and so
on. The A+ exam expects a handful of these from memory.

## 2. Why does an IT worker care?

When a user says "the website loads but email is broken", the fastest triage
is: which port, TCP or UDP, and is it reachable? Knowing that HTTPS is TCP 443
and DNS is UDP/TCP 53 turns a vague complaint into a testable question.

## 3. What you need to remember

- **TCP** — connection-oriented, ordered, reliable, retransmits. Web, email,
  remote desktop, file transfer.
- **UDP** — connectionless, no retransmit, low latency. DNS lookups, DHCP,
  streaming, VoIP media.
- Ports to know cold: 20/21 FTP, 22 SSH, 25 SMTP, 53 DNS, 67/68 DHCP,
  80 HTTP, 443 HTTPS, 3389 RDP.

## 5. Real workplace example

A laptop gets an APIPA address (169.254.x.x). DHCP uses **UDP 67/68**; if the
switch port or the DHCP server is down, the client never gets a lease and
falls back to APIPA. You check the DHCP scope before touching the laptop.

## 7. Interview / example question

*"A user can ping by IP but not by name. Where do you look first?"* — Name
resolution is DNS (port 53). Confirm the client has a DNS server set, then
test that server directly with `nslookup`.

## 8. Quick Check

Quick Check questions for this lesson are tagged to objective `2.1` in the
module question bank; they are not stored inline.
