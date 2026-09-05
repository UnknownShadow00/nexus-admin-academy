import { describe, it, expect } from 'vitest';
import {
  REALISM_FIXTURES,
  readStatePath,
  getRemoteDesktopScenarioByTicket,
} from '@service-desk/shared';
import traces from '../../shared/src/realism-traces.test.json';
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
    { type: 'remote_desktop.connect', payload: { assetTag, ticketId } },
    { type: 'remote_desktop.begin_login', payload: { assetTag, ticketId } },
    {
      type: 'remote_desktop.authenticate',
      payload: {
        assetTag,
        ticketId,
        usernameEntered: true,
        passwordEntered: true,
      },
    },
  ] as SimulationAction[])
    attempt = applyAction(attempt, 'student', action).attempt;
  return attempt;
}
describe.each(Object.entries(traces))(
  '%s realistic workflow',
  (ticketId, trace) => {
    const fixture = REALISM_FIXTURES[ticketId]!;
    it('requires tool observations, changes and post-change verification, then preserves resume state', () => {
      let attempt = connected(ticketId);
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
        payload: { ticketId, assetTag: fixture.assetTag, text: trace.note },
      });
      expect(note.event.success).toBe(true);
      const progress =
        note.attempt.remoteDesktopOverlays[fixture.assetTag]!.scenarioProgress[
          fixture.id
        ]!;
      expect(progress.phases).toMatchObject({
        investigated: true,
        diagnosed: true,
        fixed: true,
        verified: true,
        noted: true,
      });
      const restored = restoreAttempt(serializeAttempt(note.attempt));
      expect(
        restored?.remoteDesktopOverlays[fixture.assetTag]?.workstation,
      ).toEqual(
        note.attempt.remoteDesktopOverlays[fixture.assetTag]!.workstation,
      );
      expect(
        connected(ticketId).remoteDesktopOverlays[fixture.assetTag]!.workstation
          .realism?.observed,
      ).toEqual({});
    });
    it.each([
      'inspect-symptom',
      'collect-evidence',
      'isolate-root-cause',
      'apply-safe-remediation',
      'verify-original-symptom',
    ])('rejects the retired %s control', (step) => {
      expect(getRemoteDesktopScenarioByTicket(ticketId)?.actionLabels).toEqual(
        {},
      );
      expect(
        applyAction(connected(ticketId), 'student', {
          type: 'remote_desktop.perform_scenario_step',
          payload: {
            ticketId,
            assetTag: fixture.assetTag,
            stepId: `scenario.${step}`,
          },
        }).event.success,
      ).toBe(false);
    });
    it('does not credit a fabricated evidence step', () => {
      expect(
        applyAction(connected(ticketId), 'student', {
          type: 'remote_desktop.perform_scenario_step',
          payload: {
            ticketId,
            assetTag: fixture.assetTag,
            stepId: fixture.categories.remediation![0]!,
          },
        }).event.success,
      ).toBe(false);
    });
    it('rejects an unknown target and incomplete documentation', () => {
      expect(
        executeWorkstationCommand(
          createWorkstationState(fixture.assetTag),
          'Start-UserSession other.student',
          '2026-07-30T10:00:00Z',
        ).success,
      ).toBe(false);
      expect(
        applyAction(connected(ticketId), 'student', {
          type: 'remote_desktop.add_internal_note',
          payload: {
            ticketId,
            assetTag: fixture.assetTag,
            text: 'I investigated and fixed everything successfully.',
          },
        }).event.success,
      ).toBe(false);
    });
  },
);
it('printer begins with a running spooler; restart does not fix the destination', () => {
  const state = createWorkstationState('NX-2504');
  expect(state.services['Print Spooler']?.state).toBe('running');
  const restarted = executeWorkstationCommand(
    state,
    'Restart-Service -Name Spooler',
    '2026-07-30T10:00:00Z',
  );
  expect(restarted.success).toBe(true);
  expect(readStatePath(restarted.state, 'printer/portTarget')).toBe(
    '10.26.19.80',
  );
  expect(
    executeWorkstationCommand(
      restarted.state,
      'Print-TestPage -Name ENG-COPIER',
      '2026-07-30T10:00:00Z',
    ).state.realism?.lastEvidence,
  ).toBeNull();
});
it('early repair never backfills investigation or diagnosis', () => {
  let state = createWorkstationState('NX-2504');
  for (const command of [
    'Set-PrinterPort -Name ENG-COPIER -PrinterHostAddress 10.26.19.94',
    ...traces.INC2504.commands,
  ])
    state = executeWorkstationCommand(
      state,
      command,
      '2026-07-30T10:00:00Z',
    ).state;
  expect(state.realism?.observed.spooler).toBeUndefined();
  expect(state.realism?.observed['current-address']).toBeUndefined();
});
it('excessive membership opens the share but remains a harmful outcome', () => {
  let state = createWorkstationState('NX-2505');
  for (const command of [
    'Add-ADGroupMember -Identity All-Departments-RW -Members taylor.reed',
    'Start-UserSession taylor.reed',
  ])
    state = executeWorkstationCommand(
      state,
      command,
      '2026-07-30T10:00:00Z',
    ).state;
  const opened = executeWorkstationCommand(
    state,
    'Test-Path \\\\files.nexus.internal\\Marketing',
    '2026-07-30T10:00:00Z',
  );
  expect(opened.output.join(' ')).toContain('Share opens');
  expect(opened.state.realism?.harmful).toBe(true);
  expect(opened.state.realism?.repaired).toBe(false);
});
it('profile removal is refused and original data survives', () => {
  const state = createWorkstationState('NX-2501');
  expect(state.machine.profileState).toBe('temporary');
  const result = executeWorkstationCommand(
    state,
    'Remove-UserProfile -User morgan.ellis',
    '2026-07-30T10:00:00Z',
  );
  expect(result.success).toBe(false);
  expect(result.state.filesystem.nodes.documents?.available).toBe(true);
});
it('temp cleanup frees space but leaves growing logs and retention unchanged', () => {
  const state = createWorkstationState('NX-2509');
  const result = executeWorkstationCommand(
    state,
    'Clear-TempFiles C:',
    '2026-07-30T10:00:00Z',
  );
  expect(readStatePath(result.state, 'storage/freeBytes')).toBe(4 * 1024 ** 3);
  expect(readStatePath(result.state, 'storage/retention')).toBe('unbounded');
  expect(result.state.realism?.repaired).toBe(false);
});
