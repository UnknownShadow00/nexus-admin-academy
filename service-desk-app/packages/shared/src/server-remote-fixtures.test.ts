import { describe, expect, it } from 'vitest';

import { DIRECTORY_USER_FIXTURES } from './directory-fixtures';
import {
  REMOTE_DESKTOP_NETWORK_STATUSES,
  REMOTE_DESKTOP_POWER_STATES,
  REMOTE_DESKTOP_SERVICE_STATES,
  REMOTE_DESKTOP_WORKSTATION_FIXTURES,
  getRemoteDesktopWorkstation,
} from './remote-desktop-fixtures';
import {
  SERVER_ROOM_CONNECTIONS,
  SERVER_ROOM_DEVICE_FIXTURES,
  SERVER_ROOM_NODE_FIXTURES,
  SERVER_ROOM_NODE_STATUSES,
  SERVER_ROOM_SERVER_FIXTURES,
  getServerRoomNode,
} from './server-room-fixtures';

describe('Server Room fixtures', () => {
  it('defines the specified eight devices and five servers exactly once', () => {
    expect(SERVER_ROOM_DEVICE_FIXTURES).toHaveLength(8);
    expect(SERVER_ROOM_SERVER_FIXTURES).toHaveLength(5);
    expect(SERVER_ROOM_NODE_FIXTURES).toHaveLength(13);
    expect(new Set(SERVER_ROOM_NODE_FIXTURES.map((node) => node.id)).size).toBe(
      13,
    );
    expect(
      SERVER_ROOM_NODE_FIXTURES.every((node) =>
        SERVER_ROOM_NODE_STATUSES.includes(node.status),
      ),
    ).toBe(true);
  });

  it('keeps metrics, services, logs, and topology deterministic and valid', () => {
    const knownNodeIds = new Set(
      SERVER_ROOM_NODE_FIXTURES.map((node) => node.id),
    );

    expect(
      SERVER_ROOM_SERVER_FIXTURES.every(
        (server) =>
          server.cpuPercent >= 0 &&
          server.cpuPercent <= 100 &&
          server.memoryPercent >= 0 &&
          server.memoryPercent <= 100 &&
          server.serviceName.length > 0 &&
          server.logs.length >= 4,
      ),
    ).toBe(true);
    expect(
      SERVER_ROOM_CONNECTIONS.every(
        ([from, to]) => knownNodeIds.has(from) && knownNodeIds.has(to),
      ),
    ).toBe(true);
    expect(getServerRoomNode('dc01')?.name).toBe('DC01');
  });
});

describe('Remote Desktop fixtures', () => {
  it('reuses every directory identity and NX asset tag one-for-one, with ticket-only machines allowed', () => {
    const directoryWorkstations = REMOTE_DESKTOP_WORKSTATION_FIXTURES.filter(
      (workstation) =>
        DIRECTORY_USER_FIXTURES.some(
          (user) => user.id === workstation.directoryUserId,
        ),
    );

    expect(directoryWorkstations).toHaveLength(DIRECTORY_USER_FIXTURES.length);
    expect(
      new Set(
        directoryWorkstations.map((workstation) => workstation.directoryUserId),
      ),
    ).toEqual(new Set(DIRECTORY_USER_FIXTURES.map((user) => user.id)));
    expect(
      new Set(directoryWorkstations.map((workstation) => workstation.assetTag)),
    ).toEqual(new Set(DIRECTORY_USER_FIXTURES.map((user) => user.assetTag)));
  });

  it('provides deterministic system and service state for every workstation', () => {
    expect(
      REMOTE_DESKTOP_WORKSTATION_FIXTURES.every(
        (workstation) =>
          workstation.hostname.length > 0 &&
          workstation.ipAddress.length > 0 &&
          workstation.operatingSystem.length > 0 &&
          Number.isFinite(new Date(workstation.lastLogon).getTime()) &&
          REMOTE_DESKTOP_POWER_STATES.includes(workstation.powerState) &&
          REMOTE_DESKTOP_NETWORK_STATUSES.includes(workstation.networkStatus) &&
          workstation.services.length === 3 &&
          workstation.services.every((service) =>
            REMOTE_DESKTOP_SERVICE_STATES.includes(service.state),
          ),
      ),
    ).toBe(true);
    expect(getRemoteDesktopWorkstation('NX-2047')?.employeeName).toBe(
      'Harper Kim',
    );
    expect(getRemoteDesktopWorkstation('NX-4831')?.employeeName).toBe(
      'Avery Brooks',
    );
  });
});
