import {
  REMOTE_DESKTOP_APP_IDS,
  REMOTE_DESKTOP_DRIVE_STATUSES,
  REMOTE_DESKTOP_SERVICE_STATES,
  REMOTE_DESKTOP_VPN_STATUSES,
  WORKSTATION_STATE_SCHEMA_VERSION,
  type WorkstationState,
} from '@service-desk/shared';

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown): value is string {
  return typeof value === 'string';
}

function nullableText(value: unknown): value is string | null {
  return value === null || text(value);
}

function finite(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function textArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(text);
}

function valuesMatch(value: unknown, predicate: (entry: unknown) => boolean) {
  return record(value) && Object.values(value).every(predicate);
}

function isRoute(value: unknown) {
  return (
    record(value) &&
    text(value.id) &&
    text(value.destination) &&
    finite(value.prefixLength) &&
    text(value.nextHop) &&
    text(value.interfaceId) &&
    finite(value.metric) &&
    ['system', 'dhcp', 'vpn'].includes(String(value.source))
  );
}

function isWindowBounds(value: unknown) {
  return (
    record(value) &&
    finite(value.x) &&
    finite(value.y) &&
    finite(value.width) &&
    finite(value.height) &&
    value.width >= 0 &&
    value.height >= 0
  );
}

export function isWorkstationState(value: unknown): value is WorkstationState {
  if (
    !record(value) ||
    value.schemaVersion !== WORKSTATION_STATE_SCHEMA_VERSION
  ) {
    return false;
  }

  const machine = value.machine;
  const network = value.network;
  const filesystem = value.filesystem;
  const desktop = value.desktop;
  const terminal = value.terminal;

  return (
    record(machine) &&
    text(machine.assetTag) &&
    text(machine.hostname) &&
    text(machine.operatingSystem) &&
    text(machine.build) &&
    text(machine.domain) &&
    ['joined', 'workgroup', 'trust-broken'].includes(
      String(machine.domainJoinState),
    ) &&
    text(machine.signedInUser) &&
    ['normal', 'temporary', 'first-sign-in'].includes(
      String(machine.profileState),
    ) &&
    ['compliant', 'noncompliant', 'unknown'].includes(
      String(machine.compliance),
    ) &&
    text(machine.model) &&
    text(machine.location) &&
    text(machine.lastLogon) &&
    record(network) &&
    typeof network.internetReachable === 'boolean' &&
    typeof network.intranetReachable === 'boolean' &&
    Array.isArray(network.interfaces) &&
    network.interfaces.every(
      (entry) =>
        record(entry) &&
        text(entry.id) &&
        text(entry.alias) &&
        ['ethernet', 'wifi', 'vpn'].includes(String(entry.kind)) &&
        ['up', 'down', 'limited'].includes(String(entry.status)) &&
        text(entry.macAddress) &&
        record(entry.ipv4) &&
        text(entry.ipv4.address) &&
        finite(entry.ipv4.prefixLength) &&
        text(entry.ipv4.gateway) &&
        typeof entry.ipv4.dhcpEnabled === 'boolean' &&
        nullableText(entry.ipv4.dhcpServer) &&
        nullableText(entry.ipv4.leaseObtainedAt) &&
        nullableText(entry.ipv4.leaseExpiresAt) &&
        textArray(entry.dnsServers) &&
        ['dhcp', 'manual', 'vpn'].includes(String(entry.dnsSource)),
    ) &&
    Array.isArray(network.routes) &&
    network.routes.every(isRoute) &&
    Array.isArray(network.dnsCache) &&
    network.dnsCache.every(
      (entry) =>
        record(entry) &&
        text(entry.hostname) &&
        text(entry.address) &&
        text(entry.expiresAt) &&
        ['fixture', 'query'].includes(String(entry.source)),
    ) &&
    valuesMatch(
      network.knownHosts,
      (entry) =>
        record(entry) &&
        text(entry.hostname) &&
        textArray(entry.addresses) &&
        ['public', 'intranet', 'vpn'].includes(String(entry.scope)),
    ) &&
    record(network.vpn) &&
    valuesMatch(
      network.vpn.profiles,
      (profile) =>
        record(profile) &&
        text(profile.id) &&
        text(profile.name) &&
        text(profile.serverAddress) &&
        ['ikev2', 'sstp'].includes(String(profile.tunnelType)) &&
        ['certificate', 'username'].includes(
          String(profile.authenticationMethod),
        ) &&
        ['compliant', 'noncompliant', 'unknown'].includes(
          String(profile.requiredCompliance),
        ) &&
        textArray(profile.dnsServers) &&
        Array.isArray(profile.routes) &&
        profile.routes.every(
          (route) => record(route) && isRoute({ ...route, source: 'vpn' }),
        ),
    ) &&
    nullableText(network.vpn.selectedProfileId) &&
    nullableText(network.vpn.connectedProfileId) &&
    REMOTE_DESKTOP_VPN_STATUSES.includes(
      network.vpn.status as (typeof REMOTE_DESKTOP_VPN_STATUSES)[number],
    ) &&
    (network.vpn.error === null ||
      (record(network.vpn.error) &&
        text(network.vpn.error.code) &&
        text(network.vpn.error.message))) &&
    Array.isArray(network.vpn.log) &&
    network.vpn.log.every(
      (entry) =>
        record(entry) &&
        text(entry.code) &&
        text(entry.message) &&
        text(entry.timestamp),
    ) &&
    record(filesystem) &&
    valuesMatch(
      filesystem.nodes,
      (node) =>
        record(node) &&
        text(node.id) &&
        nullableText(node.parentId) &&
        text(node.name) &&
        text(node.path) &&
        ['drive', 'folder', 'file', 'share'].includes(String(node.kind)) &&
        ['read-write', 'read-only', 'denied'].includes(String(node.access)) &&
        typeof node.available === 'boolean' &&
        nullableText(node.modifiedAt) &&
        (node.sizeBytes === null || finite(node.sizeBytes)),
    ) &&
    text(filesystem.currentPath) &&
    textArray(filesystem.history) &&
    finite(filesystem.historyIndex) &&
    (filesystem.error === null ||
      (record(filesystem.error) &&
        [
          'network-path-error',
          'permission-error',
          'path-not-found',
          'name-resolution-error',
        ].includes(String(filesystem.error.code)) &&
        text(filesystem.error.message) &&
        text(filesystem.error.path))) &&
    nullableText(filesystem.lastRefreshedAt) &&
    valuesMatch(
      value.mappedDrives,
      (drive) =>
        record(drive) &&
        text(drive.id) &&
        text(drive.letter) &&
        text(drive.label) &&
        text(drive.uncPath) &&
        typeof drive.reconnectAtSignIn === 'boolean' &&
        nullableText(drive.credentialTarget) &&
        REMOTE_DESKTOP_DRIVE_STATUSES.includes(
          drive.status as (typeof REMOTE_DESKTOP_DRIVE_STATUSES)[number],
        ) &&
        nullableText(drive.lastError),
    ) &&
    valuesMatch(
      value.credentials,
      (credential) =>
        record(credential) &&
        text(credential.id) &&
        text(credential.target) &&
        text(credential.username) &&
        ['domain-password', 'generic'].includes(String(credential.type)) &&
        ['session', 'local-machine'].includes(String(credential.persistence)) &&
        text(credential.createdAt),
    ) &&
    valuesMatch(
      value.services,
      (service) =>
        record(service) &&
        text(service.name) &&
        text(service.displayName) &&
        REMOTE_DESKTOP_SERVICE_STATES.includes(
          service.state as (typeof REMOTE_DESKTOP_SERVICE_STATES)[number],
        ) &&
        ['automatic', 'manual', 'disabled'].includes(
          String(service.startupType),
        ) &&
        textArray(service.dependencies),
    ) &&
    record(desktop) &&
    valuesMatch(
      desktop.windows,
      (windowState) =>
        record(windowState) &&
        REMOTE_DESKTOP_APP_IDS.includes(
          windowState.appId as (typeof REMOTE_DESKTOP_APP_IDS)[number],
        ) &&
        typeof windowState.open === 'boolean' &&
        typeof windowState.minimized === 'boolean' &&
        typeof windowState.maximized === 'boolean' &&
        isWindowBounds(windowState.bounds) &&
        (windowState.restoreBounds === null ||
          isWindowBounds(windowState.restoreBounds)) &&
        finite(windowState.zIndex),
    ) &&
    (desktop.activeAppId === null ||
      REMOTE_DESKTOP_APP_IDS.includes(
        desktop.activeAppId as (typeof REMOTE_DESKTOP_APP_IDS)[number],
      )) &&
    typeof desktop.startMenuOpen === 'boolean' &&
    finite(desktop.nextZIndex) &&
    record(terminal) &&
    Array.isArray(terminal.history) &&
    terminal.history.every(
      (entry) =>
        record(entry) &&
        text(entry.command) &&
        textArray(entry.output) &&
        text(entry.timestamp),
    ) &&
    textArray(terminal.commandHistory) &&
    finite(terminal.historyCursor)
  );
}
