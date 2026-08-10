import { DIRECTORY_USER_FIXTURES } from './directory-fixtures';
import { AssetStatus } from './enums';

export const REMOTE_DESKTOP_POWER_STATES = [
  'online',
  'offline',
  'restarting',
] as const;
export const REMOTE_DESKTOP_NETWORK_STATUSES = [
  'online',
  'offline',
  'limited',
] as const;
export const REMOTE_DESKTOP_SERVICE_STATES = ['running', 'stopped'] as const;
export const REMOTE_DESKTOP_DRIVE_STATUSES = [
  'connected',
  'disconnected',
  'network-path-error',
  'permission-error',
] as const;
export const REMOTE_DESKTOP_CONNECTION_STATES = [
  'disconnected',
  'connecting',
  'login',
  'connected',
  'error',
] as const;
export const REMOTE_DESKTOP_VPN_STATUSES = [
  'disconnected',
  'connecting',
  'connected',
  'error',
] as const;
export const REMOTE_DESKTOP_UPDATE_STATES = [
  'pending',
  'installing',
  'restart-required',
  'applied',
] as const;
export const REMOTE_DESKTOP_APP_IDS = [
  'explorer',
  'vpn',
  'settings',
  'services',
  'chat',
  'mail',
  'browser',
  'updates',
  'trash',
  'system',
  'terminal',
] as const;

export type RemoteDesktopPowerState =
  (typeof REMOTE_DESKTOP_POWER_STATES)[number];
export type RemoteDesktopNetworkStatus =
  (typeof REMOTE_DESKTOP_NETWORK_STATUSES)[number];
export type RemoteDesktopServiceState =
  (typeof REMOTE_DESKTOP_SERVICE_STATES)[number];
export type RemoteDesktopDriveStatus =
  (typeof REMOTE_DESKTOP_DRIVE_STATUSES)[number];
export type RemoteDesktopConnectionState =
  (typeof REMOTE_DESKTOP_CONNECTION_STATES)[number];
export type RemoteDesktopVpnStatus =
  (typeof REMOTE_DESKTOP_VPN_STATUSES)[number];
export type RemoteDesktopUpdateState =
  (typeof REMOTE_DESKTOP_UPDATE_STATES)[number];
export type RemoteDesktopAppId = (typeof REMOTE_DESKTOP_APP_IDS)[number];

export const REMOTE_DESKTOP_LEARNING_MODES = [
  'guided',
  'practice',
  'assessment',
] as const;
export type RemoteDesktopLearningMode =
  (typeof REMOTE_DESKTOP_LEARNING_MODES)[number];

export interface RemoteDesktopWorkflowObjective {
  /** Stable internal evidence keys. These are mentor-only and never student copy. */
  anyOf: readonly string[];
  id: string;
}

export interface RemoteDesktopScenarioWorkflow {
  /** Establishes the scope before the student changes the environment. */
  investigate: readonly RemoteDesktopWorkflowObjective[];
  diagnose: readonly RemoteDesktopWorkflowObjective[];
  fix: readonly RemoteDesktopWorkflowObjective[];
  verify: readonly RemoteDesktopWorkflowObjective[];
  note: { minimumLength: number };
  close: { explicit: true };
  scoring: {
    investigation: number;
    diagnosis: number;
    remediation: number;
    verification: number;
    documentation: number;
  };
  finalState: {
    dnsServers?: readonly string[];
    driveStates?: Readonly<Record<string, RemoteDesktopDriveStatus>>;
    serviceStates?: Readonly<Record<string, RemoteDesktopServiceState>>;
    vpnStatus?: RemoteDesktopVpnStatus;
  };
}

export interface RemoteDesktopScenarioFixture {
  actionLabels: Readonly<Record<string, string>>;
  documentationArticleIds: readonly string[];
  id: string;
  ticketId: string;
  assetTag: string;
  title: string;
  summary: string;
  studentHints: readonly string[];
  requiredSteps: readonly string[];
  optionalSteps: readonly string[];
  incorrectSteps: readonly string[];
  /** Phase-aware objectives are opt-in so the four legacy scenarios remain unchanged. */
  workflow?: RemoteDesktopScenarioWorkflow;
  completion: {
    rootCause: string;
    whatFixed: string;
    whyItWorked: string;
  };
  explanation: string;
}

export interface RemoteDesktopServiceFixture {
  name: string;
  state: RemoteDesktopServiceState;
}

export interface RemoteDesktopExplorerEntryFixture {
  kind: 'file' | 'folder';
  modifiedAt: string;
  name: string;
  path: string;
  size?: string;
}

export interface RemoteDesktopDriveFixture {
  entries: readonly RemoteDesktopExplorerEntryFixture[];
  freeGb: number;
  initialStatus: RemoteDesktopDriveStatus;
  kind: 'local' | 'network';
  label: string;
  letter: string;
  rootPath: string;
  sharePath: string | null;
  totalGb: number;
}

export interface RemoteDesktopWorkstationFixture {
  assetTag: string;
  directoryUserId: string;
  employeeName: string;
  hostname: string;
  ipAddress: string;
  lastLogon: string;
  location: string;
  networkStatus: RemoteDesktopNetworkStatus;
  operatingSystem: string;
  pendingUpdate: { id: string; title: string } | null;
  powerState: RemoteDesktopPowerState;
  drives: readonly RemoteDesktopDriveFixture[];
  services: readonly RemoteDesktopServiceFixture[];
}

/** Static terminal facts keep command output deterministic and simulation-only. */
export interface RemoteDesktopTerminalFixture {
  currentUser: string;
  dnsServers: readonly string[];
  systemModel: string;
}

function localDrive(
  assetTag: string,
  employeeName: string,
): RemoteDesktopDriveFixture {
  const number = assetDigits(assetTag);
  const userFolder = employeeName.toLowerCase().replace(/[^a-z0-9]+/g, '.');
  const userPath = `C:\\Users\\${userFolder}`;

  return {
    entries: [
      {
        kind: 'folder',
        modifiedAt: '2026-07-12 09:10',
        name: 'Program Files',
        path: 'C:\\Program Files',
      },
      {
        kind: 'folder',
        modifiedAt: '2026-07-28 08:05',
        name: 'Users',
        path: 'C:\\Users',
      },
      {
        kind: 'folder',
        modifiedAt: '2026-07-18 14:22',
        name: 'Windows',
        path: 'C:\\Windows',
      },
      {
        kind: 'folder',
        modifiedAt: '2026-07-28 08:05',
        name: userFolder,
        path: userPath,
      },
      {
        kind: 'folder',
        modifiedAt: '2026-07-30 10:14',
        name: 'Desktop',
        path: `${userPath}\\Desktop`,
      },
      {
        kind: 'folder',
        modifiedAt: '2026-07-29 16:42',
        name: 'Documents',
        path: `${userPath}\\Documents`,
      },
      {
        kind: 'file',
        modifiedAt: '2026-07-30 10:14',
        name: 'Support Notes.txt',
        path: `${userPath}\\Desktop\\Support Notes.txt`,
        size: '2 KB',
      },
      {
        kind: 'file',
        modifiedAt: '2026-07-29 16:42',
        name: 'Quarterly Checklist.docx',
        path: `${userPath}\\Documents\\Quarterly Checklist.docx`,
        size: '38 KB',
      },
    ],
    freeGb: 96 + (number % 173),
    initialStatus: 'connected' as const,
    kind: 'local' as const,
    label: 'Local Disk',
    letter: 'C:',
    rootPath: 'C:\\',
    sharePath: null,
    totalGb: 476,
  };
}

function networkDrives(assetTag: string): readonly RemoteDesktopDriveFixture[] {
  if (assetTag === 'NX-2047') {
    return [
      {
        entries: [
          {
            kind: 'folder',
            modifiedAt: '2026-07-29 13:18',
            name: 'Active Projects',
            path: 'Z:\\Active Projects',
          },
          {
            kind: 'folder',
            modifiedAt: '2026-07-22 09:31',
            name: 'Reference',
            path: 'Z:\\Reference',
          },
          {
            kind: 'file',
            modifiedAt: '2026-07-29 13:18',
            name: 'Partner Brief.pdf',
            path: 'Z:\\Active Projects\\Partner Brief.pdf',
            size: '824 KB',
          },
        ],
        freeGb: 138,
        initialStatus: 'network-path-error',
        kind: 'network',
        label: 'Partner Workspace',
        letter: 'Z:',
        rootPath: 'Z:\\',
        sharePath: '\\\\partner.nexus.internal\\workspace',
        totalGb: 250,
      },
    ];
  }

  if (assetTag === 'NX-6128') {
    return [
      {
        entries: [
          {
            kind: 'folder',
            modifiedAt: '2026-07-30 07:45',
            name: 'Calendar Archive',
            path: 'Y:\\Calendar Archive',
          },
          {
            kind: 'folder',
            modifiedAt: '2026-07-24 15:06',
            name: 'Templates',
            path: 'Y:\\Templates',
          },
          {
            kind: 'file',
            modifiedAt: '2026-07-30 07:45',
            name: 'Facilities Calendar.xlsx',
            path: 'Y:\\Calendar Archive\\Facilities Calendar.xlsx',
            size: '116 KB',
          },
        ],
        freeGb: 312,
        initialStatus: 'disconnected',
        kind: 'network',
        label: 'Facilities Calendar',
        letter: 'Y:',
        rootPath: 'Y:\\',
        sharePath: '\\\\facilities.nexus.internal\\calendar-archive',
        totalGb: 500,
      },
    ];
  }

  if (assetTag === 'NX-4831') {
    return [
      {
        entries: [],
        freeGb: 420,
        initialStatus: 'permission-error',
        kind: 'network',
        label: 'Finance Archive',
        letter: 'F:',
        rootPath: 'F:\\',
        sharePath: '\\\\finance.nexus.internal\\archive',
        totalGb: 1000,
      },
    ];
  }

  return [];
}

function workstationDrives(
  assetTag: string,
  employeeName: string,
): readonly RemoteDesktopDriveFixture[] {
  return [localDrive(assetTag, employeeName), ...networkDrives(assetTag)];
}

function assetDigits(assetTag: string) {
  return Number(assetTag.replace(/\D/g, ''));
}

function operatingSystem(assetTag: string, deviceType: string) {
  if (assetTag === 'NX-7714') return 'Android Enterprise 15';
  return deviceType === 'mobile workstation'
    ? 'Windows 11 Enterprise'
    : 'Windows 11 Pro';
}

const DIRECTORY_REMOTE_DESKTOP_WORKSTATIONS: readonly RemoteDesktopWorkstationFixture[] =
  DIRECTORY_USER_FIXTURES.map((user, index) => {
    const device = user.devices[0];
    const number = assetDigits(user.assetTag);
    const retired = device?.status === AssetStatus.Retired;
    const damaged = device?.status === AssetStatus.Damaged;

    return {
      assetTag: user.assetTag,
      directoryUserId: user.id,
      employeeName: user.fullName,
      hostname: `NX-${String(number).padStart(4, '0')}-WKS`,
      ipAddress: `10.${20 + (index % 6)}.${Math.floor(number / 100) % 200}.${10 + (number % 200)}`,
      lastLogon: `2026-07-28T${String(8 + (index % 2)).padStart(2, '0')}:${String(
        5 + ((index * 7) % 50),
      ).padStart(2, '0')}:00.000Z`,
      location: device?.location ?? 'HQ',
      networkStatus: retired ? 'offline' : damaged ? 'limited' : 'online',
      operatingSystem: operatingSystem(
        user.assetTag,
        device?.deviceType ?? 'laptop',
      ),
      pendingUpdate:
        user.assetTag === 'NX-3560'
          ? {
              id: 'KB-NX-447',
              title: 'PDF Export Reliability Update',
            }
          : null,
      powerState: retired ? 'offline' : 'online',
      drives: workstationDrives(user.assetTag, user.fullName),
      services: [
        { name: 'Print Spooler', state: 'running' },
        {
          name: 'Network Adapter Service',
          state: damaged ? 'stopped' : 'running',
        },
        {
          name: 'Windows Update',
          state: user.assetTag === 'NX-3560' ? 'stopped' : 'running',
        },
      ],
    };
  });

/** Ticket-specific machines that are intentionally not part of the Directory tool. */
const TICKET_REMOTE_DESKTOP_WORKSTATIONS: readonly RemoteDesktopWorkstationFixture[] =
  [
    {
      assetTag: 'NX-2047',
      directoryUserId: 'directory-user-harper-kim',
      employeeName: 'Harper Kim',
      hostname: 'PM-LT-41',
      ipAddress: '10.24.47.18',
      lastLogon: '2026-07-28T09:55:00.000Z',
      location: 'Remote · Eastern region',
      networkStatus: 'limited',
      operatingSystem: 'Windows 11 Enterprise Support Image',
      pendingUpdate: null,
      powerState: 'online',
      drives: workstationDrives('NX-2047', 'Harper Kim'),
      services: [
        { name: 'VPN Client Service', state: 'running' },
        { name: 'Network Adapter Service', state: 'running' },
        { name: 'Windows Update', state: 'running' },
      ],
    },
    {
      assetTag: 'NX-8892',
      directoryUserId: 'directory-user-dana-ortiz',
      employeeName: 'Dana Ortiz',
      hostname: 'OPS-LT-92',
      ipAddress: '10.28.92.24',
      lastLogon: '2026-07-28T10:02:00.000Z',
      location: 'North Campus · Operations',
      networkStatus: 'online',
      operatingSystem: 'Windows 11 Enterprise',
      pendingUpdate: null,
      powerState: 'online',
      drives: workstationDrives('NX-8892', 'Dana Ortiz'),
      services: [
        { name: 'DNS Client', state: 'running' },
        { name: 'Network Adapter Service', state: 'running' },
        { name: 'Windows Update', state: 'running' },
      ],
    },
    {
      assetTag: 'NX-4419',
      directoryUserId: 'directory-user-eli-warren',
      employeeName: 'Eli Warren',
      hostname: 'HR-WS-19',
      ipAddress: '10.26.19.44',
      lastLogon: '2026-07-28T09:48:00.000Z',
      location: 'Central Office · Human Resources',
      networkStatus: 'online',
      operatingSystem: 'Windows 11 Enterprise',
      pendingUpdate: null,
      powerState: 'online',
      drives: workstationDrives('NX-4419', 'Eli Warren'),
      services: [
        { name: 'Print Spooler', state: 'stopped' },
        { name: 'Network Adapter Service', state: 'running' },
        { name: 'Windows Update', state: 'running' },
      ],
    },
  ];

export const REMOTE_DESKTOP_WORKSTATION_FIXTURES: readonly RemoteDesktopWorkstationFixture[] =
  [
    ...DIRECTORY_REMOTE_DESKTOP_WORKSTATIONS,
    ...TICKET_REMOTE_DESKTOP_WORKSTATIONS,
    ...([
      ['NX-2501', 'Morgan Ellis', 'ACCT-LT-17'], ['NX-2502', 'Priya Shah', 'FIN-WS-44'],
      ['NX-2503', 'Jordan Kim', 'OPS-WS-12'], ['NX-2504', 'Sofia Nguyen', 'ENG-WS-09'],
      ['NX-2505', 'Taylor Reed', 'MKT-LT-05'], ['NX-2506', 'Casey Lane', 'HR-LT-21'],
      ['NX-2507', 'Avery Monroe', 'SALES-LT-08'], ['NX-2508', 'Riley Brown', 'PAY-LT-03'],
      ['NX-2509', 'Devon Ross', 'SUP-WS-31'], ['NX-2510', 'Sam Ortiz', 'OPS-LT-58'],
    ] as const).map(([assetTag, employeeName, hostname], index) => ({
      assetTag,
      directoryUserId: `directory-user-${assetTag.toLowerCase()}`,
      employeeName,
      hostname,
      ipAddress: `10.25.${index + 1}.25`,
      lastLogon: '2026-07-28T10:00:00.000Z',
      location: 'Nexus office',
      networkStatus: 'online' as const,
      operatingSystem: 'Windows 11 Enterprise',
      pendingUpdate: null,
      powerState: 'online' as const,
      drives: workstationDrives(assetTag, employeeName),
      services: [
        { name: 'Workstation', state: 'running' as const },
        { name: 'Windows Event Log', state: 'running' as const },
        { name: 'Network Adapter Service', state: 'running' as const },
      ],
    })),
  ];

export const REMOTE_DESKTOP_TERMINAL_FIXTURES: Readonly<
  Record<string, RemoteDesktopTerminalFixture>
> = {
  'NX-2047': {
    currentUser: 'NEXUS\\harper.kim',
    dnsServers: ['10.20.0.10', '10.20.0.11'],
    systemModel: 'Nexus Latitude 7440',
  },
  'NX-3560': {
    currentUser: 'NEXUS\\casey.morgan',
    dnsServers: ['10.21.0.10', '10.21.0.11'],
    systemModel: 'Nexus OptiPlex 7010',
  },
  'NX-4831': {
    currentUser: 'NEXUS\\jordan.lee',
    dnsServers: ['10.22.0.10', '10.22.0.11'],
    systemModel: 'Nexus Latitude 5430',
  },
  'NX-7714': {
    currentUser: 'NEXUS\\riley.chen',
    dnsServers: ['10.77.14.254'],
    systemModel: 'Nexus Rugged 5424',
  },
  'NX-6128': {
    currentUser: 'NEXUS\\morgan.taylor',
    dnsServers: ['10.24.0.10', '10.24.0.11'],
    systemModel: 'Nexus Latitude 5540',
  },
  'NX-8892': {
    currentUser: 'NEXUS\\dana.ortiz',
    dnsServers: ['192.0.2.53', '192.0.2.54'],
    systemModel: 'Nexus Latitude 5450',
  },
  'NX-4419': {
    currentUser: 'NEXUS\\eli.warren',
    dnsServers: ['10.20.0.10', '10.20.0.11'],
    systemModel: 'Nexus OptiPlex 7020',
  },
};

export function getRemoteDesktopTerminalFixture(assetTag: string) {
  return (
    REMOTE_DESKTOP_TERMINAL_FIXTURES[assetTag] ?? {
      currentUser: 'NEXUS\\support.user',
      dnsServers: ['10.20.0.10'],
      systemModel: 'Nexus Managed Workstation',
    }
  );
}

export function getRemoteDesktopInitialDriveStates(assetTag: string) {
  const workstation = getRemoteDesktopWorkstation(assetTag);
  return Object.fromEntries(
    workstation?.drives.map((drive) => [drive.letter, drive.initialStatus]) ??
      [],
  ) as Readonly<Record<string, RemoteDesktopDriveStatus>>;
}

export function getRemoteDesktopWorkstation(assetTag: string) {
  return REMOTE_DESKTOP_WORKSTATION_FIXTURES.find(
    (workstation) => workstation.assetTag === assetTag,
  );
}

/**
 * These are deterministic desktop-only learning scenarios. They deliberately
 * model the ticket/asset relationship rather than a real RDP connection.
 */
const CURATED_REMOTE_DESKTOP_SCENARIOS: readonly RemoteDesktopScenarioFixture[] =
  [
    {
      id: 'vpn-shared-drive',
      ticketId: 'INC2406',
      assetTag: 'NX-2047',
      title: 'VPN disconnected blocks the partner share',
      summary:
        'The laptop has internet access, but the secure partner share is unavailable until the simulated VPN reconnects.',
      studentHints: [
        'Think about how a remote employee reaches company-only resources from home.',
        'Check whether the affected computer is connected to the company VPN.',
        'Reconnect the VPN, then test the shared drive again.',
      ],
      actionLabels: {
        'explorer.share-unreachable':
          'Confirmed the partner share was unreachable before the fix',
        'explorer.share-reachable':
          'Confirmed the partner share opened after the fix',
        'explorer.remove-share': 'Changed the shared-drive mapping',
        'explorer.verify-share': 'Tested access to the shared drive',
        'system.view-network': 'Reviewed network information',
        'terminal.ping-hostname-failed':
          'Confirmed the partner host was unreachable before the fix',
        'updates.install': 'Installed an unrelated update',
        'vpn.connect': 'Connected the company VPN',
        'vpn.connected': 'Connected the company VPN',
        'vpn.state-inspected': 'Inspected the VPN connection state',
      },
      documentationArticleIds: [
        'network-vpn-device-check',
        'network-first-response',
      ],
      requiredSteps: [],
      optionalSteps: [
        'terminal.ping-hostname-failed',
        'explorer.share-unreachable',
        'system.view-network',
      ],
      incorrectSteps: ['explorer.remove-share', 'updates.install'],
      workflow: {
        investigate: [
          {
            id: 'affected-resource-confirmed',
            anyOf: [
              'explorer.share-unreachable',
              'terminal.ping-hostname-failed',
            ],
          },
        ],
        diagnose: [
          {
            id: 'network-access-failure',
            anyOf: [
              'explorer.share-unreachable',
              'terminal.ping-hostname-failed',
            ],
          },
          { id: 'vpn-state', anyOf: ['vpn.state-inspected'] },
        ],
        fix: [{ id: 'vpn-connected', anyOf: ['vpn.connected'] }],
        verify: [
          {
            id: 'share-access-restored',
            anyOf: ['explorer.share-reachable'],
          },
        ],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: {
          driveStates: { 'Z:': 'connected' },
          vpnStatus: 'connected',
        },
      },
      explanation:
        'The share is reachable only on the secure route. Reconnecting the VPN restores the route; remapping the drive was not required.',
      completion: {
        rootCause:
          'The company VPN was disconnected, so the private partner route was unavailable.',
        whatFixed:
          'Reconnecting the VPN and confirming the shared drive was reachable.',
        whyItWorked:
          'The VPN restores the secure route required to reach the partner workspace.',
      },
    },
    {
      id: 'dns-configuration-failure',
      ticketId: 'INC2407',
      assetTag: 'NX-8892',
      title: 'Incorrect DNS servers block internal names',
      summary:
        'The workstation has working IP connectivity but cannot resolve internal hostnames because its DNS servers are incorrect.',
      studentHints: [
        'Separate basic IP connectivity from name resolution before changing the adapter.',
        'Compare an IP ping with a hostname lookup, then inspect the configured DNS servers.',
        'Set the adapter to the approved Nexus DNS servers and repeat a hostname lookup.',
      ],
      actionLabels: {
        'settings.dns-corrected': 'Configured the approved DNS servers',
        'terminal.ipconfig': 'Reviewed the adapter configuration',
        'terminal.ipconfig-all':
          'Reviewed the adapter and configured DNS servers',
        'terminal.nslookup-failed':
          'Captured the name-resolution failure before the fix',
        'terminal.nslookup-success': 'Confirmed name resolution after the fix',
        'terminal.ping-hostname-failed':
          'Confirmed hostname lookup failed before the fix',
        'terminal.ping-hostname-success':
          'Confirmed hostname connectivity after the fix',
        'terminal.ping-ip-success':
          'Confirmed basic IP connectivity was working',
        'updates.install': 'Installed an unrelated update',
      },
      documentationArticleIds: ['network-dns-triage', 'network-first-response'],
      requiredSteps: [],
      optionalSteps: [
        'terminal.ipconfig-all',
        'terminal.ping-hostname-success',
      ],
      incorrectSteps: ['updates.install'],
      workflow: {
        investigate: [
          {
            id: 'network-scope',
            anyOf: [
              'terminal.ping-ip-success',
              'terminal.ipconfig',
              'terminal.ipconfig-all',
            ],
          },
        ],
        diagnose: [
          {
            id: 'adapter-configuration',
            anyOf: ['terminal.ipconfig', 'terminal.ipconfig-all'],
          },
          { id: 'ip-connectivity', anyOf: ['terminal.ping-ip-success'] },
          {
            id: 'name-resolution-failure',
            anyOf: [
              'terminal.nslookup-failed',
              'terminal.ping-hostname-failed',
            ],
          },
        ],
        fix: [
          { id: 'approved-dns-configured', anyOf: ['settings.dns-corrected'] },
        ],
        verify: [
          {
            id: 'name-resolution-restored',
            anyOf: [
              'terminal.nslookup-success',
              'terminal.ping-hostname-success',
            ],
          },
        ],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: { dnsServers: ['10.20.0.10', '10.20.0.11'] },
      },
      explanation:
        'The adapter pointed to non-routable DNS servers. Using the approved Nexus resolvers restores internal name resolution while preserving working IP connectivity.',
      completion: {
        rootCause:
          'The workstation was configured with incorrect DNS server addresses.',
        whatFixed:
          'Replacing the DNS entries with the approved Nexus resolvers and validating a hostname lookup.',
        whyItWorked:
          'The approved resolvers can answer internal Nexus names that the incorrect servers could not resolve.',
      },
    },
    {
      id: 'service-failure',
      ticketId: 'INC2408',
      assetTag: 'NX-4419',
      title: 'Stopped Print Spooler blocks local printing',
      summary:
        'Print jobs fail because the Print Spooler service is stopped, while the rest of the workstation remains healthy.',
      studentHints: [
        'Reproduce the print symptom and inspect the local service that queues print jobs.',
        'Use Services or Terminal to confirm whether Print Spooler is running.',
        'Start or restart Print Spooler, then send another simulated test page.',
      ],
      actionLabels: {
        'printer.test-failed': 'Captured a failed test print before the fix',
        'printer.test-succeeded': 'Confirmed a test page printed after the fix',
        'service.print-spooler-running': 'Started the Print Spooler service',
        'services.state-inspected':
          'Confirmed Print Spooler was stopped in Services',
        'terminal.service-stopped':
          'Confirmed Print Spooler was stopped in Terminal',
        'terminal.tasklist-service-missing':
          'Confirmed the Print Spooler process was absent',
        'updates.install': 'Installed an unrelated update',
      },
      documentationArticleIds: [
        'server-service-health',
        'hardware-peripheral-isolation',
      ],
      requiredSteps: [],
      optionalSteps: [
        'terminal.tasklist-service-missing',
        'services.state-inspected',
      ],
      incorrectSteps: ['updates.install'],
      workflow: {
        investigate: [{ id: 'print-symptom', anyOf: ['printer.test-failed'] }],
        diagnose: [
          { id: 'print-symptom', anyOf: ['printer.test-failed'] },
          {
            id: 'service-status',
            anyOf: [
              'services.state-inspected',
              'terminal.service-stopped',
              'terminal.tasklist-service-missing',
            ],
          },
        ],
        fix: [
          {
            id: 'spooler-running',
            anyOf: ['service.print-spooler-running'],
          },
        ],
        verify: [{ id: 'print-restored', anyOf: ['printer.test-succeeded'] }],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: { serviceStates: { 'Print Spooler': 'running' } },
      },
      explanation:
        'The Print Spooler was stopped, so Windows could not queue print jobs. Starting the service restores the print pipeline.',
      completion: {
        rootCause: 'The local Print Spooler service was stopped.',
        whatFixed:
          'Starting Print Spooler and confirming a simulated test page completed.',
        whyItWorked:
          'Print Spooler queues jobs for Windows applications; once it was running, the dependent print action could complete.',
      },
    },
    {
      id: 'pdf-export-update',
      ticketId: 'INC2403',
      assetTag: 'NX-3560',
      title: 'PDF export fails while a reliability update is pending',
      summary:
        'The PDF editor crashes only when exporting the full annotated package; a pending reliability update addresses the known export component fault.',
      studentHints: [
        'Reproduce the full-package export failure before changing the application.',
        'Check whether this computer has a pending reliability or application update.',
        'A component that supports PDF export may need to reload after an update.',
        'Install the pending update, restart the PDF helper, and retry the export.',
      ],
      actionLabels: {
        'browser.retry-export': 'Retry the annotated PDF export',
        'browser.export-failed':
          'Reproduced the full annotated PDF export failure',
        'browser.export-succeeded':
          'Confirmed the annotated PDF export completed',
        'explorer.check-free-space': 'Checked available storage',
        'system.restart-pdf-helper': 'Restarted the PDF helper',
        'trash.empty': 'Emptied the recycle bin',
        'updates.install': 'Installed the pending reliability update',
        'vpn.connect': 'Connected the company VPN',
      },
      documentationArticleIds: [
        'software-large-export-crash',
        'sop-change-record',
      ],
      requiredSteps: [],
      optionalSteps: ['explorer.check-free-space'],
      incorrectSteps: ['trash.empty', 'vpn.connect'],
      workflow: {
        investigate: [
          { id: 'failure-reproduced', anyOf: ['browser.export-failed'] },
        ],
        diagnose: [
          { id: 'update-inspected', anyOf: ['updates.pending-inspected'] },
          { id: 'system-scope', anyOf: ['explorer.check-free-space'] },
        ],
        fix: [
          { id: 'reliability-update-applied', anyOf: ['updates.applied'] },
          { id: 'pdf-helper-restarted', anyOf: ['system.restart-pdf-helper'] },
        ],
        verify: [
          { id: 'export-restored', anyOf: ['browser.export-succeeded'] },
        ],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: {},
      },
      explanation:
        'The export helper was using an outdated component. Applying the pending update and restarting the helper loads the corrected version.',
      completion: {
        rootCause:
          'The PDF helper was still using an outdated export component.',
        whatFixed:
          'Installing the reliability update, restarting the helper, and validating the export.',
        whyItWorked:
          'Restarting the helper loaded the corrected component from the installed update.',
      },
    },
    {
      id: 'profile-storage',
      ticketId: 'INC2401',
      assetTag: 'NX-4831',
      title: 'Corrupt browser profile storage causes a sign-in loop',
      summary:
        'The finance portal authentication loop is isolated to the local browser profile, not the employee account.',
      studentHints: [
        'The issue may be isolated to data stored on this computer rather than the employee account.',
        'Review the browser or profile settings before making account changes.',
        'Clear the affected browser profile storage and retry the portal sign-in.',
      ],
      actionLabels: {
        'browser.retry-sign-in': 'Retry the finance portal sign-in',
        'browser.sign-in-loop-confirmed':
          'Confirmed the portal returned to sign-in before the repair',
        'browser.sign-in-restored':
          'Confirmed the finance portal opened after the repair',
        'explorer.remove-share': 'Changed the shared-drive mapping',
        'mail.review-alert': 'Reviewed the support alert',
        'settings.clear-profile-storage':
          'Cleared local browser profile storage',
        'vpn.connect': 'Connected the company VPN',
      },
      documentationArticleIds: [
        'access-signin-loop',
        'email-client-profile-repair',
      ],
      requiredSteps: [],
      optionalSteps: ['mail.review-alert'],
      incorrectSteps: ['vpn.connect', 'explorer.remove-share'],
      workflow: {
        investigate: [
          { id: 'profile-evidence-reviewed', anyOf: ['mail.review-alert'] },
        ],
        diagnose: [
          {
            id: 'sign-in-loop-reproduced',
            anyOf: ['browser.sign-in-loop-confirmed'],
          },
        ],
        fix: [
          {
            id: 'profile-storage-cleared',
            anyOf: ['settings.clear-profile-storage'],
          },
        ],
        verify: [
          {
            id: 'finance-portal-restored',
            anyOf: ['browser.sign-in-restored'],
          },
        ],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: {},
      },
      explanation:
        'Clearing the stale local profile token forces a clean browser session. Resetting the account would not correct the workstation issue.',
      completion: {
        rootCause:
          'Stale local browser profile data was returning the user to the sign-in page.',
        whatFixed:
          'Clearing the local profile storage and retrying the sign-in.',
        whyItWorked:
          'The portal started a clean local session instead of reusing the stale profile data.',
      },
    },
    {
      id: 'network-configuration',
      ticketId: 'INC2402',
      assetTag: 'NX-7714',
      title: 'Managed scanner wireless profile drops at one loading lane',
      summary:
        'The affected Android Enterprise scanner has a stale managed wireless profile; nearby scanners remain connected to the same warehouse network.',
      studentHints: [
        'Use the working scanner beside it to establish that the local access point is not the common cause.',
        'Inspect the affected device’s managed wireless profile before resetting anything.',
        'Refresh the affected managed profile, renew its lease, and confirm stability.',
      ],
      actionLabels: {
        'chat.confirm-restored': 'Confirmed the service was restored',
        'terminal.ipconfig': 'Reviewed the managed device network status',
        'terminal.ping-ip-success':
          'Confirmed basic warehouse network reachability',
        'settings.repair-network': 'Repaired the network profile',
        'system.renew-address': 'Renewed the network address',
        'trash.empty': 'Emptied the recycle bin',
        'updates.install': 'Installed an unrelated update',
      },
      documentationArticleIds: ['network-dns-triage', 'network-first-response'],
      requiredSteps: [],
      optionalSteps: ['chat.confirm-restored'],
      incorrectSteps: ['updates.install', 'trash.empty'],
      workflow: {
        investigate: [
          { id: 'affected-device-scoped', anyOf: ['terminal.ipconfig'] },
        ],
        diagnose: [
          { id: 'wireless-path-isolated', anyOf: ['terminal.ping-ip-success'] },
        ],
        fix: [
          {
            id: 'managed-profile-refreshed',
            anyOf: ['settings.repair-network'],
          },
          { id: 'lease-renewed', anyOf: ['system.renew-address'] },
        ],
        verify: [{ id: 'scanner-stable', anyOf: ['chat.confirm-restored'] }],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: {},
      },
      explanation:
        'Restoring the known-good adapter profile and renewing its address returns the device to the warehouse segment.',
      completion: {
        rootCause: 'The computer had an incorrect network adapter profile.',
        whatFixed:
          'Restoring the network profile and renewing the device address.',
        whyItWorked:
          'The computer returned to the correct internal network segment.',
      },
    },
    {
      id: 'facilities-calendar-mapping',
      ticketId: 'INC2405',
      assetTag: 'NX-6128',
      title: 'Facilities calendar shortcut points to an archived location',
      summary:
        'The coordinator already has Facilities Calendar access, but the desktop shortcut points to an archived workspace location.',
      studentHints: [
        'Confirm the calendar location before changing permissions or accounts.',
        'Inspect the mapped calendar workspace and compare it with the current Facilities location.',
        'Repair the stale mapping, then verify the requested calendar workspace opens.',
      ],
      actionLabels: {
        'chat.confirm-restored': 'Confirmed the service was restored',
        'explorer.mapping-obsolete':
          'Confirmed the calendar shortcut targeted the archived workspace',
        'explorer.repair-mapping': 'Repaired the mapped drive location',
        'explorer.verify-share': 'Tested access to the shared drive',
        'settings.clear-profile-storage':
          'Cleared local browser profile storage',
        'vpn.connect': 'Connected the company VPN',
      },
      documentationArticleIds: [
        'access-group-membership',
        'network-first-response',
      ],
      requiredSteps: [],
      optionalSteps: ['chat.confirm-restored'],
      incorrectSteps: ['vpn.connect', 'settings.clear-profile-storage'],
      workflow: {
        investigate: [
          {
            id: 'calendar-location-inspected',
            anyOf: ['explorer.mapping-obsolete'],
          },
        ],
        diagnose: [
          {
            id: 'obsolete-mapping-confirmed',
            anyOf: ['explorer.mapping-obsolete'],
          },
        ],
        fix: [
          {
            id: 'calendar-mapping-repaired',
            anyOf: ['explorer.repair-mapping'],
          },
        ],
        verify: [
          { id: 'calendar-workspace-opened', anyOf: ['explorer.verify-share'] },
        ],
        note: { minimumLength: 20 },
        close: { explicit: true },
        scoring: {
          investigation: 15,
          diagnosis: 25,
          remediation: 30,
          verification: 20,
          documentation: 10,
        },
        finalState: { driveStates: { 'Y:': 'connected' } },
      },
      explanation:
        'The user already has the correct access. Updating the stale mapped-drive target restores the calendar workspace.',
      completion: {
        rootCause:
          'The mapped drive pointed to an obsolete facilities location.',
        whatFixed:
          'Updating the mapping and confirming the workspace was available.',
        whyItWorked:
          'The drive now points to the current location the user is already allowed to access.',
      },
    },
  ];

type ConvertedScenarioSpec = {
  id: string;
  ticketId: string;
  assetTag: string;
  title: string;
  summary: string;
  rootCause: string;
  remedy: string;
  investigation: string;
  diagnosis: string;
  remediation: string;
  verification: string;
};

function convertedScenario(spec: ConvertedScenarioSpec): RemoteDesktopScenarioFixture {
  const actionLabels = {
    'scenario.inspect-symptom': spec.investigation,
    'scenario.collect-evidence': 'Collected relevant system and comparison evidence',
    'scenario.isolate-root-cause': spec.diagnosis,
    'scenario.apply-safe-remediation': spec.remediation,
    'scenario.verify-original-symptom': spec.verification,
  };
  return {
    id: spec.id,
    ticketId: spec.ticketId,
    assetTag: spec.assetTag,
    title: spec.title,
    summary: spec.summary,
    studentHints: [
      'Establish scope before changing the environment.',
      'Use the case tools to capture evidence that distinguishes likely causes.',
      'Apply the safe, specific remediation and verify the original request.',
    ],
    actionLabels,
    documentationArticleIds: ['network-first-response', 'sop-change-record'],
    requiredSteps: [], optionalSteps: ['scenario.collect-evidence'], incorrectSteps: [],
    workflow: {
      investigate: [{ id: 'scope-established', anyOf: ['scenario.inspect-symptom', 'scenario.collect-evidence'] }],
      diagnose: [{ id: 'root-cause-isolated', anyOf: ['scenario.isolate-root-cause'] }],
      fix: [{ id: 'safe-remediation-applied', anyOf: ['scenario.apply-safe-remediation'] }],
      verify: [{ id: 'original-symptom-verified', anyOf: ['scenario.verify-original-symptom'] }],
      note: { minimumLength: 20 }, close: { explicit: true },
      scoring: { investigation: 15, diagnosis: 25, remediation: 30, verification: 20, documentation: 10 },
      finalState: {},
    },
    explanation: spec.rootCause,
    completion: { rootCause: spec.rootCause, whatFixed: spec.remedy, whyItWorked: 'The action addressed the established cause and the original symptom was retested.' },
  };
}

const CONVERTED_REMOTE_DESKTOP_SCENARIOS: readonly RemoteDesktopScenarioFixture[] = [
  convertedScenario({ id: 'temporary-windows-profile', ticketId: 'INC2501', assetTag: 'NX-2501', title: 'Temporary Windows profile hides user files', summary: 'The sign-in created a temporary profile; user data must be protected before profile repair.', rootCause: 'Windows loaded a temporary profile instead of the user’s normal profile.', remedy: 'Protected the user data, repaired the profile mapping, and confirmed the normal profile loaded.', investigation: 'Inspected the sign-in profile and protected user data', diagnosis: 'Isolated a temporary profile rather than deleted files', remediation: 'Repaired the temporary profile mapping safely', verification: 'Confirmed the normal desktop and Documents returned' }),
  convertedScenario({ id: 'excel-add-in-isolation', ticketId: 'INC2502', assetTag: 'NX-2502', title: 'Excel add-in crashes one reporting workbook', summary: 'The crash must be reproduced and isolated from workbook-only and application-wide causes.', rootCause: 'A reporting add-in conflicted with the workbook load path.', remedy: 'Disabled the failing add-in and validated the workbook opens and saves.', investigation: 'Reproduced the crash with the original workbook', diagnosis: 'Used Safe Mode evidence to isolate the failing add-in', remediation: 'Disabled the identified Excel add-in', verification: 'Opened and saved the original reporting workbook' }),
  convertedScenario({ id: 'office-move-network', ticketId: 'INC2503', assetTag: 'NX-2503', title: 'Moved desk is on the wrong network path', summary: 'A single moved workstation needs physical, switch, VLAN, and DHCP isolation against a working neighbour.', rootCause: 'The moved desk was connected to an incorrectly assigned switch port/VLAN.', remedy: 'Corrected the approved switch-port assignment and renewed network access.', investigation: 'Compared the affected desk with a nearby working workstation', diagnosis: 'Isolated the physical switch-port/VLAN mismatch', remediation: 'Corrected the approved switch-port assignment', verification: 'Confirmed the original order system loads at the moved desk' }),
  convertedScenario({ id: 'printer-dhcp-port', ticketId: 'INC2504', assetTag: 'NX-2504', title: 'Local print port still uses an old DHCP address', summary: 'The printer is healthy for peers, while the affected workstation retains an obsolete print port.', rootCause: 'The workstation’s printer port still targeted the printer’s old DHCP address.', remedy: 'Updated the local print port to the approved current address and printed a test page.', investigation: 'Confirmed printing works from a nearby workstation', diagnosis: 'Compared the local print port with the current printer address', remediation: 'Updated the obsolete local print port', verification: 'Printed the original test document successfully' }),
  convertedScenario({ id: 'department-share-least-privilege', ticketId: 'INC2505', assetTag: 'NX-2505', title: 'New hire lacks approved department-share group', summary: 'Use peer comparison and approved least-privilege membership before changing access.', rootCause: 'The new employee was missing the approved Marketing share group.', remedy: 'Added only the approved department group and confirmed access.', investigation: 'Confirmed the requested share and compared an authorized peer', diagnosis: 'Identified the missing approved group membership', remediation: 'Applied the least-privilege department group change', verification: 'Opened the original Marketing share successfully' }),
  convertedScenario({ id: 'restricted-folder-escalation', ticketId: 'INC2506', assetTag: 'NX-2506', title: 'Restricted salary-folder request requires authorization', summary: 'The correct resolution is safe escalation, not a convenient group change.', rootCause: 'The request lacked authorization for restricted HR salary records.', remedy: 'Did not grant access; routed the request to the authorized HR approver.', investigation: 'Confirmed the folder is restricted and approval is absent', diagnosis: 'Identified the authorization boundary', remediation: 'Escalated through the authorized HR access path', verification: 'Confirmed the requester received the approved escalation update' }),
  convertedScenario({ id: 'recurring-lockout-stale-mapping', ticketId: 'INC2507', assetTag: 'NX-2507', title: 'Stale mapped-drive credential relocks account', summary: 'Resetting an account treats the symptom; evidence must identify the stored old credential.', rootCause: 'A mapped drive repeatedly submitted the old password after the reset.', remedy: 'Removed or updated the stale saved mapping credential and monitored for recurrence.', investigation: 'Reviewed the recurring lockout timing and saved connections', diagnosis: 'Isolated the stale mapped-drive credential', remediation: 'Removed the obsolete saved drive credential', verification: 'Confirmed the account remained unlocked after the normal interval' }),
  convertedScenario({ id: 'phishing-credential-containment', ticketId: 'INC2508', assetTag: 'NX-2508', title: 'Phishing credential exposure needs containment', summary: 'Security containment and escalation take priority over ordinary troubleshooting.', rootCause: 'Credentials were entered on a suspected phishing page.', remedy: 'Contained the account, reset credentials, revoked sessions, and escalated to security.', investigation: 'Captured the phishing report and exposure scope', diagnosis: 'Classified the event as credential compromise', remediation: 'Performed safe containment and security escalation', verification: 'Confirmed sessions were revoked and the employee received safe follow-up' }),
  convertedScenario({ id: 'recurring-disk-growth', ticketId: 'INC2509', assetTag: 'NX-2509', title: 'Recurring disk exhaustion caused by runaway logs', summary: 'Deleting temporary files is not a durable repair when application logs keep growing.', rootCause: 'A runaway application log was consuming the system drive.', remedy: 'Corrected the log retention/configuration issue and verified stable free space.', investigation: 'Compared disk use over time and identified the growing path', diagnosis: 'Isolated the runaway application log', remediation: 'Corrected log retention at the source', verification: 'Confirmed free space remained available after the scheduled interval' }),
  convertedScenario({ id: 'domain-trust-repair', ticketId: 'INC2510', assetTag: 'NX-2510', title: 'Restored laptop has a broken domain trust', summary: 'The device computer-account relationship—not the user password—must be diagnosed safely.', rootCause: 'The restored laptop’s computer account no longer had a valid secure channel with the domain.', remedy: 'Repaired the secure channel through the approved device process and retested sign-in.', investigation: 'Confirmed the trust error and ruled out a general network failure', diagnosis: 'Identified the broken computer-account secure channel', remediation: 'Repaired the device trust through the approved process', verification: 'Confirmed normal domain sign-in on the restored laptop' }),
];

export const REMOTE_DESKTOP_SCENARIOS: readonly RemoteDesktopScenarioFixture[] = [
  ...CURATED_REMOTE_DESKTOP_SCENARIOS,
  ...CONVERTED_REMOTE_DESKTOP_SCENARIOS,
];

export function getRemoteDesktopScenarioByTicket(ticketId: string) {
  return REMOTE_DESKTOP_SCENARIOS.find(
    (scenario) => scenario.ticketId === ticketId,
  );
}

export function getRemoteDesktopScenarioByAsset(assetTag: string) {
  return REMOTE_DESKTOP_SCENARIOS.find(
    (scenario) => scenario.assetTag === assetTag,
  );
}
