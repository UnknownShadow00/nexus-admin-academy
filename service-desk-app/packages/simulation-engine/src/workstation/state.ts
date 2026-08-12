import {
  WORKSTATION_STATE_SCHEMA_VERSION,
  getRemoteDesktopTerminalFixture,
  getRemoteDesktopWorkstation,
  type RemoteDesktopAppId,
  type RemoteDesktopDriveStatus,
  type RemoteDesktopServiceState,
  type RemoteDesktopVpnStatus,
  type WorkstationFilesystemNode,
  type WorkstationMappedDrive,
  type WorkstationRoute,
  type WorkstationState,
  type WorkstationWindowState,
} from '@service-desk/shared';

const FIXTURE_NOW = '2026-07-30T10:00:00.000Z';
const DHCP_LEASE_END = '2026-07-31T10:00:00.000Z';

export interface LegacyWorkstationFacts {
  dnsServers?: readonly string[];
  driveStates?: Readonly<Record<string, RemoteDesktopDriveStatus>>;
  explorerCurrentPath?: string;
  explorerError?: {
    kind: 'network-path-error' | 'permission-error';
    message: string;
    path: string;
  } | null;
  explorerLastRefreshedAt?: string | null;
  focusedApp?: RemoteDesktopAppId | null;
  minimizedApps?: readonly RemoteDesktopAppId[];
  openApps?: readonly RemoteDesktopAppId[];
  serviceStates?: Readonly<Record<string, RemoteDesktopServiceState>>;
  terminalHistory?: readonly {
    command: string;
    output: readonly string[];
    timestamp: string;
  }[];
  vpnError?: string | null;
  vpnLog?: readonly { message: string; timestamp: string }[];
  vpnStatus?: RemoteDesktopVpnStatus;
}

function gatewayFor(address: string) {
  const octets = address.split('.');
  return octets.length === 4 ? `${octets.slice(0, 3).join('.')}.1` : '0.0.0.0';
}

function macAddressFor(assetTag: string) {
  const digits = assetTag.replace(/\D/g, '').padStart(6, '0').slice(-6);
  return `02:4e:58:${digits.slice(0, 2)}:${digits.slice(2, 4)}:${digits.slice(4, 6)}`;
}

function entryId(path: string) {
  return `node-${path
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')}`;
}

function parentPath(path: string) {
  const normalized = path.replace(/\\+$/, '');
  const separator = normalized.lastIndexOf('\\');
  if (separator <= 2) return `${normalized.slice(0, 2)}\\`;
  return normalized.slice(0, separator);
}

function parseFixtureSize(size: string | undefined) {
  if (!size) return null;
  const match = /^(\d+)\s*(KB|MB|GB)$/i.exec(size.trim());
  if (!match) return null;
  const value = Number(match[1]);
  const multiplier = { KB: 1024, MB: 1024 ** 2, GB: 1024 ** 3 }[
    match[2]!.toUpperCase() as 'KB' | 'MB' | 'GB'
  ];
  return value * multiplier;
}

function filesystemFor(
  assetTag: string,
): Pick<WorkstationState, 'filesystem' | 'mappedDrives'> {
  const fixture = getRemoteDesktopWorkstation(assetTag);
  if (!fixture) throw new Error(`Missing workstation fixture for ${assetTag}.`);

  const nodes: Record<string, WorkstationFilesystemNode> = {};
  const mappedDrives: Record<string, WorkstationMappedDrive> = {};

  for (const drive of fixture.drives) {
    const driveId = `drive-${drive.letter.replace(':', '')}`;
    const driveAvailable = drive.initialStatus === 'connected';
    const driveAccess =
      drive.initialStatus === 'permission-error' ? 'denied' : 'read-write';
    nodes[driveId] = {
      id: driveId,
      parentId: null,
      name: `${drive.label} (${drive.letter})`,
      path: drive.rootPath,
      kind: 'drive',
      access: driveAccess,
      available: driveAvailable,
      modifiedAt: null,
      sizeBytes: drive.totalGb * 1024 ** 3,
    };

    for (const entry of drive.entries) {
      const id = entryId(entry.path);
      const parent = parentPath(entry.path);
      nodes[id] = {
        id,
        parentId:
          parent.toLowerCase() === drive.rootPath.toLowerCase()
            ? driveId
            : entryId(parent),
        name: entry.name,
        path: entry.path,
        kind: entry.kind,
        access: driveAccess,
        available: driveAvailable,
        modifiedAt: entry.modifiedAt,
        sizeBytes: parseFixtureSize(entry.size),
      };
    }

    if (drive.kind === 'network' && drive.sharePath) {
      mappedDrives[drive.letter] = {
        id: `mapping-${drive.letter.replace(':', '').toLowerCase()}`,
        letter: drive.letter,
        label: drive.label,
        uncPath: drive.sharePath,
        reconnectAtSignIn: true,
        credentialTarget: null,
        status: drive.initialStatus,
        lastError:
          drive.initialStatus === 'connected'
            ? null
            : drive.initialStatus === 'permission-error'
              ? 'Access is denied.'
              : 'The network path was not found.',
      };
    }
  }

  return {
    filesystem: {
      nodes,
      currentPath: 'This PC',
      history: ['This PC'],
      historyIndex: 0,
      error: null,
      lastRefreshedAt: null,
    },
    mappedDrives,
  };
}

function vpnProfile(assetTag: string): WorkstationState['network']['vpn'] {
  if (assetTag !== 'NX-2047') {
    return {
      profiles: {},
      selectedProfileId: null,
      connectedProfileId: null,
      status: 'disconnected',
      error: null,
      log: [],
    };
  }

  return {
    profiles: {
      'nexus-secure': {
        id: 'nexus-secure',
        name: 'Nexus Secure Access',
        serverAddress: 'vpn.nexus.example',
        tunnelType: 'ikev2',
        authenticationMethod: 'certificate',
        requiredCompliance: 'compliant',
        dnsServers: ['10.20.0.10', '10.20.0.11'],
        routes: [
          {
            id: 'vpn-partner-route',
            destination: '10.90.0.0',
            prefixLength: 16,
            nextHop: '0.0.0.0',
            interfaceId: 'vpn-nexus-secure',
            metric: 5,
          },
        ],
      },
    },
    selectedProfileId: 'nexus-secure',
    connectedProfileId: null,
    status: 'disconnected',
    error: null,
    log: [],
  };
}

export function createWorkstationState(assetTag: string): WorkstationState {
  const fixture = getRemoteDesktopWorkstation(assetTag);
  if (!fixture) throw new Error(`Missing workstation fixture for ${assetTag}.`);
  const terminal = getRemoteDesktopTerminalFixture(assetTag);
  const gateway = gatewayFor(fixture.ipAddress);
  const interfaceId = assetTag === 'NX-2047' ? 'wifi-0' : 'ethernet-0';
  const filesystem = filesystemFor(assetTag);
  const baseRoutes: WorkstationRoute[] = [
    {
      id: 'default-route',
      destination: '0.0.0.0',
      prefixLength: 0,
      nextHop: gateway,
      interfaceId,
      metric: 25,
      source: 'dhcp',
    },
  ];

  return {
    schemaVersion: WORKSTATION_STATE_SCHEMA_VERSION,
    machine: {
      assetTag: fixture.assetTag,
      hostname: fixture.hostname,
      operatingSystem: fixture.operatingSystem,
      build: '23H2 (22631.3880)',
      domain: 'NEXUS',
      domainJoinState: assetTag === 'NX-2510' ? 'trust-broken' : 'joined',
      signedInUser: terminal.currentUser,
      profileState: assetTag === 'NX-2501' ? 'temporary' : 'normal',
      compliance: 'compliant',
      model: terminal.systemModel,
      location: fixture.location,
      lastLogon: fixture.lastLogon,
    },
    network: {
      internetReachable: fixture.networkStatus !== 'offline',
      intranetReachable: fixture.networkStatus === 'online',
      interfaces: [
        {
          id: interfaceId,
          alias: assetTag === 'NX-2047' ? 'Wi-Fi' : 'Ethernet',
          kind: assetTag === 'NX-2047' ? 'wifi' : 'ethernet',
          status:
            fixture.networkStatus === 'online'
              ? 'up'
              : fixture.networkStatus === 'limited'
                ? 'limited'
                : 'down',
          macAddress: macAddressFor(assetTag),
          ipv4: {
            address: fixture.ipAddress,
            prefixLength: 24,
            gateway,
            dhcpEnabled: true,
            dhcpServer: gateway,
            leaseObtainedAt: FIXTURE_NOW,
            leaseExpiresAt: DHCP_LEASE_END,
          },
          dnsServers: [...terminal.dnsServers],
          dnsSource: 'dhcp',
        },
      ],
      routes: baseRoutes,
      dnsCache: [],
      knownHosts: {
        'example.com': {
          hostname: 'example.com',
          addresses: ['93.184.216.34'],
          scope: 'public',
        },
        'partner.nexus.internal': {
          hostname: 'partner.nexus.internal',
          addresses: ['10.90.20.15'],
          scope: 'vpn',
        },
        'facilities.nexus.internal': {
          hostname: 'facilities.nexus.internal',
          addresses: ['10.30.12.20'],
          scope: 'intranet',
        },
        'schedule.nexus.internal': {
          hostname: 'schedule.nexus.internal',
          addresses: ['10.20.40.12'],
          scope: 'intranet',
        },
        'vpn.nexus.example': {
          hostname: 'vpn.nexus.example',
          addresses: ['198.51.100.24'],
          scope: 'public',
        },
      },
      vpn: vpnProfile(assetTag),
    },
    ...filesystem,
    credentials: {},
    services: Object.fromEntries(
      fixture.services.map((service) => [
        service.name,
        {
          name: service.name,
          displayName: service.name,
          state: service.state,
          startupType: 'automatic' as const,
          dependencies: [],
        },
      ]),
    ),
    desktop: {
      windows: {},
      activeAppId: null,
      startMenuOpen: false,
      nextZIndex: 10,
    },
    terminal: {
      history: [],
      commandHistory: [],
      historyCursor: 0,
    },
  };
}

/**
 * Minimal quarantined state used only to retain a rejected action event for an
 * unknown asset tag. It is never exposed as a connectable fixture.
 */
export function createUnavailableWorkstationState(
  assetTag: string,
): WorkstationState {
  return {
    schemaVersion: WORKSTATION_STATE_SCHEMA_VERSION,
    machine: {
      assetTag,
      hostname: 'Unavailable',
      operatingSystem: 'Unavailable',
      build: 'Unavailable',
      domain: 'NEXUS',
      domainJoinState: 'workgroup',
      signedInUser: 'Unavailable',
      profileState: 'normal',
      compliance: 'unknown',
      model: 'Unavailable',
      location: 'Unavailable',
      lastLogon: FIXTURE_NOW,
    },
    network: {
      internetReachable: false,
      intranetReachable: false,
      interfaces: [],
      routes: [],
      dnsCache: [],
      knownHosts: {},
      vpn: {
        profiles: {},
        selectedProfileId: null,
        connectedProfileId: null,
        status: 'disconnected',
        error: null,
        log: [],
      },
    },
    filesystem: {
      nodes: {},
      currentPath: 'This PC',
      history: ['This PC'],
      historyIndex: 0,
      error: null,
      lastRefreshedAt: null,
    },
    mappedDrives: {},
    credentials: {},
    services: {},
    desktop: {
      windows: {},
      activeAppId: null,
      startMenuOpen: false,
      nextZIndex: 10,
    },
    terminal: { history: [], commandHistory: [], historyCursor: 0 },
  };
}

function migratedWindow(
  appId: RemoteDesktopAppId,
  index: number,
  minimizedApps: readonly RemoteDesktopAppId[],
): WorkstationWindowState {
  return {
    appId,
    open: true,
    minimized: minimizedApps.includes(appId),
    maximized: false,
    bounds: {
      x: 40 + index * 28,
      y: 32 + index * 24,
      width: 760,
      height: 520,
    },
    restoreBounds: null,
    zIndex: index + 1,
  };
}

export function migrateLegacyWorkstationState(
  assetTag: string,
  legacy: LegacyWorkstationFacts,
): WorkstationState {
  const initial = createWorkstationState(assetTag);
  const interfaceState = initial.network.interfaces[0];
  const openApps = legacy.openApps ?? [];
  const minimizedApps = legacy.minimizedApps ?? [];
  const windows = Object.fromEntries(
    openApps.map((appId, index) => [
      appId,
      migratedWindow(appId, index, minimizedApps),
    ]),
  );
  const mappedDrives = Object.fromEntries(
    Object.entries(initial.mappedDrives).map(([letter, drive]) => {
      const status = legacy.driveStates?.[letter] ?? drive.status;
      return [
        letter,
        {
          ...drive,
          status,
          lastError:
            status === 'connected'
              ? null
              : status === 'permission-error'
                ? 'Access is denied.'
                : 'The network path was not found.',
        },
      ];
    }),
  );
  const filesystemNodes = Object.fromEntries(
    Object.entries(initial.filesystem.nodes).map(([id, node]) => {
      if (node.kind !== 'drive' || node.path.length < 2) return [id, node];
      const status = legacy.driveStates?.[node.path.slice(0, 2)];
      if (!status) return [id, node];
      return [
        id,
        {
          ...node,
          available: status === 'connected',
          access: status === 'permission-error' ? 'denied' : node.access,
        },
      ];
    }),
  );
  const services = Object.fromEntries(
    Object.entries(initial.services).map(([name, service]) => [
      name,
      {
        ...service,
        state: legacy.serviceStates?.[name] ?? service.state,
      },
    ]),
  );
  const vpnStatus = legacy.vpnStatus ?? initial.network.vpn.status;

  return {
    ...initial,
    network: {
      ...initial.network,
      interfaces: interfaceState
        ? [
            {
              ...interfaceState,
              dnsServers: legacy.dnsServers ?? interfaceState.dnsServers,
            },
            ...initial.network.interfaces.slice(1),
          ]
        : initial.network.interfaces,
      vpn: {
        ...initial.network.vpn,
        status: vpnStatus,
        connectedProfileId:
          vpnStatus === 'connected'
            ? initial.network.vpn.selectedProfileId
            : null,
        error: legacy.vpnError
          ? { code: 'legacy-error', message: legacy.vpnError }
          : null,
        log: (legacy.vpnLog ?? []).map((entry) => ({
          code: 'legacy-event',
          message: entry.message,
          timestamp: entry.timestamp,
        })),
      },
    },
    filesystem: {
      ...initial.filesystem,
      nodes: filesystemNodes,
      currentPath: legacy.explorerCurrentPath ?? initial.filesystem.currentPath,
      history: [legacy.explorerCurrentPath ?? initial.filesystem.currentPath],
      error: legacy.explorerError
        ? {
            code: legacy.explorerError.kind,
            message: legacy.explorerError.message,
            path: legacy.explorerError.path,
          }
        : null,
      lastRefreshedAt:
        legacy.explorerLastRefreshedAt ?? initial.filesystem.lastRefreshedAt,
    },
    mappedDrives,
    credentials: {},
    services,
    desktop: {
      windows,
      activeAppId: legacy.focusedApp ?? null,
      startMenuOpen: false,
      nextZIndex: openApps.length + 10,
    },
    terminal: {
      history: [...(legacy.terminalHistory ?? [])],
      commandHistory: (legacy.terminalHistory ?? []).map(
        (entry) => entry.command,
      ),
      historyCursor: (legacy.terminalHistory ?? []).length,
    },
  };
}

/**
 * Keeps the v2 workstation model coherent while the legacy overlay fields are
 * still present for backward compatibility. New workstation features should
 * mutate this model first; this bridge can be removed with the flat v1 fields
 * in a later schema version.
 */
export function reconcileWorkstationState(
  state: WorkstationState,
  legacy: LegacyWorkstationFacts,
): WorkstationState {
  const firstInterface = state.network.interfaces[0];
  const driveStates = legacy.driveStates ?? {};
  const mappedDrives = Object.fromEntries(
    Object.entries(state.mappedDrives).map(([letter, drive]) => {
      const status = driveStates[letter] ?? drive.status;
      return [
        letter,
        {
          ...drive,
          status,
          lastError:
            status === 'connected'
              ? null
              : status === 'permission-error'
                ? 'Access is denied.'
                : 'The network path was not found.',
        },
      ];
    }),
  );
  const filesystemNodes = Object.fromEntries(
    Object.entries(state.filesystem.nodes).map(([id, node]) => {
      if (node.kind !== 'drive') return [id, node];
      const status = driveStates[node.path.slice(0, 2)];
      return status
        ? [
            id,
            {
              ...node,
              available: status === 'connected',
              access: status === 'permission-error' ? 'denied' : node.access,
            },
          ]
        : [id, node];
    }),
  );
  const services = Object.fromEntries(
    Object.entries(state.services).map(([name, service]) => [
      name,
      {
        ...service,
        state: legacy.serviceStates?.[name] ?? service.state,
      },
    ]),
  );
  const openApps =
    legacy.openApps ??
    Object.values(state.desktop.windows)
      .filter((windowState) => windowState?.open)
      .map((windowState) => windowState!.appId);
  const minimizedApps = legacy.minimizedApps ?? [];
  const windows = Object.fromEntries(
    openApps.map((appId, index) => {
      const existing = state.desktop.windows[appId];
      return [
        appId,
        existing
          ? {
              ...existing,
              open: true,
              minimized: minimizedApps.includes(appId),
              zIndex:
                legacy.focusedApp === appId
                  ? state.desktop.nextZIndex
                  : existing.zIndex,
            }
          : migratedWindow(appId, index, minimizedApps),
      ];
    }),
  );
  const vpnStatus = legacy.vpnStatus ?? state.network.vpn.status;
  const selectedProfileId = state.network.vpn.selectedProfileId;
  const selectedProfile = selectedProfileId
    ? state.network.vpn.profiles[selectedProfileId]
    : undefined;
  const baseInterfaces =
    firstInterface && legacy.dnsServers
      ? [
          {
            ...firstInterface,
            dnsServers: [...legacy.dnsServers],
            dnsSource: 'manual' as const,
          },
          ...state.network.interfaces
            .slice(1)
            .filter((entry) => entry.kind !== 'vpn'),
        ]
      : state.network.interfaces.filter((entry) => entry.kind !== 'vpn');
  const interfaces =
    vpnStatus === 'connected' && selectedProfile
      ? [
          ...baseInterfaces,
          {
            id: `vpn-${selectedProfile.id}`,
            alias: selectedProfile.name,
            kind: 'vpn' as const,
            status: 'up' as const,
            macAddress: '00:00:00:00:00:00',
            ipv4: {
              address: '172.31.20.24',
              prefixLength: 32,
              gateway: '0.0.0.0',
              dhcpEnabled: false,
              dhcpServer: null,
              leaseObtainedAt: null,
              leaseExpiresAt: null,
            },
            dnsServers: [...selectedProfile.dnsServers],
            dnsSource: 'vpn' as const,
          },
        ]
      : baseInterfaces;
  const routes = [
    ...state.network.routes.filter((route) => route.source !== 'vpn'),
    ...(vpnStatus === 'connected' && selectedProfile
      ? selectedProfile.routes.map((route) => ({
          ...route,
          source: 'vpn' as const,
        }))
      : []),
  ];

  return {
    ...state,
    network: {
      ...state.network,
      intranetReachable:
        vpnStatus === 'connected'
          ? true
          : baseInterfaces.some((entry) => entry.status === 'up'),
      interfaces,
      routes,
      vpn: {
        ...state.network.vpn,
        status: vpnStatus,
        connectedProfileId:
          vpnStatus === 'connected'
            ? state.network.vpn.selectedProfileId
            : null,
        error: legacy.vpnError
          ? { code: 'connection-error', message: legacy.vpnError }
          : null,
        log: legacy.vpnLog
          ? legacy.vpnLog.map((entry) => ({
              code: 'connection-event',
              message: entry.message,
              timestamp: entry.timestamp,
            }))
          : state.network.vpn.log,
      },
    },
    filesystem: {
      ...state.filesystem,
      nodes: filesystemNodes,
      currentPath: legacy.explorerCurrentPath ?? state.filesystem.currentPath,
      history:
        legacy.explorerCurrentPath &&
        legacy.explorerCurrentPath !== state.filesystem.currentPath
          ? [
              ...state.filesystem.history.slice(
                0,
                state.filesystem.historyIndex + 1,
              ),
              legacy.explorerCurrentPath,
            ]
          : state.filesystem.history,
      historyIndex:
        legacy.explorerCurrentPath &&
        legacy.explorerCurrentPath !== state.filesystem.currentPath
          ? state.filesystem.historyIndex + 1
          : state.filesystem.historyIndex,
      error: legacy.explorerError
        ? {
            code: legacy.explorerError.kind,
            message: legacy.explorerError.message,
            path: legacy.explorerError.path,
          }
        : null,
      lastRefreshedAt:
        legacy.explorerLastRefreshedAt ?? state.filesystem.lastRefreshedAt,
    },
    mappedDrives,
    services,
    desktop: {
      ...state.desktop,
      windows,
      activeAppId: legacy.focusedApp ?? null,
      nextZIndex:
        legacy.focusedApp === state.desktop.activeAppId
          ? state.desktop.nextZIndex
          : state.desktop.nextZIndex + 1,
    },
    terminal: legacy.terminalHistory
      ? {
          history: [...legacy.terminalHistory],
          commandHistory: legacy.terminalHistory.map((entry) => entry.command),
          historyCursor: legacy.terminalHistory.length,
        }
      : state.terminal,
  };
}
