import type {
  RemoteDesktopAppId,
  RemoteDesktopDriveStatus,
  RemoteDesktopServiceState,
  RemoteDesktopVpnStatus,
} from './remote-desktop-fixtures';

export const WORKSTATION_STATE_SCHEMA_VERSION = 2 as const;

export type WorkstationComplianceState =
  | 'compliant'
  | 'noncompliant'
  | 'unknown';
export type WorkstationProfileState = 'normal' | 'temporary' | 'first-sign-in';
export type WorkstationInterfaceStatus = 'up' | 'down' | 'limited';
export type WorkstationAccess = 'read-write' | 'read-only' | 'denied';

export interface WorkstationMachineState {
  assetTag: string;
  hostname: string;
  operatingSystem: string;
  build: string;
  domain: string;
  domainJoinState: 'joined' | 'workgroup' | 'trust-broken';
  signedInUser: string;
  profileState: WorkstationProfileState;
  compliance: WorkstationComplianceState;
  model: string;
  location: string;
  lastLogon: string;
}

export interface WorkstationIpv4State {
  address: string;
  prefixLength: number;
  gateway: string;
  dhcpEnabled: boolean;
  dhcpServer: string | null;
  leaseObtainedAt: string | null;
  leaseExpiresAt: string | null;
}

export interface WorkstationNetworkInterface {
  id: string;
  alias: string;
  kind: 'ethernet' | 'wifi' | 'vpn';
  status: WorkstationInterfaceStatus;
  macAddress: string;
  ipv4: WorkstationIpv4State;
  dnsServers: readonly string[];
  dnsSource: 'dhcp' | 'manual' | 'vpn';
}

export interface WorkstationRoute {
  id: string;
  destination: string;
  prefixLength: number;
  nextHop: string;
  interfaceId: string;
  metric: number;
  source: 'system' | 'dhcp' | 'vpn';
}

export interface WorkstationDnsCacheEntry {
  hostname: string;
  address: string;
  expiresAt: string;
  source: 'fixture' | 'query';
}

export interface WorkstationKnownHost {
  hostname: string;
  addresses: readonly string[];
  scope: 'public' | 'intranet' | 'vpn';
}

export interface WorkstationVpnProfile {
  id: string;
  name: string;
  serverAddress: string;
  tunnelType: 'ikev2' | 'sstp';
  authenticationMethod: 'certificate' | 'username';
  requiredCompliance: WorkstationComplianceState;
  dnsServers: readonly string[];
  routes: readonly Omit<WorkstationRoute, 'source'>[];
}

export interface WorkstationVpnLogEntry {
  code: string;
  message: string;
  timestamp: string;
}

export interface WorkstationVpnState {
  profiles: Readonly<Record<string, WorkstationVpnProfile>>;
  selectedProfileId: string | null;
  connectedProfileId: string | null;
  status: RemoteDesktopVpnStatus;
  error: { code: string; message: string } | null;
  log: readonly WorkstationVpnLogEntry[];
}

export interface WorkstationNetworkState {
  internetReachable: boolean;
  intranetReachable: boolean;
  interfaces: readonly WorkstationNetworkInterface[];
  routes: readonly WorkstationRoute[];
  dnsCache: readonly WorkstationDnsCacheEntry[];
  knownHosts: Readonly<Record<string, WorkstationKnownHost>>;
  vpn: WorkstationVpnState;
}

export interface WorkstationFilesystemNode {
  id: string;
  parentId: string | null;
  name: string;
  path: string;
  kind: 'drive' | 'folder' | 'file' | 'share';
  access: WorkstationAccess;
  available: boolean;
  modifiedAt: string | null;
  sizeBytes: number | null;
}

export interface WorkstationFilesystemState {
  nodes: Readonly<Record<string, WorkstationFilesystemNode>>;
  currentPath: string;
  history: readonly string[];
  historyIndex: number;
  error: {
    code:
      | 'network-path-error'
      | 'permission-error'
      | 'path-not-found'
      | 'name-resolution-error';
    message: string;
    path: string;
  } | null;
  lastRefreshedAt: string | null;
}

export interface WorkstationMappedDrive {
  id: string;
  letter: string;
  label: string;
  uncPath: string;
  reconnectAtSignIn: boolean;
  credentialTarget: string | null;
  status: RemoteDesktopDriveStatus;
  lastError: string | null;
}

export interface WorkstationCredential {
  id: string;
  target: string;
  username: string;
  type: 'domain-password' | 'generic';
  persistence: 'session' | 'local-machine';
  createdAt: string;
}

export interface WorkstationService {
  name: string;
  displayName: string;
  state: RemoteDesktopServiceState;
  startupType: 'automatic' | 'manual' | 'disabled';
  dependencies: readonly string[];
}

export interface WorkstationWindowBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface WorkstationWindowState {
  appId: RemoteDesktopAppId;
  open: boolean;
  minimized: boolean;
  maximized: boolean;
  bounds: WorkstationWindowBounds;
  restoreBounds: WorkstationWindowBounds | null;
  zIndex: number;
}

export interface WorkstationDesktopState {
  windows: Readonly<
    Partial<Record<RemoteDesktopAppId, WorkstationWindowState>>
  >;
  activeAppId: RemoteDesktopAppId | null;
  startMenuOpen: boolean;
  nextZIndex: number;
}

export interface WorkstationTerminalEntry {
  command: string;
  output: readonly string[];
  timestamp: string;
}

export interface WorkstationTerminalState {
  history: readonly WorkstationTerminalEntry[];
  commandHistory: readonly string[];
  historyCursor: number;
}

export interface WorkstationState {
  schemaVersion: typeof WORKSTATION_STATE_SCHEMA_VERSION;
  machine: WorkstationMachineState;
  network: WorkstationNetworkState;
  filesystem: WorkstationFilesystemState;
  mappedDrives: Readonly<Record<string, WorkstationMappedDrive>>;
  credentials: Readonly<Record<string, WorkstationCredential>>;
  services: Readonly<Record<string, WorkstationService>>;
  desktop: WorkstationDesktopState;
  terminal: WorkstationTerminalState;
}
