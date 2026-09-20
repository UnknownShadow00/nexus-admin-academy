---
lesson_key: lesson.aplus.network.dns_dhcp_vlan_vpn
title: DNS, DHCP, VLANs & VPNs
certification_version: comptia_aplus_220-1201
domain: '2.0'
module: module.aplus.core1.network_services_troubleshooting
lesson_order: 4
importance: job_critical
learning_relationship: deep_dive
objectives:
- '2.4'
estimated_minutes: 45
status: published
summary: Deepen Module 1 by reading DNS/DHCP configuration concepts and recognizing
  VLAN/VPN boundaries.
quick_check:
  title: "Quick Check \u2014 DNS, DHCP, VLANs & VPNs"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M7Q014
  - M7Q016
  - M7Q017
  - M7Q018
---

# 1. What is this?
Module 1 taught how DNS and DHCP affect a client. Here you go one level deeper: common DNS records, DHCP scopes/reservations/exclusions, VLAN segmentation, and VPN use.

# 2. Why does an IT worker care?
These concepts explain why one user receives the wrong address, why a device should keep the same DHCP-assigned IP, why two ports can be physically adjacent but logically separated, and why a remote user can reach the internet but not an internal resource.

# 3. Watch / Read
**Required:** Professor Messer — *VLANs and VPNs (220-1201)*.  
**Optional review:** *DNS Configuration* and *DHCP* if Module 1 knowledge is rusty.

# 4. What you actually need to remember
- **A** → name to IPv4; **AAAA** → name to IPv6.
- **CNAME** → alias to another canonical name.
- **MX** → mail exchanger.
- **TXT** → arbitrary text; often used for SPF/DKIM/DMARC-related email validation data.
- DHCP **scope/pool** defines available leases; **reservation** ties a client identity to a preferred address; **exclusions** keep addresses out of the dynamic pool.
- A **VLAN** creates logical segmentation/broadcast domains on switching infrastructure.
- A **VPN** creates a protected tunnel, commonly client-to-site or site-to-site.

# 5. At work
A network printer should remain easy to find but policy says clients must use DHCP. A reservation is usually better than hard-coding a random address that could later conflict with the DHCP pool.

# 6. Commands / Tools
Reuse Module 1 evidence such as `ipconfig /all` and `nslookup`. Do not change VLAN or VPN infrastructure without authorization.

# 7. Interview / Explain
Explain DHCP reservation vs static addressing, and VLAN vs VPN.

# 8. Quick Check
Use Module 7 Quick Check 4: Q014, Q016, Q017, Q018.
