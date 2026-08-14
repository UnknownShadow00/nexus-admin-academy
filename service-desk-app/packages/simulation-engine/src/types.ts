import type {
  DeploymentCable,
  DeploymentStepId,
  IdentityVerificationMethod,
  PcShelfComputerFixture,
  ShippingDepartment,
  ShippingEquipmentName,
  ShippingSpeed,
  TicketNote,
} from '@service-desk/shared';
import {
  AssetStatus,
  PcShelfDeviceState,
  PcShelfNetworkStatus,
  type RemoteDesktopAppId,
  type RemoteDesktopConnectionState,
  type RemoteDesktopDriveStatus,
  type RemoteDesktopLearningMode,
  type RemoteDesktopNetworkStatus,
  type RemoteDesktopPowerState,
  type RemoteDesktopServiceState,
  type RemoteDesktopUpdateState,
  type RemoteDesktopVpnStatus,
  type ServerRoomNodeStatus,
  type WorkstationState,
  TicketStatus,
} from '@service-desk/shared';

export interface ActionEvent {
  id: string;
  attemptId: string;
  actorId: string;
  type: string;
  payload: Readonly<Record<string, unknown>>;
  success: boolean;
  rejectReason: string | null;
  createdAt: string;
}

export interface TicketClosure {
  closedAt: string;
  resolutionNote: string;
  verifiedResolved: boolean;
}

export interface TicketOverlay {
  status: TicketStatus;
  assignedTo: 'you' | null;
  notes: readonly TicketNote[];
  escalated: boolean;
  hintsRevealedCount: number;
  closure: TicketClosure | null;
  /**
   * The temporary browser implementation keeps append-only ticket events with
   * the overlay. A future repository adapter can persist the same values in the
   * standalone Event table without changing applyAction's public contract.
   */
  events: readonly ActionEvent[];
}

export interface DirectoryUserOverlay {
  locked: boolean;
  disabled: boolean;
  mfaEnrolled: boolean;
  passwordState: 'current' | 'expired' | 'temporary';
  mfaFactorStatus: 'available' | 'device-unavailable' | 'reset-ready';
  inspected: boolean;
  identityVerified: boolean;
  identityVerificationMethod: IdentityVerificationMethod | null;
  primaryAuthTested: boolean;
  diagnosis:
    | 'account-locked'
    | 'password-expired'
    | 'mfa-factor-unavailable'
    | null;
  accessVerified: boolean;
  groupChanges: {
    added: readonly string[];
    removed: readonly string[];
  };
  /**
   * Directory events stay append-only alongside the overlay in this
   * browser-backed phase, matching the ticket overlay event convention.
   */
  events: readonly ActionEvent[];
}

export interface ChatMessage {
  id: string;
  fromStudent: boolean;
  body: string;
  triggerKey: string | null;
  createdAt: string;
}

export interface ChatThreadOverlay {
  messages: readonly ChatMessage[];
  pinned: boolean;
  lastReadAt: string | null;
  /**
   * Chat events remain append-only alongside the thread overlay so rejected
   * and successful actions survive the browser-backed attempt lifecycle.
   */
  events: readonly ActionEvent[];
}

export interface AssetOverlay {
  assignedDirectoryUserId: string | null;
  status: AssetStatus;
  events: readonly ActionEvent[];
}

export interface PcShelfOverlay {
  assignedDirectoryUserId: string | null;
  deviceState: PcShelfDeviceState;
  networkStatus: PcShelfNetworkStatus;
  present: boolean;
  /** Runtime profile for devices created by Computer Deployment. */
  device?: PcShelfComputerFixture;
  events: readonly ActionEvent[];
}

export interface DeploymentStep {
  id: DeploymentStepId;
  title: string;
  expectedAction: string;
  wrongActionResponses: Readonly<Record<string, string>>;
  completedAt: string | null;
}

export interface DeploymentRun {
  id: string;
  method: 'Server Imaging';
  deviceType: 'Desktop' | null;
  currentStepIndex: number;
  connectedCables: readonly DeploymentCable[];
  hostname: string | null;
  startedAt: string;
  completedAt: string | null;
  steps: readonly DeploymentStep[];
  events: readonly ActionEvent[];
}

export interface ShippingAddress {
  recipientDirectoryUserId: string;
  recipientName: string;
  street: string;
  city: string;
  state: string;
  postalCode: string;
}

export interface ShipmentEquipmentItem {
  name: ShippingEquipmentName;
  quantity: number;
}

export interface Shipment {
  id: string;
  address: ShippingAddress;
  senderDepartment: ShippingDepartment;
  equipment: readonly ShipmentEquipmentItem[];
  computerAssetTag: string | null;
  speed: ShippingSpeed;
  includeReturnLabel: boolean;
  status: 'shipped' | 'cancelled';
  createdAt: string;
  cancelledAt: string | null;
  events: readonly ActionEvent[];
}

export interface ServerRoomOverlay {
  status: ServerRoomNodeStatus;
  serviceStates: Readonly<Record<string, RemoteDesktopServiceState>>;
  events: readonly ActionEvent[];
}

export interface RemoteDesktopScenarioProgress {
  investigationEvidence: readonly string[];
  diagnosisEvidence: readonly string[];
  fixEvidence: readonly string[];
  verificationEvidence: readonly string[];
  internalNote: string | null;
  phases: {
    investigated: boolean;
    diagnosed: boolean;
    fixed: boolean;
    verified: boolean;
    noted: boolean;
    closed: boolean;
  };
  finalScore: number | null;
  feedback: string | null;
}

export interface RemoteDesktopOverlay {
  /**
   * Schema-versioned shared workstation truth. Legacy flat fields remain as a
   * compatibility projection until every app and persisted v1 attempt has
   * migrated to the workstation domain.
   */
  workstation: WorkstationState;
  connectionState: RemoteDesktopConnectionState;
  completedScenarioIds: readonly string[];
  dnsServers: readonly string[];
  driveStates: Readonly<Record<string, RemoteDesktopDriveStatus>>;
  explorerCurrentPath: string;
  explorerError: {
    kind: 'network-path-error' | 'permission-error';
    message: string;
    path: string;
  } | null;
  explorerLastRefreshedAt: string | null;
  focusedApp: RemoteDesktopAppId | null;
  lastError: string | null;
  minimizedApps: readonly RemoteDesktopAppId[];
  openApps: readonly RemoteDesktopAppId[];
  powerState: RemoteDesktopPowerState;
  networkStatus: RemoteDesktopNetworkStatus;
  learningMode: RemoteDesktopLearningMode;
  scenarioProgress: Readonly<Record<string, RemoteDesktopScenarioProgress>>;
  scenarioSteps: Readonly<Record<string, readonly string[]>>;
  serviceStates: Readonly<Record<string, RemoteDesktopServiceState>>;
  terminalHistory: readonly {
    command: string;
    output: readonly string[];
    timestamp: string;
  }[];
  /** @deprecated Kept in serialized state so pre-Phase-18 attempts migrate cleanly. */
  trainingMode: boolean;
  updateInstalledAt: string | null;
  updateState: RemoteDesktopUpdateState;
  vpnError: string | null;
  vpnLog: readonly {
    message: string;
    timestamp: string;
  }[];
  vpnStatus: RemoteDesktopVpnStatus;
  events: readonly ActionEvent[];
}

export interface Grade {
  attemptId: string;
  experienceMode?: 'guided' | 'practice' | 'assessment';
  ticketId: string;
  pointsAwarded: number;
  pointsPossible: number;
  penaltyPoints: number;
  hintsUsed: number;
  resolved: boolean;
  computedAt: string;
}

export interface Attempt {
  id: string;
  startedAt: string;
  supersededById: string | null;
  ticketOverlays: Readonly<Record<string, TicketOverlay>>;
  directoryOverlays: Readonly<Record<string, DirectoryUserOverlay>>;
  chatThreads: Readonly<Record<string, ChatThreadOverlay>>;
  assetOverlays: Readonly<Record<string, AssetOverlay>>;
  pcShelfOverlays: Readonly<Record<string, PcShelfOverlay>>;
  deploymentRuns: Readonly<Record<string, DeploymentRun>>;
  activeDeploymentRunId: string | null;
  shipments: Readonly<Record<string, Shipment>>;
  lastShippingAddress: ShippingAddress | null;
  serverRoomOverlays: Readonly<Record<string, ServerRoomOverlay>>;
  remoteDesktopOverlays: Readonly<Record<string, RemoteDesktopOverlay>>;
  grades: Readonly<Record<string, Grade>>;
}
