import {
  AssetStatus,
  CLOSED_TICKET_STATUSES,
  DEPLOYMENT_BOOT_SOURCES,
  DEPLOYMENT_CABLE_PORTS,
  DEPLOYMENT_CABLES,
  DEPLOYMENT_DOMAIN,
  DEPLOYMENT_DOMAIN_PASSWORD,
  DEPLOYMENT_DOMAIN_USERNAME,
  DEPLOYMENT_SHARE_PASSWORD,
  DEPLOYMENT_STEP_TEMPLATES,
  DIRECTORY_GROUP_NAMES,
  DIRECTORY_USER_FIXTURES,
  PC_SHELF_FIXTURES,
  PcShelfDeviceState,
  PcShelfNetworkStatus,
  SHIPPING_DEPARTMENTS,
  SHIPPING_EQUIPMENT,
  SHIPPING_SPEEDS,
  REMOTE_DESKTOP_APP_IDS,
  REMOTE_DESKTOP_LEARNING_MODES,
  getRemoteDesktopScenarioByTicket,
  getRemoteDesktopScenarioByAsset,
  getRemoteDesktopInitialDriveStates,
  getRemoteDesktopTerminalFixture,
  getRemoteDesktopWorkstation,
  getServerRoomDevice,
  getServerRoomNode,
  getServerRoomServer,
  getPcShelfFixture,
  getDirectoryUserById,
  getFixtureTicket,
  getStatusTransitions,
  TicketStatus,
  WORKSTATION_EVENT_HISTORY_LIMIT,
  WORKSTATION_RENDERED_TERMINAL_LIMIT,
  WORKSTATION_TERMINAL_COMMAND_MAX_LENGTH,
  WORKSTATION_VPN_LOG_LIMIT,
  type TicketNote,
  type RemoteDesktopScenarioFixture,
} from '@service-desk/shared';

import type {
  AssetSimulationAction,
  ChatSimulationAction,
  DeviceSimulationAction,
  DirectorySimulationAction,
  DeploymentSimulationAction,
  PcShelfSimulationAction,
  RemoteDesktopSimulationAction,
  ServerRoomSimulationAction,
  ShippingSimulationAction,
  SimulationAction,
  TicketSimulationAction,
  UpdateDirectoryGroupsAction,
} from './actions';
import { resolveScriptedChatReply } from './chat';
import {
  executeWorkstationCommand,
  mapWorkstationDrive,
} from './workstation/commands';
import {
  addWorkstationCredential,
  deleteWorkstationCredential,
} from './workstation/credentials';
import {
  closeWorkstationWindow,
  focusWorkstationWindow,
  minimizeWorkstationWindow,
  moveWorkstationWindow,
  openWorkstationWindow,
  setWorkstationStartMenu,
  toggleWorkstationWindowMaximize,
} from './workstation/windows';
import {
  createUnavailableWorkstationState,
  createWorkstationState,
  reconcileWorkstationState,
} from './workstation/state';
import type {
  ActionEvent,
  AssetOverlay,
  Attempt,
  ChatThreadOverlay,
  DirectoryUserOverlay,
  DeploymentRun,
  PcShelfOverlay,
  RemoteDesktopOverlay,
  RemoteDesktopScenarioProgress,
  ServerRoomOverlay,
  Shipment,
  ShippingAddress,
  TicketOverlay,
} from './types';

export interface ApplyActionResult {
  attempt: Attempt;
  event: ActionEvent;
}

const ACCOUNT_CASE_USER_BY_TICKET: Readonly<Record<string, string>> = {
  INC2511: 'directory-user-taylor-morgan',
  INC2512: 'directory-user-jordan-lee',
  INC2513: 'directory-user-camille-reyes',
};

const INTEGRATED_ENDPOINT_TICKET_IDS = new Set(['INC3001', 'INC3002']);

function createId(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 10)}`;
}

function createTicketOverlay(ticketId: string): TicketOverlay {
  const fixture = getFixtureTicket(ticketId);

  return {
    status: fixture?.status ?? TicketStatus.Open,
    assignedTo: fixture?.assignedTo ?? null,
    notes: fixture ? [...fixture.notes] : [],
    escalated: fixture?.escalated ?? false,
    hintsRevealedCount: 0,
    closure: null,
    events: [],
  };
}

function isMeaningfulInternalNote(text: string) {
  const words = text
    .normalize('NFKC')
    .toLocaleLowerCase()
    .match(/[\p{L}\p{N}]+/gu);
  if (!words || words.length < 5 || new Set(words).size < 4) {
    return false;
  }

  const joined = words.join(' ');
  const documentsDiagnosis =
    /\b(cause|diagnos|observ|investigat|confirm)/u.test(joined);
  const documentsRepair =
    /\b(fix(?:ed|ing)?|repair(?:ed|ing)?|appl(?:y|ied)|start(?:ed)?|connect(?:ed)?|configur(?:e|ed|ing)|set|unlock(?:ed|ing)?|reset(?:ting)?|issu(?:e|ed|ing)|clear(?:ed|ing)?)\b/u.test(
      joined,
    );
  const documentsVerification =
    /\b(verif(?:y|ied|ication)|test(?:ed|ing)?|validat(?:e|ed|ion)|resolv(?:e|ed|ing)|restor(?:e|ed|ing)|confirm)/u.test(
      joined,
    );

  return documentsDiagnosis && documentsRepair && documentsVerification;
}

function hasSuccessfulResolutionConfirmation(
  attempt: Attempt,
  ticketId: string,
) {
  const contactId = CHAT_REQUESTER_BY_TICKET[ticketId];
  return Boolean(
    contactId &&
      attempt.chatThreads[contactId]?.messages.some(
        (message) =>
          !message.fromStudent &&
          message.triggerKey === 'original-symptom-confirmed-fixed',
      ),
  );
}

function ticketRejectReason(
  attempt: Attempt,
  overlay: TicketOverlay,
  action: TicketSimulationAction,
): string | null {
  const fixture = getFixtureTicket(action.payload.ticketId);
  const accountUserId = ACCOUNT_CASE_USER_BY_TICKET[action.payload.ticketId];
  const accountOverlay = accountUserId
    ? attempt.directoryOverlays[accountUserId]
    : undefined;

  if (
    !fixture &&
    !INTEGRATED_ENDPOINT_TICKET_IDS.has(action.payload.ticketId)
  ) {
    return 'The requested ticket does not exist in this simulation.';
  }

  switch (action.type) {
    case 'ticket.assign':
      return overlay.assignedTo === 'you'
        ? 'This ticket is already assigned to you.'
        : null;
    case 'ticket.unassign':
      return overlay.assignedTo === null
        ? 'This ticket is already in the shared queue.'
        : null;
    case 'ticket.change_status':
      return getStatusTransitions(overlay.status).includes(
        action.payload.status,
      )
        ? null
        : `A ticket cannot move from ${overlay.status} to ${action.payload.status}.`;
    case 'ticket.add_note':
      if (action.payload.body.trim().length === 0) {
        return 'An internal note cannot be empty.';
      }
      if (accountUserId && !accountOverlay?.accessVerified) {
        return 'Verify the original sign-in path before writing the final resolution note.';
      }
      if (
        accountUserId &&
        !hasSuccessfulResolutionConfirmation(attempt, action.payload.ticketId)
      ) {
        return 'Ask the requester in Company Chat to retest the original sign-in symptom before documenting closure.';
      }
      if (accountUserId && !isMeaningfulInternalNote(action.payload.body)) {
        return 'Document the diagnosis, remediation, and post-fix verification in the note.';
      }
      return null;
    case 'ticket.escalate':
      return overlay.escalated
        ? 'This ticket has already been escalated.'
        : null;
    case 'ticket.reveal_hint': {
      const scenario = getRemoteDesktopScenarioByTicket(
        action.payload.ticketId,
      );
      const remoteOverlay = scenario
        ? attempt.remoteDesktopOverlays[scenario.assetTag]
        : undefined;
      if (
        scenario?.workflow &&
        remoteOverlay?.learningMode === 'assessment' &&
        !remoteOverlay.completedScenarioIds.includes(scenario.id)
      ) {
        return 'Hints are unavailable until this assessment is complete.';
      }
      const hintCount = fixture?.hints.length ?? 0;
      if (action.payload.step > hintCount) {
        return `Only ${hintCount} hints are available for this ticket.`;
      }
      if (action.payload.step <= overlay.hintsRevealedCount) {
        return `Hint ${action.payload.step} has already been revealed.`;
      }
      return action.payload.step === overlay.hintsRevealedCount + 1
        ? null
        : 'Hints must be revealed in order.';
    }
    case 'ticket.close':
      if (
        CLOSED_TICKET_STATUSES.includes(
          overlay.status as (typeof CLOSED_TICKET_STATUSES)[number],
        )
      ) {
        return 'This ticket is already closed or resolved.';
      }
      {
        if (accountUserId) {
          if (!action.payload.verifiedResolved) {
            return 'Starter account cases must be closed as verified resolved.';
          }
          if (!accountOverlay?.accessVerified) {
            return 'Verify the original sign-in path after remediation before closing this ticket.';
          }
          if (
            !hasSuccessfulResolutionConfirmation(
              attempt,
              action.payload.ticketId,
            )
          ) {
            return 'Obtain the requester’s Company Chat confirmation of the original sign-in retest before closing.';
          }
          const finalNote = [...overlay.notes]
            .reverse()
            .find((note) => isMeaningfulInternalNote(note.body));
          if (!finalNote) {
            return 'Add a meaningful note covering diagnosis, remediation, and verification before closing.';
          }
          if (action.payload.resolutionNote.trim() !== finalNote.body) {
            return 'Close the ticket with the resolution note written during this attempt.';
          }
          return null;
        }
        const scenario = getRemoteDesktopScenarioByTicket(
          action.payload.ticketId,
        );
        if (!scenario?.workflow) return null;
        if (!action.payload.verifiedResolved) {
          return 'Phase-based tickets must be closed as verified resolved.';
        }
        const progress =
          attempt.remoteDesktopOverlays[scenario.assetTag]?.scenarioProgress[
            scenario.id
          ];
        if (!progress?.phases.fixed) {
          return 'Complete the repair and leave the computer in the corrected state before closing this ticket.';
        }
        if (!progress.phases.verified) {
          return 'Perform a real post-fix verification before closing this ticket.';
        }
        if (
          CHAT_REQUESTER_BY_TICKET[action.payload.ticketId] &&
          !hasSuccessfulResolutionConfirmation(attempt, action.payload.ticketId)
        ) {
          return 'Ask the requester in Company Chat to confirm the original symptom is resolved before closing.';
        }
        if (!progress.phases.noted || !progress.internalNote) {
          return 'Add a non-trivial student-authored internal note before closing this ticket.';
        }
        if (action.payload.resolutionNote.trim() !== progress.internalNote) {
          return 'Close the ticket with the internal note written during this attempt.';
        }
        return null;
      }
  }
}

function applyValidTicketAction(
  overlay: TicketOverlay,
  action: TicketSimulationAction,
  createdAt: string,
  eventId: string,
): TicketOverlay {
  switch (action.type) {
    case 'ticket.assign':
      return { ...overlay, assignedTo: 'you' };
    case 'ticket.unassign':
      return { ...overlay, assignedTo: null };
    case 'ticket.change_status':
      return { ...overlay, status: action.payload.status };
    case 'ticket.add_note': {
      const note: TicketNote = {
        body: action.payload.body.trim(),
        createdAt,
        id: `${eventId}-note`,
      };
      return { ...overlay, notes: [...overlay.notes, note] };
    }
    case 'ticket.escalate':
      return { ...overlay, escalated: true };
    case 'ticket.reveal_hint':
      return { ...overlay, hintsRevealedCount: action.payload.step };
    case 'ticket.close': {
      const resolutionNote = action.payload.resolutionNote.trim();
      const note: TicketNote | null = resolutionNote
        ? {
            body: resolutionNote,
            createdAt,
            id: `${eventId}-resolution-note`,
          }
        : null;

      return {
        ...overlay,
        status: action.payload.verifiedResolved
          ? TicketStatus.Resolved
          : TicketStatus.Closed,
        notes:
          note && !overlay.notes.some((existing) => existing.body === note.body)
            ? [...overlay.notes, note]
            : overlay.notes,
        closure: {
          closedAt: createdAt,
          resolutionNote,
          verifiedResolved: action.payload.verifiedResolved,
        },
      };
    }
  }
}

function createDirectoryOverlay(directoryUserId: string): DirectoryUserOverlay {
  const fixture = getDirectoryUserById(directoryUserId);

  return {
    locked: fixture?.locked ?? false,
    disabled: fixture?.disabled ?? false,
    mfaEnrolled: fixture?.mfaEnrolled ?? false,
    passwordState: fixture?.passwordState ?? 'current',
    mfaFactorStatus: fixture?.mfaFactorStatus ?? 'available',
    inspected: false,
    identityVerified: false,
    identityVerificationMethod: null,
    primaryAuthTested: false,
    diagnosis: null,
    accessVerified: false,
    groupChanges: { added: [], removed: [] },
    events: [],
  };
}

function effectiveGroups(
  directoryUserId: string,
  overlay: DirectoryUserOverlay,
) {
  const fixture = getDirectoryUserById(directoryUserId);
  const removed = new Set(overlay.groupChanges.removed);
  const templateGroups = new Set<string>(fixture?.groups ?? []);

  return [
    ...(fixture?.groups.filter((group) => !removed.has(group)) ?? []),
    ...overlay.groupChanges.added.filter((group) => !templateGroups.has(group)),
  ];
}

function nextGroupsForUpdate(
  overlay: DirectoryUserOverlay,
  action: UpdateDirectoryGroupsAction,
) {
  const current = effectiveGroups(action.payload.directoryUserId, overlay);
  const next = new Set(current);

  for (const group of action.payload.remove) {
    next.delete(group);
  }
  for (const group of action.payload.add) {
    next.add(group);
  }

  return DIRECTORY_GROUP_NAMES.filter((group) => next.has(group));
}

function sameGroups(left: readonly string[], right: readonly string[]) {
  return (
    left.length === right.length && left.every((group) => right.includes(group))
  );
}

function directoryRejectReason(
  overlay: DirectoryUserOverlay,
  action: DirectorySimulationAction,
): string | null {
  const fixture = getDirectoryUserById(action.payload.directoryUserId);

  if (!fixture) {
    return 'The requested directory user does not exist in this simulation.';
  }

  switch (action.type) {
    case 'directory.inspect_account':
      return overlay.inspected
        ? 'This account state has already been reviewed.'
        : null;
    case 'directory.verify_identity':
      if (!overlay.inspected) {
        return 'Review the account state before recording the approved identity check.';
      }
      if (overlay.identityVerificationMethod !== action.payload.method) {
        return 'Complete an approved Company Chat identity-verification interaction before recording it in Directory.';
      }
      return overlay.identityVerified
        ? 'The approved training identity check is already recorded.'
        : null;
    case 'directory.test_primary_auth':
      if (!overlay.inspected) {
        return 'Review the account state before testing the primary sign-in step.';
      }
      if (overlay.primaryAuthTested) {
        return 'Primary authentication has already been tested.';
      }
      return action.payload.result ===
        (fixture.primaryAuthSucceeds ? 'succeeds' : 'blocked')
        ? null
        : 'The recorded primary-authentication result does not match the simulated sign-in.';
    case 'directory.record_diagnosis':
      if (!overlay.inspected || !overlay.identityVerified) {
        return 'Inspect the account and complete the approved identity check before diagnosing it.';
      }
      if (
        fixture.supportIssue === 'mfa-factor-unavailable' &&
        !overlay.primaryAuthTested
      ) {
        return 'Test primary password authentication before diagnosing an MFA problem.';
      }
      return action.payload.diagnosis === fixture.supportIssue
        ? null
        : 'That diagnosis does not match the account evidence.';
    case 'directory.verify_access': {
      const expectedChecks: Readonly<Record<string, string>> = {
        'account-locked': 'account-unlocked',
        'password-expired': 'temporary-password-issued',
        'mfa-factor-unavailable': 'mfa-reregistration-ready',
      };
      const expectedCheck = fixture.supportIssue
        ? expectedChecks[fixture.supportIssue]
        : undefined;
      if (!overlay.diagnosis || action.payload.check !== expectedCheck) {
        return 'Complete the correct remediation before verifying the original sign-in path.';
      }
      const remediated =
        (fixture.supportIssue === 'account-locked' && !overlay.locked) ||
        (fixture.supportIssue === 'password-expired' &&
          overlay.passwordState === 'temporary') ||
        (fixture.supportIssue === 'mfa-factor-unavailable' &&
          overlay.mfaFactorStatus === 'reset-ready');
      return remediated
        ? null
        : 'The original account problem has not been remediated yet.';
    }
    case 'directory.unlock_account':
      if (
        fixture.supportIssue &&
        (!overlay.inspected || !overlay.identityVerified)
      ) {
        return 'Review the account and record an approved identity check before using account actions.';
      }
      return overlay.locked
        ? null
        : 'This directory account is already unlocked.';
    case 'directory.reset_password':
      if (
        fixture.supportIssue &&
        (!overlay.inspected || !overlay.identityVerified)
      ) {
        return 'Review the account and record an approved identity check before using account actions.';
      }
      if (
        fixture.supportIssue === 'password-expired' &&
        action.payload.requireChangeAtNextSignIn !== true
      ) {
        return 'Starter password resets must require a change at the next sign-in.';
      }
      return overlay.disabled
        ? 'A password cannot be reset while this account is disabled.'
        : null;
    case 'directory.enable_account':
      if (fixture.supportIssue) {
        return 'Enable and disable controls are restricted for this active support case.';
      }
      return overlay.disabled
        ? null
        : 'This directory account is already enabled.';
    case 'directory.disable_account':
      if (fixture.supportIssue) {
        return 'Disabling this active requester account is not an approved training action.';
      }
      return overlay.disabled
        ? 'This directory account is already disabled.'
        : null;
    case 'directory.reset_mfa':
      if (
        fixture.supportIssue &&
        (!overlay.inspected || !overlay.identityVerified)
      ) {
        return 'Review the account and record an approved identity check before using account actions.';
      }
      return overlay.disabled
        ? 'MFA cannot be reset while this account is disabled.'
        : null;
    case 'directory.update_groups': {
      const requestedGroups = [...action.payload.add, ...action.payload.remove];
      const knownGroups = new Set<string>(DIRECTORY_GROUP_NAMES);
      const unknownGroup = requestedGroups.find(
        (group) => !knownGroups.has(group),
      );
      if (unknownGroup) {
        return `"${unknownGroup}" is not a group in this directory template.`;
      }

      const current = effectiveGroups(action.payload.directoryUserId, overlay);
      const next = nextGroupsForUpdate(overlay, action);
      return sameGroups(current, next)
        ? 'This update would not change the user’s group membership.'
        : null;
    }
  }
}

function applyValidDirectoryAction(
  overlay: DirectoryUserOverlay,
  action: DirectorySimulationAction,
): DirectoryUserOverlay {
  switch (action.type) {
    case 'directory.inspect_account':
      return { ...overlay, inspected: true };
    case 'directory.verify_identity':
      return { ...overlay, identityVerified: true };
    case 'directory.test_primary_auth':
      return { ...overlay, primaryAuthTested: true };
    case 'directory.record_diagnosis':
      return { ...overlay, diagnosis: action.payload.diagnosis };
    case 'directory.verify_access':
      return { ...overlay, accessVerified: true };
    case 'directory.unlock_account':
      return { ...overlay, locked: false };
    case 'directory.reset_password':
      return { ...overlay, passwordState: 'temporary' };
    case 'directory.enable_account':
      return { ...overlay, disabled: false };
    case 'directory.disable_account':
      return { ...overlay, disabled: true };
    case 'directory.reset_mfa':
      return {
        ...overlay,
        mfaEnrolled: false,
        mfaFactorStatus: 'reset-ready',
      };
    case 'directory.update_groups': {
      const fixture = getDirectoryUserById(action.payload.directoryUserId);
      const next = nextGroupsForUpdate(overlay, action);
      const templateGroups = fixture?.groups ?? [];

      return {
        ...overlay,
        groupChanges: {
          added: next.filter((group) => !templateGroups.includes(group)),
          removed: templateGroups.filter((group) => !next.includes(group)),
        },
      };
    }
  }
}

function createChatThreadOverlay(): ChatThreadOverlay {
  return {
    messages: [],
    pinned: false,
    lastReadAt: null,
    events: [],
  };
}

const CHAT_REQUESTER_BY_TICKET: Readonly<Record<string, string>> = {
  INC2405: 'directory-user-sloane-rivera',
  INC2406: 'directory-user-harper-kim',
  INC2511: 'directory-user-taylor-morgan',
  INC2512: 'directory-user-jordan-lee',
  INC2513: 'directory-user-camille-reyes',
  INC3001: 'directory-user-morgan-ellis',
  INC3002: 'directory-user-hr-adebayo-coker',
};

function chatRejectReason(action: ChatSimulationAction): string | null {
  const contact = getDirectoryUserById(action.payload.contactId);
  if (!contact) {
    return 'The requested chat contact does not exist in this simulation.';
  }

  if (
    (action.type === 'chat.verify_identity' ||
      action.type === 'chat.request_resolution_confirmation') &&
    CHAT_REQUESTER_BY_TICKET[action.payload.ticketId] !==
      action.payload.contactId
  ) {
    return 'This contact is not the requester for that support workflow.';
  }
  if (
    action.type === 'chat.verify_identity' &&
    contact.availableIdentityVerificationMethods.length === 0
  ) {
    return 'This workflow does not require an identity-administration verification.';
  }
  if (
    action.type === 'chat.verify_identity' &&
    !contact.availableIdentityVerificationMethods.includes(
      action.payload.method,
    )
  ) {
    return 'That approved verification method is not available in this ticket context.';
  }

  if (action.type === 'chat.send_message') {
    if (action.payload.body.trim().length === 0) {
      return 'A chat message cannot be empty.';
    }
    if (action.payload.body.length > 500) {
      return 'A chat message cannot exceed 500 characters.';
    }
  }

  return null;
}

function applyValidChatAction(
  overlay: ChatThreadOverlay,
  action: ChatSimulationAction,
  attempt: Attempt,
  createdAt: string,
  eventId: string,
): ChatThreadOverlay {
  switch (action.type) {
    case 'chat.send_message': {
      const body = action.payload.body.trim();
      const reply = resolveScriptedChatReply(body);

      return {
        ...overlay,
        messages: [
          ...overlay.messages,
          {
            id: `${eventId}-student-message`,
            fromStudent: true,
            body,
            triggerKey: null,
            createdAt,
          },
          {
            id: `${eventId}-contact-reply`,
            fromStudent: false,
            body: reply.body,
            triggerKey: reply.triggerKey,
            createdAt,
          },
        ],
      };
    }
    case 'chat.verify_identity': {
      const methodLabels = {
        'employee-id-directory-match':
          'employee ID matched to the directory record',
        'manager-confirmation':
          'manager confirmation through the approved company channel',
        'known-number-callback': 'callback to the known company number',
      } as const;
      return {
        ...overlay,
        messages: [
          ...overlay.messages,
          {
            id: `${eventId}-student-message`,
            fromStudent: true,
            body: `Identity check requested: ${methodLabels[action.payload.method]}.`,
            triggerKey: null,
            createdAt,
          },
          {
            id: `${eventId}-contact-reply`,
            fromStudent: false,
            body: 'The approved training verification completed. No password, recovery code, security answer, or personal secret was collected.',
            triggerKey: 'identity-verification-approved',
            createdAt,
          },
        ],
      };
    }
    case 'chat.request_resolution_confirmation': {
      const accountUserByTicket: Readonly<Record<string, string>> = {
        INC2511: 'directory-user-taylor-morgan',
        INC2512: 'directory-user-jordan-lee',
        INC2513: 'directory-user-camille-reyes',
      };
      const directoryUserId = accountUserByTicket[action.payload.ticketId];
      const scenario = getRemoteDesktopScenarioByTicket(
        action.payload.ticketId,
      );
      const fixed = directoryUserId
        ? attempt.directoryOverlays[directoryUserId]?.accessVerified === true
        : scenario
          ? attempt.remoteDesktopOverlays[scenario.assetTag]?.scenarioProgress[
              scenario.id
            ]?.phases.verified === true
          : false;
      return {
        ...overlay,
        messages: [
          ...overlay.messages,
          {
            id: `${eventId}-student-message`,
            fromStudent: true,
            body: 'Please repeat the original task in a fresh session and confirm the exact symptom is gone.',
            triggerKey: null,
            createdAt,
          },
          {
            id: `${eventId}-contact-reply`,
            fromStudent: false,
            body: fixed
              ? 'I repeated the original task in a fresh session. It now works and I can continue.'
              : 'I tried the original task again, but I am still seeing the same problem.',
            triggerKey: fixed
              ? 'original-symptom-confirmed-fixed'
              : 'original-symptom-still-broken',
            createdAt,
          },
        ],
      };
    }
    case 'chat.mark_pinned':
      return { ...overlay, pinned: action.payload.pinned };
    case 'chat.open_thread':
      return { ...overlay, lastReadAt: createdAt };
  }
}

function directoryAsset(assetTag: string) {
  for (const user of DIRECTORY_USER_FIXTURES) {
    const device = user.devices.find(
      (candidate) => candidate.assetTag === assetTag,
    );

    if (device) {
      return { device, directoryUserId: user.id };
    }
  }

  return null;
}

function pcShelfAssetStatus(overlay: PcShelfOverlay) {
  if (overlay.deviceState === PcShelfDeviceState.Retired) {
    return AssetStatus.Retired;
  }

  return overlay.assignedDirectoryUserId
    ? AssetStatus.Deployed
    : AssetStatus.Repaired;
}

function createPcShelfOverlay(assetTag: string): PcShelfOverlay {
  const fixture = getPcShelfFixture(assetTag);

  return {
    assignedDirectoryUserId: null,
    deviceState: fixture?.deviceState ?? PcShelfDeviceState.OnShelf,
    networkStatus: fixture?.networkStatus ?? PcShelfNetworkStatus.Unregistered,
    present: false,
    events: [],
  };
}

function createAssetOverlay(attempt: Attempt, assetTag: string): AssetOverlay {
  const directoryRecord = directoryAsset(assetTag);

  if (directoryRecord) {
    return {
      assignedDirectoryUserId: directoryRecord.directoryUserId,
      status: directoryRecord.device.status,
      events: [],
    };
  }

  const pcShelfOverlay =
    attempt.pcShelfOverlays[assetTag] ?? createPcShelfOverlay(assetTag);

  return {
    assignedDirectoryUserId: pcShelfOverlay.assignedDirectoryUserId,
    status: pcShelfAssetStatus(pcShelfOverlay),
    events: [],
  };
}

function assetRejectReason(
  attempt: Attempt,
  overlay: AssetOverlay,
  action: AssetSimulationAction,
): string | null {
  const directoryRecord = directoryAsset(action.payload.assetTag);
  const shelfFixture = getPcShelfFixture(action.payload.assetTag);
  const shelfOverlay = attempt.pcShelfOverlays[action.payload.assetTag];

  if (!directoryRecord && !shelfFixture && !shelfOverlay?.device) {
    return 'The requested asset does not exist in this simulation.';
  }
  if (shelfFixture && !shelfOverlay?.present) {
    return 'This PC is not currently available on the shelf.';
  }

  switch (action.type) {
    case 'asset.assign': {
      const user = getDirectoryUserById(action.payload.directoryUserId);
      if (!user) {
        return 'The requested directory user does not exist in this simulation.';
      }
      if (overlay.assignedDirectoryUserId === action.payload.directoryUserId) {
        return `This asset is already assigned to ${user.fullName}.`;
      }
      if (overlay.assignedDirectoryUserId) {
        const currentOwner = getDirectoryUserById(
          overlay.assignedDirectoryUserId,
        );
        return `Unassign this asset from ${currentOwner?.fullName ?? 'its current owner'} before assigning it again.`;
      }
      return null;
    }
    case 'asset.unassign':
      return overlay.assignedDirectoryUserId
        ? null
        : 'This asset is already unassigned.';
    case 'asset.change_status':
      return overlay.status === action.payload.status
        ? `This asset is already marked ${action.payload.status}.`
        : null;
    case 'asset.record_isolation':
      if (action.payload.assetTag !== 'NX-9052') {
        return 'Hardware isolation checks are available only for the affected headset.';
      }
      return null;
  }
}

function applyValidAssetAction(
  overlay: AssetOverlay,
  action: AssetSimulationAction,
): AssetOverlay {
  switch (action.type) {
    case 'asset.assign':
      return {
        ...overlay,
        assignedDirectoryUserId: action.payload.directoryUserId,
        status: AssetStatus.Deployed,
      };
    case 'asset.unassign':
      return {
        ...overlay,
        assignedDirectoryUserId: null,
        status: AssetStatus.Repaired,
      };
    case 'asset.change_status':
      return { ...overlay, status: action.payload.status };
    case 'asset.record_isolation':
      return overlay;
  }
}

function syncPcShelfFromAssetAction(
  current: PcShelfOverlay,
  updatedAsset: AssetOverlay,
  action: AssetSimulationAction,
): PcShelfOverlay {
  if (action.type === 'asset.assign') {
    return {
      ...current,
      assignedDirectoryUserId: updatedAsset.assignedDirectoryUserId,
      deviceState: PcShelfDeviceState.Assigned,
    };
  }
  if (action.type === 'asset.unassign') {
    return {
      ...current,
      assignedDirectoryUserId: null,
      deviceState: PcShelfDeviceState.OnShelf,
    };
  }
  if (action.type === 'asset.record_isolation') {
    return current;
  }
  if (action.payload.status === AssetStatus.Retired) {
    return { ...current, deviceState: PcShelfDeviceState.Retired };
  }
  if (
    action.payload.status === AssetStatus.Deployed &&
    updatedAsset.assignedDirectoryUserId
  ) {
    return { ...current, deviceState: PcShelfDeviceState.Assigned };
  }
  return current;
}

function pcShelfRejectReason(
  overlay: PcShelfOverlay,
  action: PcShelfSimulationAction,
): string | null {
  if (!getPcShelfFixture(action.payload.assetTag) && !overlay.device) {
    return 'The requested PC is not in the shelf fixture catalog.';
  }

  if (action.type === 'pc_shelf.add') {
    return overlay.present ? 'This computer is already on the PC Shelf.' : null;
  }
  if (!overlay.present) {
    return 'This computer is not currently on the PC Shelf.';
  }

  switch (action.type) {
    case 'pc_shelf.remove':
      return overlay.assignedDirectoryUserId ||
        overlay.deviceState === PcShelfDeviceState.Assigned
        ? 'An assigned computer cannot be removed from the PC Shelf.'
        : null;
    case 'pc_shelf.change_network_status':
      return overlay.networkStatus === action.payload.networkStatus
        ? `This computer is already ${action.payload.networkStatus}.`
        : null;
    case 'pc_shelf.change_device_state':
      if (action.payload.deviceState === PcShelfDeviceState.Assigned) {
        return 'Use Assign to employee to move a computer into the assigned state.';
      }
      if (overlay.assignedDirectoryUserId) {
        return 'Unassign this computer before changing its shelf state.';
      }
      return overlay.deviceState === action.payload.deviceState
        ? `This computer is already ${action.payload.deviceState}.`
        : null;
    case 'pc_shelf.assign': {
      const user = getDirectoryUserById(action.payload.directoryUserId);
      if (!user) {
        return 'The requested directory user does not exist in this simulation.';
      }
      if (overlay.assignedDirectoryUserId === action.payload.directoryUserId) {
        return `This computer is already assigned to ${user.fullName}.`;
      }
      if (overlay.assignedDirectoryUserId) {
        return 'Unassign this computer before assigning it to another employee.';
      }
      if (overlay.deviceState === PcShelfDeviceState.Retired) {
        return 'A retired computer cannot be assigned to an employee.';
      }
      return null;
    }
    case 'pc_shelf.unassign':
      return overlay.assignedDirectoryUserId
        ? null
        : 'This computer is already unassigned.';
  }
}

function applyValidPcShelfAction(
  overlay: PcShelfOverlay,
  action: PcShelfSimulationAction,
): PcShelfOverlay {
  switch (action.type) {
    case 'pc_shelf.add': {
      const fixture = getPcShelfFixture(action.payload.assetTag);
      return {
        ...overlay,
        assignedDirectoryUserId: null,
        deviceState: fixture?.deviceState ?? PcShelfDeviceState.OnShelf,
        networkStatus: fixture?.networkStatus ?? overlay.networkStatus,
        present: true,
      };
    }
    case 'pc_shelf.remove':
      return { ...overlay, present: false };
    case 'pc_shelf.change_network_status':
      return { ...overlay, networkStatus: action.payload.networkStatus };
    case 'pc_shelf.change_device_state':
      return { ...overlay, deviceState: action.payload.deviceState };
    case 'pc_shelf.assign':
      return {
        ...overlay,
        assignedDirectoryUserId: action.payload.directoryUserId,
        deviceState: PcShelfDeviceState.Assigned,
      };
    case 'pc_shelf.unassign':
      return {
        ...overlay,
        assignedDirectoryUserId: null,
        deviceState: PcShelfDeviceState.OnShelf,
      };
  }
}

function createServerRoomOverlay(nodeId: string): ServerRoomOverlay {
  const fixture = getServerRoomNode(nodeId);

  return {
    status: fixture?.status ?? 'offline',
    serviceStates:
      fixture?.kind === 'server' ? { [fixture.serviceName]: 'running' } : {},
    events: [],
  };
}

function serverRoomRejectReason(
  action: ServerRoomSimulationAction,
): string | null {
  if (action.type === 'server_room.restart_device') {
    return getServerRoomDevice(action.payload.nodeId)
      ? null
      : 'The requested network device does not exist in this simulation.';
  }

  const server = getServerRoomServer(action.payload.nodeId);
  if (!server) {
    return 'The requested server does not exist in this simulation.';
  }

  if (
    action.type === 'server_room.restart_service' &&
    action.payload.serviceName !== server.serviceName
  ) {
    return `"${action.payload.serviceName}" is not a simulated service on ${server.name}.`;
  }

  return null;
}

function applyValidServerRoomAction(
  overlay: ServerRoomOverlay,
  action: ServerRoomSimulationAction,
): ServerRoomOverlay {
  switch (action.type) {
    case 'server_room.restart_device':
      return { ...overlay, status: 'online' };
    case 'server_room.restart_service':
      return {
        ...overlay,
        status: 'online',
        serviceStates: {
          ...overlay.serviceStates,
          [action.payload.serviceName]: 'running',
        },
      };
    case 'server_room.restart_server':
      return {
        ...overlay,
        status: 'online',
        serviceStates: Object.fromEntries(
          Object.keys(overlay.serviceStates).map((serviceName) => [
            serviceName,
            'running',
          ]),
        ),
      };
  }
}

function createRemoteDesktopOverlay(assetTag: string): RemoteDesktopOverlay {
  const fixture = getRemoteDesktopWorkstation(assetTag);

  return {
    workstation: fixture
      ? createWorkstationState(assetTag)
      : createUnavailableWorkstationState(assetTag),
    connectionState: 'disconnected',
    completedScenarioIds: [],
    dnsServers: [...getRemoteDesktopTerminalFixture(assetTag).dnsServers],
    driveStates: getRemoteDesktopInitialDriveStates(assetTag),
    explorerCurrentPath: 'This PC',
    explorerError: null,
    explorerLastRefreshedAt: null,
    focusedApp: null,
    lastError: null,
    minimizedApps: [],
    openApps: [],
    powerState: fixture?.powerState ?? 'offline',
    networkStatus: fixture?.networkStatus ?? 'offline',
    learningMode: 'guided',
    scenarioProgress: {},
    scenarioSteps: {},
    serviceStates: Object.fromEntries(
      fixture?.services.map((service) => [service.name, service.state]) ?? [],
    ),
    terminalHistory: [],
    trainingMode: true,
    updateInstalledAt: null,
    updateState: fixture?.pendingUpdate ? 'pending' : 'applied',
    vpnError: null,
    vpnLog: [],
    vpnStatus: 'disconnected',
    events: [],
  };
}

function canonicalExplorerPath(assetTag: string, requestedPath: string) {
  const normalized = requestedPath.trim().replace(/\//g, '\\');
  if (normalized.toLowerCase() === 'this pc') return 'This PC';
  const workstation = getRemoteDesktopWorkstation(assetTag);
  const paths =
    workstation?.drives.flatMap((drive) => [
      drive.rootPath,
      ...drive.entries.map((entry) => entry.path),
    ]) ?? [];
  return (
    paths.find((path) => path.toLowerCase() === normalized.toLowerCase()) ??
    null
  );
}

function explorerDriveForPath(assetTag: string, path: string) {
  if (path === 'This PC') return null;
  const driveLetter = path.slice(0, 2).toUpperCase();
  return (
    getRemoteDesktopWorkstation(assetTag)?.drives.find(
      (drive) => drive.letter.toUpperCase() === driveLetter,
    ) ?? null
  );
}

function explorerErrorForPath(
  assetTag: string,
  path: string,
  overlay: RemoteDesktopOverlay,
): RemoteDesktopOverlay['explorerError'] {
  const drive = explorerDriveForPath(assetTag, path);
  if (!drive || drive.kind === 'local') return null;
  const status = overlay.driveStates[drive.letter] ?? drive.initialStatus;

  if (status === 'permission-error') {
    return {
      kind: 'permission-error',
      message: `Access denied. You don't have permission to access ${drive.label}. Contact the share owner if access is required.`,
      path,
    };
  }
  if (status === 'disconnected' || status === 'network-path-error') {
    return {
      kind: 'network-path-error',
      message: `Network path unavailable. Windows can't reach ${drive.sharePath ?? drive.label}. Check the VPN or drive connection and try again.`,
      path,
    };
  }
  return null;
}

function createRemoteDesktopScenarioProgress(): RemoteDesktopScenarioProgress {
  return {
    investigationEvidence: [],
    diagnosisEvidence: [],
    fixEvidence: [],
    verificationEvidence: [],
    internalNote: null,
    phases: {
      investigated: false,
      diagnosed: false,
      fixed: false,
      verified: false,
      noted: false,
      closed: false,
    },
    finalScore: null,
    feedback: null,
  };
}

function sameStringArray(left: readonly string[], right: readonly string[]) {
  return (
    left.length === right.length &&
    left.every((value, index) => value === right[index])
  );
}

function workflowFinalStateSatisfied(
  scenario: RemoteDesktopScenarioFixture,
  overlay: RemoteDesktopOverlay,
) {
  const finalState = scenario.workflow?.finalState;
  if (!finalState) return false;
  if (
    finalState.dnsServers &&
    !sameStringArray(overlay.dnsServers, finalState.dnsServers)
  ) {
    return false;
  }
  if (finalState.vpnStatus && overlay.vpnStatus !== finalState.vpnStatus) {
    return false;
  }
  if (
    finalState.driveStates &&
    Object.entries(finalState.driveStates).some(
      ([drive, status]) => overlay.driveStates[drive] !== status,
    )
  ) {
    return false;
  }
  if (
    finalState.serviceStates &&
    Object.entries(finalState.serviceStates).some(
      ([service, state]) => overlay.serviceStates[service] !== state,
    )
  ) {
    return false;
  }
  return true;
}

function objectivesSatisfied(
  objectives: readonly { anyOf: readonly string[] }[],
  evidence: readonly string[],
) {
  return objectives.every((objective) =>
    objective.anyOf.some((key) => evidence.includes(key)),
  );
}

function workflowScore(
  scenario: RemoteDesktopScenarioFixture,
  progress: RemoteDesktopScenarioProgress,
) {
  const weights = scenario.workflow?.scoring;
  if (!weights) return 0;
  return (
    (progress.phases.investigated ? weights.investigation : 0) +
    (progress.phases.diagnosed ? weights.diagnosis : 0) +
    (progress.phases.fixed ? weights.remediation : 0) +
    (progress.phases.verified ? weights.verification : 0) +
    (progress.phases.noted ? weights.documentation : 0)
  );
}

function addEvidence(
  evidence: readonly string[],
  key: string | null,
): readonly string[] {
  return key && !evidence.includes(key) ? [...evidence, key] : evidence;
}

function terminalWorkflowEvidence(
  scenario: RemoteDesktopScenarioFixture,
  command: string,
  before: RemoteDesktopOverlay,
  after: RemoteDesktopOverlay,
) {
  const normalized = command.trim().replace(/\s+/g, ' ').toLowerCase();
  const target = command.trim().split(/\s+/).slice(1).join(' ');
  const isIpTarget = /^\d{1,3}(?:\.\d{1,3}){3}$/.test(target);
  const dnsFinal = scenario.workflow?.finalState.dnsServers;
  const dnsBroken = dnsFinal
    ? !sameStringArray(before.dnsServers, dnsFinal)
    : before.networkStatus !== 'online';

  if (normalized === 'ipconfig') return 'terminal.ipconfig';
  if (normalized === 'ipconfig /all') return 'terminal.ipconfig-all';
  if (
    normalized === 'net use' &&
    scenario.id === 'facilities-calendar-mapping'
  ) {
    return 'explorer.mapping-obsolete';
  }
  if (normalized.startsWith('ping ')) {
    if (isIpTarget) return 'terminal.ping-ip-success';
    if (scenario.id === 'vpn-shared-drive') {
      return before.vpnStatus === 'connected'
        ? 'terminal.ping-hostname-success'
        : 'terminal.ping-hostname-failed';
    }
    return dnsBroken
      ? 'terminal.ping-hostname-failed'
      : 'terminal.ping-hostname-success';
  }
  if (normalized.startsWith('nslookup ')) {
    return dnsBroken ? 'terminal.nslookup-failed' : 'terminal.nslookup-success';
  }
  if (normalized === 'tasklist' && scenario.id === 'service-failure') {
    return before.serviceStates['Print Spooler'] === 'stopped'
      ? 'terminal.tasklist-service-missing'
      : null;
  }
  if (
    normalized.startsWith('sc query ') &&
    normalized.includes('print spooler') &&
    scenario.id === 'service-failure'
  ) {
    return before.serviceStates['Print Spooler'] === 'stopped'
      ? 'terminal.service-stopped'
      : null;
  }
  if (
    normalized.startsWith('net start ') &&
    normalized.includes('print spooler') &&
    after.serviceStates['Print Spooler'] === 'running'
  ) {
    return 'service.print-spooler-running';
  }
  return null;
}

export function workflowEvidenceForAction(
  scenario: RemoteDesktopScenarioFixture,
  action: RemoteDesktopSimulationAction,
  before: RemoteDesktopOverlay,
  after: RemoteDesktopOverlay,
) {
  if (action.type === 'remote_desktop.open_app') {
    if (
      scenario.id === 'pdf-export-update' &&
      action.payload.appId === 'updates' &&
      before.updateState === 'pending'
    ) {
      return 'updates.pending-inspected';
    }
    if (
      scenario.id === 'vpn-shared-drive' &&
      action.payload.appId === 'vpn' &&
      before.vpnStatus !== 'connected'
    ) {
      return 'vpn.state-inspected';
    }
    if (
      scenario.id === 'service-failure' &&
      action.payload.appId === 'services' &&
      before.serviceStates['Print Spooler'] === 'stopped'
    ) {
      return 'services.state-inspected';
    }
  }
  if (action.type === 'remote_desktop.run_terminal_command') {
    return terminalWorkflowEvidence(
      scenario,
      action.payload.command,
      before,
      after,
    );
  }
  if (
    action.type === 'remote_desktop.explorer_navigate' ||
    action.type === 'remote_desktop.explorer_refresh'
  ) {
    const drive = explorerDriveForPath(
      action.payload.assetTag,
      after.explorerCurrentPath,
    );
    if (scenario.id === 'vpn-shared-drive' && drive?.kind === 'network') {
      return after.explorerError
        ? 'explorer.share-unreachable'
        : 'explorer.share-reachable';
    }
    if (
      scenario.id === 'facilities-calendar-mapping' &&
      drive?.kind === 'network' &&
      !after.explorerError &&
      after.scenarioSteps[scenario.id]?.includes('explorer.repair-mapping')
    ) {
      return 'explorer.verify-share';
    }
    if (
      scenario.id === 'pdf-export-update' &&
      (after.explorerCurrentPath === 'This PC' || drive?.kind === 'local')
    ) {
      return 'explorer.check-free-space';
    }
  }
  if (
    action.type === 'remote_desktop.vpn_complete_connection' &&
    scenario.id === 'vpn-shared-drive' &&
    after.vpnStatus === 'connected'
  ) {
    return 'vpn.connected';
  }
  if (
    action.type === 'remote_desktop.map_drive' &&
    scenario.id === 'facilities-calendar-mapping' &&
    action.payload.letter.trim().toUpperCase() === 'Y:' &&
    action.payload.uncPath.trim().toLowerCase() ===
      '\\\\facilities.nexus.internal\\calendar'
  ) {
    return 'explorer.repair-mapping';
  }
  if (
    action.type === 'remote_desktop.update_restart' &&
    scenario.id === 'pdf-export-update' &&
    after.updateState === 'applied'
  ) {
    return 'updates.applied';
  }
  if (
    action.type === 'remote_desktop.settings_update_dns' &&
    scenario.id === 'dns-configuration-failure' &&
    workflowFinalStateSatisfied(scenario, after)
  ) {
    return 'settings.dns-corrected';
  }
  if (
    (action.type === 'remote_desktop.start_service' ||
      action.type === 'remote_desktop.restart_service') &&
    scenario.id === 'service-failure' &&
    action.payload.serviceName === 'Print Spooler' &&
    after.serviceStates['Print Spooler'] === 'running'
  ) {
    return 'service.print-spooler-running';
  }
  if (
    action.type === 'remote_desktop.perform_scenario_step' &&
    scenario.id === 'service-failure' &&
    action.payload.stepId === 'printer.test-page'
  ) {
    return before.serviceStates['Print Spooler'] === 'running'
      ? 'printer.test-succeeded'
      : 'printer.test-failed';
  }
  if (action.type === 'remote_desktop.perform_scenario_step') {
    if (action.payload.stepId === 'browser.retry-sign-in') {
      return before.scenarioSteps[scenario.id]?.includes(
        'settings.clear-profile-storage',
      )
        ? 'browser.sign-in-restored'
        : 'browser.sign-in-loop-confirmed';
    }
    if (action.payload.stepId === 'browser.retry-export') {
      return before.updateState === 'applied' &&
        before.scenarioSteps[scenario.id]?.includes('system.restart-pdf-helper')
        ? 'browser.export-succeeded'
        : 'browser.export-failed';
    }
    if (action.payload.stepId === 'explorer.repair-mapping') {
      return 'explorer.repair-mapping';
    }
    if (action.payload.stepId === 'explorer.verify-share') {
      return 'explorer.verify-share';
    }
    if (action.payload.stepId === 'settings.repair-network') {
      return 'settings.repair-network';
    }
    if (action.payload.stepId === 'system.renew-address') {
      return 'system.renew-address';
    }
    if (action.payload.stepId === 'chat.confirm-restored') {
      return 'chat.confirm-restored';
    }
    if (action.payload.stepId === 'mail.review-alert') {
      return 'mail.review-alert';
    }
    if (action.payload.stepId === 'settings.clear-profile-storage') {
      return 'settings.clear-profile-storage';
    }
    if (action.payload.stepId === 'system.restart-pdf-helper') {
      return 'system.restart-pdf-helper';
    }
    // Converted legacy cases use named, scenario-specific controls. The
    // control is accepted only when it belongs to the active fixture; the
    // server independently authorizes the resulting evidence for its ticket.
    if (scenario.actionLabels[action.payload.stepId]) {
      return action.payload.stepId;
    }
  }
  return null;
}

/**
 * Convert UI-reachable workflow evidence into the matching trusted server
 * action.  This keeps scenario-step events as an audit record of a real
 * simulator transition instead of exposing a second "complete" control.
 */
export function derivedRemoteDesktopWorkflowAction(
  action: RemoteDesktopSimulationAction,
  before: RemoteDesktopOverlay,
  after: RemoteDesktopOverlay,
): RemoteDesktopSimulationAction | null {
  if (
    action.type !== 'remote_desktop.explorer_navigate' &&
    action.type !== 'remote_desktop.explorer_refresh'
  ) {
    return null;
  }
  const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
  if (!scenario?.serverEvidenceSteps?.length) return null;
  const stepId = workflowEvidenceForAction(scenario, action, before, after);
  if (!stepId || !scenario.serverEvidenceSteps.includes(stepId)) return null;
  return {
    type: 'remote_desktop.perform_scenario_step',
    payload: {
      assetTag: scenario.assetTag,
      ticketId: scenario.ticketId,
      stepId,
    },
  };
}

function recordRemoteDesktopWorkflowProgress(
  before: RemoteDesktopOverlay,
  after: RemoteDesktopOverlay,
  action: RemoteDesktopSimulationAction,
) {
  const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
  if (!scenario?.workflow) return after;
  const current =
    before.scenarioProgress[scenario.id] ??
    createRemoteDesktopScenarioProgress();
  const key = workflowEvidenceForAction(scenario, action, before, after);
  const investigationKey = scenario.workflow.investigate.some((objective) =>
    objective.anyOf.includes(key ?? ''),
  )
    ? key
    : null;
  const diagnosisKey = scenario.workflow.diagnose.some((objective) =>
    objective.anyOf.includes(key ?? ''),
  )
    ? key
    : null;
  const fixKey = scenario.workflow.fix.some((objective) =>
    objective.anyOf.includes(key ?? ''),
  )
    ? key
    : null;
  const verificationKey = scenario.workflow.verify.some((objective) =>
    objective.anyOf.includes(key ?? ''),
  )
    ? key
    : null;
  const diagnosisEvidence = addEvidence(
    current.diagnosisEvidence,
    diagnosisKey,
  );
  const investigationEvidence = addEvidence(
    current.investigationEvidence,
    investigationKey,
  );
  const fixEvidence = addEvidence(current.fixEvidence, fixKey);
  const verificationEvidence = addEvidence(
    current.verificationEvidence,
    verificationKey,
  );
  const internalNote =
    action.type === 'remote_desktop.add_internal_note'
      ? action.payload.text.trim()
      : current.internalNote;
  const progress: RemoteDesktopScenarioProgress = {
    ...current,
    investigationEvidence,
    diagnosisEvidence,
    fixEvidence,
    verificationEvidence,
    internalNote,
    phases: {
      ...current.phases,
      investigated: objectivesSatisfied(
        scenario.workflow.investigate,
        investigationEvidence,
      ),
      diagnosed: objectivesSatisfied(
        scenario.workflow.diagnose,
        diagnosisEvidence,
      ),
      fixed:
        objectivesSatisfied(scenario.workflow.fix, fixEvidence) &&
        workflowFinalStateSatisfied(scenario, after),
      verified: objectivesSatisfied(
        scenario.workflow.verify,
        verificationEvidence,
      ),
      noted:
        (internalNote?.length ?? 0) >= scenario.workflow.note.minimumLength,
    },
  };
  return {
    ...after,
    scenarioProgress: {
      ...after.scenarioProgress,
      [scenario.id]: progress,
    },
  };
}

function applyRemoteDesktopScenarioStep(
  overlay: RemoteDesktopOverlay,
  assetTag: string,
  stepId: string,
): RemoteDesktopOverlay {
  const scenario = getRemoteDesktopScenarioByAsset(assetTag);
  if (!scenario) return overlay;
  const completed = overlay.scenarioSteps[scenario.id] ?? [];
  const repeatable =
    stepId === 'browser.retry-sign-in' || stepId === 'browser.retry-export';
  if (completed.includes(stepId) && !repeatable) return overlay;
  const nextSteps = completed.includes(stepId)
    ? completed
    : [...completed, stepId];
  const networkDrive = getRemoteDesktopWorkstation(assetTag)?.drives.find(
    (drive) => drive.kind === 'network',
  );
  if (scenario.workflow) {
    return stepId === 'printer.test-page'
      ? overlay
      : {
          ...overlay,
          driveStates:
            scenario.id === 'facilities-calendar-mapping' &&
            stepId === 'explorer.repair-mapping' &&
            networkDrive
              ? {
                  ...overlay.driveStates,
                  [networkDrive.letter]: 'connected' as const,
                }
              : overlay.driveStates,
          scenarioSteps: { ...overlay.scenarioSteps, [scenario.id]: nextSteps },
          networkStatus:
            stepId === 'settings.repair-network'
              ? ('online' as const)
              : overlay.networkStatus,
        };
  }
  const requiredComplete = scenario.requiredSteps.every((step) =>
    nextSteps.includes(step),
  );
  const connectsDrive =
    (scenario.id === 'vpn-shared-drive' && stepId === 'vpn.connect') ||
    (scenario.id === 'facilities-calendar-mapping' &&
      stepId === 'explorer.repair-mapping');

  return {
    ...overlay,
    completedScenarioIds:
      requiredComplete && !overlay.completedScenarioIds.includes(scenario.id)
        ? [...overlay.completedScenarioIds, scenario.id]
        : overlay.completedScenarioIds,
    driveStates:
      connectsDrive && networkDrive
        ? {
            ...overlay.driveStates,
            [networkDrive.letter]: 'connected' as const,
          }
        : overlay.driveStates,
    scenarioSteps: { ...overlay.scenarioSteps, [scenario.id]: nextSteps },
    networkStatus:
      stepId === 'settings.repair-network'
        ? ('online' as const)
        : overlay.networkStatus,
  };
}

function recordExplorerVerification(
  overlay: RemoteDesktopOverlay,
  assetTag: string,
  path: string,
) {
  const drive = explorerDriveForPath(assetTag, path);
  const scenario = getRemoteDesktopScenarioByAsset(assetTag);
  if (!scenario) return overlay;
  if (
    scenario.id === 'pdf-export-update' &&
    (path === 'This PC' || drive?.kind === 'local')
  ) {
    return applyRemoteDesktopScenarioStep(
      overlay,
      assetTag,
      'explorer.check-free-space',
    );
  }
  if (!drive || drive.kind !== 'network') return overlay;
  const completed = overlay.scenarioSteps[scenario.id] ?? [];
  const requiredCompleted = completed.filter((step) =>
    scenario.requiredSteps.includes(step),
  );
  return scenario.requiredSteps[requiredCompleted.length] ===
    'explorer.verify-share'
    ? applyRemoteDesktopScenarioStep(overlay, assetTag, 'explorer.verify-share')
    : overlay;
}

function remoteDesktopRejectReason(
  action: RemoteDesktopSimulationAction,
  overlay: RemoteDesktopOverlay,
): string | null {
  const workstation = getRemoteDesktopWorkstation(action.payload.assetTag);
  if (!workstation) {
    return 'The requested workstation does not exist in this simulation.';
  }

  if (
    (action.type === 'remote_desktop.restart_service' ||
      action.type === 'remote_desktop.start_service' ||
      action.type === 'remote_desktop.stop_service') &&
    !workstation.services.some(
      (service) => service.name === action.payload.serviceName,
    )
  ) {
    return `"${action.payload.serviceName}" is not a simulated service on ${workstation.assetTag}.`;
  }

  switch (action.type) {
    case 'remote_desktop.connect':
      return overlay.connectionState === 'disconnected' ||
        overlay.connectionState === 'error'
        ? null
        : 'Disconnect or cancel the current remote session before connecting again.';
    case 'remote_desktop.begin_login':
      return overlay.connectionState === 'connecting' ||
        overlay.connectionState === 'error'
        ? null
        : 'The connection is no longer waiting for a login prompt.';
    case 'remote_desktop.authenticate': {
      if (overlay.connectionState !== 'login') {
        return 'Open a Remote Login prompt before submitting credentials.';
      }
      if (!action.payload.usernameEntered || !action.payload.passwordEntered) {
        return 'Enter both simulated administrator fields before continuing.';
      }
      const scenario = getRemoteDesktopScenarioByTicket(
        action.payload.ticketId,
      );
      return scenario && scenario.assetTag !== action.payload.assetTag
        ? 'This is not the affected machine for the selected ticket. Disconnect and choose the reporter’s computer.'
        : null;
    }
    case 'remote_desktop.cancel_connection':
      return overlay.connectionState === 'connecting' ||
        overlay.connectionState === 'login' ||
        overlay.connectionState === 'error'
        ? null
        : 'There is no pending connection to cancel.';
    case 'remote_desktop.disconnect':
      return overlay.connectionState === 'connected' ||
        overlay.connectionState === 'error'
        ? null
        : 'There is no active remote session to disconnect.';
    case 'remote_desktop.open_app':
    case 'remote_desktop.close_app':
    case 'remote_desktop.focus_app':
    case 'remote_desktop.minimize_app':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before opening desktop applications.';
      }
      return REMOTE_DESKTOP_APP_IDS.includes(action.payload.appId)
        ? null
        : 'That application is not available on this simulated desktop.';
    case 'remote_desktop.move_window': {
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before moving desktop windows.';
      }
      const windowState =
        overlay.workstation.desktop.windows[action.payload.appId];
      if (!windowState?.open)
        return 'Open the application before moving its window.';
      const { x, y, width, height } = action.payload.bounds;
      return [x, y, width, height].every(Number.isFinite) &&
        x >= 0 &&
        y >= 0 &&
        x <= 1920 &&
        y <= 1080 &&
        width >= 320 &&
        width <= 1600 &&
        height >= 240 &&
        height <= 1000
        ? null
        : 'Keep the window within the simulated desktop and use a supported size.';
    }
    case 'remote_desktop.toggle_window_maximize':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before changing desktop windows.';
      }
      return overlay.workstation.desktop.windows[action.payload.appId]?.open
        ? null
        : 'Open the application before maximizing its window.';
    case 'remote_desktop.set_start_menu':
      return overlay.connectionState === 'connected'
        ? null
        : 'Connect to the simulated computer before opening Start.';
    case 'remote_desktop.toggle_training_mode':
      return null;
    case 'remote_desktop.set_learning_mode':
      return REMOTE_DESKTOP_LEARNING_MODES.includes(action.payload.mode)
        ? null
        : 'Choose Guided, Practice, or Assessment mode.';
    case 'remote_desktop.add_internal_note': {
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the affected computer before adding an internal note.';
      }
      const scenario = getRemoteDesktopScenarioByTicket(
        action.payload.ticketId,
      );
      if (
        !scenario?.workflow ||
        scenario.assetTag !== action.payload.assetTag
      ) {
        return 'This internal note does not apply to the selected machine and ticket.';
      }
      const length = action.payload.text.trim().length;
      if (length < scenario.workflow.note.minimumLength) {
        return `Write at least ${scenario.workflow.note.minimumLength} characters describing the diagnosis, repair, and verification.`;
      }
      if (length > 1000) {
        return 'An internal note cannot exceed 1,000 characters.';
      }
      return isMeaningfulInternalNote(action.payload.text)
        ? null
        : 'Document the diagnosis, repair, and verification in meaningful student-authored language.';
    }
    case 'remote_desktop.perform_scenario_step': {
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the affected computer before performing a troubleshooting action.';
      }
      const scenario = getRemoteDesktopScenarioByTicket(
        action.payload.ticketId,
      );
      if (!scenario || scenario.assetTag !== action.payload.assetTag) {
        return 'This action does not apply to the selected machine and ticket.';
      }
      if (scenario.workflow) {
        if (scenario.incorrectSteps.includes(action.payload.stepId)) {
          return 'That action does not address the reported issue. Review the affected service before changing the computer.';
        }
        if (
          action.payload.stepId === 'printer.test-page' ||
          scenario.actionLabels[action.payload.stepId]
        ) {
          return null;
        }
        return 'That troubleshooting action is not available for this workflow.';
      }
      const completed = overlay.scenarioSteps[scenario.id] ?? [];
      if (completed.includes(action.payload.stepId)) {
        return 'That troubleshooting action is already recorded.';
      }
      if (scenario.incorrectSteps.includes(action.payload.stepId)) {
        return 'That action does not address the reported issue. Review the affected service before changing the computer.';
      }
      if (scenario.optionalSteps.includes(action.payload.stepId)) {
        return null;
      }
      const expected =
        scenario.requiredSteps[
          completed.filter((step) => scenario.requiredSteps.includes(step))
            .length
        ];
      return expected === action.payload.stepId
        ? null
        : `Complete “${expected ?? 'the remaining required step'}” before attempting another repair.`;
    }
    case 'remote_desktop.run_terminal_command':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before running Terminal commands.';
      }
      return action.payload.command.length <=
        WORKSTATION_TERMINAL_COMMAND_MAX_LENGTH
        ? null
        : `Terminal commands cannot exceed ${WORKSTATION_TERMINAL_COMMAND_MAX_LENGTH} characters.`;
    case 'remote_desktop.explorer_navigate':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before navigating File Explorer.';
      }
      return canonicalExplorerPath(action.payload.assetTag, action.payload.path)
        ? null
        : 'That location is not available in this simulated file system.';
    case 'remote_desktop.explorer_refresh':
      return overlay.connectionState === 'connected'
        ? null
        : 'Connect to the simulated computer before refreshing File Explorer.';
    case 'remote_desktop.map_drive': {
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before mapping a drive.';
      }
      const letter = action.payload.letter.trim().toUpperCase();
      if (!/^[D-Z]:$/.test(letter)) {
        return 'Choose an available drive letter from D: through Z:.';
      }
      if (
        action.payload.credentialTarget &&
        !overlay.workstation.credentials[
          action.payload.credentialTarget.trim().toLowerCase()
        ]
      ) {
        return 'The selected stored credential does not exist.';
      }
      const mapping = mapWorkstationDrive(
        overlay.workstation,
        letter,
        action.payload.uncPath.trim(),
        action.payload.reconnectAtSignIn,
      );
      return mapping.success ? null : mapping.output.join(' ');
    }
    case 'remote_desktop.credential_add':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before managing credentials.';
      }
      return addWorkstationCredential(
        overlay.workstation,
        action.payload.target,
        action.payload.username,
        '1970-01-01T00:00:00.000Z',
      ).error;
    case 'remote_desktop.credential_delete':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before managing credentials.';
      }
      return deleteWorkstationCredential(
        overlay.workstation,
        action.payload.target,
      ).error;
    case 'remote_desktop.explorer_reconnect_drive': {
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before reconnecting a drive.';
      }
      const driveLetter = action.payload.driveLetter.trim().toUpperCase();
      const drive = workstation.drives.find(
        (candidate) => candidate.letter.toUpperCase() === driveLetter,
      );
      if (!drive) return 'That drive is not available on this workstation.';
      if (drive.kind !== 'network') return 'Local disks cannot be reconnected.';
      const status = overlay.driveStates[drive.letter] ?? drive.initialStatus;
      if (status === 'connected')
        return 'This network drive is already connected.';
      if (status === 'permission-error') {
        return `Access denied. Reconnecting cannot grant permission to ${drive.label}.`;
      }
      if (
        status === 'network-path-error' &&
        overlay.vpnStatus !== 'connected'
      ) {
        return `Network path unavailable. Connect the required VPN or network before reconnecting ${drive.label}.`;
      }
      return null;
    }
    case 'remote_desktop.vpn_connect':
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before opening a VPN session.';
      }
      if (!overlay.workstation.network.vpn.selectedProfileId) {
        return 'No VPN profile is configured on this workstation.';
      }
      return overlay.vpnStatus === 'disconnected' ||
        overlay.vpnStatus === 'error'
        ? null
        : 'The VPN client is already connected or connecting.';
    case 'remote_desktop.vpn_complete_connection': {
      if (overlay.vpnStatus !== 'connecting') {
        return 'The VPN client is not waiting for a connection result.';
      }
      if (overlay.networkStatus === 'offline') {
        return 'The VPN gateway could not be reached because this device has no network connection.';
      }
      const profileId = overlay.workstation.network.vpn.selectedProfileId;
      const profile = profileId
        ? overlay.workstation.network.vpn.profiles[profileId]
        : undefined;
      if (!profile) return 'No VPN profile is configured on this workstation.';
      return profile.requiredCompliance !==
        overlay.workstation.machine.compliance
        ? 'The VPN connection was blocked because the device compliance check failed.'
        : null;
    }
    case 'remote_desktop.vpn_disconnect':
      return overlay.vpnStatus === 'connected' || overlay.vpnStatus === 'error'
        ? null
        : 'There is no active VPN connection to disconnect.';
    case 'remote_desktop.settings_update_dns': {
      if (overlay.connectionState !== 'connected') {
        return 'Connect to the simulated computer before changing DNS settings.';
      }
      const isIpv4 = (value: string) => {
        const parts = value.trim().split('.');
        return (
          parts.length === 4 &&
          parts.every(
            (part) =>
              /^\d{1,3}$/.test(part) &&
              Number(part) >= 0 &&
              Number(part) <= 255,
          )
        );
      };
      if (!isIpv4(action.payload.primaryDns)) {
        return 'Enter a valid IPv4 address for the primary DNS server.';
      }
      if (
        action.payload.secondaryDns.trim() &&
        !isIpv4(action.payload.secondaryDns)
      ) {
        return 'Enter a valid IPv4 address for the secondary DNS server.';
      }
      const next = [
        action.payload.primaryDns.trim(),
        action.payload.secondaryDns.trim(),
      ].filter(Boolean);
      return next.length === overlay.dnsServers.length &&
        next.every((server, index) => server === overlay.dnsServers[index])
        ? 'These DNS server addresses are already configured.'
        : null;
    }
    case 'remote_desktop.start_service':
      return overlay.serviceStates[action.payload.serviceName] === 'running'
        ? `${action.payload.serviceName} is already running.`
        : null;
    case 'remote_desktop.stop_service':
      return overlay.serviceStates[action.payload.serviceName] === 'stopped'
        ? `${action.payload.serviceName} is already stopped.`
        : null;
    case 'remote_desktop.update_install':
      return overlay.updateState === 'pending'
        ? null
        : 'There is no pending update ready to install.';
    case 'remote_desktop.update_complete_install':
      return overlay.updateState === 'installing'
        ? null
        : 'Start the pending update before completing installation.';
    case 'remote_desktop.update_restart':
      return overlay.updateState === 'restart-required'
        ? null
        : 'A restart is not currently required for this update.';
    case 'remote_desktop.restart_computer':
    case 'remote_desktop.network_reset':
    case 'remote_desktop.restart_service':
      return null;
  }

  return null;
}

function applyValidRemoteDesktopAction(
  overlay: RemoteDesktopOverlay,
  action: RemoteDesktopSimulationAction,
  createdAt: string,
): RemoteDesktopOverlay {
  switch (action.type) {
    case 'remote_desktop.restart_computer':
      return { ...overlay, powerState: 'online' };
    case 'remote_desktop.network_reset':
      return { ...overlay, networkStatus: 'online' };
    case 'remote_desktop.restart_service':
      return {
        ...overlay,
        serviceStates: {
          ...overlay.serviceStates,
          [action.payload.serviceName]: 'running',
        },
      };
    case 'remote_desktop.start_service':
      return {
        ...overlay,
        serviceStates: {
          ...overlay.serviceStates,
          [action.payload.serviceName]: 'running',
        },
      };
    case 'remote_desktop.stop_service':
      return {
        ...overlay,
        serviceStates: {
          ...overlay.serviceStates,
          [action.payload.serviceName]: 'stopped',
        },
      };
    case 'remote_desktop.connect':
      return { ...overlay, connectionState: 'connecting', lastError: null };
    case 'remote_desktop.begin_login':
      return { ...overlay, connectionState: 'login', lastError: null };
    case 'remote_desktop.authenticate':
      return { ...overlay, connectionState: 'connected', lastError: null };
    case 'remote_desktop.cancel_connection':
    case 'remote_desktop.disconnect':
      return {
        ...overlay,
        workstation: setWorkstationStartMenu(overlay.workstation, false),
        connectionState: 'disconnected',
        focusedApp: null,
        lastError: null,
        minimizedApps: [],
        openApps: [],
      };
    case 'remote_desktop.open_app': {
      const openApps = overlay.openApps.includes(action.payload.appId)
        ? overlay.openApps
        : [...overlay.openApps, action.payload.appId];
      return {
        ...overlay,
        focusedApp: action.payload.appId,
        minimizedApps: overlay.minimizedApps.filter(
          (appId) => appId !== action.payload.appId,
        ),
        openApps,
        workstation: openWorkstationWindow(
          overlay.workstation,
          action.payload.appId,
        ),
      };
    }
    case 'remote_desktop.close_app': {
      const openApps = overlay.openApps.filter(
        (appId) => appId !== action.payload.appId,
      );
      return {
        ...overlay,
        focusedApp:
          overlay.focusedApp === action.payload.appId
            ? null
            : overlay.focusedApp,
        minimizedApps: overlay.minimizedApps.filter(
          (appId) => appId !== action.payload.appId,
        ),
        openApps,
        workstation: closeWorkstationWindow(
          overlay.workstation,
          action.payload.appId,
        ),
      };
    }
    case 'remote_desktop.focus_app':
      return {
        ...overlay,
        focusedApp: action.payload.appId,
        minimizedApps: overlay.minimizedApps.filter(
          (appId) => appId !== action.payload.appId,
        ),
        openApps: overlay.openApps.includes(action.payload.appId)
          ? overlay.openApps
          : [...overlay.openApps, action.payload.appId],
        workstation: focusWorkstationWindow(
          overlay.workstation,
          action.payload.appId,
        ),
      };
    case 'remote_desktop.minimize_app':
      return {
        ...overlay,
        focusedApp:
          overlay.focusedApp === action.payload.appId
            ? null
            : overlay.focusedApp,
        minimizedApps: overlay.minimizedApps.includes(action.payload.appId)
          ? overlay.minimizedApps
          : [...overlay.minimizedApps, action.payload.appId],
        workstation: minimizeWorkstationWindow(
          overlay.workstation,
          action.payload.appId,
        ),
      };
    case 'remote_desktop.move_window':
      return {
        ...overlay,
        workstation: moveWorkstationWindow(
          overlay.workstation,
          action.payload.appId,
          action.payload.bounds,
        ),
      };
    case 'remote_desktop.toggle_window_maximize':
      return {
        ...overlay,
        focusedApp: action.payload.appId,
        minimizedApps: overlay.minimizedApps.filter(
          (appId) => appId !== action.payload.appId,
        ),
        workstation: toggleWorkstationWindowMaximize(
          overlay.workstation,
          action.payload.appId,
        ),
      };
    case 'remote_desktop.set_start_menu':
      return {
        ...overlay,
        workstation: setWorkstationStartMenu(
          overlay.workstation,
          action.payload.open,
        ),
      };
    case 'remote_desktop.toggle_training_mode':
      return {
        ...overlay,
        learningMode: action.payload.enabled ? 'guided' : 'practice',
        trainingMode: action.payload.enabled,
      };
    case 'remote_desktop.set_learning_mode':
      return {
        ...overlay,
        learningMode: action.payload.mode,
        trainingMode: action.payload.mode === 'guided',
      };
    case 'remote_desktop.add_internal_note':
      return overlay;
    case 'remote_desktop.perform_scenario_step': {
      return applyRemoteDesktopScenarioStep(
        overlay,
        action.payload.assetTag,
        action.payload.stepId,
      );
    }
    case 'remote_desktop.run_terminal_command': {
      const result = executeWorkstationCommand(
        overlay.workstation,
        action.payload.command,
        createdAt,
      );
      const interfaceState = result.state.network.interfaces.find(
        (entry) => entry.kind !== 'vpn',
      );
      const mappedDriveStates = Object.fromEntries(
        Object.entries(result.state.mappedDrives).map(([letter, drive]) => [
          letter,
          drive.status,
        ]),
      );
      const serviceStates = Object.fromEntries(
        Object.entries(result.state.services).map(([name, service]) => [
          name,
          service.state,
        ]),
      );
      return {
        ...overlay,
        workstation: result.state,
        dnsServers: interfaceState?.dnsServers ?? overlay.dnsServers,
        driveStates: { ...overlay.driveStates, ...mappedDriveStates },
        networkStatus: result.state.network.internetReachable
          ? overlay.networkStatus === 'offline'
            ? 'online'
            : overlay.networkStatus
          : 'offline',
        serviceStates,
        terminalHistory: [
          ...overlay.terminalHistory,
          {
            command: action.payload.command,
            output: result.output,
            timestamp: createdAt,
          },
        ].slice(-WORKSTATION_RENDERED_TERMINAL_LIMIT),
      };
    }
    case 'remote_desktop.explorer_navigate': {
      const path = canonicalExplorerPath(
        action.payload.assetTag,
        action.payload.path,
      );
      if (!path) return overlay;
      const next: RemoteDesktopOverlay = {
        ...overlay,
        explorerCurrentPath: path,
        explorerError: explorerErrorForPath(
          action.payload.assetTag,
          path,
          overlay,
        ),
      };
      return next.explorerError
        ? next
        : recordExplorerVerification(next, action.payload.assetTag, path);
    }
    case 'remote_desktop.explorer_reconnect_drive': {
      const driveLetter = action.payload.driveLetter.trim().toUpperCase();
      const workstation = getRemoteDesktopWorkstation(action.payload.assetTag);
      const drive = workstation?.drives.find(
        (candidate) => candidate.letter.toUpperCase() === driveLetter,
      );
      if (!drive) return overlay;
      const connected: RemoteDesktopOverlay = {
        ...overlay,
        driveStates: {
          ...overlay.driveStates,
          [drive.letter]: 'connected' as const,
        },
        explorerCurrentPath: drive.rootPath,
        explorerError: null,
      };
      const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
      const withRepairStep =
        scenario?.id === 'facilities-calendar-mapping'
          ? applyRemoteDesktopScenarioStep(
              connected,
              action.payload.assetTag,
              'explorer.repair-mapping',
            )
          : connected;
      return recordExplorerVerification(
        withRepairStep,
        action.payload.assetTag,
        drive.rootPath,
      );
    }
    case 'remote_desktop.explorer_refresh': {
      const next: RemoteDesktopOverlay = {
        ...overlay,
        explorerError: explorerErrorForPath(
          action.payload.assetTag,
          overlay.explorerCurrentPath,
          overlay,
        ),
        explorerLastRefreshedAt: createdAt,
      };
      return next.explorerError
        ? next
        : recordExplorerVerification(
            next,
            action.payload.assetTag,
            overlay.explorerCurrentPath,
          );
    }
    case 'remote_desktop.map_drive': {
      const letter = action.payload.letter.trim().toUpperCase();
      const mapped = mapWorkstationDrive(
        overlay.workstation,
        letter,
        action.payload.uncPath.trim(),
        action.payload.reconnectAtSignIn,
      );
      const target =
        action.payload.credentialTarget?.trim().toLowerCase() ?? null;
      const drive = mapped.state.mappedDrives[letter];
      const workstation = drive
        ? {
            ...mapped.state,
            mappedDrives: {
              ...mapped.state.mappedDrives,
              [letter]: { ...drive, credentialTarget: target },
            },
          }
        : mapped.state;
      const connected: RemoteDesktopOverlay = {
        ...overlay,
        workstation,
        driveStates: { ...overlay.driveStates, [letter]: 'connected' },
        explorerCurrentPath: `${letter}\\`,
        explorerError: null,
      };
      const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
      const withRepairStep =
        scenario?.id === 'facilities-calendar-mapping'
          ? applyRemoteDesktopScenarioStep(
              connected,
              action.payload.assetTag,
              'explorer.repair-mapping',
            )
          : connected;
      return recordExplorerVerification(
        withRepairStep,
        action.payload.assetTag,
        `${letter}\\`,
      );
    }
    case 'remote_desktop.credential_add':
      return {
        ...overlay,
        workstation: addWorkstationCredential(
          overlay.workstation,
          action.payload.target,
          action.payload.username,
          createdAt,
        ).state,
      };
    case 'remote_desktop.credential_delete':
      return {
        ...overlay,
        workstation: deleteWorkstationCredential(
          overlay.workstation,
          action.payload.target,
        ).state,
      };
    case 'remote_desktop.vpn_connect':
      return {
        ...overlay,
        vpnError: null,
        vpnLog: [
          ...overlay.vpnLog,
          {
            message: 'Connection requested for vpn.nexus.internal.',
            timestamp: createdAt,
          },
        ],
        vpnStatus: 'connecting',
      };
    case 'remote_desktop.vpn_complete_connection': {
      const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
      const connected: RemoteDesktopOverlay = {
        ...overlay,
        vpnError: null,
        vpnLog: [
          ...overlay.vpnLog,
          {
            message: 'Connected. Secure company routes are available.',
            timestamp: createdAt,
          },
        ],
        vpnStatus: 'connected',
      };
      return scenario?.id === 'vpn-shared-drive'
        ? applyRemoteDesktopScenarioStep(
            connected,
            action.payload.assetTag,
            'vpn.connect',
          )
        : connected;
    }
    case 'remote_desktop.vpn_disconnect': {
      const workstation = getRemoteDesktopWorkstation(action.payload.assetTag);
      const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
      const driveStates: RemoteDesktopOverlay['driveStates'] =
        scenario?.id === 'vpn-shared-drive'
          ? (Object.fromEntries(
              workstation?.drives
                .filter((drive) => drive.kind === 'network')
                .map((drive) => [
                  drive.letter,
                  'network-path-error' as const,
                ]) ?? [],
            ) as RemoteDesktopOverlay['driveStates'])
          : {};
      const disconnected: RemoteDesktopOverlay = {
        ...overlay,
        driveStates: { ...overlay.driveStates, ...driveStates },
        vpnError: null,
        vpnLog: [
          ...overlay.vpnLog,
          {
            message: 'Disconnected from Nexus Secure VPN.',
            timestamp: createdAt,
          },
        ],
        vpnStatus: 'disconnected' as const,
      };
      return {
        ...disconnected,
        explorerError: explorerErrorForPath(
          action.payload.assetTag,
          disconnected.explorerCurrentPath,
          disconnected,
        ),
      };
    }
    case 'remote_desktop.settings_update_dns': {
      const updated: RemoteDesktopOverlay = {
        ...overlay,
        dnsServers: [
          action.payload.primaryDns.trim(),
          action.payload.secondaryDns.trim(),
        ].filter(Boolean),
        networkStatus: 'online',
      };
      const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
      return scenario?.id === 'network-configuration'
        ? applyRemoteDesktopScenarioStep(
            updated,
            action.payload.assetTag,
            'settings.repair-network',
          )
        : updated;
    }
    case 'remote_desktop.update_install':
      return { ...overlay, updateState: 'installing' };
    case 'remote_desktop.update_complete_install':
      return { ...overlay, updateState: 'restart-required' };
    case 'remote_desktop.update_restart': {
      const updated: RemoteDesktopOverlay = {
        ...overlay,
        powerState: 'online',
        serviceStates: {
          ...overlay.serviceStates,
          ...(overlay.serviceStates['Windows Update']
            ? { 'Windows Update': 'running' as const }
            : {}),
        },
        updateInstalledAt: createdAt,
        updateState: 'applied',
      };
      const scenario = getRemoteDesktopScenarioByAsset(action.payload.assetTag);
      return scenario?.id === 'pdf-export-update'
        ? applyRemoteDesktopScenarioStep(
            updated,
            action.payload.assetTag,
            'updates.install',
          )
        : updated;
    }
  }
}

function applyRejectedRemoteDesktopAction(
  overlay: RemoteDesktopOverlay,
  action: RemoteDesktopSimulationAction,
  rejectReason: string,
  createdAt: string,
): RemoteDesktopOverlay {
  if (action.type === 'remote_desktop.vpn_complete_connection') {
    return {
      ...overlay,
      vpnError: rejectReason,
      vpnLog: [
        ...overlay.vpnLog,
        { message: `Connection failed: ${rejectReason}`, timestamp: createdAt },
      ],
      vpnStatus: 'error',
    };
  }
  if (action.type === 'remote_desktop.authenticate') {
    return { ...overlay, connectionState: 'error', lastError: rejectReason };
  }
  if (action.type === 'remote_desktop.perform_scenario_step') {
    return { ...overlay, lastError: rejectReason };
  }
  if (action.type === 'remote_desktop.explorer_reconnect_drive') {
    const workstation = getRemoteDesktopWorkstation(action.payload.assetTag);
    const drive = workstation?.drives.find(
      (candidate) =>
        candidate.letter.toUpperCase() ===
        action.payload.driveLetter.trim().toUpperCase(),
    );
    return drive
      ? {
          ...overlay,
          explorerCurrentPath: drive.rootPath,
          explorerError: explorerErrorForPath(
            action.payload.assetTag,
            drive.rootPath,
            overlay,
          ),
        }
      : overlay;
  }
  return { ...overlay };
}

function completeDeploymentStep(
  run: DeploymentRun,
  stepIndex: number,
  createdAt: string,
) {
  return run.steps.map((step, index) =>
    index === stepIndex ? { ...step, completedAt: createdAt } : { ...step },
  );
}

function createDeploymentRun(runId: string, createdAt: string): DeploymentRun {
  return {
    id: runId,
    method: 'Server Imaging',
    deviceType: null,
    currentStepIndex: 0,
    connectedCables: [],
    hostname: null,
    startedAt: createdAt,
    completedAt: null,
    steps: DEPLOYMENT_STEP_TEMPLATES.map((step) => ({
      ...step,
      wrongActionResponses: { ...step.wrongActionResponses },
      completedAt: null,
    })),
    events: [],
  };
}

function currentDeploymentStep(run: DeploymentRun) {
  return run.steps[run.currentStepIndex];
}

function deploymentRejectReason(
  attempt: Attempt,
  run: DeploymentRun | undefined,
  action: Exclude<DeploymentSimulationAction, { type: 'deployment.start' }>,
): string | null {
  if (!run) {
    return 'The requested deployment run does not exist.';
  }
  if (run.completedAt) {
    return 'This deployment run is already complete.';
  }

  const step = currentDeploymentStep(run);
  if (!step || step.expectedAction !== action.type) {
    return step
      ? `Complete “${step.title}” before attempting another deployment action.`
      : 'This deployment run has no active step.';
  }

  switch (action.type) {
    case 'deployment.select_device_type':
      return action.payload.deviceType === 'Desktop'
        ? null
        : (step.wrongActionResponses.unsupported ??
            'Select Desktop Deployment to continue.');
    case 'deployment.connect_cable':
      if (run.connectedCables.includes(action.payload.cable)) {
        return (
          step.wrongActionResponses.duplicate ??
          'That cable is already connected.'
        );
      }
      return DEPLOYMENT_CABLE_PORTS[action.payload.cable] ===
        action.payload.port
        ? null
        : (step.wrongActionResponses['wrong-port'] ??
            'That cable does not match the selected port.');
    case 'deployment.press_f12':
      return action.payload.timing === 'window'
        ? null
        : (step.wrongActionResponses[action.payload.timing] ??
            'F12 was not accepted during the boot window.');
    case 'deployment.select_boot_source':
      if (action.payload.source === 'PXE Network Boot IPv4') {
        return null;
      }
      return action.payload.source === DEPLOYMENT_BOOT_SOURCES[0]
        ? (step.wrongActionResponses.local ?? 'Choose the IPv4 network boot.')
        : (step.wrongActionResponses.ipv6 ?? 'IPv6 PXE is not configured.');
    case 'deployment.authenticate_share':
      return action.payload.password === DEPLOYMENT_SHARE_PASSWORD
        ? null
        : (step.wrongActionResponses.password ?? 'The password is incorrect.');
    case 'deployment.set_hostname': {
      const hostname = action.payload.hostname.trim();
      if (!/^SD\d{4}$/.test(hostname)) {
        return (
          step.wrongActionResponses.format ?? 'Use the uppercase SD#### format.'
        );
      }
      const registeredTags = new Set([
        ...DIRECTORY_USER_FIXTURES.flatMap((user) =>
          user.devices.map((device) => device.assetTag),
        ),
        ...PC_SHELF_FIXTURES.map((device) => device.assetTag),
        ...Object.keys(attempt.pcShelfOverlays),
        ...Object.values(attempt.deploymentRuns)
          .filter((candidate) => candidate.id !== run.id)
          .flatMap((candidate) =>
            candidate.hostname ? [candidate.hostname] : [],
          ),
      ]);
      return registeredTags.has(hostname)
        ? (step.wrongActionResponses.duplicate ??
            'That computer name is already registered.')
        : null;
    }
    case 'deployment.run_task_sequence':
    case 'deployment.reboot':
      return null;
    case 'deployment.domain_login':
      if (action.payload.domain !== DEPLOYMENT_DOMAIN) {
        return (
          step.wrongActionResponses.domain ??
          `Sign in to the ${DEPLOYMENT_DOMAIN} domain.`
        );
      }
      return action.payload.username === DEPLOYMENT_DOMAIN_USERNAME &&
        action.payload.password === DEPLOYMENT_DOMAIN_PASSWORD
        ? null
        : (step.wrongActionResponses.credentials ??
            'The password is incorrect. Try again.');
  }
}

function applyValidDeploymentAction(
  run: DeploymentRun,
  action: Exclude<DeploymentSimulationAction, { type: 'deployment.start' }>,
  createdAt: string,
): DeploymentRun {
  const stepIndex = run.currentStepIndex;

  if (action.type === 'deployment.connect_cable') {
    const connectedCables = [...run.connectedCables, action.payload.cable];
    const cablesComplete = connectedCables.length === DEPLOYMENT_CABLES.length;
    return {
      ...run,
      connectedCables,
      currentStepIndex: cablesComplete ? stepIndex + 1 : stepIndex,
      steps: cablesComplete
        ? completeDeploymentStep(run, stepIndex, createdAt)
        : run.steps.map((step) => ({ ...step })),
    };
  }

  const next: DeploymentRun = {
    ...run,
    currentStepIndex: stepIndex + 1,
    steps: completeDeploymentStep(run, stepIndex, createdAt),
  };

  if (action.type === 'deployment.select_device_type') {
    return { ...next, deviceType: 'Desktop' };
  }
  if (action.type === 'deployment.set_hostname') {
    return { ...next, hostname: action.payload.hostname.trim() };
  }
  if (action.type === 'deployment.domain_login') {
    return {
      ...next,
      currentStepIndex: 10,
      completedAt: createdAt,
      steps: next.steps.map((step, index) =>
        index === 9 || index === 10
          ? { ...step, completedAt: createdAt }
          : step,
      ),
    };
  }

  return next;
}

function dynamicPcProfile(hostname: string) {
  return {
    assetTag: hostname,
    cpu: 'Intel Core i5-14500',
    deploymentMethod: 'Server Imaging',
    deviceState: PcShelfDeviceState.OnShelf,
    location: 'IT Staging - Deployment Bench',
    networkStatus: PcShelfNetworkStatus.Online,
    operatingSystem: 'Windows 11 Enterprise',
    ram: '16 GB DDR5',
    serialNumber: `NXS-${hostname}-${hostname.slice(2)}9`,
    storage: '512 GB NVMe',
  };
}

function shippingAddressFromAction(
  action: Extract<ShippingSimulationAction, { type: 'shipping.create' }>,
): ShippingAddress {
  return {
    recipientDirectoryUserId: action.payload.recipientDirectoryUserId,
    recipientName: action.payload.recipientName.trim(),
    street: action.payload.street.trim(),
    city: action.payload.city.trim(),
    state: action.payload.state.trim(),
    postalCode: action.payload.postalCode.trim(),
  };
}

function shippingRejectReason(
  attempt: Attempt,
  action: ShippingSimulationAction,
): string | null {
  if (action.type === 'shipping.cancel') {
    const shipment = attempt.shipments[action.payload.shipmentId];
    if (!shipment) {
      return 'The requested shipment does not exist.';
    }
    return shipment.status === 'cancelled'
      ? 'This shipment is already cancelled.'
      : null;
  }

  const address = shippingAddressFromAction(action);
  if (
    !address.recipientDirectoryUserId ||
    !address.recipientName ||
    !address.street ||
    !address.city ||
    !address.state ||
    !address.postalCode
  ) {
    return 'Enter the full shipping address before shipping.';
  }
  if (!getDirectoryUserById(address.recipientDirectoryUserId)) {
    return 'Select a recipient from the company directory.';
  }
  if (!SHIPPING_DEPARTMENTS.includes(action.payload.senderDepartment)) {
    return 'Select a valid sender department.';
  }
  if (
    action.payload.equipment.length === 0 ||
    action.payload.equipment.some(
      (item) =>
        !SHIPPING_EQUIPMENT.includes(item.name) ||
        !Number.isInteger(item.quantity) ||
        item.quantity < 1,
    )
  ) {
    return 'Add at least one valid equipment item before shipping.';
  }
  if (!SHIPPING_SPEEDS.some((speed) => speed.id === action.payload.speed)) {
    return 'Select a valid shipping speed.';
  }

  const includesComputer = action.payload.equipment.some(
    (item) => item.name === 'Computer' && item.quantity > 0,
  );
  if (includesComputer && !action.payload.computerAssetTag) {
    return 'Select a provisioned PC from the shelf.';
  }
  if (!includesComputer && action.payload.computerAssetTag) {
    return 'Add Computer to the equipment list before selecting a shelf PC.';
  }
  if (action.payload.computerAssetTag) {
    const shelfPc = attempt.pcShelfOverlays[action.payload.computerAssetTag];
    if (!shelfPc?.present) {
      return 'The selected computer is no longer available on the PC Shelf.';
    }
  }

  return null;
}

function isDirectoryAction(
  action: SimulationAction,
): action is DirectorySimulationAction {
  return action.type.startsWith('directory.');
}

function isDeviceAction(
  action: SimulationAction,
): action is DeviceSimulationAction {
  return action.type.startsWith('device.');
}

function isChatAction(
  action: SimulationAction,
): action is ChatSimulationAction {
  return action.type.startsWith('chat.');
}

function isAssetAction(
  action: SimulationAction,
): action is AssetSimulationAction {
  return action.type.startsWith('asset.');
}

function isPcShelfAction(
  action: SimulationAction,
): action is PcShelfSimulationAction {
  return action.type.startsWith('pc_shelf.');
}

function isServerRoomAction(
  action: SimulationAction,
): action is ServerRoomSimulationAction {
  return action.type.startsWith('server_room.');
}

function isRemoteDesktopAction(
  action: SimulationAction,
): action is RemoteDesktopSimulationAction {
  return action.type.startsWith('remote_desktop.');
}

function isDeploymentAction(
  action: SimulationAction,
): action is DeploymentSimulationAction {
  return action.type.startsWith('deployment.');
}

function isShippingAction(
  action: SimulationAction,
): action is ShippingSimulationAction {
  return action.type.startsWith('shipping.');
}

function eventPayload(action: SimulationAction): Record<string, unknown> {
  if (action.type === 'directory.update_groups') {
    return {
      ...action.payload,
      add: [...action.payload.add],
      remove: [...action.payload.remove],
    };
  }

  if (action.type === 'shipping.create') {
    return {
      ...action.payload,
      equipment: action.payload.equipment.map((item) => ({ ...item })),
    };
  }

  return { ...action.payload };
}

function createEvent(
  attempt: Attempt,
  actorId: string,
  action: SimulationAction,
  rejectReason: string | null,
  eventId: string,
  createdAt: string,
): ActionEvent {
  return {
    id: eventId,
    attemptId: attempt.id,
    actorId,
    type: action.type,
    payload: eventPayload(action),
    success: rejectReason === null,
    rejectReason,
    createdAt,
  };
}

export function applyAction(
  attempt: Attempt,
  actorId: string,
  action: SimulationAction,
): ApplyActionResult {
  const createdAt = new Date().toISOString();
  const eventId = createId('event');

  if (isDeploymentAction(action)) {
    if (action.type === 'deployment.start') {
      const activeRun = attempt.activeDeploymentRunId
        ? attempt.deploymentRuns[attempt.activeDeploymentRunId]
        : undefined;
      const rejectReason =
        activeRun && !activeRun.completedAt
          ? 'A deployment is already in progress. Resume it before starting another.'
          : null;
      const event = createEvent(
        attempt,
        actorId,
        action,
        rejectReason,
        eventId,
        createdAt,
      );

      if (rejectReason && activeRun) {
        return {
          attempt: {
            ...attempt,
            deploymentRuns: {
              ...attempt.deploymentRuns,
              [activeRun.id]: {
                ...activeRun,
                events: [...activeRun.events, event],
              },
            },
          },
          event,
        };
      }

      const runId = createId('deployment');
      const run = createDeploymentRun(runId, createdAt);
      return {
        attempt: {
          ...attempt,
          activeDeploymentRunId: runId,
          deploymentRuns: {
            ...attempt.deploymentRuns,
            [runId]: { ...run, events: [event] },
          },
        },
        event,
      };
    }

    const run = attempt.deploymentRuns[action.payload.runId];
    const rejectReason = deploymentRejectReason(attempt, run, action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    if (!run) {
      return { attempt: { ...attempt }, event };
    }

    const updatedRun =
      rejectReason === null
        ? applyValidDeploymentAction(run, action, createdAt)
        : { ...run, steps: run.steps.map((step) => ({ ...step })) };
    const runWithEvent = {
      ...updatedRun,
      connectedCables: [...updatedRun.connectedCables],
      events: [...run.events, event],
    };
    let pcShelfOverlays = { ...attempt.pcShelfOverlays };

    if (
      rejectReason === null &&
      action.type === 'deployment.domain_login' &&
      runWithEvent.hostname
    ) {
      const device = dynamicPcProfile(runWithEvent.hostname);
      pcShelfOverlays = {
        ...pcShelfOverlays,
        [runWithEvent.hostname]: {
          assignedDirectoryUserId: null,
          deviceState: PcShelfDeviceState.OnShelf,
          networkStatus: PcShelfNetworkStatus.Online,
          present: true,
          device,
          events: [],
        },
      };
    }

    return {
      attempt: {
        ...attempt,
        deploymentRuns: {
          ...attempt.deploymentRuns,
          [run.id]: runWithEvent,
        },
        pcShelfOverlays,
      },
      event,
    };
  }

  if (isShippingAction(action)) {
    const rejectReason = shippingRejectReason(attempt, action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );

    if (action.type === 'shipping.create') {
      if (rejectReason) {
        return { attempt: { ...attempt }, event };
      }

      const shipmentId = createId('shipment');
      const address = shippingAddressFromAction(action);
      const shipment: Shipment = {
        id: shipmentId,
        address,
        senderDepartment: action.payload.senderDepartment,
        equipment: action.payload.equipment.map((item) => ({ ...item })),
        computerAssetTag: action.payload.computerAssetTag,
        speed: action.payload.speed,
        includeReturnLabel: action.payload.includeReturnLabel,
        status: 'shipped',
        createdAt,
        cancelledAt: null,
        events: [event],
      };
      const computerOverlay = action.payload.computerAssetTag
        ? attempt.pcShelfOverlays[action.payload.computerAssetTag]
        : undefined;

      return {
        attempt: {
          ...attempt,
          shipments: { ...attempt.shipments, [shipmentId]: shipment },
          lastShippingAddress: address,
          pcShelfOverlays:
            action.payload.computerAssetTag && computerOverlay
              ? {
                  ...attempt.pcShelfOverlays,
                  [action.payload.computerAssetTag]: {
                    ...computerOverlay,
                    present: false,
                  },
                }
              : { ...attempt.pcShelfOverlays },
        },
        event,
      };
    }

    const shipment = attempt.shipments[action.payload.shipmentId];
    if (!shipment) {
      return { attempt: { ...attempt }, event };
    }
    const updatedShipment: Shipment = rejectReason
      ? { ...shipment, events: [...shipment.events, event] }
      : {
          ...shipment,
          status: 'cancelled',
          cancelledAt: createdAt,
          events: [...shipment.events, event],
        };
    const computerOverlay = shipment.computerAssetTag
      ? attempt.pcShelfOverlays[shipment.computerAssetTag]
      : undefined;

    return {
      attempt: {
        ...attempt,
        shipments: {
          ...attempt.shipments,
          [shipment.id]: updatedShipment,
        },
        pcShelfOverlays:
          !rejectReason && shipment.computerAssetTag && computerOverlay
            ? {
                ...attempt.pcShelfOverlays,
                [shipment.computerAssetTag]: {
                  ...computerOverlay,
                  present: true,
                },
              }
            : { ...attempt.pcShelfOverlays },
      },
      event,
    };
  }

  if (isDirectoryAction(action)) {
    const directoryUserId = action.payload.directoryUserId;
    const currentOverlay =
      attempt.directoryOverlays[directoryUserId] ??
      createDirectoryOverlay(directoryUserId);
    const rejectReason = directoryRejectReason(currentOverlay, action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    const updatedOverlay =
      rejectReason === null
        ? applyValidDirectoryAction(currentOverlay, action)
        : { ...currentOverlay };
    const overlayWithEvent: DirectoryUserOverlay = {
      ...updatedOverlay,
      groupChanges: {
        added: [...updatedOverlay.groupChanges.added],
        removed: [...updatedOverlay.groupChanges.removed],
      },
      events: [...currentOverlay.events, event],
    };

    return {
      attempt: {
        ...attempt,
        ticketOverlays: { ...attempt.ticketOverlays },
        directoryOverlays: {
          ...attempt.directoryOverlays,
          [directoryUserId]: overlayWithEvent,
        },
        chatThreads: { ...attempt.chatThreads },
        assetOverlays: { ...attempt.assetOverlays },
        pcShelfOverlays: { ...attempt.pcShelfOverlays },
        serverRoomOverlays: { ...attempt.serverRoomOverlays },
        remoteDesktopOverlays: { ...attempt.remoteDesktopOverlays },
        grades: { ...attempt.grades },
      },
      event,
    };
  }

  if (isDeviceAction(action)) {
    const currentOverlay =
      attempt.ticketOverlays[action.payload.ticketId] ??
      createTicketOverlay(action.payload.ticketId);
    const event = createEvent(
      attempt,
      actorId,
      action,
      null,
      eventId,
      createdAt,
    );
    return {
      attempt: {
        ...attempt,
        ticketOverlays: {
          ...attempt.ticketOverlays,
          [action.payload.ticketId]: {
            ...currentOverlay,
            events: [...currentOverlay.events, event],
          },
        },
      },
      event,
    };
  }

  if (isChatAction(action)) {
    const contactId = action.payload.contactId;
    const currentOverlay =
      attempt.chatThreads[contactId] ?? createChatThreadOverlay();
    const rejectReason = chatRejectReason(action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    const updatedOverlay =
      rejectReason === null
        ? applyValidChatAction(
            currentOverlay,
            action,
            attempt,
            createdAt,
            eventId,
          )
        : { ...currentOverlay };
    const overlayWithEvent: ChatThreadOverlay = {
      ...updatedOverlay,
      messages: [...updatedOverlay.messages],
      events: [...currentOverlay.events, event],
    };

    return {
      attempt: {
        ...attempt,
        ticketOverlays: { ...attempt.ticketOverlays },
        directoryOverlays:
          action.type === 'chat.verify_identity' && rejectReason === null
            ? {
                ...attempt.directoryOverlays,
                [contactId]: {
                  ...(attempt.directoryOverlays[contactId] ??
                    createDirectoryOverlay(contactId)),
                  identityVerificationMethod: action.payload.method,
                },
              }
            : { ...attempt.directoryOverlays },
        chatThreads: {
          ...attempt.chatThreads,
          [contactId]: overlayWithEvent,
        },
        assetOverlays: { ...attempt.assetOverlays },
        pcShelfOverlays: { ...attempt.pcShelfOverlays },
        serverRoomOverlays: { ...attempt.serverRoomOverlays },
        remoteDesktopOverlays: { ...attempt.remoteDesktopOverlays },
        grades: { ...attempt.grades },
      },
      event,
    };
  }

  if (isAssetAction(action)) {
    const assetTag = action.payload.assetTag;
    const currentOverlay =
      attempt.assetOverlays[assetTag] ?? createAssetOverlay(attempt, assetTag);
    const rejectReason = assetRejectReason(attempt, currentOverlay, action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    const updatedOverlay =
      rejectReason === null
        ? applyValidAssetAction(currentOverlay, action)
        : { ...currentOverlay };
    const overlayWithEvent: AssetOverlay = {
      ...updatedOverlay,
      events: [...currentOverlay.events, event],
    };
    const currentPcShelf = attempt.pcShelfOverlays[assetTag];
    const updatedPcShelf =
      rejectReason === null && currentPcShelf
        ? syncPcShelfFromAssetAction(currentPcShelf, updatedOverlay, action)
        : currentPcShelf;

    return {
      attempt: {
        ...attempt,
        ticketOverlays: { ...attempt.ticketOverlays },
        directoryOverlays: { ...attempt.directoryOverlays },
        chatThreads: { ...attempt.chatThreads },
        assetOverlays: {
          ...attempt.assetOverlays,
          [assetTag]: overlayWithEvent,
        },
        pcShelfOverlays: updatedPcShelf
          ? { ...attempt.pcShelfOverlays, [assetTag]: updatedPcShelf }
          : { ...attempt.pcShelfOverlays },
        serverRoomOverlays: { ...attempt.serverRoomOverlays },
        remoteDesktopOverlays: { ...attempt.remoteDesktopOverlays },
        grades: { ...attempt.grades },
      },
      event,
    };
  }

  if (isPcShelfAction(action)) {
    const assetTag = action.payload.assetTag;
    const currentOverlay =
      attempt.pcShelfOverlays[assetTag] ?? createPcShelfOverlay(assetTag);
    const rejectReason = pcShelfRejectReason(currentOverlay, action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    const updatedOverlay =
      rejectReason === null
        ? applyValidPcShelfAction(currentOverlay, action)
        : { ...currentOverlay };
    const overlayWithEvent: PcShelfOverlay = {
      ...updatedOverlay,
      events: [...currentOverlay.events, event],
    };
    const currentAsset = attempt.assetOverlays[assetTag];
    const syncedAsset =
      rejectReason === null && currentAsset
        ? {
            ...currentAsset,
            assignedDirectoryUserId: updatedOverlay.assignedDirectoryUserId,
            status: pcShelfAssetStatus(updatedOverlay),
          }
        : currentAsset;

    return {
      attempt: {
        ...attempt,
        ticketOverlays: { ...attempt.ticketOverlays },
        directoryOverlays: { ...attempt.directoryOverlays },
        chatThreads: { ...attempt.chatThreads },
        assetOverlays: syncedAsset
          ? { ...attempt.assetOverlays, [assetTag]: syncedAsset }
          : { ...attempt.assetOverlays },
        pcShelfOverlays: {
          ...attempt.pcShelfOverlays,
          [assetTag]: overlayWithEvent,
        },
        serverRoomOverlays: { ...attempt.serverRoomOverlays },
        remoteDesktopOverlays: { ...attempt.remoteDesktopOverlays },
        grades: { ...attempt.grades },
      },
      event,
    };
  }

  if (isServerRoomAction(action)) {
    const nodeId = action.payload.nodeId;
    const currentOverlay =
      attempt.serverRoomOverlays[nodeId] ?? createServerRoomOverlay(nodeId);
    const rejectReason = serverRoomRejectReason(action);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    const updatedOverlay =
      rejectReason === null
        ? applyValidServerRoomAction(currentOverlay, action)
        : { ...currentOverlay };
    const overlayWithEvent: ServerRoomOverlay = {
      ...updatedOverlay,
      serviceStates: { ...updatedOverlay.serviceStates },
      events: [...currentOverlay.events, event],
    };

    return {
      attempt: {
        ...attempt,
        ticketOverlays: { ...attempt.ticketOverlays },
        directoryOverlays: { ...attempt.directoryOverlays },
        chatThreads: { ...attempt.chatThreads },
        assetOverlays: { ...attempt.assetOverlays },
        pcShelfOverlays: { ...attempt.pcShelfOverlays },
        serverRoomOverlays: {
          ...attempt.serverRoomOverlays,
          [nodeId]: overlayWithEvent,
        },
        remoteDesktopOverlays: { ...attempt.remoteDesktopOverlays },
        grades: { ...attempt.grades },
      },
      event,
    };
  }

  if (isRemoteDesktopAction(action)) {
    const assetTag = action.payload.assetTag;
    const currentOverlay =
      attempt.remoteDesktopOverlays[assetTag] ??
      createRemoteDesktopOverlay(assetTag);
    const rejectReason = remoteDesktopRejectReason(action, currentOverlay);
    const event = createEvent(
      attempt,
      actorId,
      action,
      rejectReason,
      eventId,
      createdAt,
    );
    const appliedOverlay =
      rejectReason === null
        ? applyValidRemoteDesktopAction(currentOverlay, action, createdAt)
        : applyRejectedRemoteDesktopAction(
            currentOverlay,
            action,
            rejectReason,
            createdAt,
          );
    const updatedOverlay =
      rejectReason === null
        ? recordRemoteDesktopWorkflowProgress(
            currentOverlay,
            appliedOverlay,
            action,
          )
        : appliedOverlay;
    const synchronizedOverlay: RemoteDesktopOverlay = {
      ...updatedOverlay,
      workstation: reconcileWorkstationState(updatedOverlay.workstation, {
        dnsServers: updatedOverlay.dnsServers,
        driveStates: updatedOverlay.driveStates,
        explorerCurrentPath: updatedOverlay.explorerCurrentPath,
        explorerError: updatedOverlay.explorerError,
        explorerLastRefreshedAt: updatedOverlay.explorerLastRefreshedAt,
        focusedApp: updatedOverlay.focusedApp,
        minimizedApps: updatedOverlay.minimizedApps,
        openApps: updatedOverlay.openApps,
        serviceStates: updatedOverlay.serviceStates,
        terminalHistory: updatedOverlay.terminalHistory,
        vpnError: updatedOverlay.vpnError,
        vpnLog: updatedOverlay.vpnLog,
        vpnStatus: updatedOverlay.vpnStatus,
      }),
    };
    const overlayWithEvent: RemoteDesktopOverlay = {
      ...synchronizedOverlay,
      dnsServers: [...synchronizedOverlay.dnsServers],
      driveStates: { ...synchronizedOverlay.driveStates },
      serviceStates: { ...synchronizedOverlay.serviceStates },
      scenarioProgress: { ...synchronizedOverlay.scenarioProgress },
      terminalHistory: [...synchronizedOverlay.terminalHistory],
      vpnLog: synchronizedOverlay.vpnLog.slice(-WORKSTATION_VPN_LOG_LIMIT),
      events: [...currentOverlay.events, event].slice(
        -WORKSTATION_EVENT_HISTORY_LIMIT,
      ),
    };

    let ticketOverlays = { ...attempt.ticketOverlays };
    if (
      rejectReason === null &&
      action.type === 'remote_desktop.add_internal_note'
    ) {
      const ticketOverlay =
        attempt.ticketOverlays[action.payload.ticketId] ??
        createTicketOverlay(action.payload.ticketId);
      const body = action.payload.text.trim();
      ticketOverlays = {
        ...ticketOverlays,
        [action.payload.ticketId]: {
          ...ticketOverlay,
          notes: [
            ...ticketOverlay.notes,
            { body, createdAt, id: `${eventId}-internal-note` },
          ],
          events: [...ticketOverlay.events, event],
        },
      };
    }

    return {
      attempt: {
        ...attempt,
        ticketOverlays,
        directoryOverlays: { ...attempt.directoryOverlays },
        chatThreads: { ...attempt.chatThreads },
        assetOverlays: { ...attempt.assetOverlays },
        pcShelfOverlays: { ...attempt.pcShelfOverlays },
        serverRoomOverlays: { ...attempt.serverRoomOverlays },
        remoteDesktopOverlays: {
          ...attempt.remoteDesktopOverlays,
          [assetTag]: overlayWithEvent,
        },
        grades: { ...attempt.grades },
      },
      event,
    };
  }

  const ticketId = action.payload.ticketId;
  const currentOverlay =
    attempt.ticketOverlays[ticketId] ?? createTicketOverlay(ticketId);
  const rejectReason = ticketRejectReason(attempt, currentOverlay, action);
  const event = createEvent(
    attempt,
    actorId,
    action,
    rejectReason,
    eventId,
    createdAt,
  );
  const updatedOverlay =
    rejectReason === null
      ? applyValidTicketAction(currentOverlay, action, createdAt, eventId)
      : { ...currentOverlay };
  const overlayWithEvent: TicketOverlay = {
    ...updatedOverlay,
    notes: [...updatedOverlay.notes],
    events: [...currentOverlay.events, event],
  };
  let remoteDesktopOverlays = { ...attempt.remoteDesktopOverlays };
  if (rejectReason === null && action.type === 'ticket.close') {
    const scenario = getRemoteDesktopScenarioByTicket(action.payload.ticketId);
    const remoteOverlay = scenario
      ? attempt.remoteDesktopOverlays[scenario.assetTag]
      : undefined;
    const progress =
      scenario && remoteOverlay
        ? remoteOverlay.scenarioProgress[scenario.id]
        : undefined;
    if (scenario?.workflow && remoteOverlay && progress) {
      remoteDesktopOverlays = {
        ...remoteDesktopOverlays,
        [scenario.assetTag]: {
          ...remoteOverlay,
          completedScenarioIds: remoteOverlay.completedScenarioIds.includes(
            scenario.id,
          )
            ? remoteOverlay.completedScenarioIds
            : [...remoteOverlay.completedScenarioIds, scenario.id],
          scenarioProgress: {
            ...remoteOverlay.scenarioProgress,
            [scenario.id]: {
              ...progress,
              phases: { ...progress.phases, closed: true },
              finalScore: workflowScore(scenario, progress),
              feedback:
                progress.phases.diagnosed && progress.phases.investigated
                  ? 'All troubleshooting-process, repair, verification, note, and closure checks passed.'
                  : 'The original symptom was repaired and verified, but investigation or diagnosis evidence was incomplete.',
            },
          },
        },
      };
    }
  }

  return {
    attempt: {
      ...attempt,
      ticketOverlays: {
        ...attempt.ticketOverlays,
        [ticketId]: overlayWithEvent,
      },
      directoryOverlays: { ...attempt.directoryOverlays },
      chatThreads: { ...attempt.chatThreads },
      assetOverlays: { ...attempt.assetOverlays },
      pcShelfOverlays: { ...attempt.pcShelfOverlays },
      serverRoomOverlays: { ...attempt.serverRoomOverlays },
      remoteDesktopOverlays,
      grades: { ...attempt.grades },
    },
    event,
  };
}
