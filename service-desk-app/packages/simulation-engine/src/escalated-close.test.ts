import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';
import type { Attempt } from './types';

const ACTOR = 'escalation-student';
const TICKET = 'INC2506';
const ASSET = 'NX-2506';
// A realistic hand-off note: it states what was confirmed, that no access
// change was applied, and where the request went.
const NOTE =
  'Confirmed the salary folder is restricted and that no approval exists for this requester. I did not apply any access change; the request was escalated to Identity & Access with the evidence, and I confirmed the requester was told who now owns it.';

function act(attempt: Attempt, action: SimulationAction) {
  return applyAction(attempt, ACTOR, action);
}

function run(attempt: Attempt, actions: readonly SimulationAction[]) {
  return actions.reduce((current, action) => act(current, action).attempt, attempt);
}

function connected(): Attempt {
  return run(
    createAttempt({ id: 'attempt-2506', startedAt: '2026-09-04T09:00:00.000Z' }),
    [
      { type: 'ticket.assign', payload: { ticketId: TICKET } },
      {
        type: 'remote_desktop.connect',
        payload: { assetTag: ASSET, ticketId: TICKET },
      },
      {
        type: 'remote_desktop.begin_login',
        payload: { assetTag: ASSET, ticketId: TICKET },
      },
      {
        type: 'remote_desktop.authenticate',
        payload: {
          assetTag: ASSET,
          ticketId: TICKET,
          usernameEntered: true,
          passwordEntered: true,
        },
      },
    ],
  );
}

const close: SimulationAction = {
  type: 'ticket.close',
  payload: { ticketId: TICKET, resolutionNote: NOTE, verifiedResolved: false },
};

const escalate: SimulationAction = {
  type: 'ticket.escalate',
  payload: {
    ticketId: TICKET,
    reason: 'policy-authorization',
    routeTeam: 'Identity & Access',
  },
};

const handOffNote: SimulationAction = {
  type: 'remote_desktop.add_internal_note',
  payload: { assetTag: ASSET, ticketId: TICKET, text: NOTE },
};

describe('closing a ticket that was escalated', () => {
  it('does not demand a local repair the technician correctly refused to make', () => {
    // Without this, the only way to finish INC2506 in the browser was to run
    // the remediation the server treats as a prohibited, critical failure.
    const attempt = run(connected(), [escalate, handOffNote]);
    const result = act(attempt, close);

    expect(result.event.rejectReason).toBeFalsy();
    expect(result.event.success).toBe(true);
  });

  it('still requires the hand-off documentation', () => {
    const result = act(run(connected(), [escalate]), close);

    expect(result.event.success).toBe(false);
    expect(result.event.rejectReason).toContain('hand-off note');
  });

  it('leaves the repair-and-verify gate in place when nothing was escalated', () => {
    const result = act(run(connected(), [handOffNote]), close);

    expect(result.event.success).toBe(false);
    expect(result.event.rejectReason).toBeTruthy();
  });
});
