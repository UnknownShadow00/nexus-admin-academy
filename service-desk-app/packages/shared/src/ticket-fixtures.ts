import { Priority, TicketCategory } from './enums';
import { TicketStatus, type Ticket } from './ticket-types';

export const FIXTURE_REFERENCE_TIME = '2026-07-28T10:30:00.000Z';

export const TICKET_FIXTURES = [
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
        'The finance reporting portal accepts the first authentication step, then returns to the sign-in screen before the dashboard loads.',
      reportedByLine:
        'Submitted through the employee support portal after two failed sign-in attempts.',
      troubleshooting: [
        'Closed and reopened the browser.',
        'Confirmed other internal sites load normally.',
        'Tried a private browsing window with the same result.',
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
      'Review the directory record for a locked account or an expired access policy.',
      'Check the knowledge base for the finance portal sign-in loop procedure.',
      'Ask the requester to start a fresh session after the account state is corrected.',
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
      'Open Remote Desktop and compare the affected scanner’s network settings with the working unit.',
      'Repair the affected network profile, renew its address, and then watch the connection long enough to verify stability.',
    ],
    id: 'INC2402',
    notes: [],
    priority: Priority.Critical,
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
        'The new starter can sign in to email but the facilities scheduling calendar is not listed.',
      reportedByLine:
        'Raised by the facilities team lead during the new starter checklist.',
      troubleshooting: [
        'Signed out and back in to the calendar application.',
        'Searched for the calendar by its full display name.',
        'Confirmed the user can open their personal calendar.',
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
      'Verify the requester identity and the intended facilities team membership.',
      'Compare the directory groups with another coordinator in the same role.',
      'Review the access guide before changing any group membership.',
      'Ask the requester to refresh the calendar list after access synchronizes.',
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
    title: 'New coordinator cannot see the facilities calendar',
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
        'The remote access client reaches the gateway, then stops while checking the device profile.',
      reportedByLine:
        'Submitted from a home network before a scheduled partner review.',
      troubleshooting: [
        'Restarted the laptop.',
        'Confirmed normal internet browsing works.',
        'Retried the connection after closing other applications.',
      ],
    },
    device: {
      assetTag: 'NX-2047',
      deviceName: 'PM-LT-41',
      kind: 'laptop',
      operatingSystem: 'macOS 16',
      state: 'active',
    },
    escalated: false,
    hints: [
      'Confirm the client version and capture the exact device-check stage.',
      'Review the device asset record for compliance status.',
      'Check current remote access guidance for the reported platform.',
      'Retry after correcting any documented client or compliance mismatch.',
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
    title: 'Remote access pauses during the device compliance check',
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

export function getFixtureTicket(ticketId: string) {
  return TICKET_FIXTURES.find((ticket) => ticket.id === ticketId);
}
