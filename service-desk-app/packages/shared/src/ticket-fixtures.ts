import { Priority, TicketCategory } from './enums';
import { TicketStatus, type Ticket } from './ticket-types';

export const FIXTURE_REFERENCE_TIME = '2026-07-28T10:30:00.000Z';

type ConvertedTicketSpec = {
  id: string;
  title: string;
  category: TicketCategory;
  priority: Priority;
  assetTag: string;
  deviceName: string;
  deviceKind: Ticket['device']['kind'];
  operatingSystem: string;
  requester: string;
  department: string;
  issue: string;
  impact: string;
  troubleshooting: readonly string[];
  hints: readonly string[];
};

function convertedTicket(spec: ConvertedTicketSpec): Ticket {
  return {
    activity: [{ id: `${spec.id}-created`, label: 'Ticket created', timestamp: FIXTURE_REFERENCE_TIME }],
    assignedTo: 'you',
    category: spec.category,
    createdAt: FIXTURE_REFERENCE_TIME,
    description: {
      businessImpact: spec.impact,
      issue: spec.issue,
      reportedByLine: 'Submitted through the employee support portal.',
      troubleshooting: [...spec.troubleshooting],
    },
    device: { assetTag: spec.assetTag, deviceName: spec.deviceName, kind: spec.deviceKind, operatingSystem: spec.operatingSystem, state: 'attention' },
    escalated: false,
    hints: [...spec.hints],
    id: spec.id as `INC${number}`,
    notes: [],
    priority: spec.priority,
    requester: { contact: 'Employee support portal', department: spec.department, email: `${spec.requester.toLowerCase().replace(/ /g, '.')}@nexus.example`, location: 'Nexus office', name: spec.requester },
    sla: { dueAt: '2026-07-28T14:30:00.000Z', target: 'Respond within 4 hours' },
    status: TicketStatus.Open,
    suggestedTools: ['remote-desktop', 'documentation', 'company-chat'],
    title: spec.title,
  };
}

const CONVERTED_LEGACY_TICKETS: readonly Ticket[] = [
  convertedTicket({ id: 'INC2501', title: 'Desktop opens with a temporary Windows profile', category: TicketCategory.Software, priority: Priority.High, assetTag: 'NX-2501', deviceName: 'ACCT-LT-17', deviceKind: 'laptop', operatingSystem: 'Windows 11 Enterprise', requester: 'Morgan Ellis', department: 'Accounting', issue: 'After signing in, Morgan sees a fresh desktop and cannot find the usual Documents files.', impact: 'Month-end work is paused while the user data appears unavailable.', troubleshooting: ['The user restarted once.', 'A nearby teammate can open the same shared files.'], hints: ['Protect user data before profile repair.', 'Compare the sign-in profile path with the expected local profile.', 'Confirm the original files are available after repairing the profile.'] }),
  convertedTicket({ id: 'INC2502', title: 'Excel crashes only when one reporting workbook opens', category: TicketCategory.Software, priority: Priority.Medium, assetTag: 'NX-2502', deviceName: 'FIN-WS-44', deviceKind: 'desktop', operatingSystem: 'Windows 11 Enterprise', requester: 'Priya Shah', department: 'Finance', issue: 'Excel closes when the monthly reporting workbook opens, but other workbooks remain usable.', impact: 'The finance team cannot finish the monthly report.', troubleshooting: ['A blank workbook opens normally.', 'The workbook was copied locally and still crashes.'], hints: ['Reproduce the specific crash before changing Office.', 'Use Safe Mode or add-in isolation to separate workbook and add-in causes.', 'Verify the original workbook opens and saves after the repair.'] }),
  convertedTicket({ id: 'INC2503', title: 'One desk lost network after an office move', category: TicketCategory.Network, priority: Priority.High, assetTag: 'NX-2503', deviceName: 'OPS-WS-12', deviceKind: 'desktop', operatingSystem: 'Windows 11 Enterprise', requester: 'Jordan Kim', department: 'Operations', issue: 'A workstation moved to a new desk has no network while adjacent desks work normally.', impact: 'One dispatcher cannot access the order system.', troubleshooting: ['The workstation was restarted.', 'Nearby workstations remain connected.'], hints: ['Start with physical link and compare the nearby working desk.', 'Check the assigned switch port and VLAN before renewing addresses.', 'Verify the original order system after the port is corrected.'] }),
  convertedTicket({ id: 'INC2504', title: 'Department printer stopped after its DHCP address changed', category: TicketCategory.Hardware, priority: Priority.High, assetTag: 'NX-2504', deviceName: 'ENG-WS-09', deviceKind: 'desktop', operatingSystem: 'Windows 11 Enterprise', requester: 'Sofia Nguyen', department: 'Engineering', issue: 'The shared department printer is reachable from one workstation but this workstation still sends jobs to its old address.', impact: 'Engineering cannot print drawing review packets from the affected workstation.', troubleshooting: ['The printer is powered on.', 'A colleague printed successfully from a nearby computer.'], hints: ['Confirm whether this is local or printer-wide.', 'Compare the configured print port with the printer’s current address.', 'Update the port safely and print a test page.'] }),
  convertedTicket({ id: 'INC2505', title: 'New employee cannot open the department share', category: TicketCategory.Access, priority: Priority.Medium, assetTag: 'NX-2505', deviceName: 'MKT-LT-05', deviceKind: 'laptop', operatingSystem: 'Windows 11 Enterprise', requester: 'Taylor Reed', department: 'Marketing', issue: 'A new employee receives Access Denied for the Marketing share that peers can use.', impact: 'The new hire cannot access approved team materials.', troubleshooting: ['The share opens for the team lead.', 'The employee can sign in successfully.'], hints: ['Confirm the requested resource and compare a peer with the same role.', 'Check approved group access before granting anything.', 'Verify the original share after the least-privilege change.'] }),
  convertedTicket({ id: 'INC2506', title: 'Assistant requests access to restricted salary records', category: TicketCategory.Access, priority: Priority.High, assetTag: 'NX-2506', deviceName: 'HR-LT-21', deviceKind: 'laptop', operatingSystem: 'Windows 11 Enterprise', requester: 'Casey Lane', department: 'Executive Office', issue: 'An executive assistant asks for access to the restricted HR salary folder to help with a meeting.', impact: 'The request needs a timely, safe response without expanding access improperly.', troubleshooting: ['The requester has access to general HR materials.', 'No written approval is attached.'], hints: ['Identify the authorization boundary.', 'Do not use a group change as a substitute for approval.', 'Document a safe escalation and verify the request is routed correctly.'] }),
  convertedTicket({ id: 'INC2507', title: 'Account keeps locking after a password change', category: TicketCategory.Access, priority: Priority.High, assetTag: 'NX-2507', deviceName: 'SALES-LT-08', deviceKind: 'laptop', operatingSystem: 'Windows 11 Enterprise', requester: 'Avery Monroe', department: 'Sales', issue: 'The account locks again shortly after each successful password reset.', impact: 'The employee repeatedly loses access to sales systems.', troubleshooting: ['The account was unlocked once.', 'The employee can sign in immediately after the reset.'], hints: ['Find what is reusing the old credential instead of resetting again.', 'Inspect saved mappings, Credential Manager, and scheduled connections.', 'Remove the stale credential and monitor for another lockout.'] }),
  convertedTicket({ id: 'INC2508', title: 'Employee entered credentials into a phishing page', category: TicketCategory.Access, priority: Priority.High, assetTag: 'NX-2508', deviceName: 'PAY-LT-03', deviceKind: 'laptop', operatingSystem: 'Windows 11 Enterprise', requester: 'Riley Brown', department: 'Payroll', issue: 'An employee reports entering their password into a page reached from a suspicious email.', impact: 'The account and payroll data may be exposed until containment is complete.', troubleshooting: ['The employee closed the page.', 'No access changes have been made yet.'], hints: ['Contain first; do not treat this as ordinary password troubleshooting.', 'Reset credentials, revoke active sessions, and escalate through the security path.', 'Record the actions and safe follow-up for the employee.'] }),
  convertedTicket({ id: 'INC2509', title: 'Workstation disk fills again every few days', category: TicketCategory.Software, priority: Priority.Medium, assetTag: 'NX-2509', deviceName: 'SUP-WS-31', deviceKind: 'desktop', operatingSystem: 'Windows 11 Enterprise', requester: 'Devon Ross', department: 'Support', issue: 'The C: drive fills repeatedly even after temporary files are deleted.', impact: 'The support workstation becomes slow and cannot install approved updates.', troubleshooting: ['Temporary files were removed last week.', 'Free space returned briefly, then fell again.'], hints: ['Identify what is growing rather than repeatedly deleting symptoms.', 'Inspect log and application storage trends.', 'Correct the source safely and verify free space remains stable.'] }),
  convertedTicket({ id: 'INC2510', title: 'Restored laptop reports a trust relationship failure', category: TicketCategory.Access, priority: Priority.Medium, assetTag: 'NX-2510', deviceName: 'OPS-LT-58', deviceKind: 'laptop', operatingSystem: 'Windows 11 Enterprise', requester: 'Sam Ortiz', department: 'Operations', issue: 'A restored domain laptop rejects sign-in with a trust relationship error while peer laptops work.', impact: 'The employee cannot access the domain workstation after recovery.', troubleshooting: ['The network is connected.', 'Other domain users can sign in on nearby devices.'], hints: ['Separate user credentials from the computer account relationship.', 'Confirm the secure-channel failure before changing the user account.', 'Repair or escalate the device trust safely and verify domain sign-in.'] }),
];

const BASE_TICKET_FIXTURES = [
  {
    activity: [
      {
        detail: 'Created from the employee support portal.',
        id: 'INC2401-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T09:42:00.000Z',
      },
      {
        detail: 'Queue routing matched this request to your practice shift.',
        id: 'INC2401-assigned',
        label: 'Assigned to you',
        timestamp: '2026-07-28T09:49:00.000Z',
        tone: 'info',
      },
    ],
    assignedTo: 'you',
    category: TicketCategory.Access,
    createdAt: '2026-07-28T09:42:00.000Z',
    description: {
      businessImpact:
        'A month-end reconciliation is paused until the analyst can reach the reporting workspace.',
      issue:
        'The finance reporting portal accepts the first authentication step, then returns to the sign-in screen before the dashboard loads. Other internal services continue to accept the analyst’s account.',
      reportedByLine:
        'Submitted through the employee support portal after two failed sign-in attempts.',
      troubleshooting: [
        'Closed and reopened the browser.',
        'Confirmed other internal sites load normally.',
        'Tried a private browsing window with the same result.',
        'Confirmed the account is not locked and the second-factor prompt succeeds on another internal service.',
      ],
    },
    device: {
      assetTag: 'NX-4831',
      deviceName: 'FIN-LT-27',
      kind: 'laptop',
      operatingSystem: 'Windows 11 Enterprise',
      state: 'active',
    },
    escalated: false,
    hints: [
      'Confirm whether the requester can complete the second authentication prompt on another internal service.',
      'Review the browser/profile evidence before changing the employee account.',
      'Check the knowledge base for the finance portal sign-in loop procedure.',
      'Ask the requester to start a fresh session after the local profile data is cleared.',
    ],
    id: 'INC2401',
    notes: [],
    priority: Priority.High,
    requester: {
      contact: 'Ext. 4318',
      department: 'Finance Operations',
      email: 'avery.brooks@nexus.example',
      location: 'North Campus · Level 4',
      name: 'Avery Brooks',
    },
    sla: {
      dueAt: '2026-07-28T11:15:00.000Z',
      target: 'Respond within 90 minutes',
    },
    status: TicketStatus.InProgress,
    suggestedTools: [
      'remote-desktop',
      'directory',
      'documentation',
      'company-chat',
    ],
    title: 'Finance portal returns to sign-in after verification',
  },
  {
    activity: [
      {
        detail: 'Monitoring generated an incident after repeated disconnects.',
        id: 'INC2402-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T10:08:00.000Z',
        tone: 'warning',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Network,
    createdAt: '2026-07-28T10:08:00.000Z',
    description: {
      businessImpact:
        'One loading lane is recording orders on paper, slowing dispatch and increasing re-entry work.',
      issue:
        'The scanner at loading lane 2 disconnects from the warehouse network every few minutes. The scanner at the next lane stays connected.',
      reportedByLine:
        'Reported by the morning dispatch lead after the issue continued through the first hour of the shift.',
      troubleshooting: [
        'Restarted one handheld scanner.',
        'Moved the affected scanner beside a working scanner; only the affected unit disconnected.',
        'Confirmed wired packing stations remain connected.',
      ],
    },
    device: {
      assetTag: 'NX-7714',
      deviceName: 'SCAN-DK-14',
      kind: 'mobile',
      operatingSystem: 'Android Enterprise 15',
      state: 'attention',
    },
    escalated: false,
    hints: [
      'Use the working scanner beside it to decide whether the fault follows the network area or one device.',
      'Open the managed device console and compare the affected scanner’s wireless profile with the working unit.',
      'Refresh the affected managed wireless profile, renew its address, and then watch the connection long enough to verify stability.',
    ],
    id: 'INC2402',
    notes: [],
    priority: Priority.High,
    requester: {
      contact: 'Radio channel 3',
      department: 'Distribution',
      email: 'noah.vance@nexus.example',
      location: 'West Warehouse · Loading Dock',
      name: 'Noah Vance',
    },
    sla: {
      dueAt: '2026-07-28T10:50:00.000Z',
      target: 'Restore service within 45 minutes',
    },
    status: TicketStatus.Open,
    suggestedTools: [
      'remote-desktop',
      'server-room',
      'asset-management',
      'company-chat',
    ],
    title: 'Loading dock scanners repeatedly lose their wireless connection',
  },
  {
    activity: [
      {
        id: 'INC2403-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T09:18:00.000Z',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Software,
    createdAt: '2026-07-28T09:18:00.000Z',
    description: {
      businessImpact:
        'The design review can continue, but annotated exports cannot be shared with the supplier.',
      issue:
        'The approved PDF editor closes when a large drawing package is exported with comments included.',
      reportedByLine:
        'Submitted from the desktop support shortcut with an application crash report attached.',
      troubleshooting: [
        'Reopened the drawing package.',
        'Exported a single page successfully.',
        'Restarted the workstation before trying the full package again.',
      ],
    },
    device: {
      assetTag: 'NX-3560',
      deviceName: 'DSN-WS-08',
      kind: 'desktop',
      operatingSystem: 'Windows 11 Enterprise',
      state: 'active',
    },
    escalated: false,
    hints: [
      'Reproduce the export with a smaller group of annotated pages.',
      'Review the workstation for available disk space and pending application updates.',
      'Check documentation for known large-file export limitations.',
      'Record the smallest repeatable failure before considering escalation.',
    ],
    id: 'INC2403',
    notes: [],
    priority: Priority.Medium,
    requester: {
      contact: 'Ext. 2874',
      department: 'Product Design',
      email: 'mina.patel@nexus.example',
      location: 'Studio Annex · Bay 6',
      name: 'Mina Patel',
    },
    sla: {
      dueAt: '2026-07-28T14:00:00.000Z',
      target: 'Respond within 4 hours',
    },
    status: TicketStatus.Open,
    suggestedTools: ['remote-desktop', 'documentation', 'asset-management'],
    title: 'PDF editor closes while exporting annotated drawings',
  },
  {
    activity: [
      {
        detail: 'Email intake converted the request into an incident.',
        id: 'INC2404-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T08:24:00.000Z',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Hardware,
    createdAt: '2026-07-28T08:24:00.000Z',
    description: {
      businessImpact:
        'Calls can still be answered, but the advisor cannot reliably hear customers.',
      issue:
        'A USB headset produces short bursts of static after several minutes in a call.',
      reportedByLine:
        'Reported by the customer care floor coordinator on behalf of one advisor.',
      troubleshooting: [
        'Disconnected and reconnected the USB cable.',
        'Tested a second USB port.',
        'Confirmed the problem occurs in two calling applications.',
      ],
    },
    device: {
      assetTag: 'NX-9052',
      deviceName: 'AUDIO-CC-52',
      kind: 'peripheral',
      operatingSystem: 'USB audio device',
      state: 'attention',
    },
    escalated: false,
    hints: [
      'Work out whether the fault follows the headset or remains with the workstation.',
      'Use Asset Management to record the confirmed hardware condition, then review replacement options.',
      'Mark the faulty headset as damaged, ship one replacement headset to Elliot Ward, and document how the requester should verify it.',
    ],
    id: 'INC2404',
    notes: [],
    priority: Priority.Medium,
    requester: {
      contact: 'Ext. 1189',
      department: 'Customer Care',
      email: 'elliot.ward@nexus.example',
      location: 'South Campus · Level 2',
      name: 'Elliot Ward',
    },
    sla: {
      dueAt: '2026-07-28T13:30:00.000Z',
      target: 'Respond within 4 hours',
    },
    status: TicketStatus.Pending,
    suggestedTools: ['asset-management', 'shipping-manager', 'company-chat'],
    title: 'USB headset develops static during longer calls',
  },
  {
    activity: [
      {
        id: 'INC2405-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T07:05:00.000Z',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Access,
    createdAt: '2026-07-28T07:05:00.000Z',
    description: {
      businessImpact:
        'A new coordinator can complete orientation but cannot access the shared scheduling calendar.',
      issue:
        'The new starter can sign in to email and see the Facilities Calendar entry, but opening it returns an archived-location error.',
      reportedByLine:
        'Raised by the facilities team lead during the new starter checklist.',
      troubleshooting: [
        'Signed out and back in to the calendar application.',
        'Confirmed the user can open their personal calendar and another current Facilities calendar.',
        'Used the desktop calendar shortcut, which opened an archived-location error.',
      ],
    },
    device: {
      assetTag: 'NX-6128',
      deviceName: 'FAC-LT-12',
      kind: 'laptop',
      operatingSystem: 'Windows 11 Enterprise',
      state: 'active',
    },
    escalated: false,
    hints: [
      'Verify the requester already has the expected Facilities Calendar access before changing memberships.',
      'Inspect the calendar workspace location in the desktop shortcut.',
      'Review the access guide before changing any mapping.',
      'Ask the requester to reopen the original calendar after the shortcut is repaired.',
    ],
    id: 'INC2405',
    notes: [],
    priority: Priority.Low,
    requester: {
      contact: 'Ext. 5520',
      department: 'Facilities',
      email: 'sloane.rivera@nexus.example',
      location: 'Central Office · Level 1',
      name: 'Sloane Rivera',
    },
    sla: {
      dueAt: '2026-07-29T09:00:00.000Z',
      target: 'Respond by next business day',
    },
    status: TicketStatus.Open,
    suggestedTools: [
      'remote-desktop',
      'directory',
      'documentation',
      'company-chat',
    ],
    title: 'New coordinator cannot open the facilities calendar shortcut',
  },
  {
    activity: [
      {
        detail: 'The requester selected desktop support in the portal.',
        id: 'INC2406-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T09:55:00.000Z',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Network,
    createdAt: '2026-07-28T09:55:00.000Z',
    description: {
      businessImpact:
        'The project manager can work locally but cannot join the secure partner workspace.',
      issue:
        'The remote access client can reach the gateway, but the secure partner workspace is unavailable because the company VPN is disconnected.',
      reportedByLine:
        'Submitted from a home network before a scheduled partner review.',
      troubleshooting: [
        'Restarted the laptop.',
        'Confirmed normal internet browsing works.',
        'Confirmed the VPN client shows Disconnected.',
      ],
    },
    device: {
      assetTag: 'NX-2047',
      deviceName: 'PM-LT-41',
      kind: 'laptop',
      operatingSystem: 'Windows 11 Enterprise',
      state: 'active',
    },
    escalated: false,
    hints: [
      'Confirm the secure partner share is unavailable while ordinary internet browsing works.',
      'Review the company VPN connection state.',
      'Check current remote access guidance for the VPN route.',
      'Reconnect the VPN and retest the original partner workspace.',
    ],
    id: 'INC2406',
    notes: [],
    priority: Priority.High,
    requester: {
      contact: 'Mobile ending 604',
      department: 'Program Delivery',
      email: 'harper.kim@nexus.example',
      location: 'Remote · Eastern region',
      name: 'Harper Kim',
    },
    sla: {
      dueAt: '2026-07-28T11:40:00.000Z',
      target: 'Respond within 2 hours',
    },
    status: TicketStatus.Open,
    suggestedTools: ['remote-desktop', 'documentation', 'asset-management'],
    title: 'Remote partner workspace unavailable while VPN is disconnected',
  },
  {
    activity: [
      {
        detail: 'Created from the employee support portal.',
        id: 'INC2407-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T10:02:00.000Z',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Network,
    createdAt: '2026-07-28T10:02:00.000Z',
    description: {
      businessImpact:
        'Operations cannot open the internal scheduling portal, delaying same-day staffing changes.',
      issue:
        'The workstation can reach internet sites and known IP addresses, but internal Nexus hostnames do not load.',
      reportedByLine:
        'Submitted after the scheduling portal failed in two browsers.',
      troubleshooting: [
        'Restarted both browsers.',
        'Confirmed a public website loads.',
        'Restarted the workstation once.',
      ],
    },
    device: {
      assetTag: 'NX-8892',
      deviceName: 'OPS-LT-92',
      kind: 'laptop',
      operatingSystem: 'Windows 11 Enterprise',
      state: 'active',
    },
    escalated: false,
    hints: [
      'Separate address connectivity from hostname resolution.',
      'Inspect the adapter DNS configuration.',
      'Use an approved resolver and repeat the original name test.',
    ],
    id: 'INC2407',
    notes: [],
    priority: Priority.High,
    requester: {
      contact: 'Ext. 8892',
      department: 'Operations',
      email: 'dana.ortiz@nexus.example',
      location: 'North Campus · Operations',
      name: 'Dana Ortiz',
    },
    sla: {
      dueAt: '2026-07-28T12:02:00.000Z',
      target: 'Restore service within 2 hours',
    },
    status: TicketStatus.Open,
    suggestedTools: ['remote-desktop', 'documentation'],
    title: 'Internal sites fail while IP connectivity still works',
  },
  {
    activity: [
      {
        detail: 'Created from the desktop support shortcut.',
        id: 'INC2408-created',
        label: 'Ticket created',
        timestamp: '2026-07-28T09:48:00.000Z',
      },
    ],
    assignedTo: null,
    category: TicketCategory.Software,
    createdAt: '2026-07-28T09:48:00.000Z',
    description: {
      businessImpact:
        'Human Resources cannot print onboarding packets for the morning orientation.',
      issue:
        'Print jobs disappear immediately and no test page reaches the office printer.',
      reportedByLine:
        'Reported after the same document printed successfully from another workstation.',
      troubleshooting: [
        'Confirmed the printer is powered on.',
        'Printed the document from a neighboring workstation.',
        'Reopened the document on the affected computer.',
      ],
    },
    device: {
      assetTag: 'NX-4419',
      deviceName: 'HR-WS-19',
      kind: 'desktop',
      operatingSystem: 'Windows 11 Enterprise',
      state: 'attention',
    },
    escalated: false,
    hints: [
      'Reproduce the local symptom before changing the printer.',
      'Inspect the Windows service that queues print jobs.',
      'After restoring the service, send another test page.',
    ],
    id: 'INC2408',
    notes: [],
    priority: Priority.High,
    requester: {
      contact: 'Ext. 4419',
      department: 'Human Resources',
      email: 'eli.warren@nexus.example',
      location: 'Central Office · Human Resources',
      name: 'Eli Warren',
    },
    sla: {
      dueAt: '2026-07-28T11:48:00.000Z',
      target: 'Restore service within 2 hours',
    },
    status: TicketStatus.Open,
    suggestedTools: ['remote-desktop', 'documentation'],
    title: 'Print jobs disappear on the HR workstation',
  },
 ] as const satisfies readonly Ticket[];

export const TICKET_FIXTURES = [
  ...BASE_TICKET_FIXTURES,
  ...CONVERTED_LEGACY_TICKETS,
] as const;

export function getFixtureTicket(ticketId: string) {
  return TICKET_FIXTURES.find((ticket) => ticket.id === ticketId);
}
