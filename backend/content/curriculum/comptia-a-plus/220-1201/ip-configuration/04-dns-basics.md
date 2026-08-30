---
lesson_key: lesson.aplus.core1.ip_configuration.dns_basics
title: DNS Basics
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
  - lesson.aplus.core1.ip_configuration.default_gateway
estimated_minutes: 13
status: draft
source_name: "CompTIA A+ Certification Exam Objectives (Core 1, 220-1201), objectives 2.5 and 5.7"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

Computers route traffic using IP addresses, but people use **names** like
`www.comptia.org` or `fileserver01`. **DNS** (Domain Name System) is the
"phone book" that translates a name into an IP address.

When you open `intranet.company.com`, the PC asks its configured **DNS
server** (from `ipconfig /all`), gets back an IP such as `192.168.1.10`, and
*then* connects. If DNS can't answer, the connection never starts — even
though the network itself is perfectly fine.

For A+ you need beginner-level DNS: what it does, where the PC gets its DNS
server address, and how to recognise a DNS problem. Record types (A, CNAME,
MX, TXT) and how DNS servers talk to each other are Network+ depth.

## 2. Why does an IT worker care?

DNS failures produce a signature symptom: **"I can ping `8.8.8.8` but not
`google.com`,"** or "some sites work, one doesn't." The network is up, the
gateway is fine — names just aren't resolving. Knowing that lets you skip the
cable and the router and go straight to the DNS setting or the DNS server.

## 3. Watch / read

- **Professor Messer – "Domain Name System (DNS)" (220-1201)** – what DNS is
  and the client's role, at A+ level. *(required)*
- **Professor Messer – "Network Troubleshooting" (220-1201)** – the "IP works,
  names don't" pattern and `nslookup`. *(optional)*
- **Microsoft Learn – "nslookup"** – official command reference. *(optional)*

## 4. What you actually need to remember

- DNS turns **names → IP addresses**. No DNS, no name-based connections.
- The PC's DNS server address comes from **DHCP** (or a static entry). See it
  with `ipconfig /all` on the **"DNS Servers"** line.
- On a company network the DNS server is usually an **internal server** so that
  internal names (`fileserver01`, `intranet.company.com`) resolve. A PC stuck
  on a random public DNS often can't find internal resources.
- Classic DNS symptom: **`ping 8.8.8.8` works, `ping google.com` fails** ("could
  not find host"). Network = fine. DNS = broken.
- Tools: `nslookup <name>` asks DNS directly and shows which server answered.
  `ipconfig /flushdns` clears the local cache when a name resolves to a stale
  (old) address.
- A single site failing for one user, while everyone else is fine, is often a
  local `hosts` file entry or cached bad record — not the DNS server.

## 5. Real workplace example

A user says "the internet is broken." You check: `ipconfig` looks healthy,
`ping 1.1.1.1` replies fine, but `ping companyportal.com` returns "could not
find host companyportal.com". `ipconfig /all` shows the DNS server set to
`8.8.8.8` instead of the internal `192.168.1.10` — someone changed it while
troubleshooting Wi-Fi at home and never changed it back. You set the adapter
to obtain DNS automatically, `ipconfig /renew`, `ipconfig /flushdns`,
`nslookup companyportal.com` now resolves against `192.168.1.10`, and the site
loads. Verified.

## 6. Commands / tools

```
C:\> nslookup google.com                 # ask DNS for this name
C:\> nslookup fileserver01 192.168.1.10   # ask a specific DNS server
C:\> ipconfig /displaydns                 # what's in the local cache
C:\> ipconfig /flushdns                   # clear the local cache
```

Read `nslookup` output for two things: **which server answered** ("Server:" /
"Address:") and **whether you got an answer** or "Non-existent domain" /
"request timed out".

## 7. Interview / example question

**"How would you troubleshoot a computer that can reach IP addresses but not
host names?"**

Model answer outline: that points at DNS, not connectivity. I confirm with
`ping 8.8.8.8` (works) versus `ping <name>` (fails). Then `ipconfig /all` to
see the configured DNS server — is it the right one for this network? I try
`nslookup <name>` to see if the server responds. Fixes range from switching the
adapter back to automatic DNS and `ipconfig /renew` / `/flushdns`, to
escalating if the DNS server itself is down. Then I verify a name resolves and
the resource opens.

## 8. Quick Check

Quick Check questions for this lesson are tagged to objectives `2.5` and `5.7`
in the module question bank.
