---
lesson_key: lesson.aplus.core2.windows_support_tools.network_commands
title: Network Commands as Evidence
certification_version: comptia_aplus_220-1202
domain: "1.0"
module: module.aplus.core2.windows_support_tools
importance: job_critical
learning_relationship: review
objectives: ["1.2"]
estimated_minutes: 11
status: published
source_name: "CompTIA A+ 220-1202 objective 1.2; review of Nexus IP Configuration module"
source_url: "https://www.comptia.org/certifications/a"
---

## 1. What is this?

`ipconfig`, `ping`, and `nslookup` turn a vague connectivity complaint into
configuration, reachability, and name-resolution evidence. This lesson reviews
the existing IP Configuration module at Core 2 tool-selection depth.

## 2. Why does an IT worker care?

Evidence prevents unrelated fixes and makes escalation useful.

## 3. Watch / read

- Microsoft Windows command references for `ipconfig`, `ping`, and `nslookup`. *(required)*

## 4. What you need to remember

- `ipconfig /all`: address, gateway, DHCP, and DNS configuration.
- `ping`: reachability/latency clue, not proof that every service works. A failed
  ping is not conclusive either, because ICMP may be filtered.
- `nslookup`: asks DNS directly.
- Test in a sequence and record output; do not infer root cause from one command.

## 5. Real workplace example

Public IP ping succeeds but a hostname fails. `nslookup` times out against the
configured resolver, narrowing the incident to DNS.

## 6. Commands / tools

`ipconfig /all`, `ping <gateway>`, `ping <known IP>`, `nslookup <name>`.

## 7. Interview / example

**What does a successful ping prove?** That ICMP received a reply on that path;
it does not prove DNS, HTTPS, authentication, or the user's application works.

## 8. Quick Check

Four formative review questions mapped to objective 1.2.
