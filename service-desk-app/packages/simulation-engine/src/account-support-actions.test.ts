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
  result = act(result.attempt, {
    type: 'directory.verify_identity',
    payload: { directoryUserId, method: 'approved-training-check' },
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
    const note =
      'Confirmed the lock diagnosis, repaired it by unlocking the account, and verified the original sign-in was restored.';
    const documented = act(verify.attempt, {
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
    const documented = act(verify.attempt, {
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
    const documented = act(verify.attempt, {
      type: 'ticket.add_note',
      payload: {
        ticketId: 'INC2513',
        body: 'Confirmed primary authentication succeeds, reset the unavailable MFA factor, and verified re-registration is ready.',
      },
    });
    expect(documented.event.success).toBe(true);
  });
});
