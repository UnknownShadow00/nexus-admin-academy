import {
  AssetStatus,
  DEPLOYMENT_CABLES,
  DEPLOYMENT_STEP_IDS,
  PcShelfDeviceState,
  PcShelfNetworkStatus,
  REMOTE_DESKTOP_APP_IDS,
  REMOTE_DESKTOP_CONNECTION_STATES,
  REMOTE_DESKTOP_DRIVE_STATUSES,
  REMOTE_DESKTOP_LEARNING_MODES,
  REMOTE_DESKTOP_NETWORK_STATUSES,
  REMOTE_DESKTOP_POWER_STATES,
  REMOTE_DESKTOP_SERVICE_STATES,
  REMOTE_DESKTOP_UPDATE_STATES,
  REMOTE_DESKTOP_VPN_STATUSES,
  SERVER_ROOM_NODE_STATUSES,
  SHIPPING_DEPARTMENTS,
  SHIPPING_EQUIPMENT,
  SHIPPING_SPEEDS,
  TicketStatus,
  getRemoteDesktopInitialDriveStates,
  getDirectoryUserById,
  getRemoteDesktopTerminalFixture,
  getRemoteDesktopWorkstation,
  getServerRoomNode,
} from '@service-desk/shared';

import {
  createInitialPcShelfOverlays,
  createInitialRemoteDesktopOverlays,
  createInitialServerRoomOverlays,
} from './attempt';
import type {
  ActionEvent,
  AssetOverlay,
  Attempt,
  ChatMessage,
  ChatThreadOverlay,
  DirectoryUserOverlay,
  DeploymentRun,
  DeploymentStep,
  Grade,
  PcShelfOverlay,
  RemoteDesktopOverlay,
  ServerRoomOverlay,
  Shipment,
  ShipmentEquipmentItem,
  ShippingAddress,
  TicketClosure,
  TicketOverlay,
} from './types';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isIsoDate(value: unknown): value is string {
  return (
    isString(value) &&
    Number.isFinite(new Date(value).getTime()) &&
    value.includes('T')
  );
}

function isActionEvent(value: unknown): value is ActionEvent {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isString(value.attemptId) &&
    isString(value.actorId) &&
    isString(value.type) &&
    isRecord(value.payload) &&
    typeof value.success === 'boolean' &&
    (value.rejectReason === null || isString(value.rejectReason)) &&
    isIsoDate(value.createdAt)
  );
}

function isClosure(value: unknown): value is TicketClosure | null {
  return (
    value === null ||
    (isRecord(value) &&
      isIsoDate(value.closedAt) &&
      isString(value.resolutionNote) &&
      typeof value.verifiedResolved === 'boolean')
  );
}

function isTicketOverlay(value: unknown): value is TicketOverlay {
  return (
    isRecord(value) &&
    Object.values(TicketStatus).includes(value.status as TicketStatus) &&
    (value.assignedTo === 'you' || value.assignedTo === null) &&
    Array.isArray(value.notes) &&
    value.notes.every(
      (note) =>
        isRecord(note) &&
        isString(note.id) &&
        isString(note.body) &&
        isIsoDate(note.createdAt),
    ) &&
    typeof value.escalated === 'boolean' &&
    Number.isInteger(value.hintsRevealedCount) &&
    (value.hintsRevealedCount as number) >= 0 &&
    isClosure(value.closure) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isString);
}

function isDirectoryUserOverlay(value: unknown): value is DirectoryUserOverlay {
  return (
    isRecord(value) &&
    typeof value.locked === 'boolean' &&
    typeof value.disabled === 'boolean' &&
    typeof value.mfaEnrolled === 'boolean' &&
    (value.passwordState === 'current' ||
      value.passwordState === 'expired' ||
      value.passwordState === 'temporary') &&
    (value.mfaFactorStatus === 'available' ||
      value.mfaFactorStatus === 'device-unavailable' ||
      value.mfaFactorStatus === 'reset-ready') &&
    typeof value.inspected === 'boolean' &&
    typeof value.identityVerified === 'boolean' &&
    typeof value.primaryAuthTested === 'boolean' &&
    (value.diagnosis === null ||
      value.diagnosis === 'account-locked' ||
      value.diagnosis === 'password-expired' ||
      value.diagnosis === 'mfa-factor-unavailable') &&
    typeof value.accessVerified === 'boolean' &&
    isRecord(value.groupChanges) &&
    isStringArray(value.groupChanges.added) &&
    isStringArray(value.groupChanges.removed) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isChatMessage(value: unknown): value is ChatMessage {
  return (
    isRecord(value) &&
    isString(value.id) &&
    typeof value.fromStudent === 'boolean' &&
    isString(value.body) &&
    (value.triggerKey === null || isString(value.triggerKey)) &&
    isIsoDate(value.createdAt)
  );
}

function isChatThreadOverlay(value: unknown): value is ChatThreadOverlay {
  return (
    isRecord(value) &&
    Array.isArray(value.messages) &&
    value.messages.every(isChatMessage) &&
    typeof value.pinned === 'boolean' &&
    (value.lastReadAt === null || isIsoDate(value.lastReadAt)) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isAssetOverlay(value: unknown): value is AssetOverlay {
  return (
    isRecord(value) &&
    (value.assignedDirectoryUserId === null ||
      isString(value.assignedDirectoryUserId)) &&
    Object.values(AssetStatus).includes(value.status as AssetStatus) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isPcShelfOverlay(value: unknown): value is PcShelfOverlay {
  return (
    isRecord(value) &&
    (value.assignedDirectoryUserId === null ||
      isString(value.assignedDirectoryUserId)) &&
    Object.values(PcShelfDeviceState).includes(
      value.deviceState as PcShelfDeviceState,
    ) &&
    Object.values(PcShelfNetworkStatus).includes(
      value.networkStatus as PcShelfNetworkStatus,
    ) &&
    typeof value.present === 'boolean' &&
    (value.device === undefined ||
      (isRecord(value.device) &&
        isString(value.device.assetTag) &&
        isString(value.device.cpu) &&
        isString(value.device.deploymentMethod) &&
        Object.values(PcShelfDeviceState).includes(
          value.device.deviceState as PcShelfDeviceState,
        ) &&
        isString(value.device.location) &&
        Object.values(PcShelfNetworkStatus).includes(
          value.device.networkStatus as PcShelfNetworkStatus,
        ) &&
        isString(value.device.operatingSystem) &&
        isString(value.device.ram) &&
        isString(value.device.serialNumber) &&
        isString(value.device.storage))) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isDeploymentStep(value: unknown): value is DeploymentStep {
  return (
    isRecord(value) &&
    DEPLOYMENT_STEP_IDS.includes(
      value.id as (typeof DEPLOYMENT_STEP_IDS)[number],
    ) &&
    isString(value.title) &&
    isString(value.expectedAction) &&
    isRecord(value.wrongActionResponses) &&
    Object.values(value.wrongActionResponses).every(isString) &&
    (value.completedAt === null || isIsoDate(value.completedAt))
  );
}

function isDeploymentRun(value: unknown): value is DeploymentRun {
  return (
    isRecord(value) &&
    isString(value.id) &&
    value.method === 'Server Imaging' &&
    (value.deviceType === null || value.deviceType === 'Desktop') &&
    Number.isInteger(value.currentStepIndex) &&
    (value.currentStepIndex as number) >= 0 &&
    (value.currentStepIndex as number) < DEPLOYMENT_STEP_IDS.length &&
    Array.isArray(value.connectedCables) &&
    value.connectedCables.every((cable) =>
      DEPLOYMENT_CABLES.includes(cable as (typeof DEPLOYMENT_CABLES)[number]),
    ) &&
    (value.hostname === null || isString(value.hostname)) &&
    isIsoDate(value.startedAt) &&
    (value.completedAt === null || isIsoDate(value.completedAt)) &&
    Array.isArray(value.steps) &&
    value.steps.length === DEPLOYMENT_STEP_IDS.length &&
    value.steps.every(isDeploymentStep) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isShippingAddress(value: unknown): value is ShippingAddress {
  return (
    isRecord(value) &&
    isString(value.recipientDirectoryUserId) &&
    isString(value.recipientName) &&
    isString(value.street) &&
    isString(value.city) &&
    isString(value.state) &&
    isString(value.postalCode)
  );
}

function isShipmentEquipmentItem(
  value: unknown,
): value is ShipmentEquipmentItem {
  return (
    isRecord(value) &&
    SHIPPING_EQUIPMENT.includes(
      value.name as (typeof SHIPPING_EQUIPMENT)[number],
    ) &&
    Number.isInteger(value.quantity) &&
    (value.quantity as number) > 0
  );
}

function isShipment(value: unknown): value is Shipment {
  return (
    isRecord(value) &&
    isString(value.id) &&
    isShippingAddress(value.address) &&
    SHIPPING_DEPARTMENTS.includes(
      value.senderDepartment as (typeof SHIPPING_DEPARTMENTS)[number],
    ) &&
    Array.isArray(value.equipment) &&
    value.equipment.every(isShipmentEquipmentItem) &&
    (value.computerAssetTag === null || isString(value.computerAssetTag)) &&
    SHIPPING_SPEEDS.some((speed) => speed.id === value.speed) &&
    typeof value.includeReturnLabel === 'boolean' &&
    (value.status === 'shipped' || value.status === 'cancelled') &&
    isIsoDate(value.createdAt) &&
    (value.cancelledAt === null || isIsoDate(value.cancelledAt)) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isServiceStates(value: unknown) {
  return (
    isRecord(value) &&
    Object.values(value).every(
      (state) =>
        isString(state) &&
        REMOTE_DESKTOP_SERVICE_STATES.includes(
          state as (typeof REMOTE_DESKTOP_SERVICE_STATES)[number],
        ),
    )
  );
}

function getInitialRemoteDesktopServiceStates(assetTag: string) {
  return Object.fromEntries(
    getRemoteDesktopWorkstation(assetTag)?.services.map((service) => [
      service.name,
      service.state,
    ]) ?? [],
  );
}

function getInitialServerRoomServiceStates(nodeId: string) {
  const fixture = getServerRoomNode(nodeId);
  return fixture?.kind === 'server'
    ? { [fixture.serviceName]: 'running' as const }
    : {};
}

function isTerminalHistory(value: unknown) {
  return (
    Array.isArray(value) &&
    value.every(
      (entry) =>
        isRecord(entry) &&
        isString(entry.command) &&
        isStringArray(entry.output) &&
        isIsoDate(entry.timestamp),
    )
  );
}

function isDriveStates(value: unknown) {
  return (
    isRecord(value) &&
    Object.values(value).every(
      (status) =>
        isString(status) &&
        REMOTE_DESKTOP_DRIVE_STATUSES.includes(
          status as (typeof REMOTE_DESKTOP_DRIVE_STATUSES)[number],
        ),
    )
  );
}

function isExplorerError(value: unknown) {
  return (
    value === null ||
    (isRecord(value) &&
      (value.kind === 'network-path-error' ||
        value.kind === 'permission-error') &&
      isString(value.message) &&
      isString(value.path))
  );
}

function isRemoteDesktopScenarioProgress(value: unknown) {
  return (
    isRecord(value) &&
    isStringArray(value.investigationEvidence) &&
    isStringArray(value.diagnosisEvidence) &&
    isStringArray(value.fixEvidence) &&
    isStringArray(value.verificationEvidence) &&
    (value.internalNote === null || isString(value.internalNote)) &&
    isRecord(value.phases) &&
    typeof value.phases.investigated === 'boolean' &&
    typeof value.phases.diagnosed === 'boolean' &&
    typeof value.phases.fixed === 'boolean' &&
    typeof value.phases.verified === 'boolean' &&
    typeof value.phases.noted === 'boolean' &&
    typeof value.phases.closed === 'boolean' &&
    (value.finalScore === null || Number.isInteger(value.finalScore)) &&
    (value.feedback === null || isString(value.feedback))
  );
}

function isServerRoomOverlay(value: unknown): value is ServerRoomOverlay {
  return (
    isRecord(value) &&
    SERVER_ROOM_NODE_STATUSES.includes(
      value.status as (typeof SERVER_ROOM_NODE_STATUSES)[number],
    ) &&
    isServiceStates(value.serviceStates) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isRemoteDesktopOverlay(value: unknown): value is RemoteDesktopOverlay {
  return (
    isRecord(value) &&
    REMOTE_DESKTOP_CONNECTION_STATES.includes(
      value.connectionState as (typeof REMOTE_DESKTOP_CONNECTION_STATES)[number],
    ) &&
    isStringArray(value.completedScenarioIds) &&
    isStringArray(value.dnsServers) &&
    isDriveStates(value.driveStates) &&
    isString(value.explorerCurrentPath) &&
    isExplorerError(value.explorerError) &&
    (value.explorerLastRefreshedAt === null ||
      isIsoDate(value.explorerLastRefreshedAt)) &&
    (value.focusedApp === null ||
      REMOTE_DESKTOP_APP_IDS.includes(
        value.focusedApp as (typeof REMOTE_DESKTOP_APP_IDS)[number],
      )) &&
    (value.lastError === null || isString(value.lastError)) &&
    isStringArray(value.minimizedApps) &&
    (value.minimizedApps as string[]).every((appId) =>
      REMOTE_DESKTOP_APP_IDS.includes(
        appId as (typeof REMOTE_DESKTOP_APP_IDS)[number],
      ),
    ) &&
    isStringArray(value.openApps) &&
    (value.openApps as string[]).every((appId) =>
      REMOTE_DESKTOP_APP_IDS.includes(
        appId as (typeof REMOTE_DESKTOP_APP_IDS)[number],
      ),
    ) &&
    REMOTE_DESKTOP_POWER_STATES.includes(
      value.powerState as (typeof REMOTE_DESKTOP_POWER_STATES)[number],
    ) &&
    REMOTE_DESKTOP_NETWORK_STATUSES.includes(
      value.networkStatus as (typeof REMOTE_DESKTOP_NETWORK_STATUSES)[number],
    ) &&
    REMOTE_DESKTOP_LEARNING_MODES.includes(
      value.learningMode as (typeof REMOTE_DESKTOP_LEARNING_MODES)[number],
    ) &&
    isRecord(value.scenarioProgress) &&
    Object.values(value.scenarioProgress).every(
      isRemoteDesktopScenarioProgress,
    ) &&
    isRecord(value.scenarioSteps) &&
    Object.values(value.scenarioSteps).every(isStringArray) &&
    isServiceStates(value.serviceStates) &&
    isTerminalHistory(value.terminalHistory) &&
    typeof value.trainingMode === 'boolean' &&
    (value.updateInstalledAt === null || isIsoDate(value.updateInstalledAt)) &&
    REMOTE_DESKTOP_UPDATE_STATES.includes(
      value.updateState as (typeof REMOTE_DESKTOP_UPDATE_STATES)[number],
    ) &&
    (value.vpnError === null || isString(value.vpnError)) &&
    Array.isArray(value.vpnLog) &&
    value.vpnLog.every(
      (entry) =>
        isRecord(entry) &&
        isString(entry.message) &&
        isIsoDate(entry.timestamp),
    ) &&
    REMOTE_DESKTOP_VPN_STATUSES.includes(
      value.vpnStatus as (typeof REMOTE_DESKTOP_VPN_STATUSES)[number],
    ) &&
    Array.isArray(value.events) &&
    value.events.every(isActionEvent)
  );
}

function isGrade(value: unknown): value is Grade {
  return (
    isRecord(value) &&
    isString(value.attemptId) &&
    isString(value.ticketId) &&
    Number.isInteger(value.pointsAwarded) &&
    Number.isInteger(value.pointsPossible) &&
    Number.isInteger(value.penaltyPoints) &&
    Number.isInteger(value.hintsUsed) &&
    typeof value.resolved === 'boolean' &&
    isIsoDate(value.computedAt)
  );
}

function isAttempt(value: unknown): value is Attempt {
  if (
    !isRecord(value) ||
    !isString(value.id) ||
    !isIsoDate(value.startedAt) ||
    !(value.supersededById === null || isString(value.supersededById)) ||
    !isRecord(value.ticketOverlays) ||
    !isRecord(value.directoryOverlays) ||
    !isRecord(value.chatThreads) ||
    !isRecord(value.assetOverlays) ||
    !isRecord(value.pcShelfOverlays) ||
    !isRecord(value.deploymentRuns) ||
    !(
      value.activeDeploymentRunId === null ||
      isString(value.activeDeploymentRunId)
    ) ||
    !isRecord(value.shipments) ||
    !(
      value.lastShippingAddress === null ||
      isShippingAddress(value.lastShippingAddress)
    ) ||
    !isRecord(value.serverRoomOverlays) ||
    !isRecord(value.remoteDesktopOverlays) ||
    !isRecord(value.grades)
  ) {
    return false;
  }

  return (
    Object.entries(value.ticketOverlays).every(
      ([ticketId, overlay]) =>
        ticketId.length > 0 &&
        isTicketOverlay(overlay) &&
        overlay.events.every(
          (event) =>
            event.attemptId === value.id && event.payload.ticketId === ticketId,
        ),
    ) &&
    Object.entries(value.directoryOverlays).every(
      ([directoryUserId, overlay]) =>
        directoryUserId.length > 0 &&
        isDirectoryUserOverlay(overlay) &&
        overlay.events.every(
          (event) =>
            event.attemptId === value.id &&
            event.payload.directoryUserId === directoryUserId,
        ),
    ) &&
    Object.entries(value.chatThreads).every(
      ([contactId, thread]) =>
        contactId.length > 0 &&
        isChatThreadOverlay(thread) &&
        thread.events.every(
          (event) =>
            event.attemptId === value.id &&
            event.payload.contactId === contactId,
        ),
    ) &&
    Object.entries(value.assetOverlays).every(
      ([assetTag, overlay]) =>
        assetTag.length > 0 &&
        isAssetOverlay(overlay) &&
        overlay.events.every(
          (event) =>
            event.attemptId === value.id && event.payload.assetTag === assetTag,
        ),
    ) &&
    Object.entries(value.pcShelfOverlays).every(
      ([assetTag, overlay]) =>
        assetTag.length > 0 &&
        isPcShelfOverlay(overlay) &&
        overlay.events.every(
          (event) =>
            event.attemptId === value.id && event.payload.assetTag === assetTag,
        ),
    ) &&
    Object.entries(value.deploymentRuns).every(
      ([runId, run]) =>
        runId.length > 0 &&
        isDeploymentRun(run) &&
        run.id === runId &&
        run.events.every(
          (event) =>
            event.attemptId === value.id &&
            (event.type === 'deployment.start' ||
              event.payload.runId === runId),
        ),
    ) &&
    (value.activeDeploymentRunId === null ||
      value.deploymentRuns[value.activeDeploymentRunId] !== undefined) &&
    Object.entries(value.shipments).every(
      ([shipmentId, shipment]) =>
        shipmentId.length > 0 &&
        isShipment(shipment) &&
        shipment.id === shipmentId &&
        shipment.events.every(
          (event) =>
            event.attemptId === value.id &&
            (event.type === 'shipping.create' ||
              event.payload.shipmentId === shipmentId),
        ),
    ) &&
    Object.entries(value.serverRoomOverlays).every(
      ([nodeId, overlay]) =>
        nodeId.length > 0 &&
        isServerRoomOverlay(overlay) &&
        overlay.events.every(
          (event) =>
            event.attemptId === value.id && event.payload.nodeId === nodeId,
        ),
    ) &&
    Object.entries(value.remoteDesktopOverlays).every(
      ([assetTag, overlay]) =>
        assetTag.length > 0 &&
        isRemoteDesktopOverlay(overlay) &&
        overlay.events.every(
          (event) =>
            event.attemptId === value.id && event.payload.assetTag === assetTag,
        ),
    ) &&
    Object.entries(value.grades).every(
      ([ticketId, grade]) =>
        ticketId.length > 0 &&
        isGrade(grade) &&
        grade.attemptId === value.id &&
        grade.ticketId === ticketId,
    )
  );
}

export function serializeAttempt(attempt: Attempt): string {
  return JSON.stringify(attempt);
}

export function restoreAttempt(json: string): Attempt | null {
  try {
    const value: unknown = JSON.parse(json);
    const normalizedDirectory =
      isRecord(value) && value.directoryOverlays === undefined
        ? { ...value, directoryOverlays: {} }
        : value;
    const normalizedDirectoryState =
      isRecord(normalizedDirectory) &&
      isRecord(normalizedDirectory.directoryOverlays)
        ? {
            ...normalizedDirectory,
            directoryOverlays: Object.fromEntries(
              Object.entries(normalizedDirectory.directoryOverlays).map(
                ([directoryUserId, overlay]) => {
                  const fixture = getDirectoryUserById(directoryUserId);
                  return [
                    directoryUserId,
                    isRecord(overlay)
                      ? {
                          ...overlay,
                          passwordState:
                            overlay.passwordState ??
                            fixture?.passwordState ??
                            'current',
                          mfaFactorStatus:
                            overlay.mfaFactorStatus ??
                            fixture?.mfaFactorStatus ??
                            'available',
                          inspected: overlay.inspected ?? false,
                          identityVerified: overlay.identityVerified ?? false,
                          primaryAuthTested: overlay.primaryAuthTested ?? false,
                          diagnosis: overlay.diagnosis ?? null,
                          accessVerified: overlay.accessVerified ?? false,
                        }
                      : overlay,
                  ];
                },
              ),
            ),
          }
        : normalizedDirectory;
    const normalized =
      isRecord(normalizedDirectoryState) &&
      normalizedDirectoryState.chatThreads === undefined
        ? { ...normalizedDirectoryState, chatThreads: {} }
        : normalizedDirectoryState;
    const normalizedAssets =
      isRecord(normalized) && normalized.assetOverlays === undefined
        ? { ...normalized, assetOverlays: {} }
        : normalized;
    const normalizedPcShelf =
      isRecord(normalizedAssets) &&
      normalizedAssets.pcShelfOverlays === undefined
        ? {
            ...normalizedAssets,
            pcShelfOverlays: createInitialPcShelfOverlays(),
          }
        : normalizedAssets;
    const normalizedServerRoom =
      isRecord(normalizedPcShelf) &&
      normalizedPcShelf.serverRoomOverlays === undefined
        ? {
            ...normalizedPcShelf,
            serverRoomOverlays: createInitialServerRoomOverlays(),
          }
        : normalizedPcShelf;
    const normalizedRemoteDesktop =
      isRecord(normalizedServerRoom) &&
      normalizedServerRoom.remoteDesktopOverlays === undefined
        ? {
            ...normalizedServerRoom,
            remoteDesktopOverlays: createInitialRemoteDesktopOverlays(),
          }
        : normalizedServerRoom;
    const normalizedServerRoomState =
      isRecord(normalizedRemoteDesktop) &&
      isRecord(normalizedRemoteDesktop.serverRoomOverlays)
        ? {
            ...normalizedRemoteDesktop,
            serverRoomOverlays: Object.fromEntries(
              Object.entries(normalizedRemoteDesktop.serverRoomOverlays).map(
                ([nodeId, overlay]) => [
                  nodeId,
                  isRecord(overlay)
                    ? {
                        ...overlay,
                        serviceStates:
                          overlay.serviceStates ??
                          getInitialServerRoomServiceStates(nodeId),
                      }
                    : overlay,
                ],
              ),
            ),
          }
        : normalizedRemoteDesktop;
    const normalizedRemoteDesktopState =
      isRecord(normalizedServerRoomState) &&
      isRecord(normalizedServerRoomState.remoteDesktopOverlays)
        ? {
            ...normalizedServerRoomState,
            remoteDesktopOverlays: Object.fromEntries(
              Object.entries(
                normalizedServerRoomState.remoteDesktopOverlays,
              ).map(([assetTag, overlay]) => [
                assetTag,
                isRecord(overlay)
                  ? {
                      ...overlay,
                      connectionState:
                        overlay.connectionState ?? 'disconnected',
                      completedScenarioIds: overlay.completedScenarioIds ?? [],
                      dnsServers: overlay.dnsServers ?? [
                        ...getRemoteDesktopTerminalFixture(assetTag).dnsServers,
                      ],
                      driveStates:
                        overlay.driveStates ??
                        getRemoteDesktopInitialDriveStates(assetTag),
                      explorerCurrentPath:
                        overlay.explorerCurrentPath ?? 'This PC',
                      explorerError: overlay.explorerError ?? null,
                      explorerLastRefreshedAt:
                        overlay.explorerLastRefreshedAt ?? null,
                      focusedApp: overlay.focusedApp ?? null,
                      lastError: overlay.lastError ?? null,
                      learningMode:
                        overlay.learningMode ??
                        (overlay.trainingMode === false
                          ? 'practice'
                          : 'guided'),
                      minimizedApps: overlay.minimizedApps ?? [],
                      openApps: overlay.openApps ?? [],
                      scenarioProgress: isRecord(overlay.scenarioProgress)
                        ? Object.fromEntries(
                            Object.entries(overlay.scenarioProgress).map(
                              ([scenarioId, progress]) => [
                                scenarioId,
                                isRecord(progress)
                                  ? {
                                      ...progress,
                                      investigationEvidence:
                                        progress.investigationEvidence ?? [],
                                      phases: isRecord(progress.phases)
                                        ? {
                                            ...progress.phases,
                                            investigated:
                                              progress.phases.investigated ??
                                              false,
                                          }
                                        : progress.phases,
                                    }
                                  : progress,
                              ],
                            ),
                          )
                        : {},
                      scenarioSteps: overlay.scenarioSteps ?? {},
                      serviceStates:
                        overlay.serviceStates ??
                        getInitialRemoteDesktopServiceStates(assetTag),
                      terminalHistory: overlay.terminalHistory ?? [],
                      trainingMode:
                        overlay.trainingMode ??
                        (typeof overlay.learningMode === 'string'
                          ? overlay.learningMode === 'guided'
                          : true),
                      updateInstalledAt: overlay.updateInstalledAt ?? null,
                      updateState:
                        overlay.updateState ??
                        (getRemoteDesktopWorkstation(assetTag)?.pendingUpdate
                          ? 'pending'
                          : 'applied'),
                      vpnError: overlay.vpnError ?? null,
                      vpnLog: overlay.vpnLog ?? [],
                      vpnStatus: overlay.vpnStatus ?? 'disconnected',
                    }
                  : overlay,
              ]),
            ),
          }
        : normalizedServerRoomState;
    const normalizedDeployment =
      isRecord(normalizedRemoteDesktopState) &&
      normalizedRemoteDesktopState.deploymentRuns === undefined
        ? {
            ...normalizedRemoteDesktopState,
            deploymentRuns: {},
            activeDeploymentRunId: null,
          }
        : normalizedRemoteDesktopState;
    const normalizedShipping =
      isRecord(normalizedDeployment) &&
      normalizedDeployment.shipments === undefined
        ? {
            ...normalizedDeployment,
            shipments: {},
            lastShippingAddress: null,
          }
        : normalizedDeployment;
    return isAttempt(normalizedShipping) ? normalizedShipping : null;
  } catch {
    return null;
  }
}
