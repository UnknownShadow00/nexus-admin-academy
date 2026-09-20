# A+ IP Configuration editorial review

Review date: 2026-09-05
Bank: `backend/content/questions/aplus-ip-configuration.csv`
Quiz title: `A+ IP Configuration & Basic Connectivity — Module Bank`
Module: `module.aplus.core1.ip_configuration`
Verdict: **validated after repair**

## Authoritative scope

The repository's 220-1201 objective catalog is the scope authority. This bank
uses only these objectives:

| Objective | Repository definition | Bank mapping |
|---|---|---:|
| 2.4 | Explain common network configuration concepts, including DNS and DHCP leases, reservations, scopes, and exclusions. | 10 questions |
| 2.6 | Configure basic wired/wireless SOHO networks, including IPv4/IPv6, APIPA, static/dynamic addressing, subnet mask, and gateway. | 19 questions |
| 5.5 | Troubleshoot network issues, including limited or no connectivity. | 25 questions |

Counts include ordered multi-objective mappings, so they overlap. Primary
objective distribution is 2.4 × 10, 2.6 × 18, and 5.5 × 12. The prior 2.5,
5.1, and 5.7 mappings were rejected: 2.5 is network hardware, 5.1 is
motherboard/RAM/CPU/power troubleshooting, and 5.7 is a legacy Nexus alias
rather than an official 220-1201 objective.

## Coverage by subtopic

Tag-based counts overlap where one scenario tests more than one skill.

| Subtopic | Questions | Representation |
|---|---:|---|
| IPv4 address recognition and healthy client configuration | 3 | Syntax, expected values, and private/public distinction |
| Private/public IPv4 addressing | 1 | All three private ranges, contrasted with link-local and public space |
| Subnet mask | 3 | Meaning, wrong-mask effect, and gateway subnet check |
| Static vs. dynamic configuration | 5 | Identification, bad manual settings, pool conflict, reservation, short answer |
| DHCP | 8 | Supplied settings, lease renewal, scope exhaustion, reservation, reachability |
| APIPA/link-local IPv4 | 8 | Recognition, characteristics, causes, isolation, and free response |
| Default gateway | 7 | Purpose, same-subnet requirement, local-vs-remote symptom, upstream isolation |
| DNS client configuration and resolution | 12 | Purpose, internal resolver, IP-vs-name symptom, nslookup, verification |
| Basic IPv6 recognition | 1 | Recognizes an IPv6 link-local address without adding Network+ depth |
| Windows network commands | 13 | ipconfig, ping, nslookup, renew, flushdns, and evidence order |
| Applied scenarios/troubleshooting | 20 | Workstation, DHCP, gateway, DNS, and reachability decisions |

The bank intentionally has one basic IPv6-recognition item because objective
2.6 requires basic IPv6 configuration awareness, while the module's practical
promise is focused on common Windows IPv4 support. It does not introduce DNS
record administration, DHCP relay configuration, subnetting arithmetic, or
other unrelated Network+ depth to inflate the count.

## Question-by-question review

Every key was solved independently after the stem and distractors were
reviewed. `Q01` corresponds to CSV data row 2.

| ID | Type | Objective(s) | Verified answer | Focus / editorial result |
|---|---|---|---|---|
| Q01 | single | 2.6 | A | Valid IPv4 host syntax; invalid octet/delimiter distractors |
| Q02 | single | 2.6 | B | Subnet-mask purpose; routing wording clarified |
| Q03 | single | 2.6 | C | Static configuration; removed claim that it can never change |
| Q04 | multi | 2.6 | A, C, E | Three private ranges; APIPA correctly identified as link-local |
| Q05 | single | 2.6, 5.5 | A | Wrong /16 mask on a /24 office LAN; effect scoped to remote subnets |
| Q06 | single | 2.6 | B | IPv6/link-local recognition at beginner depth |
| Q07 | multi | 2.6 | B, C, E | Usable client address, mask, and same-subnet gateway |
| Q08 | single | 2.4 | D | Typical DHCP options and lease qualification |
| Q09 | single | 2.6 | A | APIPA `169.254.0.0/16`; no incorrect usable-range endpoints |
| Q10 | single | 2.6, 5.5 | C | DHCP-enabled 169.254 diagnosis with explicit assumption |
| Q11 | single | 2.6 | D | What APIPA supplies; gateway/DNS claim made precise |
| Q12 | single | 2.6, 5.5 | B | Same-switch/VLAN comparison makes the local-path inference valid |
| Q13 | single | 2.4, 5.5 | A | Scope exhaustion without giving the term away in the stem |
| Q14 | single | 2.6, 5.5 | C | Replaced ambiguous 0.0.0.0/cable item with manual-setting diagnosis |
| Q15 | multi | 2.4, 5.5 | A, C | Two unambiguous DHCP-reachability causes; removed unplugged-link ambiguity |
| Q16 | single | 2.4, 2.6 | D | Static address inside DHCP pool and conflict risk |
| Q17 | single | 2.4 | A | DHCP reservation for a centrally managed fixed assignment |
| Q18 | single | 2.6 | C | Default-gateway role |
| Q19 | single | 2.6 | C | Same-subnet gateway candidate; avoids claiming the actual router address |
| Q20 | single | 2.6, 5.5 | D | Local IP works/remote IP fails; DNS explicitly excluded |
| Q21 | single | 5.5 | A | Known-IP-before-name test separates connectivity from DNS |
| Q22 | single | 5.5 | C | Multi-client upstream failure with multiple known targets |
| Q23 | single | 5.5 | C | Replaced true/false trick with ICMP-blocked, HTTPS-working scenario |
| Q24 | single | 2.4 | D | DNS purpose |
| Q25 | single | 2.4, 5.5 | A | Known service works by IP but not name |
| Q26 | single | 2.4, 5.5 | C | Approved internal resolver and private-name rationale |
| Q27 | single | 2.4, 5.5 | A | Explicit nslookup comparison; removed public-resolver assumption |
| Q28 | multi | 5.5 | B, D, E | Correct diagnostic tools; shuffled repeated A/B/C pattern |
| Q29 | single | 5.5 | D | Verify original function and document after a DNS correction |
| Q30 | single | 5.5 | B | Evidence-first troubleshooting sequence; removed misleading own-IP test |
| Q31 | short answer | 5.5 | `ipconfig` | Basic client configuration display |
| Q32 | short answer | 5.5 | `ipconfig /all` | Extended client/DHCP/DNS display; invalid `-all` alias removed |
| Q33 | short answer | 5.5 | `ping` | ICMP echo command with timeout caveat |
| Q34 | short answer | 5.5 | `nslookup` | Direct DNS query and resolver identification |
| Q35 | short answer | 5.5 | `ipconfig /renew` | DHCP lease request |
| Q36 | short answer | 5.5 | `ipconfig /flushdns` | Local resolver-cache clearing |
| Q37 | short answer | 2.6 | static configuration | Replaced duplicate APIPA recall with static/dynamic understanding |
| Q38 | free response | 2.6, 5.5 | rubric | APIPA/DHCP isolation and end-to-end verification; rubric aligned to threshold |
| Q39 | free response | 2.4, 5.5 | rubric | DNS diagnosis, direct test, evidence-based fix, and verification |
| Q40 | free response | 2.6, 5.5 | rubric | Gateway diagnosis, client fix/upstream escalation, and verification |

## Quality and randomization findings

- No exact normalized stem is duplicated within the bank or in another
  checked-in A+ CSV bank.
- All 40 rows changed because every prior objective mapping was invalid. No
  rows were removed or added, preserving randomized-attempt depth.
- APIPA recall repetition was reduced by replacing one duplicate with a static
  configuration short answer and by making the remaining items test distinct
  decisions: recognition, supplied values, local isolation, scope exhaustion,
  DHCP reachability, and full troubleshooting.
- Single-choice key distribution is A × 8, B × 4, C × 8, D × 6. No position
  exceeds 31%, and every position is represented. Multi-select keys are no
  longer all `A|B|C`.
- The correct option is uniquely longest in 6 of 26 single-choice items (23%);
  those six retain natural wording rather than being padded to manufacture a
  length tie.
- Difficulty is 14 level-1, 17 level-2, and 9 level-3 items. Importance is 37
  job-critical and 3 working-knowledge items.
- Five Quick Checks now filter by lesson-relevant tags and use satisfiable
  randomized constrained selections. The 12-question Module Quiz enforces
  objective quotas of 2.4 × 3, 2.6 × 4, and 5.5 × 5 plus topic minima for IP
  addressing, DHCP/APIPA, gateway, DNS, commands, and troubleshooting.

## Editorial gate

The approval entry in `editorial-approvals.yaml` binds the exact reviewed CSV
bytes to SHA-256
`b3a0d587782b95ba4bf1d9a2c462a0182ae33f63ba2a55371215f5c1d6f26e25`,
question count 40, status `validated`, and review date 2026-09-05. The standard
loader verifies the file hash and imported count before setting the shared
quiz row to published, editorially validated, answer-key validated, and
explanations complete. No status is set outside that workflow.
