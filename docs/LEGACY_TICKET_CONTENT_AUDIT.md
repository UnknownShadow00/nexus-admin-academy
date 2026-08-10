# Legacy Support Ticket Content Audit

Reviewed 2026-08-10 before retiring the student-facing Support Tickets product. The `Ticket` and `TicketSubmission` records remain preserved as dormant history; this audit preserves the training decisions and any useful future ideas.

| Classification | Count | Meaning |
| --- | ---: | --- |
| CONVERT NOW | 10 | Converted to an interactive, server-graded Service Desk scenario in this phase. |
| SAVE FOR LATER | 30 | Sound advanced/lab/capstone material, but not converted in this focused pass. |
| REDUNDANT | 5 | Already taught by a stronger current Service Desk scenario. |
| LOW QUALITY / RETIRE | 3 | Multi-incident or answer-key style content without one teachable root cause. |

| Legacy ticket | Category | Classification | Decision / replacement |
| --- | --- | --- | --- |
| User cannot browse the internet — DNS resolution failing | Networking | REDUNDANT | `INC2407` provides the stronger IP-versus-hostname diagnosis. |
| User account locked out — cannot log in to Windows | Authentication | REDUNDANT | `INC2507` teaches the recurring stale-credential cause rather than an unlock click. |
| Printer offline — user cannot print from Windows | Hardware | REDUNDANT | `INC2408` and `INC2504` cover local spooler and changed-port isolation. |
| Laptop cannot connect to corporate Wi-Fi | Networking | REDUNDANT | `INC2402` covers managed wireless/device comparison. |
| PC running very slowly — high CPU usage on startup | Performance | SAVE FOR LATER | Good process/Startup Apps variant for a future desktop-performance set. |
| External hard drive not recognized in Windows | Hardware | SAVE FOR LATER | Useful data-safety and driver/port isolation scenario. |
| Email client cannot send mail — SMTP authentication error | Email | SAVE FOR LATER | Retain for an email-profile or credential-expiry variant. |
| New employee laptop will not join AD domain | Active Directory | SAVE FOR LATER | Strong AD/DNS scenario for advanced curriculum. |
| Desktop won't turn on at all | Hardware | SAVE FOR LATER | Preserve as a physical power-isolation beginner scenario. |
| My desktop looks brand new and my files are gone | Windows | CONVERT NOW | `INC2501` — temporary profile; protect data, repair profile, verify files. |
| Windows Update keeps failing | Windows | SAVE FOR LATER | Needs a distinct, evidence-rich update failure state before conversion. |
| Strange pop-ups and the mouse moved by itself | Security | SAVE FOR LATER | Preserve for a security escalation and containment scenario. |
| Multi-Ticket Simulation 1 | Mixed | LOW QUALITY / RETIRE | Multiple unrelated roots make process grading ambiguous. |
| Laptop stuck spinning dots after Tuesday updates | Windows | SAVE FOR LATER | Retain as an advanced recovery/startup-repair lab. |
| Excel crashes the moment it opens | Software | CONVERT NOW | `INC2502` — reproduce, Safe Mode/add-in isolation, repair, save verification. |
| C: drive full but deleted everything | Performance | CONVERT NOW | `INC2509` — identify runaway logs and correct durable retention. |
| New team member cannot open department share | Access | CONVERT NOW | `INC2505` — peer comparison, least privilege, original-share verification. |
| Executive assistant requests salary review folder | Access | CONVERT NOW | `INC2506` — do not grant; authorization boundary and escalation. |
| Locked out again third time week | Authentication | CONVERT NOW | `INC2507` — stale mapped-drive credential, not repeated account unlocks. |
| Defender caught something user asks okay | Security | SAVE FOR LATER | Worth a safe malware triage/escalation scenario after security tooling is expanded. |
| Payroll update phishing, user entered password | Security | CONVERT NOW | `INC2508` — containment, reset/session revocation, security escalation. |
| Can’t RDP shared lab workstation | Access | SAVE FOR LATER | Preserve for a permissions/network/service comparison scenario. |
| One desk no network after office move | Networking | CONVERT NOW | `INC2503` — cable/switch/VLAN/DHCP comparison and verification. |
| Whole floor printer down after DHCP change | Printing | CONVERT NOW | `INC2504` — current IP, local print port, test print. |
| VPN broken remote worker names fail | Networking | REDUNDANT | `INC2407` already teaches DNS isolation; future VPN-DNS variant remains possible. |
| Multi Ticket Simulation 2 | Mixed | LOW QUALITY / RETIRE | No single root cause or safe objective set. |
| New static IP can reach office not internet servers | Networking | SAVE FOR LATER | Good addressing/gateway advanced scenario. |
| New desk wrong VLAN after reshuffle | Networking | SAVE FOR LATER | Preserve as a switch/VLAN variant distinct from `INC2503`. |
| Whole new VLAN no IP | Networking | SAVE FOR LATER | Retain for DHCP relay/SVI advanced practice. |
| Switch swap half VLANs unreachable | Networking | SAVE FOR LATER | Retain for trunking assessment. |
| Switch port keeps shutting | Networking | SAVE FOR LATER | Retain for port-security escalation. |
| VLAN users can reach each other but nothing else | Networking | SAVE FOR LATER | Retain for SVI/gateway diagnosis. |
| Bulk onboarding 5 new hires | Active Directory | SAVE FOR LATER | Preserve for approval-aware provisioning workflows. |
| Trust relationship failed restored laptop | Active Directory | CONVERT NOW | `INC2510` — computer-account secure channel, safe repair/escalation. |
| policy not reaching department | Group Policy | SAVE FOR LATER | Strong GPO/OU scenario for the advanced track. |
| report locked & stale accounts | PowerShell | SAVE FOR LATER | Preserve as a reporting/automation exercise. |
| restore deleted quarterly folder | Backup | SAVE FOR LATER | Preserve for authorization, restore scope, and verification practice. |
| Linux permission denied shared reports | Linux | SAVE FOR LATER | Retain for Linux ownership/group evidence. |
| SSH lockout after .ssh | Linux | SAVE FOR LATER | Retain for key permissions and recovery escalation. |
| internal wiki down | Linux | SAVE FOR LATER | Retain for service/configuration diagnosis. |
| nightly cleanup cron stopped | Linux | SAVE FOR LATER | Retain for cron environment/path troubleshooting. |
| app server disk 96% | Linux | SAVE FOR LATER | Keep as a Linux/log-growth variant of `INC2509`, not duplicate it now. |
| website outside down inside fine | Networking | SAVE FOR LATER | Retain for firewall/DNS/public-path isolation. |
| Entra exec locked out | Cloud identity | SAVE FOR LATER | Preserve for conditional-access/MFA escalation. |
| Azure RDP VM unavailable | Azure | SAVE FOR LATER | Preserve for cloud network/VM-state scenario. |
| Azure partner download link expired | Azure | SAVE FOR LATER | Preserve for SAS authorization/expiry diagnosis. |
| Maple Finch Friday outage | Major incident | SAVE FOR LATER | Keep as a later capstone with coordination objectives. |
| Multi Ticket Simulation 3 | Mixed | LOW QUALITY / RETIRE | Multi-root answer-key exercise; replace only after a scoped incident framework exists. |

## Converted scenario design

Every converted case has one technical root cause, scoped evidence, one safe remediation (or an explicit authorized escalation for `INC2506`), verification of the original user symptom, and a concise closure note. Server grading uses the existing 15/25/30/20/10 process weighting; remediation alone cannot pass a case.

## Future variants

The recurring-lockout design intentionally leaves room for later variants (phone, Credential Manager, mapped drive, scheduled task, or service credential) without changing the Service Desk grading categories. The advanced AD, network, Linux, Azure, and incident material above remains available for later phases.
