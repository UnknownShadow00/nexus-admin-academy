import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  SLOANE_RIVERA_DIRECTORY_USER_ID,
  TICKET_FIXTURES,
  TicketStatus,
  type Ticket,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt, resetAttempt } from './attempt';
import { isChatThreadUnread } from './chat';
import { evaluateObjectives } from './evaluate-objectives';
import type { ChatThreadOverlay } from './types';

const ACTOR_ID = 'student-1';

function apply(
  attempt: ReturnType<typeof createAttempt>,
  action: SimulationAction,
) {
  return applyAction(attempt, ACTOR_ID, action);
}

describe('applyAction happy paths', () => {
  it('applies assign, unassign, status, note, escalation, hint, and close actions', () => {
    const assigned = apply(createAttempt(), {
      type: 'ticket.assign',
      payload: { ticketId: 'INC2402' },
    });
    expect(assigned.event.success).toBe(true);
    expect(assigned.attempt.ticketOverlays.INC2402?.assignedTo).toBe('you');

    const unassigned = apply(createAttempt(), {
      type: 'ticket.unassign',
      payload: { ticketId: 'INC2401' },
    });
    expect(unassigned.event.success).toBe(true);
    expect(unassigned.attempt.ticketOverlays.INC2401?.assignedTo).toBeNull();

    const changed = apply(createAttempt(), {
      type: 'ticket.change_status',
      payload: { ticketId: 'INC2402', status: TicketStatus.InProgress },
    });
    expect(changed.event.success).toBe(true);
    expect(changed.attempt.ticketOverlays.INC2402?.status).toBe(
      TicketStatus.InProgress,
    );

    const noted = apply(createAttempt(), {
      type: 'ticket.add_note',
      payload: { ticketId: 'INC2402', body: '  Link is stable now.  ' },
    });
    expect(noted.event.success).toBe(true);
    expect(noted.attempt.ticketOverlays.INC2402?.notes.at(-1)?.body).toBe(
      'Link is stable now.',
    );

    const escalated = apply(createAttempt(), {
      type: 'ticket.escalate',
      payload: { ticketId: 'INC2402' },
    });
    expect(escalated.event.success).toBe(true);
    expect(escalated.attempt.ticketOverlays.INC2402?.escalated).toBe(true);

    const revealed = apply(createAttempt(), {
      type: 'ticket.reveal_hint',
      payload: { ticketId: 'INC2402', step: 1 },
    });
    expect(revealed.event.success).toBe(true);
    expect(revealed.attempt.ticketOverlays.INC2402?.hintsRevealedCount).toBe(1);

    const closed = apply(createAttempt(), {
      type: 'ticket.close',
      payload: {
        ticketId: 'INC2404',
        resolutionNote: 'Connectivity verified with dispatch.',
        verifiedResolved: true,
      },
    });
    expect(closed.event.success).toBe(true);
    expect(closed.attempt.ticketOverlays.INC2404?.status).toBe(
      TicketStatus.Resolved,
    );
    expect(closed.attempt.ticketOverlays.INC2404?.closure).toMatchObject({
      resolutionNote: 'Connectivity verified with dispatch.',
      verifiedResolved: true,
    });
  });

  it('returns copy-on-write state without mutating its input', () => {
    const attempt = createAttempt();
    const originalOverlays = attempt.ticketOverlays;
    const result = apply(attempt, {
      type: 'ticket.assign',
      payload: { ticketId: 'INC2402' },
    });

    expect(attempt.ticketOverlays).toBe(originalOverlays);
    expect(attempt.ticketOverlays.INC2402).toBeUndefined();
    expect(result.attempt).not.toBe(attempt);
    expect(result.attempt.ticketOverlays).not.toBe(originalOverlays);
  });
});

describe('directory actions', () => {
  const disabledUserId = 'directory-user-iris-caldwell';

  it('rejects unlocking the healthy Finance account', () => {
    const unlocked = apply(createAttempt(), {
      type: 'directory.unlock_account',
      payload: { directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID },
    });
    const rejected = apply(unlocked.attempt, {
      type: 'directory.unlock_account',
      payload: { directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID },
    });

    expect(unlocked.event.success).toBe(false);
    expect(unlocked.event.rejectReason).toContain('already unlocked');
    expect(rejected.event.success).toBe(false);
    expect(
      rejected.attempt.directoryOverlays[AVERY_BROOKS_DIRECTORY_USER_ID]
        ?.events,
    ).toHaveLength(2);
  });

  it('logs a password reset and rejects it for a disabled account', () => {
    const reset = apply(createAttempt(), {
      type: 'directory.reset_password',
      payload: { directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID },
    });
    const rejected = apply(createAttempt(), {
      type: 'directory.reset_password',
      payload: { directoryUserId: disabledUserId },
    });

    expect(reset.event.success).toBe(true);
    expect(reset.event.type).toBe('directory.reset_password');
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('disabled');
    expect(
      rejected.attempt.directoryOverlays[disabledUserId]?.events,
    ).toContainEqual(rejected.event);
  });

  it('enables a disabled account and rejects enabling an enabled account', () => {
    const enabled = apply(createAttempt(), {
      type: 'directory.enable_account',
      payload: { directoryUserId: disabledUserId },
    });
    const rejected = apply(createAttempt(), {
      type: 'directory.enable_account',
      payload: { directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID },
    });

    expect(enabled.attempt.directoryOverlays[disabledUserId]?.disabled).toBe(
      false,
    );
    expect(enabled.event.success).toBe(true);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already enabled');
  });

  it('disables an enabled account and rejects disabling it again', () => {
    const disabled = apply(createAttempt(), {
      type: 'directory.disable_account',
      payload: { directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID },
    });
    const rejected = apply(disabled.attempt, {
      type: 'directory.disable_account',
      payload: { directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID },
    });

    expect(
      disabled.attempt.directoryOverlays[SLOANE_RIVERA_DIRECTORY_USER_ID]
        ?.disabled,
    ).toBe(true);
    expect(disabled.event.success).toBe(true);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('already disabled');
  });

  it('resets MFA and rejects the reset for a disabled account', () => {
    const reset = apply(createAttempt(), {
      type: 'directory.reset_mfa',
      payload: { directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID },
    });
    const rejected = apply(createAttempt(), {
      type: 'directory.reset_mfa',
      payload: { directoryUserId: disabledUserId },
    });

    expect(
      reset.attempt.directoryOverlays[SLOANE_RIVERA_DIRECTORY_USER_ID]
        ?.mfaEnrolled,
    ).toBe(false);
    expect(reset.event.success).toBe(true);
    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('disabled');
  });

  it('updates group additions/removals and rejects an unchanged result', () => {
    const added = apply(createAttempt(), {
      type: 'directory.update_groups',
      payload: {
        directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID,
        add: ['Product Design Review'],
        remove: [],
      },
    });
    const unchanged = apply(added.attempt, {
      type: 'directory.update_groups',
      payload: {
        directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID,
        add: ['Product Design Review'],
        remove: [],
      },
    });
    const removed = apply(added.attempt, {
      type: 'directory.update_groups',
      payload: {
        directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID,
        add: [],
        remove: ['Product Design Review'],
      },
    });

    expect(
      added.attempt.directoryOverlays[SLOANE_RIVERA_DIRECTORY_USER_ID]
        ?.groupChanges.added,
    ).toContain('Product Design Review');
    expect(unchanged.event.success).toBe(false);
    expect(unchanged.event.rejectReason).toContain('would not change');
    expect(
      unchanged.attempt.directoryOverlays[SLOANE_RIVERA_DIRECTORY_USER_ID]
        ?.events,
    ).toHaveLength(2);
    expect(removed.event.success).toBe(true);
    expect(
      removed.attempt.directoryOverlays[SLOANE_RIVERA_DIRECTORY_USER_ID]
        ?.groupChanges.added,
    ).toEqual([]);
  });

  it('returns copy-on-write directory state without mutating its input', () => {
    const attempt = createAttempt();
    const originalOverlays = attempt.directoryOverlays;
    const result = apply(attempt, {
      type: 'directory.reset_password',
      payload: { directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID },
    });

    expect(attempt.directoryOverlays).toBe(originalOverlays);
    expect(
      attempt.directoryOverlays[SLOANE_RIVERA_DIRECTORY_USER_ID],
    ).toBeUndefined();
    expect(result.attempt).not.toBe(attempt);
    expect(result.attempt.directoryOverlays).not.toBe(originalOverlays);
  });
});

describe('company chat actions', () => {
  const contactId = AVERY_BROOKS_DIRECTORY_USER_ID;

  it('appends a student message and the matching scripted reply', () => {
    const result = apply(createAttempt(), {
      type: 'chat.send_message',
      payload: {
        contactId,
        body: '  Can you confirm which device is involved?  ',
      },
    });
    const thread = result.attempt.chatThreads[contactId];

    expect(result.event.success).toBe(true);
    expect(thread?.messages).toHaveLength(2);
    expect(thread?.messages[0]).toMatchObject({
      fromStudent: true,
      body: 'Can you confirm which device is involved?',
      triggerKey: null,
    });
    expect(thread?.messages[1]).toMatchObject({
      fromStudent: false,
      triggerKey: 'confirm-device',
    });
    expect(thread?.events).toContainEqual(result.event);
  });

  it('rejects a message longer than 500 characters and still logs it', () => {
    const result = apply(createAttempt(), {
      type: 'chat.send_message',
      payload: { contactId, body: 'x'.repeat(501) },
    });
    const thread = result.attempt.chatThreads[contactId];

    expect(result.event.success).toBe(false);
    expect(result.event.rejectReason).toContain('500 characters');
    expect(thread?.messages).toEqual([]);
    expect(thread?.events).toEqual([result.event]);
  });

  it.each(['', '   \n  '])(
    'rejects an empty or whitespace-only message: %j',
    (body) => {
      const result = apply(createAttempt(), {
        type: 'chat.send_message',
        payload: { contactId, body },
      });

      expect(result.event.success).toBe(false);
      expect(result.event.rejectReason).toContain('cannot be empty');
      expect(result.attempt.chatThreads[contactId]?.messages).toEqual([]);
      expect(result.attempt.chatThreads[contactId]?.events).toEqual([
        result.event,
      ]);
    },
  );

  it('updates the thread read timestamp when it is opened', () => {
    const result = apply(createAttempt(), {
      type: 'chat.open_thread',
      payload: { contactId },
    });

    expect(result.event.success).toBe(true);
    expect(result.attempt.chatThreads[contactId]?.lastReadAt).toBe(
      result.event.createdAt,
    );
  });

  it('pins and unpins a thread through copy-on-write actions', () => {
    const pinned = apply(createAttempt(), {
      type: 'chat.mark_pinned',
      payload: { contactId, pinned: true },
    });
    const unpinned = apply(pinned.attempt, {
      type: 'chat.mark_pinned',
      payload: { contactId, pinned: false },
    });

    expect(pinned.event.success).toBe(true);
    expect(pinned.attempt.chatThreads[contactId]?.pinned).toBe(true);
    expect(unpinned.event.success).toBe(true);
    expect(unpinned.attempt.chatThreads[contactId]?.pinned).toBe(false);
    expect(unpinned.attempt.chatThreads[contactId]?.events).toHaveLength(2);
  });

  it('computes unread state from contact replies newer than lastReadAt', () => {
    const thread = {
      messages: [
        {
          id: 'student-message',
          fromStudent: true,
          body: 'Checking in.',
          triggerKey: null,
          createdAt: '2026-07-28T10:00:00.000Z',
        },
        {
          id: 'contact-reply',
          fromStudent: false,
          body: 'I have an update.',
          triggerKey: 'general-acknowledgement',
          createdAt: '2026-07-28T10:02:00.000Z',
        },
      ],
      pinned: false,
      lastReadAt: '2026-07-28T10:01:00.000Z',
      events: [],
    } satisfies ChatThreadOverlay;

    expect(isChatThreadUnread(thread)).toBe(true);
    expect(
      isChatThreadUnread({
        ...thread,
        lastReadAt: '2026-07-28T10:02:00.000Z',
      }),
    ).toBe(false);
  });
});

describe('applyAction rejection paths', () => {
  it.each([
    {
      name: 'assigning an already-assigned ticket',
      action: {
        type: 'ticket.assign',
        payload: { ticketId: 'INC2401' },
      } satisfies SimulationAction,
    },
    {
      name: 'using an invalid status transition',
      action: {
        type: 'ticket.change_status',
        payload: { ticketId: 'INC2402', status: TicketStatus.Open },
      } satisfies SimulationAction,
    },
    {
      name: 'revealing beyond the available hint count',
      action: {
        type: 'ticket.reveal_hint',
        payload: { ticketId: 'INC2402', step: 5 },
      } satisfies SimulationAction,
    },
  ])('logs $name', ({ action }) => {
    const result = apply(createAttempt(), action);
    const overlay = result.attempt.ticketOverlays[action.payload.ticketId];

    expect(result.event.success).toBe(false);
    expect(result.event.rejectReason).toEqual(expect.any(String));
    expect(result.event.id).toEqual(expect.any(String));
    expect(overlay?.events).toContainEqual(result.event);
  });

  it('rejects a second close and still appends its event', () => {
    const first = apply(createAttempt(), {
      type: 'ticket.close',
      payload: {
        ticketId: 'INC2404',
        resolutionNote: '',
        verifiedResolved: false,
      },
    });
    const second = apply(first.attempt, {
      type: 'ticket.close',
      payload: {
        ticketId: 'INC2404',
        resolutionNote: '',
        verifiedResolved: true,
      },
    });

    expect(second.event.success).toBe(false);
    expect(second.event.rejectReason).toContain('already');
    expect(second.attempt.ticketOverlays.INC2404?.events).toHaveLength(2);
  });
});

describe('objective evaluation', () => {
  const highFixture = {
    ...TICKET_FIXTURES[3],
    activity: [],
    hints: ['One', 'Two', 'Three'],
    notes: [],
  } satisfies Ticket;
  const fixtures: readonly Ticket[] = [highFixture];

  it('awards full priority points for a verified resolution', () => {
    const closed = apply(createAttempt(), {
      type: 'ticket.close',
      payload: {
        ticketId: highFixture.id,
        resolutionNote: 'Requester confirmed access.',
        verifiedResolved: true,
      },
    });

    expect(
      evaluateObjectives(closed.attempt, highFixture.id, fixtures),
    ).toMatchObject({
      pointsAwarded: 80,
      pointsPossible: 80,
      penaltyPoints: 0,
      resolved: true,
    });
  });

  it('applies the unresolved-close deduction', () => {
    const closed = apply(createAttempt(), {
      type: 'ticket.close',
      payload: {
        ticketId: highFixture.id,
        resolutionNote: '',
        verifiedResolved: false,
      },
    });

    expect(
      evaluateObjectives(closed.attempt, highFixture.id, fixtures),
    ).toMatchObject({
      pointsAwarded: 60,
      pointsPossible: 80,
      penaltyPoints: 20,
      resolved: false,
    });
  });

  it('deducts five points for each hint after the first free hint', () => {
    let attempt = createAttempt();
    for (const step of [1, 2, 3]) {
      attempt = apply(attempt, {
        type: 'ticket.reveal_hint',
        payload: { ticketId: highFixture.id, step },
      }).attempt;
    }
    attempt = apply(attempt, {
      type: 'ticket.close',
      payload: {
        ticketId: highFixture.id,
        resolutionNote: 'Requester verified the new session.',
        verifiedResolved: true,
      },
    }).attempt;

    expect(evaluateObjectives(attempt, highFixture.id, fixtures)).toMatchObject(
      {
        hintsUsed: 3,
        pointsAwarded: 70,
        penaltyPoints: 10,
      },
    );
  });
});

describe('attempt reset', () => {
  it('supersedes a preserved old attempt and creates a fresh empty attempt', () => {
    const original = apply(createAttempt(), {
      type: 'ticket.add_note',
      payload: { ticketId: 'INC2402', body: 'Preserve this.' },
    }).attempt;
    const result = resetAttempt(original);

    expect(original.supersededById).toBeNull();
    expect(result.oldAttempt).not.toBe(original);
    expect(result.oldAttempt.supersededById).toBe(result.newAttempt.id);
    expect(result.oldAttempt.ticketOverlays).toEqual(original.ticketOverlays);
    expect(result.oldAttempt.directoryOverlays).toEqual(
      original.directoryOverlays,
    );
    expect(result.oldAttempt.chatThreads).toEqual(original.chatThreads);
    expect(result.oldAttempt.assetOverlays).toEqual(original.assetOverlays);
    expect(result.oldAttempt.pcShelfOverlays).toEqual(original.pcShelfOverlays);
    expect(result.newAttempt.id).not.toBe(original.id);
    expect(result.newAttempt.ticketOverlays).toEqual({});
    expect(result.newAttempt.directoryOverlays).toEqual({});
    expect(result.newAttempt.chatThreads).toEqual({});
    expect(result.newAttempt.assetOverlays).toEqual({});
    expect(Object.keys(result.newAttempt.pcShelfOverlays)).toHaveLength(4);
    expect(result.newAttempt.grades).toEqual({});
  });
});
