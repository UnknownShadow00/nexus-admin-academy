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
  diagnose: readonly RemoteDesktopWorkflowObjective[];
  fix: readonly RemoteDesktopWorkflowObjective[];
  verify: readonly RemoteDesktopWorkflowObjective[];
  note: { minimumLength: number };
  close: { explicit: true };
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

function operatingSystem(deviceType: string) {
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
      operatingSystem: operatingSystem(device?.deviceType ?? 'laptop'),
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
export const REMOTE_DESKTOP_SCENARIOS: readonly RemoteDesktopScenarioFixture[] =
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
        'A known export component fix is queued. Install the update, restart the PDF helper, then retry the export.',
      studentHints: [
        'Check whether this computer has a pending reliability or application update.',
        'A component that supports PDF export may need to reload after an update.',
        'Install the pending update, restart the PDF helper, and retry the export.',
      ],
      actionLabels: {
        'browser.retry-export': 'Retried the PDF export',
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
      requiredSteps: [
        'updates.install',
        'system.restart-pdf-helper',
        'browser.retry-export',
      ],
      optionalSteps: ['explorer.check-free-space'],
      incorrectSteps: ['trash.empty', 'vpn.connect'],
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
        'browser.retry-sign-in': 'Retried the portal sign-in',
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
      requiredSteps: [
        'settings.clear-profile-storage',
        'browser.retry-sign-in',
      ],
      optionalSteps: ['mail.review-alert'],
      incorrectSteps: ['vpn.connect', 'explorer.remove-share'],
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
      title: 'Incorrect network configuration interrupts warehouse access',
      summary:
        'A bad adapter profile prevents the device from maintaining its internal network route.',
      studentHints: [
        'Compare the computer’s network configuration with the route it needs to reach.',
        'Look for a network profile or address configuration that may be out of date.',
        'Repair the adapter profile, renew the address, and confirm the connection.',
      ],
      actionLabels: {
        'chat.confirm-restored': 'Confirmed the service was restored',
        'settings.repair-network': 'Repaired the network profile',
        'system.renew-address': 'Renewed the network address',
        'trash.empty': 'Emptied the recycle bin',
        'updates.install': 'Installed an unrelated update',
      },
      documentationArticleIds: ['network-dns-triage', 'network-first-response'],
      requiredSteps: ['settings.repair-network', 'system.renew-address'],
      optionalSteps: ['chat.confirm-restored'],
      incorrectSteps: ['updates.install', 'trash.empty'],
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
      id: 'mapped-drive-permissions',
      ticketId: 'INC2405',
      assetTag: 'NX-6128',
      title: 'Mapped drive points to the wrong facilities location',
      summary:
        'The calendar workspace mapping targets an obsolete location; update it and validate access without changing permissions.',
      studentHints: [
        'The user may already have access, but the computer could be pointing to the wrong location.',
        'Inspect the mapped drive before changing permissions or accounts.',
        'Repair the drive mapping, then verify the shared location opens.',
      ],
      actionLabels: {
        'chat.confirm-restored': 'Confirmed the service was restored',
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
      requiredSteps: ['explorer.repair-mapping', 'explorer.verify-share'],
      optionalSteps: ['chat.confirm-restored'],
      incorrectSteps: ['vpn.connect', 'settings.clear-profile-storage'],
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
