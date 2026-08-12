import { describe, expect, it } from 'vitest';

import { createAttempt } from './attempt';
import { applyAction } from './apply-action';
import type { SimulationAction } from './actions';
import type { Attempt } from './types';

const ACTOR = 'starter-student';

function act(attempt: Attempt, action: SimulationAction) {
  return applyAction(attempt, ACTOR, action);
}

function establishDiagnosis(
  attempt: Attempt,
  directoryUserId: string,
  diagnosis: 'account-locked' | 'password-expired' | 'mfa-factor-unavailable',
) {
  let result = act(attempt, {
    type: 'directory.inspect_account',
    payload: { directoryUserId },
  });
  expect(result.event.success).toBe(true);
  const ticketByUser: Readonly<Record<string, string>> = {
    'directory-user-taylor-morgan': 'INC2511',
    'directory-user-jordan-lee': 'INC2512',
    'directory-user-camille-reyes': 'INC2513',
  };
  result = act(result.attempt, {
    type: 'chat.verify_identity',
    payload: {
      contactId: directoryUserId,
      ticketId: ticketByUser[directoryUserId]!,
      method: 'employee-id-directory-match',
    },
  });
  expect(result.event.success).toBe(true);
  result = act(result.attempt, {
    type: 'directory.verify_identity',
    payload: { directoryUserId, method: 'employee-id-directory-match' },
  });
  expect(result.event.success).toBe(true);
  if (diagnosis === 'mfa-factor-unavailable') {
    result = act(result.attempt, {
      type: 'directory.test_primary_auth',
      payload: { directoryUserId, result: 'succeeds' },
    });
    expect(result.event.success).toBe(true);
  }
  result = act(result.attempt, {
    type: 'directory.record_diagnosis',
    payload: { directoryUserId, diagnosis },
  });
  expect(result.event.success).toBe(true);
  return result.attempt;
}

describe('foundational account support workflows', () => {
  it('requires matching Company Chat evidence before identity can be recorded', () => {
    const directoryUserId = 'directory-user-taylor-morgan';
    const inspected = act(createAttempt(), {
      type: 'directory.inspect_account',
      payload: { directoryUserId },
    });

    const withoutChat = act(inspected.attempt, {
      type: 'directory.verify_identity',
      payload: { directoryUserId, method: 'employee-id-directory-match' },
    });
    expect(withoutChat.event.success).toBe(false);
    expect(withoutChat.event.rejectReason).toContain('Company Chat');

    const wrongTicket = act(withoutChat.attempt, {
      type: 'chat.verify_identity',
      payload: {
        contactId: directoryUserId,
        ticketId: 'INC2512',
        method: 'employee-id-directory-match',
      },
    });
    expect(wrongTicket.event.success).toBe(false);
    expect(
      wrongTicket.attempt.directoryOverlays[directoryUserId]
        ?.identityVerificationMethod,
    ).toBeNull();

    const matchingChat = act(wrongTicket.attempt, {
      type: 'chat.verify_identity',
      payload: {
        contactId: directoryUserId,
        ticketId: 'INC2511',
        method: 'manager-confirmation',
      },
    });
    expect(matchingChat.event.success).toBe(true);

    const wrongMethod = act(matchingChat.attempt, {
      type: 'directory.verify_identity',
      payload: { directoryUserId, method: 'known-number-callback' },
    });
    expect(wrongMethod.event.success).toBe(false);

    const matchingMethod = act(wrongMethod.attempt, {
      type: 'directory.verify_identity',
      payload: { directoryUserId, method: 'manager-confirmation' },
    });
    expect(matchingMethod.event.success).toBe(true);
  });

  it('reports the original symptom as broken before remediation', () => {
    const contactId = 'directory-user-taylor-morgan';
    const earlyRetest = act(createAttempt(), {
      type: 'chat.request_resolution_confirmation',
      payload: { contactId, ticketId: 'INC2511' },
    });

    expect(earlyRetest.event.success).toBe(true);
    expect(
      earlyRetest.attempt.chatThreads[contactId]?.messages.at(-1)?.triggerKey,
    ).toBe('original-symptom-still-broken');

    const prematureNote = act(earlyRetest.attempt, {
      type: 'ticket.add_note',
      payload: {
        ticketId: 'INC2511',
        body: 'Confirmed the cause, repaired the lock, and verified sign-in was restored.',
      },
    });
    expect(prematureNote.event.success).toBe(false);
    expect(prematureNote.event.rejectReason).toContain('sign-in');
  });

  it('rejects a guessed unlock, then supports inspect through verification', () => {
    const directoryUserId = 'directory-user-taylor-morgan';
    const guessed = act(createAttempt(), {
      type: 'directory.unlock_account',
      payload: { directoryUserId },
    });
    expect(guessed.event.success).toBe(false);
    expect(guessed.event.rejectReason).toContain('diagnosis');
    const guessedClose = act(guessed.attempt, {
      type: 'ticket.close',
      payload: {
        ticketId: 'INC2511',
        resolutionNote: 'Verified after repair.',
        verifiedResolved: true,
      },
    });
    expect(guessedClose.event.success).toBe(false);

    let attempt = establishDiagnosis(
      guessed.attempt,
      directoryUserId,
      'account-locked',
    );
    const unlock = act(attempt, {
      type: 'directory.unlock_account',
      payload: { directoryUserId },
    });
    expect(unlock.event.success).toBe(true);
    expect(unlock.attempt.directoryOverlays[directoryUserId]?.locked).toBe(
      false,
    );
    attempt = unlock.attempt;
    const verify = act(attempt, {
      type: 'directory.verify_access',
      payload: { directoryUserId, check: 'account-unlocked' },
    });
    expect(verify.event.success).toBe(true);
    expect(
      verify.attempt.directoryOverlays[directoryUserId]?.accessVerified,
    ).toBe(true);
    const confirmed = act(verify.attempt, {
      type: 'chat.request_resolution_confirmation',
      payload: { contactId: directoryUserId, ticketId: 'INC2511' },
    });
    expect(confirmed.event.success).toBe(true);
    const note =
      'Confirmed the lock diagnosis, repaired it by unlocking the account, and verified the original sign-in was restored.';
    const documented = act(confirmed.attempt, {
      type: 'ticket.add_note',
      payload: { ticketId: 'INC2511', body: note },
    });
    expect(documented.event.success).toBe(true);
    const close = act(documented.attempt, {
      type: 'ticket.close',
      payload: {
        ticketId: 'INC2511',
        resolutionNote: note,
        verifiedResolved: true,
      },
    });
    expect(close.event.success).toBe(true);
  });

  it('issues a temporary password with a required next-sign-in change', () => {
    const directoryUserId = 'directory-user-jordan-lee';
    const diagnosed = establishDiagnosis(
      createAttempt(),
      directoryUserId,
      'password-expired',
    );
    const reset = act(diagnosed, {
      type: 'directory.reset_password',
      payload: { directoryUserId, requireChangeAtNextSignIn: true },
    });
    expect(reset.event.success).toBe(true);
    expect(
      reset.attempt.directoryOverlays[directoryUserId]?.passwordState,
    ).toBe('temporary');
    const verify = act(reset.attempt, {
      type: 'directory.verify_access',
      payload: { directoryUserId, check: 'temporary-password-issued' },
    });
    expect(verify.event.success).toBe(true);
    const confirmed = act(verify.attempt, {
      type: 'chat.request_resolution_confirmation',
      payload: { contactId: directoryUserId, ticketId: 'INC2512' },
    });
    expect(confirmed.event.success).toBe(true);
    const documented = act(confirmed.attempt, {
      type: 'ticket.add_note',
      payload: {
        ticketId: 'INC2512',
        body: 'Confirmed the expired password diagnosis, issued a temporary password, and verified the required-change sign-in handoff.',
      },
    });
    expect(documented.event.success).toBe(true);
  });

  it('separates successful primary authentication from an unusable MFA factor', () => {
    const directoryUserId = 'directory-user-camille-reyes';
    const diagnosed = establishDiagnosis(
      createAttempt(),
      directoryUserId,
      'mfa-factor-unavailable',
    );
    const reset = act(diagnosed, {
      type: 'directory.reset_mfa',
      payload: { directoryUserId },
    });
    expect(reset.event.success).toBe(true);
    expect(
      reset.attempt.directoryOverlays[directoryUserId]?.mfaFactorStatus,
    ).toBe('reset-ready');
    const verify = act(reset.attempt, {
      type: 'directory.verify_access',
      payload: { directoryUserId, check: 'mfa-reregistration-ready' },
    });
    expect(verify.event.success).toBe(true);
    const confirmed = act(verify.attempt, {
      type: 'chat.request_resolution_confirmation',
      payload: { contactId: directoryUserId, ticketId: 'INC2513' },
    });
    expect(confirmed.event.success).toBe(true);
    const documented = act(confirmed.attempt, {
      type: 'ticket.add_note',
      payload: {
        ticketId: 'INC2513',
        body: 'Confirmed primary authentication succeeds, reset the unavailable MFA factor, and verified re-registration is ready.',
      },
    });
    expect(documented.event.success).toBe(true);
  });
});
