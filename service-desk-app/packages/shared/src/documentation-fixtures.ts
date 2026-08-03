export const DOCUMENTATION_CATEGORY_NAMES = [
  'Environment Overview',
  'Email & Mail Server',
  'Password & Security',
  'Network & Connectivity',
  'Server Documentation',
  'Standard Procedures / SOPs',
  'Software & Licensing',
  'Hardware & Assets',
  'Contacts & Escalation',
  'Credentials & Access',
] as const;

export type DocumentationCategoryName =
  (typeof DOCUMENTATION_CATEGORY_NAMES)[number];

export interface DocumentationArticle {
  id: string;
  category: DocumentationCategoryName;
  title: string;
  body: readonly string[];
}

export interface DocumentationCategory {
  id: string;
  name: DocumentationCategoryName;
  articles: readonly DocumentationArticle[];
}

interface ArticleSeed {
  id: string;
  title: string;
  body: readonly [string, string, ...string[]];
}

function createCategory(
  id: string,
  name: DocumentationCategoryName,
  articles: readonly ArticleSeed[],
): DocumentationCategory {
  return {
    id,
    name,
    articles: articles.map((article) => ({
      ...article,
      category: name,
      body: [...article.body],
    })),
  };
}

export const DOCUMENTATION_CATEGORY_FIXTURES: readonly DocumentationCategory[] =
  [
    createCategory('environment-overview', 'Environment Overview', [
      {
        id: 'environment-support-landscape',
        title: 'Support Environment at a Glance',
        body: [
          'The training environment represents a mid-sized organization with office, warehouse, and remote staff. Core services include managed endpoints, cloud productivity tools, internal line-of-business applications, and segmented workplace networks.',
          'Treat Directory records, asset details, and current service alerts as the authoritative operational view. Changes made in one support tool may affect what another tool reports during the same simulation attempt.',
        ],
      },
    ]),
    createCategory('email-mail-server', 'Email & Mail Server', [
      {
        id: 'email-delayed-delivery-checks',
        title: 'Checking Delayed Message Delivery',
        body: [
          'Start by confirming the sender, recipient, approximate send time, and whether the delay affects internal mail, external mail, or both. Ask for the subject without requesting confidential message content.',
          'Review the mail service status and queued-delivery notices before changing a mailbox. If only one recipient is affected, verify the address and mailbox state, then document the message trace reference in the ticket.',
        ],
      },
      {
        id: 'email-shared-mailbox-access',
        title: 'Shared Mailbox Access Checklist',
        body: [
          'Verify that the requester has manager approval and that the mailbox name matches the intended team function. Shared mailbox access should be granted through the approved access group rather than by sharing another employee’s credentials.',
          'After membership is updated, allow time for access synchronization and ask the requester to restart the mail client. Escalate only after the group is correct and the mailbox remains absent in both web and desktop clients.',
        ],
      },
      {
        id: 'email-client-profile-repair',
        title: 'Repairing a Mail Client Profile',
        body: [
          'Use profile repair when the web mailbox works but the installed mail client repeatedly fails to synchronize. Record any error code, confirm free disk space, and verify that the workstation clock is accurate.',
          'Create a fresh client profile without deleting the original data file until synchronization is confirmed. Reopen the client, test a new message, and retain the old profile only long enough to support a safe rollback.',
        ],
      },
      {
        id: 'email-quarantine-review',
        title: 'Reviewing Quarantined Messages',
        body: [
          'Confirm the expected sender and business purpose before releasing a quarantined message. A familiar display name is not sufficient; compare the full sending address and any warning details shown by the mail security service.',
          'Do not release executable attachments or messages that request urgent credential entry. Send suspicious items to Security Operations with the quarantine reference and tell the requester not to forward the message.',
        ],
      },
    ]),
    createCategory('password-security', 'Password & Security', [
      {
        id: 'security-password-reset-verification',
        title: 'Identity Checks Before a Password Reset',
        body: [
          'Confirm the employee through two approved attributes already present in trusted support records. Never use information supplied only within the reset request as the sole proof of identity.',
          'Issue a temporary password through the supported reset action and require a change at next sign-in. Do not place passwords in ticket notes, chat messages, or email, even in this simulated environment.',
        ],
      },
      {
        id: 'security-mfa-reenrollment',
        title: 'MFA Re-enrollment Procedure',
        body: [
          'Establish whether the employee still controls any registered authentication method. If a device was lost or replaced, verify identity and clear the old enrollment before the user registers a new authenticator.',
          'Ask the user to complete enrollment during the support session and test a fresh sign-in. Report unexpected prompts, repeated enrollment loops, or sign-ins from unfamiliar locations to Security Operations.',
        ],
      },
      {
        id: 'security-suspicious-signin',
        title: 'Responding to a Suspicious Sign-in Alert',
        body: [
          'Record the alert time, service, approximate location, and whether the employee recognizes the activity. If the activity is unknown, contain the account by following the security escalation path before investigating endpoint symptoms.',
          'Preserve the alert identifier and avoid deleting related messages or browser history. Reset credentials and revoke active sessions only under the incident lead’s direction so evidence remains useful.',
        ],
      },
      {
        id: 'security-screen-lock-baseline',
        title: 'Workstation Lock and Session Safety',
        body: [
          'Managed workstations should lock automatically after the configured idle period, and staff should lock the screen whenever leaving a shared area. A lock policy issue can be device-specific or a sign that management policy is not applying.',
          'Confirm the device is enrolled and has recently synchronized before forcing local settings. Escalate repeated policy drift with the asset tag, last sync time, and a summary of the observed timeout.',
        ],
      },
    ]),
    createCategory('network-connectivity', 'Network & Connectivity', [
      {
        id: 'network-first-response',
        title: 'First Response for Connectivity Incidents',
        body: [
          'Define the scope before restarting equipment: one device, one room, one network segment, or multiple sites. Capture whether wired, wireless, and internet access are affected and note the last known working time.',
          'Compare the affected device with a known-good device on the same segment. Check current service alerts, then record the smallest reproducible failure before changing network settings.',
        ],
      },
      {
        id: 'network-wireless-dropouts',
        title: 'Investigating Repeated Wireless Dropouts',
        body: [
          'Record the access point or work area, affected device count, signal level, and whether movement changes the symptom. Frequent reconnects across several devices usually point to the shared wireless path rather than one endpoint.',
          'Compare radio health and recent alerts with a nearby stable area. Avoid resetting an access point during active operations unless the network owner approves the interruption.',
        ],
      },
      {
        id: 'network-vpn-device-check',
        title: 'Remote Access Device Check Failures',
        body: [
          'When a remote access client reaches the gateway but pauses at device validation, confirm the client version, operating system, management enrollment, and last compliance sync. Normal web browsing does not prove the device is compliant.',
          'Correct only the documented mismatch, then synchronize the device and retry a new connection. Escalate with the exact validation stage and client log timestamp if the compliant device is still rejected.',
        ],
      },
      {
        id: 'network-dns-triage',
        title: 'Name Resolution Triage',
        body: [
          'Suspect name resolution when a service fails by hostname but responds by a verified network address. Confirm the spelling, test another internal hostname, and compare results from a known-good workstation.',
          'Do not add permanent local host entries as a workaround. Capture the resolver in use and the failed name, then route widespread or inconsistent responses to the network team.',
        ],
      },
      {
        id: 'network-warehouse-segments',
        title: 'Warehouse Scanner Network Notes',
        body: [
          'Warehouse scanners use managed wireless profiles tied to their assigned operational segment. Loading-lane coverage is designed for roaming, but metal doors, parked vehicles, and temporary staging can alter radio conditions.',
          'For repeated drops, list the affected scanner asset tags and lanes, then compare them with a stable scanner. Keep wired packing stations in service while the wireless issue is assessed.',
        ],
      },
    ]),
    createCategory('server-documentation', 'Server Documentation', [
      {
        id: 'server-service-health',
        title: 'Reading Service Health Signals',
        body: [
          'Use service health signals together: availability, response time, error rate, and recent change history. A single warning does not always mean the server is the cause of a user-facing incident.',
          'Correlate the signal time with the ticket and check dependencies before restarting anything. Record the service name, alert identifier, and observed impact when escalating.',
        ],
      },
      {
        id: 'server-restart-approval',
        title: 'Restart Approval and Communication',
        body: [
          'A production service restart requires an identified owner, an approved window, and a rollback plan. Confirm affected teams and active jobs before scheduling the interruption.',
          'Announce the start and completion through the approved status channel. Afterward, validate the service from a user perspective and attach the change reference to related tickets.',
        ],
      },
      {
        id: 'server-storage-capacity',
        title: 'Server Storage Capacity Response',
        body: [
          'Treat rapidly increasing storage use as an incident even before the volume is full. Identify which service and path are growing, and preserve evidence of the trend instead of deleting unfamiliar files.',
          'Clear only documented temporary data with owner approval. Capacity expansion, log retention changes, and application cleanup belong to the responsible server or application team.',
        ],
      },
      {
        id: 'server-backup-restore-request',
        title: 'Preparing a Restore Request',
        body: [
          'A restore request needs the system name, item or path, last known good time, business impact, and data owner approval. Times should include a time zone to avoid selecting the wrong recovery point.',
          'Do not promise recovery until backup coverage is verified. Keep restored data in the approved recovery location until the owner confirms its contents and destination.',
        ],
      },
    ]),
    createCategory('standard-procedures', 'Standard Procedures / SOPs', [
      {
        id: 'sop-ticket-first-response',
        title: 'Ticket First-response Standard',
        body: [
          'A useful first response acknowledges the impact, restates the problem in plain language, and asks only for information needed for the next diagnostic step. Set a realistic update time rather than promising immediate resolution.',
          'Record actions as they happen and separate observed facts from assumptions. Keep internal technical notes concise enough that another analyst can continue the work.',
        ],
      },
      {
        id: 'sop-new-device-handoff',
        title: 'New Device Preparation and Handoff',
        body: [
          'Confirm the recipient, approved device profile, asset tag, required software, and delivery method before starting preparation. Apply the standard image and allow management policies to finish before testing.',
          'Verify sign-in, encryption, network access, and assigned applications. Record the handoff or shipping reference and obtain recipient confirmation before closing the request.',
        ],
      },
      {
        id: 'sop-change-record',
        title: 'Recording a Support Change',
        body: [
          'Document the reason, target, expected result, validation method, and rollback step before a change that can affect access or service. Link the originating ticket so the operational history remains traceable.',
          'After the change, record the actual outcome and any variance from the plan. A successful click is not validation; test the user-facing behavior that the change was intended to restore.',
        ],
      },
      {
        id: 'sop-shift-handoff',
        title: 'End-of-shift Ticket Handoff',
        body: [
          'For every active handoff, state the current impact, work completed, evidence collected, next action, owner, and promised update time. Remove duplicate notes and make blockers explicit.',
          'Contact the receiving analyst for urgent or time-sensitive incidents rather than relying on a queue note alone. Tell the requester who will provide the next update when ownership changes.',
        ],
      },
    ]),
    createCategory('software-licensing', 'Software & Licensing', [
      {
        id: 'software-license-assignment',
        title: 'Software License Assignment',
        body: [
          'Confirm that the requested product is approved for the employee’s role and that a license is available. Use the organization’s assignment group or license action instead of sharing activation keys.',
          'Allow the vendor directory to synchronize, then ask the user to sign out and back in. If access remains missing, capture the account, product edition, and displayed licensing message.',
        ],
      },
      {
        id: 'software-large-export-crash',
        title: 'Large Document Export Failures',
        body: [
          'For crashes during a large export, reproduce with a smaller page range and then add pages until the failure returns. Check free disk space, application version, and whether comments or embedded media change the result.',
          'Preserve the smallest repeatable sample and the crash timestamp. Use a supported reduced-batch workaround only after confirming the output remains complete and suitable for the requester’s work.',
        ],
      },
      {
        id: 'software-approved-install',
        title: 'Approved Software Installation',
        body: [
          'Check the approved software catalog, device compatibility, and licensing requirement before installation. Requests for unlisted tools need owner and security review before any package is downloaded.',
          'Install through the managed portal whenever possible and validate launch under the requester’s account. Record the installed version and remove temporary installer files through the standard cleanup process.',
        ],
      },
    ]),
    createCategory('hardware-assets', 'Hardware & Assets', [
      {
        id: 'hardware-peripheral-isolation',
        title: 'Isolating a Peripheral Fault',
        body: [
          'Use a controlled swap to learn whether the fault follows the peripheral, cable, port, or workstation. Change one item at a time and record which combination reproduces the symptom.',
          'Return known-good loan equipment to its original state after testing. If the fault follows the accessory, check warranty and replacement eligibility in the asset record.',
        ],
      },
      {
        id: 'hardware-audio-static',
        title: 'USB Audio Static Troubleshooting',
        body: [
          'Confirm whether static occurs in more than one calling application and whether it begins immediately or after sustained use. Test the headset on a known-good workstation and a known-good headset on the affected workstation.',
          'Inspect the cable and connector without opening the device. Replace the headset when the fault follows it; escalate the workstation when multiple known-good audio devices show the same behavior.',
        ],
      },
      {
        id: 'hardware-asset-state',
        title: 'Understanding Asset Lifecycle States',
        body: [
          'Deployed assets are assigned and in active service; attention states indicate a support or compliance concern; storage and return states mean the device should not be reassigned without review.',
          'Update custody only after a confirmed handoff. Keep the physical label, directory record, and asset record aligned so later support work identifies the correct device.',
        ],
      },
      {
        id: 'hardware-loaner-issue',
        title: 'Issuing a Loan Device',
        body: [
          'Confirm the business need, expected return date, recipient, and required device profile. Select a ready asset whose security and management checks are current.',
          'Record both the outgoing loan and any retained faulty device. Give the recipient return instructions and validate basic access before the device leaves support custody.',
        ],
      },
      {
        id: 'hardware-damage-intake',
        title: 'Physical Damage Intake',
        body: [
          'Record the asset tag, visible condition, reported circumstances, and whether the device can be powered safely. Disconnect damaged batteries or wet equipment from power and move people away from any immediate hazard.',
          'Do not open sealed equipment at the service desk. Route the asset through the repair or replacement process and preserve accessories that may be needed for vendor assessment.',
        ],
      },
    ]),
    createCategory('contacts-escalation', 'Contacts & Escalation', [
      {
        id: 'escalation-network',
        title: 'When to Escalate to Network Operations',
        body: [
          'Escalate when impact spans multiple devices or locations, a managed network component reports a fault, or standard endpoint checks isolate the issue beyond the device. Urgent operational disruption should be raised immediately.',
          'Include affected segments, locations, device samples, timestamps, service alerts, and tests already completed. Keep the user ticket active until ownership and the next update are confirmed.',
        ],
      },
      {
        id: 'escalation-security',
        title: 'Security Operations Contact Criteria',
        body: [
          'Contact Security Operations for unrecognized sign-ins, suspected phishing, exposed credentials, malware indicators, or loss of a device containing organizational data. Containment takes priority over routine troubleshooting.',
          'Provide the employee, device, time, observed indicators, and actions already taken. Do not investigate suspicious files or messages beyond the approved intake steps.',
        ],
      },
      {
        id: 'escalation-vendor',
        title: 'Preparing a Vendor Support Case',
        body: [
          'Before contacting a vendor, collect the product, version, entitlement, reproducible steps, timestamps, and sanitized logs. Remove credentials and unrelated personal or business data from attachments.',
          'Record the vendor case number and expected response time in the ticket. Continue safe workarounds internally while the case is open and confirm ownership of vendor follow-up.',
        ],
      },
      {
        id: 'escalation-major-incident',
        title: 'Major Incident Notification',
        body: [
          'Potential major incidents combine broad or critical impact with urgency, uncertainty, or rapid spread. Notify the duty lead early; the lead decides whether to start the formal coordination process.',
          'State what is affected, who is affected, when it began, what remains available, and the current evidence. Use confirmed facts and give a time for the next update even when the cause is unknown.',
        ],
      },
    ]),
    createCategory('credentials-access', 'Credentials & Access', [
      {
        id: 'access-group-membership',
        title: 'Access Through Directory Groups',
        body: [
          'Many shared resources are assigned through role-based directory groups. Compare the requester with a peer in the same approved role, then add only the missing group that provides the required resource.',
          'Avoid copying every group from another employee. Record the approval and intended resource, allow synchronization, and ask the requester to refresh or start a new session.',
        ],
      },
      {
        id: 'access-calendar',
        title: 'Shared Calendar Access',
        body: [
          'Confirm the calendar’s full name, the requester’s role, and manager approval. Check the documented calendar access group before applying direct permissions.',
          'After a group change, allow synchronization and have the requester refresh the calendar list. If peers with the same group can connect, capture the client and account details for messaging support.',
        ],
      },
      {
        id: 'access-signin-loop',
        title: 'Resolving an Authentication Loop',
        body: [
          'A return to the sign-in screen after verification can indicate a locked identity, stale session, incomplete MFA enrollment, or an application-specific access problem. Confirm whether another internal service completes authentication.',
          'Correct the verified directory condition, then close all old sessions and test a fresh private session. Escalate repeated loops with the application, time, and identity checks already performed.',
        ],
      },
      {
        id: 'access-service-account',
        title: 'Service Account Handling',
        body: [
          'Service accounts require a named owner, documented purpose, approved systems, and a managed credential process. They must not be used as shared personal accounts for routine employee work.',
          'Route password changes and access expansion through the owning technical team. Never reveal a service credential in a ticket, chat, email, or troubleshooting screenshot.',
        ],
      },
    ]),
  ];

export const DOCUMENTATION_ARTICLE_FIXTURES: readonly DocumentationArticle[] =
  DOCUMENTATION_CATEGORY_FIXTURES.flatMap((category) => category.articles);

export function getDocumentationCategory(categoryId: string) {
  return DOCUMENTATION_CATEGORY_FIXTURES.find(
    (category) => category.id === categoryId,
  );
}

export function getDocumentationArticle(articleId: string) {
  return DOCUMENTATION_ARTICLE_FIXTURES.find(
    (article) => article.id === articleId,
  );
}
