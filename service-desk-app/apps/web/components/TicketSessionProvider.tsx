'use client';

import {
  AssetStatus,
  type DeploymentBootSource,
  type DeploymentCable,
  type DeploymentPort,
  DIRECTORY_GROUP_NAMES,
  DIRECTORY_USER_FIXTURES,
  FIXTURE_REFERENCE_TIME,
  PC_SHELF_FIXTURES,
  PcShelfDeviceState,
  REMOTE_DESKTOP_WORKSTATION_FIXTURES,
  getRemoteDesktopScenarioByTicket,
  getRemoteDesktopScenarioByAsset,
  getRemoteDesktopTerminalFixture,
  SERVER_ROOM_NODE_FIXTURES,
  type RemoteDesktopNetworkStatus,
  type RemoteDesktopAppId,
  type RemoteDesktopConnectionState,
  type RemoteDesktopPowerState,
  type RemoteDesktopServiceState,
  type RemoteDesktopUpdateState,
  type RemoteDesktopVpnStatus,
  type RemoteDesktopDriveStatus,
  type RemoteDesktopLearningMode,
  type RemoteDesktopWorkstationFixture,
  type ServerRoomNodeFixture,
  type ServerRoomNodeStatus,
  type PcShelfComputerFixture,
  type PcShelfNetworkStatus,
  TICKET_FIXTURES,
  TicketStatus,
  type ActivityEvent,
  type DirectoryGroupName,
  type DirectoryUserTemplate,
  type Ticket,
} from '@service-desk/shared';
import {
  applyAction,
  createAttempt,
  deriveAnalyticsSummary,
  derivePastTickets,
  evaluateObjectives,
  evaluateAchievements,
  isChatThreadUnread,
  restoreAttempt,
  serializeAttempt,
  type ActionEvent,
  type AssetSimulationAction,
  type AnalyticsSummary,
  type Attempt,
  type ChatThreadOverlay,
  type DeploymentRun,
  type EvaluatedAchievement,
  type Grade,
  type PastTicket,
  type SimulationAction,
  type Shipment,
  type ShippingAddress,
  type RemoteDesktopScenarioProgress,
  type TicketSimulationAction,
  type DirectorySimulationAction,
  type RemoteDesktopSimulationAction,
  type ShippingSimulationAction,
} from '@service-desk/simulation-engine';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import { TICKET_STATUS_LABELS } from './ticket-labels';
import {
  completeAttempt,
  requestAttemptAction,
  persistAttemptSnapshot,
  getAttempt,
  listAssignments,
  recordAttemptEvent,
  recordAttemptHint,
  startOrResumeAttempt,
  type NexusAssignment,
  type NexusAttemptCompletionInput,
} from '../lib/nexus-service-desk-client';
import {
  outboxStatus,
  readNexusOutbox,
  writeNexusOutbox,
  type NexusOutbox,
  type NexusSyncStatus,
} from '../lib/nexus-sync-outbox';

interface TicketSessionContextValue {
  addNote: (ticketId: string, body: string) => void;
  assignTicket: (ticketId: string) => void;
  changeStatus: (ticketId: string, status: TicketStatus) => void;
  closeTicket: (
    ticketId: string,
    options: { resolutionNote: string; verifiedResolved: boolean },
  ) => void;
  escalateTicket: (ticketId: string) => void;
  getTicket: (ticketId: string) => Ticket | undefined;
  recordHintReveal: (ticketId: string, step: number) => void;
  tickets: readonly Ticket[];
  unassignTicket: (ticketId: string) => void;
}

interface AttemptScoreContextValue {
  pointsTotal: number;
  previewCloseGrade: (
    ticketId: string,
    verifiedResolved: boolean,
  ) => Grade | null;
}

interface ProgressContextValue {
  achievements: readonly EvaluatedAchievement[];
  analyticsSummary: AnalyticsSummary;
  isHydrated: boolean;
  pastTickets: readonly PastTicket[];
  syncStatus: NexusSyncStatus;
}

export interface SessionIdentity {
  email: string;
  isAdmin: boolean;
  isMentor: boolean;
  name: string;
  userId: string;
}

interface DirectorySessionContextValue {
  directoryUsers: readonly DirectoryUserTemplate[];
  disableAccount: (directoryUserId: string) => ActionEvent;
  enableAccount: (directoryUserId: string) => ActionEvent;
  isHydrated: boolean;
  resetMfa: (directoryUserId: string) => ActionEvent;
  resetPassword: (directoryUserId: string) => ActionEvent;
  unlockAccount: (directoryUserId: string) => ActionEvent;
  updateGroups: (
    directoryUserId: string,
    add: string[],
    remove: string[],
  ) => ActionEvent;
}

interface CompanyChatSessionContextValue {
  chatThreads: Readonly<Record<string, ChatThreadOverlay>>;
  isHydrated: boolean;
  markPinned: (contactId: string, pinned: boolean) => ActionEvent;
  openThread: (contactId: string) => ActionEvent;
  sendMessage: (contactId: string, body: string) => ActionEvent;
  unreadThreadCount: number;
}

export interface AssetInventoryRecord {
  assetTag: string;
  assignedDirectoryUserId: string | null;
  deviceType: string;
  location: string;
  serialNumber: string;
  source: 'directory' | 'pc-shelf';
  status: AssetStatus;
}

export interface PcShelfComputerRecord extends PcShelfComputerFixture {
  assignedDirectoryUserId: string | null;
  deviceState: PcShelfDeviceState;
  networkStatus: PcShelfNetworkStatus;
}

interface AssetManagementSessionContextValue {
  assets: readonly AssetInventoryRecord[];
  assignAsset: (assetTag: string, directoryUserId: string) => ActionEvent;
  changeAssetStatus: (assetTag: string, status: AssetStatus) => ActionEvent;
  directoryUsers: readonly DirectoryUserTemplate[];
  isHydrated: boolean;
  unassignAsset: (assetTag: string) => ActionEvent;
}

interface PcShelfSessionContextValue {
  addComputer: (assetTag: string) => ActionEvent;
  assignComputer: (assetTag: string, directoryUserId: string) => ActionEvent;
  catalog: readonly PcShelfComputerFixture[];
  changeDeviceState: (
    assetTag: string,
    deviceState: PcShelfDeviceState,
  ) => ActionEvent;
  changeNetworkStatus: (
    assetTag: string,
    networkStatus: PcShelfNetworkStatus,
  ) => ActionEvent;
  computers: readonly PcShelfComputerRecord[];
  directoryUsers: readonly DirectoryUserTemplate[];
  isHydrated: boolean;
  removeComputer: (assetTag: string) => ActionEvent;
  unassignComputer: (assetTag: string) => ActionEvent;
}

export type ServerRoomNodeRecord = ServerRoomNodeFixture & {
  serviceStates: Readonly<Record<string, RemoteDesktopServiceState>>;
  status: ServerRoomNodeStatus;
};

interface ServerRoomSessionContextValue {
  isHydrated: boolean;
  nodes: readonly ServerRoomNodeRecord[];
  restartDevice: (nodeId: string) => ActionEvent;
  restartServer: (nodeId: string) => ActionEvent;
  restartService: (nodeId: string, serviceName: string) => ActionEvent;
}

export interface RemoteDesktopWorkstationRecord
  extends RemoteDesktopWorkstationFixture {
  completedScenarioIds: readonly string[];
  connectionState: RemoteDesktopConnectionState;
  dnsServers: readonly string[];
  focusedApp: RemoteDesktopAppId | null;
  lastError: string | null;
  minimizedApps: readonly RemoteDesktopAppId[];
  openApps: readonly RemoteDesktopAppId[];
  networkStatus: RemoteDesktopNetworkStatus;
  powerState: RemoteDesktopPowerState;
  learningMode: RemoteDesktopLearningMode;
  scenarioProgress: Readonly<Record<string, RemoteDesktopScenarioProgress>>;
  scenarioSteps: Readonly<Record<string, readonly string[]>>;
  driveStates: Readonly<Record<string, RemoteDesktopDriveStatus>>;
  explorerCurrentPath: string;
  explorerError: {
    kind: 'network-path-error' | 'permission-error';
    message: string;
    path: string;
  } | null;
  explorerLastRefreshedAt: string | null;
  serviceStates: Readonly<Record<string, RemoteDesktopServiceState>>;
  terminalHistory: readonly {
    command: string;
    output: readonly string[];
    timestamp: string;
  }[];
  trainingMode: boolean;
  updateInstalledAt: string | null;
  updateState: RemoteDesktopUpdateState;
  vpnError: string | null;
  vpnLog: readonly { message: string; timestamp: string }[];
  vpnStatus: RemoteDesktopVpnStatus;
}

interface RemoteDesktopSessionContextValue {
  addInternalNote: (
    assetTag: string,
    ticketId: string,
    text: string,
  ) => ActionEvent;
  authenticate: (
    assetTag: string,
    ticketId: string,
    usernameEntered: boolean,
    passwordEntered: boolean,
  ) => ActionEvent;
  beginLogin: (assetTag: string, ticketId: string) => ActionEvent;
  cancelConnection: (assetTag: string) => ActionEvent;
  closeApp: (assetTag: string, appId: RemoteDesktopAppId) => ActionEvent;
  connect: (assetTag: string, ticketId: string) => ActionEvent;
  disconnect: (assetTag: string) => ActionEvent;
  focusApp: (assetTag: string, appId: RemoteDesktopAppId) => ActionEvent;
  isHydrated: boolean;
  minimizeApp: (assetTag: string, appId: RemoteDesktopAppId) => ActionEvent;
  networkReset: (assetTag: string) => ActionEvent;
  openApp: (assetTag: string, appId: RemoteDesktopAppId) => ActionEvent;
  performScenarioStep: (
    assetTag: string,
    ticketId: string,
    stepId: string,
  ) => ActionEvent;
  runTerminalCommand: (assetTag: string, command: string) => ActionEvent;
  navigateExplorer: (assetTag: string, path: string) => ActionEvent;
  reconnectExplorerDrive: (
    assetTag: string,
    driveLetter: string,
  ) => ActionEvent;
  refreshExplorer: (assetTag: string) => ActionEvent;
  connectVpn: (assetTag: string) => ActionEvent;
  completeVpnConnection: (assetTag: string) => ActionEvent;
  disconnectVpn: (assetTag: string) => ActionEvent;
  updateDns: (
    assetTag: string,
    primaryDns: string,
    secondaryDns: string,
  ) => ActionEvent;
  startService: (assetTag: string, serviceName: string) => ActionEvent;
  stopService: (assetTag: string, serviceName: string) => ActionEvent;
  installUpdate: (assetTag: string) => ActionEvent;
  completeUpdateInstall: (assetTag: string) => ActionEvent;
  restartAfterUpdate: (assetTag: string) => ActionEvent;
  restartComputer: (assetTag: string) => ActionEvent;
  restartService: (assetTag: string, serviceName: string) => ActionEvent;
  setTrainingMode: (assetTag: string, enabled: boolean) => ActionEvent;
  setLearningMode: (
    assetTag: string,
    mode: RemoteDesktopLearningMode,
  ) => ActionEvent;
  workstations: readonly RemoteDesktopWorkstationRecord[];
}

type CreateShipmentPayload = Extract<
  SimulationAction,
  { type: 'shipping.create' }
>['payload'];

interface ComputerDeploymentSessionContextValue {
  authenticateShare: (runId: string, password: string) => ActionEvent;
  connectCable: (
    runId: string,
    cable: DeploymentCable,
    port: DeploymentPort,
  ) => ActionEvent;
  domainLogin: (
    runId: string,
    domain: string,
    username: string,
    password: string,
  ) => ActionEvent;
  isHydrated: boolean;
  pressF12: (runId: string, timing: 'early' | 'window' | 'late') => ActionEvent;
  reboot: (runId: string) => ActionEvent;
  run: DeploymentRun | null;
  runTaskSequence: (runId: string) => ActionEvent;
  selectBootSource: (
    runId: string,
    source: DeploymentBootSource,
  ) => ActionEvent;
  selectDeviceType: (runId: string, deviceType: string) => ActionEvent;
  setHostname: (runId: string, hostname: string) => ActionEvent;
  startDeployment: () => ActionEvent;
}

interface ShippingManagerSessionContextValue {
  cancelShipment: (shipmentId: string) => ActionEvent;
  computers: readonly PcShelfComputerRecord[];
  createShipment: (payload: CreateShipmentPayload) => ActionEvent;
  directoryUsers: readonly DirectoryUserTemplate[];
  isHydrated: boolean;
  lastAddress: ShippingAddress | null;
  shipments: readonly Shipment[];
}

const ATTEMPT_STORAGE_KEY = 'nexus-sd-attempt-v1';
const OUTBOX_STORAGE_KEY = 'nexus-sd-outbox-v1';
const ACTOR_ID = 'student-you';
const NEXUS_INTEGRATION_ENABLED =
  process.env.NEXT_PUBLIC_NEXUS_INTEGRATION === '1';
const SESSION_URL = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/api/session`;
const STANDALONE_IDENTITY: SessionIdentity = {
  email: '',
  isAdmin: false,
  isMentor: false,
  name: 'Alex',
  userId: 'you',
};

const TicketSessionContext = createContext<TicketSessionContextValue | null>(
  null,
);
const AttemptScoreContext = createContext<AttemptScoreContextValue | null>(
  null,
);
const ProgressContext = createContext<ProgressContextValue | null>(null);
const DirectorySessionContext =
  createContext<DirectorySessionContextValue | null>(null);
const CompanyChatSessionContext =
  createContext<CompanyChatSessionContextValue | null>(null);
const AssetManagementSessionContext =
  createContext<AssetManagementSessionContextValue | null>(null);
const PcShelfSessionContext = createContext<PcShelfSessionContextValue | null>(
  null,
);
const ServerRoomSessionContext =
  createContext<ServerRoomSessionContextValue | null>(null);
const RemoteDesktopSessionContext =
  createContext<RemoteDesktopSessionContextValue | null>(null);
const ComputerDeploymentSessionContext =
  createContext<ComputerDeploymentSessionContextValue | null>(null);
const ShippingManagerSessionContext =
  createContext<ShippingManagerSessionContextValue | null>(null);
const SessionIdentityContext = createContext<SessionIdentity | null>(null);

function isSessionIdentity(value: unknown): value is SessionIdentity {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  return (
    'email' in value &&
    typeof value.email === 'string' &&
    'isAdmin' in value &&
    typeof value.isAdmin === 'boolean' &&
    'isMentor' in value &&
    typeof value.isMentor === 'boolean' &&
    'name' in value &&
    typeof value.name === 'string' &&
    'userId' in value &&
    typeof value.userId === 'string'
  );
}

interface NexusProgressEvent {
  detail?: string;
  event_type: 'ticket_resolved' | 'achievement_unlocked';
  ticket_id?: string;
  title: string;
  xp_delta?: number;
}

interface NexusTicketMapping {
  assignmentId: string | number;
  attemptId?: string | number;
}

interface NexusSnapshotTarget {
  assignmentId: string | number;
  attemptId: string | number;
}

const DIRECTORY_TICKET_BY_USER_ID: Readonly<Record<string, string>> = {
  'directory-user-avery-brooks': 'INC2401',
  'directory-user-sloane-rivera': 'INC2405',
};
const ASSET_TICKET_BY_TAG: Readonly<Record<string, string>> = {
  'NX-9052': 'INC2404',
};
const SHIPPING_TICKET_BY_RECIPIENT: Readonly<Record<string, string>> = {
  'directory-user-elliot-ward': 'INC2404',
};

const REMOTE_DESKTOP_TICKET_ACTION_TYPES = new Set([
  'remote_desktop.connect',
  'remote_desktop.begin_login',
  'remote_desktop.authenticate',
  'remote_desktop.add_internal_note',
  'remote_desktop.perform_scenario_step',
]);

const REMOTE_DESKTOP_EVIDENCE_ACTION_TYPES = new Set([
  'remote_desktop.run_terminal_command',
  'remote_desktop.restart_computer',
  'remote_desktop.network_reset',
  'remote_desktop.restart_service',
  'remote_desktop.start_service',
  'remote_desktop.stop_service',
  'remote_desktop.explorer_navigate',
  'remote_desktop.explorer_reconnect_drive',
  'remote_desktop.explorer_refresh',
  'remote_desktop.vpn_connect',
  'remote_desktop.vpn_complete_connection',
  'remote_desktop.vpn_disconnect',
  'remote_desktop.settings_update_dns',
  'remote_desktop.update_install',
  'remote_desktop.update_complete_install',
  'remote_desktop.update_restart',
  'remote_desktop.disconnect',
]);

type NexusEvidenceAction =
  | AssetSimulationAction
  | TicketSimulationAction
  | DirectorySimulationAction
  | RemoteDesktopSimulationAction
  | ShippingSimulationAction;

interface NexusActionSyncDetails {
  resultingState: Readonly<Record<string, unknown>>;
  ticketId: string;
  tool: 'asset' | 'directory' | 'remote_desktop' | 'shipping' | 'ticket';
}

function isTicketSimulationAction(
  action: SimulationAction,
): action is TicketSimulationAction {
  return action.type.startsWith('ticket.');
}

function hasLegacyNexusTicketState(
  value: Record<string, unknown>,
): value is Record<string, unknown> & { events: readonly ActionEvent[] } {
  return (
    typeof value.status === 'string' &&
    Array.isArray(value.events) &&
    typeof value.escalated === 'boolean' &&
    Array.isArray(value.notes) &&
    Number.isInteger(value.hintsRevealedCount)
  );
}

export function normalizeTicketKey(value: string): string {
  return value.toUpperCase();
}

function isDirectorySimulationAction(
  action: SimulationAction,
): action is DirectorySimulationAction {
  return action.type.startsWith('directory.');
}

function isRemoteDesktopSimulationAction(
  action: SimulationAction,
): action is RemoteDesktopSimulationAction {
  return action.type.startsWith('remote_desktop.');
}

function isAssetSimulationAction(action: SimulationAction): action is AssetSimulationAction {
  return action.type.startsWith('asset.');
}

function isShippingSimulationAction(action: SimulationAction): action is ShippingSimulationAction {
  return action.type.startsWith('shipping.');
}

function isRemoteDesktopTicketAction(
  action: RemoteDesktopSimulationAction,
): action is Extract<
  RemoteDesktopSimulationAction,
  { payload: { ticketId: string } }
> {
  return REMOTE_DESKTOP_TICKET_ACTION_TYPES.has(action.type);
}

/**
 * Remote Desktop state is intentionally scoped to the one workstation whose
 * action was performed. Directory state is similarly scoped to the one user;
 * Nexus receives evidence without the unrelated session-wide overlays.
 */
export function getNexusActionSyncDetails(
  action: NexusEvidenceAction,
  attempt: Attempt,
): NexusActionSyncDetails | null {
  if (isAssetSimulationAction(action)) {
    const ticketId = ASSET_TICKET_BY_TAG[action.payload.assetTag];
    if (!ticketId) return null;
    return {
      resultingState: { ...attempt.assetOverlays[action.payload.assetTag] },
      ticketId,
      tool: 'asset',
    };
  }

  if (isShippingSimulationAction(action)) {
    if (action.type !== 'shipping.create') return null;
    const ticketId = SHIPPING_TICKET_BY_RECIPIENT[action.payload.recipientDirectoryUserId];
    if (!ticketId) return null;
    return {
      resultingState: { shipments: attempt.shipments },
      ticketId,
      tool: 'shipping',
    };
  }
  if (isDirectorySimulationAction(action)) {
    const ticketId =
      DIRECTORY_TICKET_BY_USER_ID[action.payload.directoryUserId];
    if (!ticketId) {
      return null;
    }

    return {
      resultingState: {
        ...attempt.directoryOverlays[action.payload.directoryUserId],
      },
      ticketId,
      tool: 'directory',
    };
  }

  if (isRemoteDesktopSimulationAction(action)) {
    if (isRemoteDesktopTicketAction(action)) {
      return {
        resultingState: {
          ...attempt.remoteDesktopOverlays[action.payload.assetTag],
        },
        ticketId: action.payload.ticketId,
        tool: 'remote_desktop',
      };
    }

    if (!REMOTE_DESKTOP_EVIDENCE_ACTION_TYPES.has(action.type)) {
      return null;
    }

    const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
    if (!scenario) {
      return null;
    }

    return {
      resultingState: {
        ...attempt.remoteDesktopOverlays[action.payload.assetTag],
      },
      ticketId: scenario.ticketId,
      tool: 'remote_desktop',
    };
  }

  return {
    resultingState: { ...attempt.ticketOverlays[action.payload.ticketId] },
    ticketId: action.payload.ticketId,
    tool: 'ticket',
  };
}

function getUnattributedNexusActionWarningKey(
  action: SimulationAction,
): string | null {
  if (isDirectorySimulationAction(action)) {
    return `directory:${action.payload.directoryUserId}`;
  }

  if (
    isRemoteDesktopSimulationAction(action) &&
    !isRemoteDesktopTicketAction(action) &&
    REMOTE_DESKTOP_EVIDENCE_ACTION_TYPES.has(action.type)
  ) {
    return `remote_desktop:${action.payload.assetTag}`;
  }

  return null;
}

function mapAssignmentsByTicket(
  assignments: readonly NexusAssignment[],
): Record<string, NexusTicketMapping> {
  return Object.fromEntries(
    assignments.map((assignment) => [
      normalizeTicketKey(assignment.scenario.stable_key),
      {
        assignmentId: assignment.id,
        ...(assignment.most_recent_attempt?.status === 'in_progress'
          ? { attemptId: assignment.most_recent_attempt.id }
          : {}),
      },
    ]),
  );
}

function syncNexusProgress(event: NexusProgressEvent) {
  if (!NEXUS_INTEGRATION_ENABLED) {
    return;
  }

  void fetch('/api/service-desk/progress', {
    body: JSON.stringify(event),
    credentials: 'same-origin',
    headers: { 'content-type': 'application/json' },
    keepalive: true,
    method: 'POST',
  })
    .then((response) => {
      if (!response.ok) {
        console.warn(
          `Nexus progress sync returned ${String(response.status)}.`,
        );
      }
    })
    .catch(() => {
      console.warn('Nexus progress sync could not reach the server.');
    });
}

function actionEventToActivity(event: ActionEvent): ActivityEvent {
  if (!event.success) {
    return {
      detail: event.rejectReason ?? 'The simulation rejected this action.',
      id: event.id,
      label: 'Action rejected',
      timestamp: event.createdAt,
      tone: 'warning',
    };
  }

  switch (event.type) {
    case 'ticket.assign':
      return {
        detail: 'This incident is now in your active practice queue.',
        id: event.id,
        label: 'You assigned this ticket to yourself',
        timestamp: event.createdAt,
        tone: 'info',
      };
    case 'ticket.unassign':
      return {
        detail: 'The incident returned to the shared open queue.',
        id: event.id,
        label: 'You unassigned this ticket',
        timestamp: event.createdAt,
        tone: 'info',
      };
    case 'ticket.change_status': {
      const status = event.payload.status as TicketStatus;
      const label = TICKET_STATUS_LABELS[status] ?? String(status);
      return {
        detail: `Status is now ${label}.`,
        id: event.id,
        label: `You changed status to ${label}`,
        timestamp: event.createdAt,
        tone: 'info',
      };
    }
    case 'ticket.add_note':
      return {
        detail: 'A private note was added to the ticket record.',
        id: event.id,
        label: 'You added an internal note',
        timestamp: event.createdAt,
        tone: 'info',
      };
    case 'ticket.escalate':
      return {
        detail: 'A senior support review was requested for this incident.',
        id: event.id,
        label: 'You escalated this ticket',
        timestamp: event.createdAt,
        tone: 'warning',
      };
    case 'ticket.reveal_hint':
      return {
        detail: `Guidance step ${String(event.payload.step)} is now visible in this attempt.`,
        id: event.id,
        label: `You revealed hint step ${String(event.payload.step)}`,
        timestamp: event.createdAt,
        tone: 'info',
      };
    case 'ticket.close': {
      const verifiedResolved = event.payload.verifiedResolved === true;
      const resolutionNote = String(event.payload.resolutionNote ?? '').trim();
      return {
        detail: resolutionNote || 'No final resolution note was provided.',
        id: event.id,
        label: verifiedResolved
          ? 'You resolved this ticket'
          : 'You closed this ticket without a verified resolution',
        timestamp: event.createdAt,
        tone: verifiedResolved ? 'success' : 'warning',
      };
    }
    default:
      return {
        detail: 'The simulation recorded this ticket update.',
        id: event.id,
        label: 'Ticket updated',
        timestamp: event.createdAt,
        tone: 'info',
      };
  }
}

function projectTickets(attempt: Attempt, fixtures: readonly Ticket[]): Ticket[] {
  return fixtures.map((fixture) => {
    const overlay = attempt.ticketOverlays[fixture.id];

    if (!overlay) {
      return {
        ...fixture,
        activity: [...fixture.activity],
        hints: [...fixture.hints],
        hintsRevealedCount: 0,
        notes: [...fixture.notes],
        suggestedTools: [...fixture.suggestedTools],
      };
    }

    return {
      ...fixture,
      activity: [
        ...fixture.activity,
        ...overlay.events.map(actionEventToActivity),
      ],
      assignedTo: overlay.assignedTo,
      escalated: overlay.escalated,
      hints: [...fixture.hints],
      hintsRevealedCount: overlay.hintsRevealedCount,
      notes: [...overlay.notes],
      status: overlay.status,
      suggestedTools: [...fixture.suggestedTools],
    };
  });
}

export function ticketsForAssignments(assignments: readonly NexusAssignment[]): readonly Ticket[] {
  const definitions = new Map(
    assignments.flatMap((assignment) => {
      const definition = assignment.latest_published_version?.definition_json;
      const expectedId = normalizeTicketKey(assignment.scenario.stable_key);
      if (
        !definition ||
        typeof definition.title !== 'string' ||
        typeof definition.description !== 'object' ||
        definition.description === null ||
        typeof definition.requester !== 'object' ||
        definition.requester === null
      ) {
        return [];
      }
      const legacy = definition.id === expectedId;
      const projected = legacy
        ? definition
        : {
            activity: [],
            assignedTo: null,
            category: definition.category,
            createdAt: FIXTURE_REFERENCE_TIME,
            description: definition.description,
            device: definition.device,
            escalated: false,
            hints: Array.isArray(definition.hints)
              ? definition.hints.map((hint) =>
                  typeof hint === 'object' && hint !== null && 'text' in hint
                    ? String(hint.text)
                    : String(hint),
                )
              : [],
            id: expectedId,
            notes: [],
            priority: definition.priority,
            requester: definition.requester,
            sla: definition.sla,
            status: TicketStatus.Open,
            suggestedTools: [],
            title: definition.title,
          };
      return [[expectedId, projected] as const];
    }),
  );
  const fixtures = TICKET_FIXTURES.map((fixture) => {
    const definition = definitions.get(fixture.id);
    return definition ? ({ ...fixture, ...definition, id: fixture.id } as Ticket) : fixture;
  });
  const known = new Set(fixtures.map((fixture) => fixture.id));
  return [
    ...fixtures,
    ...[...definitions.entries()]
      .filter(([id]) => !known.has(id as Ticket['id']))
      .map(([, definition]) => definition as unknown as Ticket),
  ];
}

function projectDirectoryUsers(attempt: Attempt): DirectoryUserTemplate[] {
  return DIRECTORY_USER_FIXTURES.map((fixture) => {
    const overlay = attempt.directoryOverlays[fixture.id];

    if (!overlay) {
      return {
        ...fixture,
        devices: fixture.devices.map((device) => ({ ...device })),
        groups: [...fixture.groups],
        licenses: fixture.licenses.map((license) => ({ ...license })),
      };
    }

    const removed = new Set(overlay.groupChanges.removed);
    const added = new Set(overlay.groupChanges.added);
    const groups = DIRECTORY_GROUP_NAMES.filter(
      (group): group is DirectoryGroupName =>
        (fixture.groups.includes(group) && !removed.has(group)) ||
        added.has(group),
    );

    return {
      ...fixture,
      disabled: overlay.disabled,
      devices: fixture.devices.map((device) => ({ ...device })),
      groups,
      licenses: fixture.licenses.map((license) => ({ ...license })),
      locked: overlay.locked,
      mfaEnrolled: overlay.mfaEnrolled,
    };
  });
}

function projectPcShelfComputers(attempt: Attempt): PcShelfComputerRecord[] {
  return Object.entries(attempt.pcShelfOverlays).flatMap(
    ([assetTag, overlay]) => {
      const fixture =
        PC_SHELF_FIXTURES.find(
          (candidate) => candidate.assetTag === assetTag,
        ) ?? overlay.device;

      return overlay.present && fixture
        ? [
            {
              ...fixture,
              assignedDirectoryUserId: overlay.assignedDirectoryUserId,
              deviceState: overlay.deviceState,
              networkStatus: overlay.networkStatus,
            },
          ]
        : [];
    },
  );
}

function projectServerRoomNodes(attempt: Attempt): ServerRoomNodeRecord[] {
  return SERVER_ROOM_NODE_FIXTURES.map((fixture) => {
    const overlay = attempt.serverRoomOverlays[fixture.id];

    return {
      ...fixture,
      serviceStates: overlay?.serviceStates ?? {},
      status: overlay?.status ?? fixture.status,
    };
  });
}

function projectRemoteDesktopWorkstations(
  attempt: Attempt,
): RemoteDesktopWorkstationRecord[] {
  return REMOTE_DESKTOP_WORKSTATION_FIXTURES.map((fixture) => {
    const overlay = attempt.remoteDesktopOverlays[fixture.assetTag];

    return {
      ...fixture,
      completedScenarioIds: overlay?.completedScenarioIds ?? [],
      dnsServers:
        overlay?.dnsServers ??
        getRemoteDesktopTerminalFixture(fixture.assetTag).dnsServers,
      driveStates:
        overlay?.driveStates ??
        Object.fromEntries(
          fixture.drives.map((drive) => [drive.letter, drive.initialStatus]),
        ),
      explorerCurrentPath: overlay?.explorerCurrentPath ?? 'This PC',
      explorerError: overlay?.explorerError ?? null,
      explorerLastRefreshedAt: overlay?.explorerLastRefreshedAt ?? null,
      connectionState: overlay?.connectionState ?? 'disconnected',
      focusedApp: overlay?.focusedApp ?? null,
      lastError: overlay?.lastError ?? null,
      minimizedApps: overlay?.minimizedApps ?? [],
      openApps: overlay?.openApps ?? [],
      networkStatus: overlay?.networkStatus ?? fixture.networkStatus,
      powerState: overlay?.powerState ?? fixture.powerState,
      learningMode:
        overlay?.learningMode ??
        (overlay?.trainingMode === false ? 'practice' : 'guided'),
      scenarioProgress: overlay?.scenarioProgress ?? {},
      scenarioSteps: overlay?.scenarioSteps ?? {},
      serviceStates:
        overlay?.serviceStates ??
        Object.fromEntries(
          fixture.services.map((service) => [service.name, service.state]),
        ),
      terminalHistory: overlay?.terminalHistory ?? [],
      trainingMode: overlay?.trainingMode ?? true,
      updateInstalledAt: overlay?.updateInstalledAt ?? null,
      updateState:
        overlay?.updateState ?? (fixture.pendingUpdate ? 'pending' : 'applied'),
      vpnError: overlay?.vpnError ?? null,
      vpnLog: overlay?.vpnLog ?? [],
      vpnStatus: overlay?.vpnStatus ?? 'disconnected',
    };
  });
}

function shelfAssetStatus(computer: PcShelfComputerRecord) {
  if (computer.deviceState === PcShelfDeviceState.Retired) {
    return AssetStatus.Retired;
  }

  return computer.assignedDirectoryUserId
    ? AssetStatus.Deployed
    : AssetStatus.Repaired;
}

function projectAssets(
  attempt: Attempt,
  shelfComputers: readonly PcShelfComputerRecord[],
): AssetInventoryRecord[] {
  const directoryAssets = DIRECTORY_USER_FIXTURES.flatMap((user) =>
    user.devices.map((device) => {
      const overlay = attempt.assetOverlays[device.assetTag];

      return {
        assetTag: device.assetTag,
        assignedDirectoryUserId: overlay
          ? overlay.assignedDirectoryUserId
          : user.id,
        deviceType: device.deviceType,
        location: device.location,
        serialNumber: device.serialNumber,
        source: 'directory' as const,
        status: overlay?.status ?? device.status,
      };
    }),
  );
  const shelfAssets = shelfComputers.map((computer) => {
    const overlay = attempt.assetOverlays[computer.assetTag];

    return {
      assetTag: computer.assetTag,
      assignedDirectoryUserId: overlay
        ? overlay.assignedDirectoryUserId
        : computer.assignedDirectoryUserId,
      deviceType: 'desktop computer',
      location: computer.location,
      serialNumber: computer.serialNumber,
      source: 'pc-shelf' as const,
      status: overlay?.status ?? shelfAssetStatus(computer),
    };
  });

  return [...directoryAssets, ...shelfAssets];
}

function attachEffectiveDevices(
  users: readonly DirectoryUserTemplate[],
  assets: readonly AssetInventoryRecord[],
): DirectoryUserTemplate[] {
  return users.map((user) => {
    const devices = assets
      .filter((asset) => asset.assignedDirectoryUserId === user.id)
      .map((asset) => ({
        assetTag: asset.assetTag,
        deviceType: asset.deviceType,
        location: asset.location,
        serialNumber: asset.serialNumber,
        status: asset.status,
      }));

    return {
      ...user,
      assetTag: devices[0]?.assetTag ?? user.assetTag,
      devices,
    };
  });
}

export function TicketSessionProvider({
  children,
}: Readonly<{ children: ReactNode }>) {
  const hydrationId = useId();
  const [identity, setIdentity] = useState<SessionIdentity | null>(null);
  const [identityError, setIdentityError] = useState(false);
  const [attempt, setAttempt] = useState<Attempt>(() =>
    createAttempt({
      id: `hydration-${hydrationId}`,
      startedAt: FIXTURE_REFERENCE_TIME,
    }),
  );
  const attemptRef = useRef(attempt);
  const [hydrated, setHydrated] = useState(false);
  const [syncStatus, setSyncStatus] = useState<NexusSyncStatus>('saved');
  const [runtimeTickets, setRuntimeTickets] = useState<readonly Ticket[]>(TICKET_FIXTURES);
  const storageKey =
    identity?.userId && identity.userId !== 'you'
      ? `svc-desk-attempt:${identity.userId}`
      : ATTEMPT_STORAGE_KEY;
  const actorId =
    identity?.userId && identity.userId !== 'you' ? identity.userId : ACTOR_ID;
  const nexusTicketMappingsRef = useRef<Record<string, NexusTicketMapping>>({});
  const nexusAssignmentsUserRef = useRef<string | null>(null);
  const nexusAssignmentsPromiseRef = useRef<Promise<
    readonly NexusAssignment[]
  > | null>(null);
  const nexusOutboxRef = useRef<NexusOutbox>({ items: [] });
  const nexusOutboxFlushRef = useRef<Promise<void> | null>(null);
  const nexusSyncFailedRef = useRef(false);
  const nexusUnmappedWarningsRef = useRef<Set<string>>(new Set());
  // Global simulator domains have no honest ticket relationship. This is an
  // existing, student-owned attempt used only as an untrusted resume bucket.
  const nexusSnapshotTargetRef = useRef<NexusSnapshotTarget | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadIdentity() {
      try {
        const response = await fetch(SESSION_URL, {
          cache: 'no-store',
          credentials: 'same-origin',
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(
            `Session request failed with ${String(response.status)}`,
          );
        }

        const result: unknown = await response.json();
        if (!isSessionIdentity(result)) {
          throw new Error('Session response had an invalid shape.');
        }

        setIdentity(result);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (NEXUS_INTEGRATION_ENABLED) {
          console.warn('Unable to load the Nexus service desk session.', error);
          setIdentityError(true);
        } else {
          setIdentity(STANDALONE_IDENTITY);
        }
      }
    }

    void loadIdentity();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!identity) {
      return;
    }

    const resolvedIdentity = identity;
    let active = true;

    async function hydrateAttempt() {
      let restored: Attempt | null = null;

      try {
        let serialized = localStorage.getItem(storageKey);

        if (
          resolvedIdentity.userId !== 'you' &&
          (serialized === null || serialized === '')
        ) {
          const legacyAttempt = localStorage.getItem(ATTEMPT_STORAGE_KEY);
          if (legacyAttempt) {
            // Keep both keys so standalone mode retains its original local attempt.
            localStorage.setItem(storageKey, legacyAttempt);
            serialized = legacyAttempt;
          }
        }

        restored = serialized ? restoreAttempt(serialized) : null;
      } catch {
        // Storage can be corrupt or unavailable; create a fresh attempt below.
      }

      let nextAttempt = restored ?? createAttempt();

      try {
        nexusOutboxRef.current = readNexusOutbox(
          localStorage,
          `${OUTBOX_STORAGE_KEY}:${resolvedIdentity.userId}`,
        );
        setSyncStatus(outboxStatus(nexusOutboxRef.current, false));
      } catch {
        nexusOutboxRef.current = { items: [] };
      }

      // Queue only after the post-action snapshot is the canonical local state.
      attemptRef.current = nextAttempt;

      if (
        active &&
        NEXUS_INTEGRATION_ENABLED &&
        resolvedIdentity.userId !== 'you'
      ) {
        if (nexusAssignmentsUserRef.current !== resolvedIdentity.userId) {
          nexusAssignmentsUserRef.current = resolvedIdentity.userId;
          nexusAssignmentsPromiseRef.current = listAssignments();
        }
        const assignments = await (nexusAssignmentsPromiseRef.current ??
          Promise.resolve([]));
        if (!active) {
          return;
        }

        const mappings = mapAssignmentsByTicket(assignments);
        setRuntimeTickets(ticketsForAssignments(assignments));
        nexusTicketMappingsRef.current = mappings;
        nexusSnapshotTargetRef.current = null;
        let restoredNexusSnapshot = false;

        for (const assignment of assignments) {
          const recentAttempt = assignment.most_recent_attempt;
          if (!recentAttempt || recentAttempt.status !== 'in_progress') {
            continue;
          }

          const nexusAttempt = await getAttempt(recentAttempt.id);
          if (!active) {
            return;
          }

          const currentState = nexusAttempt?.current_state;
          if (!nexusSnapshotTargetRef.current && nexusAttempt) {
            nexusSnapshotTargetRef.current = {
              assignmentId: assignment.id,
              attemptId: nexusAttempt.id,
            };
          }
          if (!currentState) {
            continue;
          }

          // A validated full snapshot is authoritative for this hydration
          // pass. Do not merge older per-ticket state into it: those records
          // are intentionally partial and do not satisfy an Attempt overlay.
          if (restoredNexusSnapshot) {
            continue;
          }

          const snapshot = currentState.nexus_service_desk_attempt;
          if (
            nexusOutboxRef.current.items.length === 0 &&
            snapshot &&
            typeof snapshot === 'object'
          ) {
            const restoredSnapshot = restoreAttempt(JSON.stringify(snapshot));
            if (restoredSnapshot) {
              nextAttempt = restoredSnapshot;
              restoredNexusSnapshot = true;
              continue;
            }
          }

          const ticketId = normalizeTicketKey(assignment.scenario.stable_key);
          if (!hasLegacyNexusTicketState(currentState)) {
            continue;
          }
          const currentOverlay = nextAttempt.ticketOverlays[ticketId];
          nextAttempt = {
            ...nextAttempt,
            ticketOverlays: {
              ...nextAttempt.ticketOverlays,
              [ticketId]: {
                ...currentOverlay,
                ...currentState,
              } as NonNullable<typeof currentOverlay>,
            },
          };
        }
      } else if (active) {
        nexusTicketMappingsRef.current = {};
        nexusSnapshotTargetRef.current = null;
        setRuntimeTickets(TICKET_FIXTURES);
      }

      if (!active) {
        return;
      }

      attemptRef.current = nextAttempt;
      setAttempt(nextAttempt);
      setHydrated(true);
    }

    void hydrateAttempt();

    return () => {
      active = false;
    };
  }, [identity, storageKey]);

  const persistOutbox = useCallback(() => {
    if (!identity) return;
    try {
      writeNexusOutbox(
        localStorage,
        `${OUTBOX_STORAGE_KEY}:${identity.userId}`,
        nexusOutboxRef.current,
      );
    } catch {
      // The visible warning remains; no local-only completion is claimed.
    }
    setSyncStatus(outboxStatus(nexusOutboxRef.current, nexusSyncFailedRef.current));
  }, [identity]);

  const flushNexusOutbox = useCallback(() => {
    if (!NEXUS_INTEGRATION_ENABLED || nexusOutboxFlushRef.current) {
      return nexusOutboxFlushRef.current ?? Promise.resolve();
    }
    const flush = (async () => {
      while (nexusOutboxRef.current.items.length > 0) {
        const item = nexusOutboxRef.current.items[0];
        if (!item) break;
        let attemptId = item.attemptId;
        if (!attemptId) {
          const started = await startOrResumeAttempt(item.assignmentId);
          if (!started) throw new Error('Nexus could not start the saved attempt.');
          attemptId = started.id;
          for (const queued of nexusOutboxRef.current.items) {
            if (queued.assignmentId === item.assignmentId) queued.attemptId = attemptId;
          }
          persistOutbox();
        }
        const accepted = item.isSnapshot
          ? await persistAttemptSnapshot(attemptId, {
              idempotency_key: item.event.idempotency_key,
              snapshot: item.event.resulting_state,
            })
          : item.isHint
          ? await recordAttemptHint(attemptId, {
              idempotency_key: item.event.idempotency_key,
              payload: item.event.payload,
              resulting_state: item.event.resulting_state,
              tool: item.event.tool,
            })
          : item.event.event_type === 'ticket.close'
            ? await recordAttemptEvent(attemptId, item.event)
            : await requestAttemptAction(attemptId, {
                idempotency_key: item.event.idempotency_key,
                event_type: item.event.event_type,
                payload: item.event.payload,
                resulting_state: item.event.resulting_state,
                tool: item.event.tool,
              });
        if (!accepted) throw new Error('Nexus did not confirm the saved action.');
        if (item.completion && !await completeAttempt(attemptId, item.completion)) {
          throw new Error('Nexus could not complete the attempt yet.');
        }
        nexusOutboxRef.current.items.shift();
        nexusSyncFailedRef.current = false;
        persistOutbox();
      }
    })().catch((error) => {
      nexusSyncFailedRef.current = true;
      console.warn('Nexus sync is pending retry.', error);
      persistOutbox();
    }).finally(() => { nexusOutboxFlushRef.current = null; });
    nexusOutboxFlushRef.current = flush;
    return flush;
  }, [persistOutbox]);

  useEffect(() => {
    if (!hydrated || !NEXUS_INTEGRATION_ENABLED) return;
    const retry = () => { void flushNexusOutbox(); };
    retry();
    window.addEventListener('online', retry);
    const timer = window.setInterval(retry, 5000);
    return () => { window.removeEventListener('online', retry); window.clearInterval(timer); };
  }, [flushNexusOutbox, hydrated]);

  useEffect(() => {
    if (!hydrated || !identity) {
      return;
    }

    try {
      localStorage.setItem(storageKey, serializeAttempt(attempt));
    } catch {
      // Storage can be unavailable in privacy modes; in-memory play still works.
    }
  }, [attempt, hydrated, identity, storageKey]);

  const queueNexusActionSync = useCallback(
    (
      action: NexusEvidenceAction,
      event: ActionEvent,
      syncDetails: NexusActionSyncDetails,
      completion: NexusAttemptCompletionInput | null,
    ) => {
      if (!NEXUS_INTEGRATION_ENABLED) {
        return;
      }

      const ticketId = syncDetails.ticketId;
      const normalizedTicketId = normalizeTicketKey(ticketId);
      const mapping = nexusTicketMappingsRef.current[normalizedTicketId];
      if (!mapping) {
        const warningKey = `${syncDetails.tool}:${normalizedTicketId}`;
        if (!nexusUnmappedWarningsRef.current.has(warningKey)) {
          nexusUnmappedWarningsRef.current.add(warningKey);
          console.warn(
            `Nexus has no service desk assignment for ticket ${ticketId}; keeping it local-only.`,
          );
        }
        return;
      }

      const eventInput = {
          event_type: event.type,
          idempotency_key: event.id,
          payload: event.payload,
          resulting_state: {
            nexus_service_desk_attempt: JSON.parse(serializeAttempt(attemptRef.current)),
            schema_version: 1,
          },
          success: event.success,
          tool: syncDetails.tool,
      };
      nexusOutboxRef.current.items.push({
        assignmentId: mapping.assignmentId,
        attemptId: mapping.attemptId,
        completion: completion ?? undefined,
        event: eventInput,
        isHint: syncDetails.tool === 'ticket' && action.type === 'ticket.reveal_hint',
        ticketId: normalizedTicketId,
      });
      nexusSyncFailedRef.current = false;
      persistOutbox();
      void flushNexusOutbox();
    },
    [flushNexusOutbox, persistOutbox],
  );

  const queueNexusSnapshotSync = useCallback(
    (event: ActionEvent) => {
      if (!NEXUS_INTEGRATION_ENABLED || !event.success) return;
      const target = nexusSnapshotTargetRef.current;
      if (!target) {
        if (!nexusUnmappedWarningsRef.current.has('snapshot:no-active-attempt')) {
          nexusUnmappedWarningsRef.current.add('snapshot:no-active-attempt');
          console.warn('Nexus has no active attempt available for resume-only simulator state.');
        }
        return;
      }
      nexusOutboxRef.current.items.push({
        assignmentId: target.assignmentId,
        attemptId: target.attemptId,
        event: {
          event_type: 'snapshot.persisted',
          idempotency_key: event.id,
          payload: {},
          resulting_state: {
            nexus_service_desk_attempt: JSON.parse(serializeAttempt(attemptRef.current)),
            schema_version: 1,
          },
          success: true,
          tool: 'snapshot',
        },
        isHint: false,
        isSnapshot: true,
        ticketId: '__snapshot__',
      });
      nexusSyncFailedRef.current = false;
      persistOutbox();
      void flushNexusOutbox();
    },
    [flushNexusOutbox, persistOutbox],
  );

  const dispatchAction = useCallback(
    (action: SimulationAction) => {
      const previousAchievements = NEXUS_INTEGRATION_ENABLED
        ? evaluateAchievements(attemptRef.current, runtimeTickets)
        : [];
      const result = applyAction(attemptRef.current, actorId, action);
      let nextAttempt = result.attempt;
      let completion: NexusAttemptCompletionInput | null = null;

      if (action.type === 'ticket.close' && result.event.success) {
        const grade = evaluateObjectives(
          result.attempt,
          action.payload.ticketId,
          runtimeTickets,
        );

        const scenario = getRemoteDesktopScenarioByTicket(
          action.payload.ticketId,
        );
        const remoteOverlay = scenario
          ? result.attempt.remoteDesktopOverlays[scenario.assetTag]
          : undefined;
        const progress =
          scenario && remoteOverlay
            ? remoteOverlay.scenarioProgress[scenario.id]
            : undefined;
        const normalizedScore = grade.pointsPossible
          ? Math.round((grade.pointsAwarded / grade.pointsPossible) * 100)
          : 0;
        const feedbackSummary =
          grade.penaltyPoints > 0
            ? `All required workflow checks passed. The final score includes ${grade.penaltyPoints} hint or closure penalty points.`
            : 'All required diagnosis, repair, verification, note, and closure checks passed.';
        const remoteDesktopOverlays =
          scenario?.workflow && remoteOverlay && progress
            ? {
                ...result.attempt.remoteDesktopOverlays,
                [scenario.assetTag]: {
                  ...remoteOverlay,
                  scenarioProgress: {
                    ...remoteOverlay.scenarioProgress,
                    [scenario.id]: {
                      ...progress,
                      finalScore: normalizedScore,
                      feedback: feedbackSummary,
                    },
                  },
                },
              }
            : result.attempt.remoteDesktopOverlays;

        nextAttempt = {
          ...result.attempt,
          remoteDesktopOverlays,
          grades: {
            ...result.attempt.grades,
            [action.payload.ticketId]: grade,
          },
        };

        if (NEXUS_INTEGRATION_ENABLED) {
          if (grade.resolved) {
            const ticket = runtimeTickets.find(
              (candidate) => candidate.id === action.payload.ticketId,
            );
            if (!nexusTicketMappingsRef.current[action.payload.ticketId]) {
              syncNexusProgress({
                detail: action.payload.resolutionNote.trim() || undefined,
                event_type: 'ticket_resolved',
                ticket_id: action.payload.ticketId,
                title: ticket?.title ?? action.payload.ticketId,
                xp_delta: grade.pointsAwarded,
              });
            }
          }

          completion = {
            idempotency_key: result.event.id,
          };

          const previouslyEarned = new Set(
            previousAchievements
              .filter((achievement) => achievement.earned)
              .map((achievement) => achievement.code),
          );
          for (const achievement of evaluateAchievements(
            nextAttempt,
            runtimeTickets,
          )) {
            if (achievement.earned && !previouslyEarned.has(achievement.code)) {
              syncNexusProgress({
                detail: achievement.description,
                event_type: 'achievement_unlocked',
                title: achievement.name,
              });
            }
          }
        }
      }

      if (
        NEXUS_INTEGRATION_ENABLED &&
        result.event.success &&
        (isTicketSimulationAction(action) ||
          isAssetSimulationAction(action) ||
          isDirectorySimulationAction(action) ||
          isRemoteDesktopSimulationAction(action) ||
          isShippingSimulationAction(action))
      ) {
        // Every queued Nexus event carries the full post-action snapshot used
        // by a clean browser context.  Publish it before queueing so the
        // snapshot includes this action rather than the preceding one.
        attemptRef.current = nextAttempt;
        const syncDetails = getNexusActionSyncDetails(action, nextAttempt);
        if (syncDetails) {
          queueNexusActionSync(
            action,
            result.event,
            syncDetails,
            action.type === 'ticket.close' && result.event.success
              ? completion
              : null,
          );
        } else {
          const warningKey = getUnattributedNexusActionWarningKey(action);
          if (warningKey && !nexusUnmappedWarningsRef.current.has(warningKey)) {
            nexusUnmappedWarningsRef.current.add(warningKey);
            console.warn(
              `Nexus cannot attribute ${action.type} to a service desk ticket; keeping it local-only.`,
            );
          }
        }
      }

      if (
        NEXUS_INTEGRATION_ENABLED &&
        result.event.success &&
        !(isTicketSimulationAction(action) ||
          isDirectorySimulationAction(action) ||
          isRemoteDesktopSimulationAction(action))
      ) {
        // No ticket is fabricated for these domains. The snapshot endpoint
        // only updates the selected attempt's untrusted resume state.
        attemptRef.current = nextAttempt;
        queueNexusSnapshotSync(result.event);
      }

      attemptRef.current = nextAttempt;
      setAttempt(nextAttempt);
      return result.event;
    },
    [actorId, queueNexusActionSync, queueNexusSnapshotSync, runtimeTickets],
  );

  const tickets = useMemo(() => projectTickets(attempt, runtimeTickets), [attempt, runtimeTickets]);
  const baseDirectoryUsers = useMemo(
    () => projectDirectoryUsers(attempt),
    [attempt],
  );
  const pcShelfComputers = useMemo(
    () => projectPcShelfComputers(attempt),
    [attempt],
  );
  const assets = useMemo(
    () => projectAssets(attempt, pcShelfComputers),
    [attempt, pcShelfComputers],
  );
  const directoryUsers = useMemo(
    () => attachEffectiveDevices(baseDirectoryUsers, assets),
    [assets, baseDirectoryUsers],
  );
  const serverRoomNodes = useMemo(
    () => projectServerRoomNodes(attempt),
    [attempt],
  );
  const remoteDesktopWorkstations = useMemo(
    () => projectRemoteDesktopWorkstations(attempt),
    [attempt],
  );
  const activeDeploymentRun = attempt.activeDeploymentRunId
    ? (attempt.deploymentRuns[attempt.activeDeploymentRunId] ?? null)
    : null;
  const shipments = useMemo(
    () =>
      Object.values(attempt.shipments).sort((left, right) =>
        right.createdAt.localeCompare(left.createdAt),
      ),
    [attempt.shipments],
  );
  const markChatPinned = useCallback(
    (contactId: string, pinned: boolean) =>
      dispatchAction({
        type: 'chat.mark_pinned',
        payload: { contactId, pinned },
      }),
    [dispatchAction],
  );
  const openChatThread = useCallback(
    (contactId: string) =>
      dispatchAction({
        type: 'chat.open_thread',
        payload: { contactId },
      }),
    [dispatchAction],
  );
  const sendChatMessage = useCallback(
    (contactId: string, body: string) =>
      dispatchAction({
        type: 'chat.send_message',
        payload: { contactId, body },
      }),
    [dispatchAction],
  );

  const previewCloseGrade = useCallback(
    (ticketId: string, verifiedResolved: boolean) => {
      const result = applyAction(attempt, actorId, {
        type: 'ticket.close',
        payload: {
          ticketId,
          resolutionNote: '',
          verifiedResolved,
        },
      });

      return result.event.success
        ? evaluateObjectives(result.attempt, ticketId, runtimeTickets)
        : (attempt.grades[ticketId] ?? null);
    },
    [actorId, attempt, runtimeTickets],
  );

  const ticketSessionValue = useMemo<TicketSessionContextValue>(
    () => ({
      addNote: (ticketId, body) => {
        dispatchAction({
          type: 'ticket.add_note',
          payload: { ticketId, body },
        });
      },
      assignTicket: (ticketId) => {
        dispatchAction({
          type: 'ticket.assign',
          payload: { ticketId },
        });
      },
      changeStatus: (ticketId, status) => {
        dispatchAction({
          type: 'ticket.change_status',
          payload: { ticketId, status },
        });
      },
      closeTicket: (ticketId, options) => {
        dispatchAction({
          type: 'ticket.close',
          payload: { ticketId, ...options },
        });
      },
      escalateTicket: (ticketId) => {
        dispatchAction({
          type: 'ticket.escalate',
          payload: { ticketId },
        });
      },
      getTicket: (ticketId) => tickets.find((ticket) => ticket.id === ticketId),
      recordHintReveal: (ticketId, step) => {
        dispatchAction({
          type: 'ticket.reveal_hint',
          payload: { ticketId, step },
        });
      },
      tickets,
      unassignTicket: (ticketId) => {
        dispatchAction({
          type: 'ticket.unassign',
          payload: { ticketId },
        });
      },
    }),
    [dispatchAction, tickets],
  );

  const scoreValue = useMemo<AttemptScoreContextValue>(
    () => ({
      pointsTotal: Object.values(attempt.grades).reduce(
        (total, grade) => total + grade.pointsAwarded,
        0,
      ),
      previewCloseGrade,
    }),
    [attempt.grades, previewCloseGrade],
  );
  const progressValue = useMemo<ProgressContextValue>(
    () => ({
      achievements: evaluateAchievements(attempt, runtimeTickets),
      analyticsSummary: deriveAnalyticsSummary(attempt, runtimeTickets),
      isHydrated: hydrated,
      pastTickets: derivePastTickets(attempt, runtimeTickets),
      syncStatus,
    }),
    [attempt, hydrated, runtimeTickets, syncStatus],
  );
  const directorySessionValue = useMemo<DirectorySessionContextValue>(
    () => ({
      directoryUsers,
      disableAccount: (directoryUserId) =>
        dispatchAction({
          type: 'directory.disable_account',
          payload: { directoryUserId },
        }),
      enableAccount: (directoryUserId) =>
        dispatchAction({
          type: 'directory.enable_account',
          payload: { directoryUserId },
        }),
      isHydrated: hydrated,
      resetMfa: (directoryUserId) =>
        dispatchAction({
          type: 'directory.reset_mfa',
          payload: { directoryUserId },
        }),
      resetPassword: (directoryUserId) =>
        dispatchAction({
          type: 'directory.reset_password',
          payload: { directoryUserId },
        }),
      unlockAccount: (directoryUserId) =>
        dispatchAction({
          type: 'directory.unlock_account',
          payload: { directoryUserId },
        }),
      updateGroups: (directoryUserId, add, remove) =>
        dispatchAction({
          type: 'directory.update_groups',
          payload: { directoryUserId, add, remove },
        }),
    }),
    [directoryUsers, dispatchAction, hydrated],
  );
  const companyChatSessionValue = useMemo<CompanyChatSessionContextValue>(
    () => ({
      chatThreads: attempt.chatThreads,
      isHydrated: hydrated,
      markPinned: markChatPinned,
      openThread: openChatThread,
      sendMessage: sendChatMessage,
      unreadThreadCount: Object.values(attempt.chatThreads).filter(
        isChatThreadUnread,
      ).length,
    }),
    [
      attempt.chatThreads,
      hydrated,
      markChatPinned,
      openChatThread,
      sendChatMessage,
    ],
  );
  const assetManagementSessionValue =
    useMemo<AssetManagementSessionContextValue>(
      () => ({
        assets,
        assignAsset: (assetTag, directoryUserId) =>
          dispatchAction({
            type: 'asset.assign',
            payload: { assetTag, directoryUserId },
          }),
        changeAssetStatus: (assetTag, status) =>
          dispatchAction({
            type: 'asset.change_status',
            payload: { assetTag, status },
          }),
        directoryUsers,
        isHydrated: hydrated,
        unassignAsset: (assetTag) =>
          dispatchAction({
            type: 'asset.unassign',
            payload: { assetTag },
          }),
      }),
      [assets, directoryUsers, dispatchAction, hydrated],
    );
  const pcShelfSessionValue = useMemo<PcShelfSessionContextValue>(
    () => ({
      addComputer: (assetTag) =>
        dispatchAction({
          type: 'pc_shelf.add',
          payload: { assetTag },
        }),
      assignComputer: (assetTag, directoryUserId) =>
        dispatchAction({
          type: 'pc_shelf.assign',
          payload: { assetTag, directoryUserId },
        }),
      catalog: PC_SHELF_FIXTURES,
      changeDeviceState: (assetTag, deviceState) =>
        dispatchAction({
          type: 'pc_shelf.change_device_state',
          payload: { assetTag, deviceState },
        }),
      changeNetworkStatus: (assetTag, networkStatus) =>
        dispatchAction({
          type: 'pc_shelf.change_network_status',
          payload: { assetTag, networkStatus },
        }),
      computers: pcShelfComputers,
      directoryUsers,
      isHydrated: hydrated,
      removeComputer: (assetTag) =>
        dispatchAction({
          type: 'pc_shelf.remove',
          payload: { assetTag },
        }),
      unassignComputer: (assetTag) =>
        dispatchAction({
          type: 'pc_shelf.unassign',
          payload: { assetTag },
        }),
    }),
    [directoryUsers, dispatchAction, hydrated, pcShelfComputers],
  );
  const serverRoomSessionValue = useMemo<ServerRoomSessionContextValue>(
    () => ({
      isHydrated: hydrated,
      nodes: serverRoomNodes,
      restartDevice: (nodeId) =>
        dispatchAction({
          type: 'server_room.restart_device',
          payload: { nodeId },
        }),
      restartServer: (nodeId) =>
        dispatchAction({
          type: 'server_room.restart_server',
          payload: { nodeId },
        }),
      restartService: (nodeId, serviceName) =>
        dispatchAction({
          type: 'server_room.restart_service',
          payload: { nodeId, serviceName },
        }),
    }),
    [dispatchAction, hydrated, serverRoomNodes],
  );
  const remoteDesktopSessionValue = useMemo<RemoteDesktopSessionContextValue>(
    () => ({
      addInternalNote: (assetTag, ticketId, text) =>
        dispatchAction({
          type: 'remote_desktop.add_internal_note',
          payload: { assetTag, ticketId, text },
        }),
      authenticate: (assetTag, ticketId, usernameEntered, passwordEntered) =>
        dispatchAction({
          type: 'remote_desktop.authenticate',
          payload: { assetTag, ticketId, usernameEntered, passwordEntered },
        }),
      beginLogin: (assetTag, ticketId) =>
        dispatchAction({
          type: 'remote_desktop.begin_login',
          payload: { assetTag, ticketId },
        }),
      cancelConnection: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.cancel_connection',
          payload: { assetTag },
        }),
      closeApp: (assetTag, appId) =>
        dispatchAction({
          type: 'remote_desktop.close_app',
          payload: { assetTag, appId },
        }),
      connect: (assetTag, ticketId) =>
        dispatchAction({
          type: 'remote_desktop.connect',
          payload: { assetTag, ticketId },
        }),
      disconnect: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.disconnect',
          payload: { assetTag },
        }),
      focusApp: (assetTag, appId) =>
        dispatchAction({
          type: 'remote_desktop.focus_app',
          payload: { assetTag, appId },
        }),
      isHydrated: hydrated,
      minimizeApp: (assetTag, appId) =>
        dispatchAction({
          type: 'remote_desktop.minimize_app',
          payload: { assetTag, appId },
        }),
      networkReset: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.network_reset',
          payload: { assetTag },
        }),
      navigateExplorer: (assetTag, path) =>
        dispatchAction({
          type: 'remote_desktop.explorer_navigate',
          payload: { assetTag, path },
        }),
      openApp: (assetTag, appId) =>
        dispatchAction({
          type: 'remote_desktop.open_app',
          payload: { assetTag, appId },
        }),
      performScenarioStep: (assetTag, ticketId, stepId) =>
        dispatchAction({
          type: 'remote_desktop.perform_scenario_step',
          payload: { assetTag, ticketId, stepId },
        }),
      runTerminalCommand: (assetTag, command) =>
        dispatchAction({
          type: 'remote_desktop.run_terminal_command',
          payload: { assetTag, command },
        }),
      reconnectExplorerDrive: (assetTag, driveLetter) =>
        dispatchAction({
          type: 'remote_desktop.explorer_reconnect_drive',
          payload: { assetTag, driveLetter },
        }),
      refreshExplorer: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.explorer_refresh',
          payload: { assetTag },
        }),
      connectVpn: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.vpn_connect',
          payload: { assetTag },
        }),
      completeVpnConnection: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.vpn_complete_connection',
          payload: { assetTag },
        }),
      disconnectVpn: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.vpn_disconnect',
          payload: { assetTag },
        }),
      updateDns: (assetTag, primaryDns, secondaryDns) =>
        dispatchAction({
          type: 'remote_desktop.settings_update_dns',
          payload: { assetTag, primaryDns, secondaryDns },
        }),
      startService: (assetTag, serviceName) =>
        dispatchAction({
          type: 'remote_desktop.start_service',
          payload: { assetTag, serviceName },
        }),
      stopService: (assetTag, serviceName) =>
        dispatchAction({
          type: 'remote_desktop.stop_service',
          payload: { assetTag, serviceName },
        }),
      installUpdate: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.update_install',
          payload: { assetTag },
        }),
      completeUpdateInstall: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.update_complete_install',
          payload: { assetTag },
        }),
      restartAfterUpdate: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.update_restart',
          payload: { assetTag },
        }),
      restartComputer: (assetTag) =>
        dispatchAction({
          type: 'remote_desktop.restart_computer',
          payload: { assetTag },
        }),
      restartService: (assetTag, serviceName) =>
        dispatchAction({
          type: 'remote_desktop.restart_service',
          payload: { assetTag, serviceName },
        }),
      setTrainingMode: (assetTag, enabled) =>
        dispatchAction({
          type: 'remote_desktop.toggle_training_mode',
          payload: { assetTag, enabled },
        }),
      setLearningMode: (assetTag, mode) =>
        dispatchAction({
          type: 'remote_desktop.set_learning_mode',
          payload: { assetTag, mode },
        }),
      workstations: remoteDesktopWorkstations,
    }),
    [dispatchAction, hydrated, remoteDesktopWorkstations],
  );
  const computerDeploymentSessionValue =
    useMemo<ComputerDeploymentSessionContextValue>(
      () => ({
        authenticateShare: (runId, password) =>
          dispatchAction({
            type: 'deployment.authenticate_share',
            payload: { runId, password },
          }),
        connectCable: (runId, cable, port) =>
          dispatchAction({
            type: 'deployment.connect_cable',
            payload: { runId, cable, port },
          }),
        domainLogin: (runId, domain, username, password) =>
          dispatchAction({
            type: 'deployment.domain_login',
            payload: { runId, domain, username, password },
          }),
        isHydrated: hydrated,
        pressF12: (runId, timing) =>
          dispatchAction({
            type: 'deployment.press_f12',
            payload: { runId, timing },
          }),
        reboot: (runId) =>
          dispatchAction({ type: 'deployment.reboot', payload: { runId } }),
        run: activeDeploymentRun,
        runTaskSequence: (runId) =>
          dispatchAction({
            type: 'deployment.run_task_sequence',
            payload: { runId },
          }),
        selectBootSource: (runId, source) =>
          dispatchAction({
            type: 'deployment.select_boot_source',
            payload: { runId, source },
          }),
        selectDeviceType: (runId, deviceType) =>
          dispatchAction({
            type: 'deployment.select_device_type',
            payload: { runId, deviceType },
          }),
        setHostname: (runId, hostname) =>
          dispatchAction({
            type: 'deployment.set_hostname',
            payload: { runId, hostname },
          }),
        startDeployment: () =>
          dispatchAction({ type: 'deployment.start', payload: {} }),
      }),
      [activeDeploymentRun, dispatchAction, hydrated],
    );
  const shippingManagerSessionValue =
    useMemo<ShippingManagerSessionContextValue>(
      () => ({
        cancelShipment: (shipmentId) =>
          dispatchAction({
            type: 'shipping.cancel',
            payload: { shipmentId },
          }),
        computers: pcShelfComputers,
        createShipment: (payload) =>
          dispatchAction({ type: 'shipping.create', payload }),
        directoryUsers,
        isHydrated: hydrated,
        lastAddress: attempt.lastShippingAddress,
        shipments,
      }),
      [
        attempt.lastShippingAddress,
        directoryUsers,
        dispatchAction,
        hydrated,
        pcShelfComputers,
        shipments,
      ],
    );

  if (identityError) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 text-sm text-zinc-300"
        role="alert"
      >
        Unable to load your service desk session.
      </div>
    );
  }

  if (!identity || !hydrated) {
    return (
      <div
        className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 text-sm text-zinc-400"
        role="status"
      >
        Loading service desk…
      </div>
    );
  }

  return (
    <SessionIdentityContext.Provider value={identity}>
      <TicketSessionContext.Provider value={ticketSessionValue}>
        <AttemptScoreContext.Provider value={scoreValue}>
          <ProgressContext.Provider value={progressValue}>
            <DirectorySessionContext.Provider value={directorySessionValue}>
              <CompanyChatSessionContext.Provider
                value={companyChatSessionValue}
              >
                <AssetManagementSessionContext.Provider
                  value={assetManagementSessionValue}
                >
                  <PcShelfSessionContext.Provider value={pcShelfSessionValue}>
                    <ServerRoomSessionContext.Provider
                      value={serverRoomSessionValue}
                    >
                      <RemoteDesktopSessionContext.Provider
                        value={remoteDesktopSessionValue}
                      >
                        <ComputerDeploymentSessionContext.Provider
                          value={computerDeploymentSessionValue}
                        >
                          <ShippingManagerSessionContext.Provider
                            value={shippingManagerSessionValue}
                          >
                            {children}
                          </ShippingManagerSessionContext.Provider>
                        </ComputerDeploymentSessionContext.Provider>
                      </RemoteDesktopSessionContext.Provider>
                    </ServerRoomSessionContext.Provider>
                  </PcShelfSessionContext.Provider>
                </AssetManagementSessionContext.Provider>
              </CompanyChatSessionContext.Provider>
            </DirectorySessionContext.Provider>
          </ProgressContext.Provider>
        </AttemptScoreContext.Provider>
      </TicketSessionContext.Provider>
    </SessionIdentityContext.Provider>
  );
}

export function useSessionIdentity() {
  const value = useContext(SessionIdentityContext);

  if (!value) {
    throw new Error(
      'useSessionIdentity must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useTicketSession() {
  const value = useContext(TicketSessionContext);

  if (!value) {
    throw new Error(
      'useTicketSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useAttemptScore() {
  const value = useContext(AttemptScoreContext);

  if (!value) {
    throw new Error(
      'useAttemptScore must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

function useProgressContext() {
  const value = useContext(ProgressContext);

  if (!value) {
    throw new Error(
      'Progress selectors must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useAnalyticsSummary() {
  const { analyticsSummary, isHydrated } = useProgressContext();
  return { ...analyticsSummary, isHydrated };
}

export function useAchievements() {
  const { achievements, isHydrated } = useProgressContext();
  return { achievements, isHydrated };
}

export function usePastTickets() {
  const { isHydrated, pastTickets } = useProgressContext();
  return { isHydrated, pastTickets };
}

export function useSyncStatus() {
  return useProgressContext().syncStatus;
}

export function useSessionHydrated() {
  return useProgressContext().isHydrated;
}

export function useDirectorySession() {
  const value = useContext(DirectorySessionContext);

  if (!value) {
    throw new Error(
      'useDirectorySession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useCompanyChatSession() {
  const value = useContext(CompanyChatSessionContext);

  if (!value) {
    throw new Error(
      'useCompanyChatSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useAssetManagementSession() {
  const value = useContext(AssetManagementSessionContext);

  if (!value) {
    throw new Error(
      'useAssetManagementSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function usePcShelfSession() {
  const value = useContext(PcShelfSessionContext);

  if (!value) {
    throw new Error(
      'usePcShelfSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useServerRoomSession() {
  const value = useContext(ServerRoomSessionContext);

  if (!value) {
    throw new Error(
      'useServerRoomSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useRemoteDesktopSession() {
  const value = useContext(RemoteDesktopSessionContext);

  if (!value) {
    throw new Error(
      'useRemoteDesktopSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useComputerDeploymentSession() {
  const value = useContext(ComputerDeploymentSessionContext);

  if (!value) {
    throw new Error(
      'useComputerDeploymentSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}

export function useShippingManagerSession() {
  const value = useContext(ShippingManagerSessionContext);

  if (!value) {
    throw new Error(
      'useShippingManagerSession must be used inside TicketSessionProvider.',
    );
  }

  return value;
}
