import { describe, it, expect } from 'vitest';
import {
  REALISM_FIXTURES,
  getRemoteDesktopScenarioByTicket,
  readStatePath,
} from '@service-desk/shared';
import traces from '../../shared/src/realism-v2-traces.test.json';
import { createAttempt } from './attempt';
import { applyAction } from './apply-action';
import { serializeAttempt, restoreAttempt } from './serialize';
import { createWorkstationState } from './workstation/state';
import { executeWorkstationCommand } from './workstation/commands';
import type { SimulationAction } from './actions';

function connected(ticketId: string) {
  const assetTag = REALISM_FIXTURES[ticketId]!.assetTag;
  let attempt = createAttempt();
  for (const action of [
    { type: 'remote_desktop.connect', payload: { ticketId, assetTag } },
    { type: 'remote_desktop.begin_login', payload: { ticketId, assetTag } },
    {
      type: 'remote_desktop.authenticate',
      payload: {
        ticketId,
        assetTag,
        usernameEntered: true,
        passwordEntered: true,
      },
    },
  ] as SimulationAction[])
    attempt = applyAction(attempt, 'student', action).attempt;
  return attempt;
}

describe.each(Object.entries(traces))(
  '%s real evidence workflow',
  (ticket, trace) => {
    const fixture = REALISM_FIXTURES[ticket]!;
    it('replays tool changes, documentation, refresh and clean retries', () => {
      let attempt = connected(ticket);
      for (const command of trace.commands) {
        const result = applyAction(attempt, 'student', {
          type: 'remote_desktop.run_terminal_command',
          payload: { assetTag: fixture.assetTag, command },
        });
        expect(result.event.success, command).toBe(true);
        attempt = result.attempt;
      }
      const note = applyAction(attempt, 'student', {
        type: 'remote_desktop.add_internal_note',
        payload: {
          ticketId: ticket,
          assetTag: fixture.assetTag,
          text: trace.note,
        },
      });
      expect(note.event.success).toBe(true);
      const overlay = note.attempt.remoteDesktopOverlays[fixture.assetTag]!;
      expect(overlay.scenarioProgress[fixture.id]!.phases).toMatchObject({
        investigated: true,
        diagnosed: true,
        noted: true,
        fixed: fixture.escalation?.verificationApplicable !== false,
        verified: fixture.escalation?.verificationApplicable !== false,
      });
      expect(
        restoreAttempt(serializeAttempt(note.attempt))?.remoteDesktopOverlays[
          fixture.assetTag
        ]?.workstation,
      ).toEqual(overlay.workstation);
      expect(
        connected(ticket).remoteDesktopOverlays[fixture.assetTag]!.workstation
          .realism?.observed,
      ).toEqual({});
    });
    it.each([
      'inspect-symptom',
      'collect-evidence',
      'isolate-root-cause',
      'apply-safe-remediation',
      'verify-original-symptom',
    ])('rejects old wizard %s', (step) => {
      expect(getRemoteDesktopScenarioByTicket(ticket)?.actionLabels).toEqual(
        {},
      );
      expect(
        applyAction(connected(ticket), 'student', {
          type: 'remote_desktop.perform_scenario_step',
          payload: {
            ticketId: ticket,
            assetTag: fixture.assetTag,
            stepId: `scenario.${step}`,
          },
        }).event.success,
      ).toBe(false);
    });
    it('rejects an arbitrary requester question or another user', () => {
      for (const command of [
        'Ask-Requester forged',
        'Reset-Password other.student',
      ]) {
        expect(
          executeWorkstationCommand(
            createWorkstationState(fixture.assetTag),
            command,
            '2026-09-05T10:00:00Z',
          ).success,
        ).toBe(false);
      }
    });
  },
);

it('Company Chat can record an authored question before connecting to the workstation', () => {
  const result = applyAction(createAttempt(), 'student', {
    type: 'remote_desktop.run_terminal_command',
    payload: { assetTag: 'NX-2508', command: 'Ask-Requester exposure' },
  });
  expect(result.event.success).toBe(true);
  expect(
    result.attempt.remoteDesktopOverlays['NX-2508']!.workstation.realism
      ?.observed.exposure,
  ).toBe(true);
});

it('time is bounded and recurrence does not spill between scenarios', () => {
  let state = createWorkstationState('NX-2507');
  for (const command of [
    'Unlock-Account avery.monroe',
    ...Array<string>(20).fill('Advance-Time 15'),
  ])
    state = executeWorkstationCommand(
      state,
      command,
      '2026-09-05T10:00:00Z',
    ).state;
  expect(readStatePath(state, 'account/locked')).toBe(true);
  expect(readStatePath(state, 'clock/elapsedMinutes')).toBe(240);
  const printer = createWorkstationState('NX-2504');
  expect(
    executeWorkstationCommand(
      printer,
      'Advance-Time 15',
      '2026-09-05T10:00:00Z',
    ).success,
  ).toBe(false);
  expect(printer.realism?.harmful).toBe(false);
});
