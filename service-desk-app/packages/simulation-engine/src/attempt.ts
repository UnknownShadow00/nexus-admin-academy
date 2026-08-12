import {
  INITIAL_PC_SHELF_ASSET_TAGS,
  REMOTE_DESKTOP_WORKSTATION_FIXTURES,
  SERVER_ROOM_NODE_FIXTURES,
  getPcShelfFixture,
  getRemoteDesktopInitialDriveStates,
  getRemoteDesktopTerminalFixture,
} from '@service-desk/shared';

import type {
  Attempt,
  PcShelfOverlay,
  RemoteDesktopOverlay,
  ServerRoomOverlay,
} from './types';
import { createWorkstationState } from './workstation/state';

export interface AttemptSeed {
  id?: string;
  startedAt?: string;
}

export interface ResetAttemptResult {
  oldAttempt: Attempt;
  newAttempt: Attempt;
}

export function createInitialPcShelfOverlays(): Record<string, PcShelfOverlay> {
  return Object.fromEntries(
    INITIAL_PC_SHELF_ASSET_TAGS.map((assetTag) => {
      const fixture = getPcShelfFixture(assetTag);

      if (!fixture) {
        throw new Error(`Missing PC Shelf fixture for ${assetTag}.`);
      }

      return [
        assetTag,
        {
          assignedDirectoryUserId: null,
          deviceState: fixture.deviceState,
          networkStatus: fixture.networkStatus,
          present: true,
          events: [],
        },
      ];
    }),
  );
}

export function createInitialServerRoomOverlays(): Record<
  string,
  ServerRoomOverlay
> {
  return Object.fromEntries(
    SERVER_ROOM_NODE_FIXTURES.map((fixture) => [
      fixture.id,
      {
        status: fixture.status,
        serviceStates:
          fixture.kind === 'server'
            ? { [fixture.serviceName]: 'running' as const }
            : {},
        events: [],
      },
    ]),
  );
}

export function createInitialRemoteDesktopOverlays(): Record<
  string,
  RemoteDesktopOverlay
> {
  return Object.fromEntries(
    REMOTE_DESKTOP_WORKSTATION_FIXTURES.map((fixture) => [
      fixture.assetTag,
      {
        workstation: createWorkstationState(fixture.assetTag),
        connectionState: 'disconnected',
        completedScenarioIds: [],
        dnsServers: [
          ...getRemoteDesktopTerminalFixture(fixture.assetTag).dnsServers,
        ],
        driveStates: getRemoteDesktopInitialDriveStates(fixture.assetTag),
        explorerCurrentPath: 'This PC',
        explorerError: null,
        explorerLastRefreshedAt: null,
        focusedApp: null,
        lastError: null,
        minimizedApps: [],
        openApps: [],
        powerState: fixture.powerState,
        networkStatus: fixture.networkStatus,
        learningMode: 'guided',
        scenarioProgress: {},
        scenarioSteps: {},
        serviceStates: Object.fromEntries(
          fixture.services.map((service) => [service.name, service.state]),
        ),
        terminalHistory: [],
        trainingMode: true,
        updateInstalledAt: null,
        updateState: fixture.pendingUpdate ? 'pending' : 'applied',
        vpnError: null,
        vpnLog: [],
        vpnStatus: 'disconnected',
        events: [],
      },
    ]),
  );
}

function createId(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 10)}`;
}

export function createAttempt(seed: AttemptSeed = {}): Attempt {
  return {
    id: seed.id ?? createId('attempt'),
    startedAt: seed.startedAt ?? new Date().toISOString(),
    supersededById: null,
    ticketOverlays: {},
    directoryOverlays: {},
    chatThreads: {},
    assetOverlays: {},
    pcShelfOverlays: createInitialPcShelfOverlays(),
    deploymentRuns: {},
    activeDeploymentRunId: null,
    shipments: {},
    lastShippingAddress: null,
    serverRoomOverlays: createInitialServerRoomOverlays(),
    remoteDesktopOverlays: createInitialRemoteDesktopOverlays(),
    grades: {},
  };
}

export function resetAttempt(attempt: Attempt): ResetAttemptResult {
  const newAttempt = createAttempt();

  return {
    oldAttempt: {
      ...attempt,
      supersededById: newAttempt.id,
      ticketOverlays: { ...attempt.ticketOverlays },
      directoryOverlays: { ...attempt.directoryOverlays },
      chatThreads: { ...attempt.chatThreads },
      assetOverlays: { ...attempt.assetOverlays },
      pcShelfOverlays: { ...attempt.pcShelfOverlays },
      deploymentRuns: { ...attempt.deploymentRuns },
      shipments: { ...attempt.shipments },
      serverRoomOverlays: { ...attempt.serverRoomOverlays },
      remoteDesktopOverlays: { ...attempt.remoteDesktopOverlays },
      grades: { ...attempt.grades },
    },
    newAttempt,
  };
}
