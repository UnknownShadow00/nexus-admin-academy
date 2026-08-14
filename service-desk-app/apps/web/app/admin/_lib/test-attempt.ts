import {
  AssetStatus,
  TicketStatus,
  getDirectoryUserById,
  getTestAttemptStorageKey,
  type ScenarioVersion,
} from '@service-desk/shared';
import {
  createAttempt,
  restoreAttempt,
  scenarioTicketId,
  serializeAttempt,
  type Attempt,
} from '@service-desk/simulation-engine';

function seedAttempt(
  base: Attempt,
  versions: readonly ScenarioVersion[],
): Attempt {
  const directoryOverlays = { ...base.directoryOverlays };
  const assetOverlays = { ...base.assetOverlays };
  const chatThreads = { ...base.chatThreads };
  const ticketOverlays = { ...base.ticketOverlays };

  for (const version of versions) {
    for (const [userId, seed] of Object.entries(
      version.initialWorldState.directoryOverlaySeeds,
    )) {
      const fixture = getDirectoryUserById(userId);
      if (directoryOverlays[userId]) {
        continue;
      }
      directoryOverlays[userId] = {
        disabled: seed.disabled ?? fixture?.disabled ?? false,
        events: [],
        groupChanges: {
          added: [...(seed.groupChanges?.added ?? [])],
          removed: [...(seed.groupChanges?.removed ?? [])],
        },
        locked: seed.locked ?? fixture?.locked ?? false,
        mfaEnrolled: seed.mfaEnrolled ?? fixture?.mfaEnrolled ?? true,
        passwordState: fixture?.passwordState ?? 'current',
        mfaFactorStatus: fixture?.mfaFactorStatus ?? 'available',
        inspected: false,
      identityVerified: false,
      identityVerificationMethod: null,
        primaryAuthTested: false,
        diagnosis: null,
        accessVerified: false,
      };
    }

    for (const [assetTag, seed] of Object.entries(
      version.initialWorldState.assetOverlaySeeds,
    )) {
      if (assetOverlays[assetTag]) {
        continue;
      }
      assetOverlays[assetTag] = {
        assignedDirectoryUserId: seed.assignedDirectoryUserId ?? null,
        events: [],
        status: seed.status ?? AssetStatus.Deployed,
      };
    }

    for (const seed of version.initialWorldState.chatMessageSeeds) {
      const current = chatThreads[seed.contactId] ?? {
        events: [],
        lastReadAt: null,
        messages: [],
        pinned: false,
      };
      const messageId = `seed-${version.id}-${current.messages.length + 1}`;
      if (
        current.messages.some((message) =>
          message.id.startsWith(`seed-${version.id}-`),
        )
      ) {
        continue;
      }
      chatThreads[seed.contactId] = {
        ...current,
        messages: [
          ...current.messages,
          {
            body: seed.body,
            createdAt: base.startedAt,
            fromStudent: seed.fromStudent ?? false,
            id: messageId,
            triggerKey: seed.triggerKey ?? null,
          },
        ],
      };
    }

    const ticketId = scenarioTicketId(version);
    ticketOverlays[ticketId] ??= {
      assignedTo: null,
      closure: null,
      escalated: false,
      events: [],
      hintsRevealedCount: 0,
      notes: [],
      status: TicketStatus.Open,
    };
  }

  return {
    ...base,
    assetOverlays,
    chatThreads,
    directoryOverlays,
    ticketOverlays,
  };
}

function createSeededAttempt(versions: readonly ScenarioVersion[]): Attempt {
  return seedAttempt(createAttempt(), versions);
}

export function loadTestAttempt(
  slotId: string,
  versions: readonly ScenarioVersion[],
): Attempt {
  try {
    const raw = localStorage.getItem(getTestAttemptStorageKey(slotId));
    const restored = raw ? restoreAttempt(raw) : null;
    return restored ?? createSeededAttempt(versions);
  } catch {
    return createSeededAttempt(versions);
  }
}

export function saveTestAttempt(slotId: string, attempt: Attempt) {
  try {
    localStorage.setItem(
      getTestAttemptStorageKey(slotId),
      serializeAttempt(attempt),
    );
  } catch {
    // In-memory test play remains usable when browser storage is unavailable.
  }
}

export function resetTestAttempt(
  slotId: string,
  versions: readonly ScenarioVersion[],
) {
  const attempt = createSeededAttempt(versions);
  saveTestAttempt(slotId, attempt);
  return attempt;
}

export function addScenarioToTestAttempt(
  slotId: string,
  attempt: Attempt,
  version: ScenarioVersion,
) {
  const next = seedAttempt(attempt, [version]);
  saveTestAttempt(slotId, next);
  return next;
}

export function clearTestAttempt(slotId: string) {
  try {
    localStorage.removeItem(getTestAttemptStorageKey(slotId));
  } catch {
    // The next visit still gets an in-memory fresh attempt.
  }
}
