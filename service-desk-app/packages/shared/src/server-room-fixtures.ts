export const SERVER_ROOM_NODE_STATUSES = [
  'online',
  'offline',
  'degraded',
] as const;

export type ServerRoomNodeStatus = (typeof SERVER_ROOM_NODE_STATUSES)[number];

interface ServerRoomNodeBase {
  id: string;
  location: string;
  name: string;
  status: ServerRoomNodeStatus;
}

export interface ServerRoomDeviceFixture extends ServerRoomNodeBase {
  kind: 'device';
}

export interface ServerRoomServerFixture extends ServerRoomNodeBase {
  cpuPercent: number;
  kind: 'server';
  logs: readonly string[];
  memoryPercent: number;
  role: string;
  serviceName: string;
}

export type ServerRoomNodeFixture =
  | ServerRoomDeviceFixture
  | ServerRoomServerFixture;

export const SERVER_ROOM_DEVICE_FIXTURES: readonly ServerRoomDeviceFixture[] = [
  {
    id: 'metro-isp',
    kind: 'device',
    location: 'External',
    name: 'Metro ISP',
    status: 'online',
  },
  {
    id: 'core-router',
    kind: 'device',
    location: 'Server Room A',
    name: 'Core Router',
    status: 'online',
  },
  {
    id: 'floor-1-switch',
    kind: 'device',
    location: 'Server Room A',
    name: 'Floor 1 Switch',
    status: 'online',
  },
  {
    id: 'floor-2-switch',
    kind: 'device',
    location: 'Server Room A',
    name: 'Floor 2 Switch',
    status: 'online',
  },
  {
    id: 'floor-3-switch',
    kind: 'device',
    location: 'Server Room B',
    name: 'Floor 3 Switch',
    status: 'online',
  },
  {
    id: 'main-firewall',
    kind: 'device',
    location: 'Server Room A',
    name: 'Main Firewall',
    status: 'online',
  },
  {
    id: 'lobby-wifi-ap',
    kind: 'device',
    location: 'Lobby',
    name: 'Lobby WiFi AP',
    status: 'online',
  },
  {
    id: 'cafeteria-wifi-ap',
    kind: 'device',
    location: 'Cafeteria',
    name: 'Cafeteria WiFi AP',
    status: 'online',
  },
] as const;

export const SERVER_ROOM_SERVER_FIXTURES: readonly ServerRoomServerFixture[] = [
  {
    cpuPercent: 25,
    id: 'dc01',
    kind: 'server',
    location: 'Server Room A',
    logs: [
      '09:42:11 Directory replication completed with DC02.',
      '09:47:03 Kerberos ticket service health check passed.',
      '09:51:26 DNS zone nexus.example synchronized successfully.',
      '09:55:00 Domain Services heartbeat acknowledged.',
    ],
    memoryPercent: 60,
    name: 'DC01',
    role: 'Domain Controller',
    serviceName: 'Domain Services',
    status: 'online',
  },
  {
    cpuPercent: 20,
    id: 'dc02',
    kind: 'server',
    location: 'Server Room B',
    logs: [
      '09:41:54 Directory replication completed with DC01.',
      '09:46:19 Authentication service health check passed.',
      '09:50:08 SYSVOL consistency check completed.',
      '09:55:00 Domain Services heartbeat acknowledged.',
    ],
    memoryPercent: 55,
    name: 'DC02',
    role: 'Domain Controller',
    serviceName: 'Domain Services',
    status: 'online',
  },
  {
    cpuPercent: 45,
    id: 'fileserv01',
    kind: 'server',
    location: 'Server Room A',
    logs: [
      '09:38:22 Finance share snapshot completed.',
      '09:44:10 File integrity scan found no errors.',
      '09:49:37 Replication backlog is 0 files.',
      '09:55:00 File Replication heartbeat acknowledged.',
    ],
    memoryPercent: 70,
    name: 'FILESERV01',
    role: 'File Server',
    serviceName: 'File Replication',
    status: 'online',
  },
  {
    cpuPercent: 55,
    id: 'mailsrv01',
    kind: 'server',
    location: 'Server Room B',
    logs: [
      '09:40:05 Outbound queue processed 18 messages.',
      '09:45:33 TLS certificate validation passed.',
      '09:52:14 Mail queue depth returned to 0.',
      '09:55:00 SMTP Relay heartbeat acknowledged.',
    ],
    memoryPercent: 75,
    name: 'MAILSRV01',
    role: 'Mail Server',
    serviceName: 'SMTP Relay',
    status: 'online',
  },
  {
    cpuPercent: 40,
    id: 'print01',
    kind: 'server',
    location: 'Server Room B',
    logs: [
      '09:39:48 Driver catalog validation completed.',
      '09:43:21 Print queue Finance-4F processed job 8842.',
      '09:50:02 No stalled print jobs detected.',
      '09:55:00 Print Spooler heartbeat acknowledged.',
    ],
    memoryPercent: 65,
    name: 'PRINT01',
    role: 'Print Server',
    serviceName: 'Print Spooler',
    status: 'online',
  },
] as const;

export const SERVER_ROOM_NODE_FIXTURES: readonly ServerRoomNodeFixture[] = [
  ...SERVER_ROOM_DEVICE_FIXTURES,
  ...SERVER_ROOM_SERVER_FIXTURES,
];

export const SERVER_ROOM_CONNECTIONS = [
  ['metro-isp', 'main-firewall'],
  ['main-firewall', 'core-router'],
  ['core-router', 'floor-1-switch'],
  ['core-router', 'floor-2-switch'],
  ['core-router', 'floor-3-switch'],
  ['floor-1-switch', 'lobby-wifi-ap'],
  ['floor-1-switch', 'cafeteria-wifi-ap'],
  ['floor-2-switch', 'dc01'],
  ['floor-2-switch', 'fileserv01'],
  ['floor-3-switch', 'dc02'],
  ['floor-3-switch', 'mailsrv01'],
  ['floor-3-switch', 'print01'],
] as const satisfies readonly (readonly [string, string])[];

export const SERVER_ROOM_NETWORK_LOAD_PERCENT = 45;

export function getServerRoomNode(nodeId: string) {
  return SERVER_ROOM_NODE_FIXTURES.find((node) => node.id === nodeId);
}

export function getServerRoomDevice(nodeId: string) {
  return SERVER_ROOM_DEVICE_FIXTURES.find((node) => node.id === nodeId);
}

export function getServerRoomServer(nodeId: string) {
  return SERVER_ROOM_SERVER_FIXTURES.find((node) => node.id === nodeId);
}
