---
lesson_key: lesson.aplus.security.wireless_auth
title: Wireless Encryption & Enterprise Authentication
certification_version: comptia_aplus_220-1202
domain: '2.0'
module: module.aplus.core2.connected_endpoint_mobile_security
lesson_order: 1
importance: job_critical
learning_relationship: deep_dive
objectives:
- '2.3'
estimated_minutes: 25
status: published
summary: Choose modern wireless encryption and understand the role of RADIUS, TACACS+,
  Kerberos, and MFA at an A+ support level.
quick_check:
  title: "Quick Check \u2014 Wireless Encryption & Enterprise Authentication"
  displayed_count: 4
  pass_percent: 60
  tags_any:
  - M14Q001
  - M14Q002
  - M14Q003
  - M14Q004
---
# Wireless Encryption & Enterprise Authentication

## 1. What is this?
Choose modern wireless encryption and understand the role of RADIUS, TACACS+, Kerberos, and MFA at an A+ support level.

## 2. Why does an IT worker care?
Phones, browsers, Wi-Fi, and small routers sit directly between users and company data. The support technician must distinguish ordinary configuration failure from a security problem without bypassing management, encryption, certificates, or policy.

## 3. Watch / Read
Complete the required resource **resource.aplus.m14.wireless_encryption**. Use supplemental resources only where another vendor-specific view is useful.

## 4. What you actually need to remember
- WPA3 is the preferred modern option when supported; WPA2 with AES remains common. Avoid obsolete/insecure choices such as WEP and TKIP when stronger options are available.
- Encryption protects wireless traffic; authentication determines who is allowed to connect.
- Enterprise Wi-Fi can use centralized authentication rather than one shared pre-shared key.
- RADIUS is commonly associated with centralized network-access authentication; TACACS+ is commonly associated with administrative access to network devices; Kerberos is common in Windows domain authentication.
- MFA can strengthen wireless/VPN/identity workflows but does not replace encryption.

## 5. At work
- Do not 'fix' a connection by downgrading encryption without authorization.
- Compare a failing client with a known-good client: SSID, security type, certificate/profile, time, and credentials.

## 6. Commands / Tools
- Wi-Fi network properties
- Managed wireless profile
- Certificate/profile status
- RADIUS/identity-service status if visible to support

## 7. Interview / Explain
Explain WPA2 vs WPA3 and why enterprise Wi-Fi may use a centralized authentication service.

## 8. Quick Check
- `M14Q001`
- `M14Q002`
- `M14Q003`
- `M14Q004`
