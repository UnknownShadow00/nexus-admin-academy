---
lesson_key: lesson.aplus.core1.ip_configuration.ipv4_basics
title: IPv4 Configuration Basics
certification_version: comptia_aplus_220-1201
domain: "2.0"
module: module.aplus.core1.ip_configuration
importance: job_critical
learning_relationship: new
objectives:
  - "2.6"
estimated_minutes: 14
status: published
source_name: "CompTIA A+ Certification Exam Objectives (Core 1, 220-1201), objective 2.6"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

Every device on a network needs an **IPv4 address** so other devices can find
it. An IPv4 address is four numbers from 0 to 255, separated by dots, like
`192.168.1.42`.

A working IPv4 setup on a normal office PC has four parts:

- **IP address** – this computer's own address, e.g. `192.168.1.42`
- **Subnet mask** – tells the computer which addresses are "local" (on the same
  network) and which are "far away", e.g. `255.255.255.0`
- **Default gateway** – the address of the router that forwards traffic to
  other networks, including the internet, e.g. `192.168.1.1`
- **DNS server** – the address of the service that turns names like
  `intranet.company.com` into IP addresses, e.g. `192.168.1.10`

You will also hear about **IPv6**, a newer, much larger addressing system that
uses long hexadecimal addresses like `fe80::1c2d:...`. For A+ support work you
just need to **recognise** an IPv6 address when you see one; you configure IPv4
far more often.

## 2. Why does an IT worker care?

"My computer can't get online" is one of the most common help desk tickets. The
first thing a technician does is look at these four values. If the IP address,
subnet mask, gateway, or DNS server is wrong or missing, that one screen
usually tells you where the problem is before you touch anything else.

## 3. Watch / read

- **Professor Messer – "IPv4 and IPv6" (220-1201)** – short, beginner-level
  walkthrough of what an address, mask, and gateway are. *(required)*
- **Microsoft Learn – "Change TCP/IP settings"** – the official steps for
  viewing and setting IPv4 on Windows. *(optional)*

These support the lesson; they do not replace it.

## 4. What you actually need to remember

- An IPv4 address is `x.x.x.x`, each part `0`–`255`.
- The four values that matter on a client: **IP address, subnet mask, default
  gateway, DNS server**.
- **Static** configuration = a human entered the values and they do not change
  automatically.
  **Dynamic** configuration = the computer was given the values automatically
  by DHCP (next lesson). Most workstations are dynamic.
- `255.255.255.0` is by far the most common home/small-office subnet mask. With
  that mask, devices whose first three numbers match (e.g. `192.168.1.x`) are
  on the same local network.
- Private address ranges you will see constantly on internal networks:
  `10.x.x.x`, `172.16.x.x`–`172.31.x.x`, and `192.168.x.x`.
- If a device has **no** IPv4 address, or an address starting `169.254`, it is
  not properly on the network. (That specific case is the next lesson.)

## 5. Real workplace example

A user says the shared drive won't open. You check their network settings and
see:

```
IPv4 Address. . . . . . . . . . . : 192.168.1.42
Subnet Mask . . . . . . . . . . . : 255.255.0.0
Default Gateway . . . . . . . . . : 192.168.1.1
```

The address and gateway look fine, but the **subnet mask is wrong** – it should
be `255.255.255.0` like everyone else in the office. With `255.255.0.0` the PC
thinks devices such as `192.168.250.5` are "local" and tries to reach them
directly instead of sending them through the gateway (you will see exactly why
that breaks things in the *Default Gateway* lesson). Correcting the mask (or
letting DHCP set it) fixes the ticket.

## 6. Commands / tools

You will do this hands-on in the "Windows Network Troubleshooting Commands"
lesson, but the quick version:

```
C:\> ipconfig
```

shows the IP address, subnet mask, and default gateway for each adapter.

```
C:\> ipconfig /all
```

adds the DNS servers, whether DHCP is enabled, and the DHCP server's address.

## 7. Interview / example question

**"What information do you need to see before you can say a PC's IP
configuration is healthy?"**

Model answer outline: the IPv4 address (and that it is in the expected range,
not `169.254.x.x` and not blank), the subnet mask (matches the rest of the
network), the default gateway (present and on the same subnet), and at least
one DNS server. If any of those is missing or clearly wrong, that is where you
start.

## 8. Quick Check

Quick Check questions for this lesson are tagged to objective `2.6` in the
module question bank.
