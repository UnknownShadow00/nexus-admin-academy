import { TicketStatus } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';
import { restoreAttempt, serializeAttempt } from './serialize';
import type { Attempt } from './types';

const ACTOR = 'phase-18-student';

function act(attempt: Attempt, action: SimulationAction) {
  return applyAction(attempt, ACTOR, action);
}

function connected(assetTag: string, ticketId: string) {
  let attempt = createAttempt({
    id: `attempt-${ticketId}`,
    startedAt: '2026-07-31T12:00:00.000Z',
  });
  for (const action of [
    {
      type: 'remote_desktop.connect',
      payload: { assetTag, ticketId },
    },
    {
      type: 'remote_desktop.begin_login',
      payload: { assetTag, ticketId },
    },
    {
      type: 'remote_desktop.authenticate',
      payload: {
        assetTag,
        ticketId,
        usernameEntered: true,
        passwordEntered: true,
      },
    },
  ] satisfies SimulationAction[]) {
    attempt = act(attempt, action).attempt;
  }
  return attempt;
}

function run(attempt: Attempt, actions: readonly SimulationAction[]) {
  return actions.reduce(
    (current, action) => act(current, action).attempt,
    attempt,
  );
}

function note(assetTag: string, ticketId: string): SimulationAction {
  return {
    type: 'remote_desktop.add_internal_note',
    payload: {
      assetTag,
      ticketId,
      text: 'Confirmed the root cause, applied the correct fix, and verified the original symptom is resolved.',
    },
  };
}

function close(ticketId: string): SimulationAction {
  return {
    type: 'ticket.close',
    payload: {
      ticketId,
      resolutionNote:
        'Confirmed the root cause, applied the correct fix, and verified the original symptom is resolved.',
      verifiedResolved: true,
    },
  };
}

function expectClosed(
  attempt: Attempt,
  assetTag: string,
  ticketId: string,
  scenarioId: string,
) {
  expect(attempt.ticketOverlays[ticketId]).toMatchObject({
    status: TicketStatus.Resolved,
    closure: { verifiedResolved: true },
    notes: [
      {
        body: 'Confirmed the root cause, applied the correct fix, and verified the original symptom is resolved.',
      },
    ],
  });
  expect(
    attempt.remoteDesktopOverlays[assetTag]?.scenarioProgress[scenarioId]
      ?.phases,
  ).toEqual({
    diagnosed: true,
    fixed: true,
    verified: true,
    noted: true,
    closed: true,
  });
  expect(
    attempt.remoteDesktopOverlays[assetTag]?.completedScenarioIds,
  ).toContain(scenarioId);
  expect(
    attempt.remoteDesktopOverlays[assetTag]?.scenarioProgress[scenarioId]
      ?.finalScore,
  ).toBe(100);
}

describe('Phase 18 phase-aware Remote Desktop workflows', () => {
  it('enforces per-mode hint gating in the engine', () => {
    const assessment = act(createAttempt(), {
      type: 'remote_desktop.set_learning_mode',
      payload: { assetTag: 'NX-2047', mode: 'assessment' },
    });
    const blocked = act(assessment.attempt, {
      type: 'ticket.reveal_hint',
      payload: { ticketId: 'INC2406', step: 1 },
    });
    const practice = act(blocked.attempt, {
      type: 'remote_desktop.set_learning_mode',
      payload: { assetTag: 'NX-2047', mode: 'practice' },
    });
    const allowed = act(practice.attempt, {
      type: 'ticket.reveal_hint',
      payload: { ticketId: 'INC2406', step: 1 },
    });

    expect(blocked.event.success).toBe(false);
    expect(blocked.event.rejectReason).toContain('assessment');
    expect(allowed.event.success).toBe(true);
  });

  it('completes Ticket A through diagnose, fix, verify, note, and close', () => {
    const attempt = run(connected('NX-2047', 'INC2406'), [
      {
        type: 'remote_desktop.explorer_navigate',
        payload: { assetTag: 'NX-2047', path: 'Z:\\' },
      },
      {
        type: 'remote_desktop.open_app',
        payload: { assetTag: 'NX-2047', appId: 'vpn' },
      },
      {
        type: 'remote_desktop.vpn_connect',
        payload: { assetTag: 'NX-2047' },
      },
      {
        type: 'remote_desktop.vpn_complete_connection',
        payload: { assetTag: 'NX-2047' },
      },
      {
        type: 'remote_desktop.explorer_navigate',
        payload: { assetTag: 'NX-2047', path: 'Z:\\' },
      },
      note('NX-2047', 'INC2406'),
      close('INC2406'),
    ]);

    expectClosed(attempt, 'NX-2047', 'INC2406', 'vpn-shared-drive');
  });

  it('accepts Ticket A in an alternate evidence order', () => {
    const attempt = run(connected('NX-2047', 'INC2406'), [
      note('NX-2047', 'INC2406'),
      {
        type: 'remote_desktop.open_app',
        payload: { assetTag: 'NX-2047', appId: 'vpn' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-2047',
          command: 'ping partner.nexus.internal',
        },
      },
      {
        type: 'remote_desktop.vpn_connect',
        payload: { assetTag: 'NX-2047' },
      },
      {
        type: 'remote_desktop.vpn_complete_connection',
        payload: { assetTag: 'NX-2047' },
      },
      {
        type: 'remote_desktop.explorer_navigate',
        payload: { assetTag: 'NX-2047', path: 'Z:\\' },
      },
      close('INC2406'),
    ]);

    expectClosed(attempt, 'NX-2047', 'INC2406', 'vpn-shared-drive');
  });

  it('rejects Ticket A closure when diagnosis evidence is incomplete', () => {
    const attempt = run(connected('NX-2047', 'INC2406'), [
      {
        type: 'remote_desktop.vpn_connect',
        payload: { assetTag: 'NX-2047' },
      },
      {
        type: 'remote_desktop.vpn_complete_connection',
        payload: { assetTag: 'NX-2047' },
      },
      {
        type: 'remote_desktop.explorer_navigate',
        payload: { assetTag: 'NX-2047', path: 'Z:\\' },
      },
      note('NX-2047', 'INC2406'),
    ]);
    const rejected = act(attempt, close('INC2406'));

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('diagnosis evidence');
  });

  it('completes Ticket B through diagnose, fix, verify, note, and close', () => {
    const attempt = run(connected('NX-8892', 'INC2407'), [
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ipconfig' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ping 10.20.0.15' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'nslookup intranet.nexus.internal',
        },
      },
      {
        type: 'remote_desktop.settings_update_dns',
        payload: {
          assetTag: 'NX-8892',
          primaryDns: '10.20.0.10',
          secondaryDns: '10.20.0.11',
        },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'nslookup intranet.nexus.internal',
        },
      },
      note('NX-8892', 'INC2407'),
      close('INC2407'),
    ]);

    expectClosed(attempt, 'NX-8892', 'INC2407', 'dns-configuration-failure');
  });

  it('accepts Ticket B in an alternate evidence order', () => {
    const attempt = run(connected('NX-8892', 'INC2407'), [
      note('NX-8892', 'INC2407'),
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ping 10.20.0.15' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'ping intranet.nexus.internal',
        },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ipconfig /all' },
      },
      {
        type: 'remote_desktop.settings_update_dns',
        payload: {
          assetTag: 'NX-8892',
          primaryDns: '10.20.0.10',
          secondaryDns: '10.20.0.11',
        },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'ping intranet.nexus.internal',
        },
      },
      close('INC2407'),
    ]);

    expectClosed(attempt, 'NX-8892', 'INC2407', 'dns-configuration-failure');
  });

  it('rejects Ticket B closure without post-fix verification evidence', () => {
    const attempt = run(connected('NX-8892', 'INC2407'), [
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ipconfig /all' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ping 10.20.0.15' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'nslookup intranet.nexus.internal',
        },
      },
      {
        type: 'remote_desktop.settings_update_dns',
        payload: {
          assetTag: 'NX-8892',
          primaryDns: '10.20.0.10',
          secondaryDns: '10.20.0.11',
        },
      },
      note('NX-8892', 'INC2407'),
    ]);
    const rejected = act(attempt, close('INC2407'));

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('post-fix verification');
  });

  it('completes Ticket C through diagnose, fix, verify, note, and close', () => {
    const attempt = run(connected('NX-4419', 'INC2408'), [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      {
        type: 'remote_desktop.open_app',
        payload: { assetTag: 'NX-4419', appId: 'services' },
      },
      {
        type: 'remote_desktop.start_service',
        payload: { assetTag: 'NX-4419', serviceName: 'Print Spooler' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      note('NX-4419', 'INC2408'),
      close('INC2408'),
    ]);

    expectClosed(attempt, 'NX-4419', 'INC2408', 'service-failure');
  });

  it('accepts Ticket C in an alternate evidence order and Terminal repair path', () => {
    const attempt = run(connected('NX-4419', 'INC2408'), [
      note('NX-4419', 'INC2408'),
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-4419', command: 'tasklist' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-4419', command: 'net start Print Spooler' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      close('INC2408'),
    ]);

    expectClosed(attempt, 'NX-4419', 'INC2408', 'service-failure');
  });

  it('rejects Ticket C closure when the dependent print action was not verified', () => {
    const attempt = run(connected('NX-4419', 'INC2408'), [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-4419', command: 'sc query Print Spooler' },
      },
      {
        type: 'remote_desktop.start_service',
        payload: { assetTag: 'NX-4419', serviceName: 'Print Spooler' },
      },
      note('NX-4419', 'INC2408'),
    ]);
    const rejected = act(attempt, close('INC2408'));

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('post-fix verification');
  });

  it('rechecks final system state at closure instead of trusting a historical fix click', () => {
    const repaired = run(connected('NX-4419', 'INC2408'), [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      {
        type: 'remote_desktop.open_app',
        payload: { assetTag: 'NX-4419', appId: 'services' },
      },
      {
        type: 'remote_desktop.start_service',
        payload: { assetTag: 'NX-4419', serviceName: 'Print Spooler' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4419',
          ticketId: 'INC2408',
          stepId: 'printer.test-page',
        },
      },
      note('NX-4419', 'INC2408'),
      {
        type: 'remote_desktop.stop_service',
        payload: { assetTag: 'NX-4419', serviceName: 'Print Spooler' },
      },
    ]);
    const rejected = act(repaired, close('INC2408'));

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('corrected state');
  });

  it('rejects empty or trivial internal notes and never substitutes scenario explanation text', () => {
    const attempt = connected('NX-2047', 'INC2406');
    const rejected = act(attempt, {
      type: 'remote_desktop.add_internal_note',
      payload: { assetTag: 'NX-2047', ticketId: 'INC2406', text: 'VPN fixed' },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('at least 20 characters');
    expect(
      rejected.attempt.remoteDesktopOverlays['NX-2047']?.scenarioProgress[
        'vpn-shared-drive'
      ],
    ).toMatchObject({ internalNote: null, phases: { noted: false } });
  });

  it.each([
    'x'.repeat(40),
    'fixed fixed fixed fixed fixed fixed fixed fixed',
    '\u200b'.repeat(40),
  ])('rejects malformed internal notes that only satisfy the length check', (text) => {
    const rejected = act(connected('NX-2047', 'INC2406'), {
      type: 'remote_desktop.add_internal_note',
      payload: { assetTag: 'NX-2047', ticketId: 'INC2406', text },
    });

    expect(rejected.event.success).toBe(false);
    expect(rejected.event.rejectReason).toContain('meaningful student-authored');
    expect(
      rejected.attempt.remoteDesktopOverlays['NX-2047']?.scenarioProgress[
        'vpn-shared-drive'
      ],
    ).toMatchObject({ internalNote: null, phases: { noted: false } });
  });

  it('preserves diagnose, fix, and verify progress through serialization refresh', () => {
    const beforeRefresh = run(connected('NX-8892', 'INC2407'), [
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ipconfig' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-8892', command: 'ping 10.20.0.15' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'nslookup intranet.nexus.internal',
        },
      },
      {
        type: 'remote_desktop.settings_update_dns',
        payload: {
          assetTag: 'NX-8892',
          primaryDns: '10.20.0.10',
          secondaryDns: '10.20.0.11',
        },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: {
          assetTag: 'NX-8892',
          command: 'nslookup intranet.nexus.internal',
        },
      },
    ]);

    const restored = restoreAttempt(serializeAttempt(beforeRefresh));
    expect(
      restored?.remoteDesktopOverlays['NX-8892']?.scenarioProgress[
        'dns-configuration-failure'
      ]?.phases,
    ).toMatchObject({ diagnosed: true, fixed: true, verified: true });
  });

  it('keeps the four unchanged pre-existing scenarios working with their original steps', () => {
    const cases = [
      {
        assetTag: 'NX-3560',
        ticketId: 'INC2403',
        scenarioId: 'pdf-export-update',
        steps: [
          'updates.install',
          'system.restart-pdf-helper',
          'browser.retry-export',
        ],
      },
      {
        assetTag: 'NX-4831',
        ticketId: 'INC2401',
        scenarioId: 'profile-storage',
        steps: ['settings.clear-profile-storage', 'browser.retry-sign-in'],
      },
      {
        assetTag: 'NX-7714',
        ticketId: 'INC2402',
        scenarioId: 'network-configuration',
        steps: ['settings.repair-network', 'system.renew-address'],
      },
      {
        assetTag: 'NX-6128',
        ticketId: 'INC2405',
        scenarioId: 'mapped-drive-permissions',
        steps: ['explorer.repair-mapping', 'explorer.verify-share'],
      },
    ] as const;

    for (const item of cases) {
      let attempt = connected(item.assetTag, item.ticketId);
      for (const stepId of item.steps) {
        const result = act(attempt, {
          type: 'remote_desktop.perform_scenario_step',
          payload: {
            assetTag: item.assetTag,
            ticketId: item.ticketId,
            stepId,
          },
        });
        expect(result.event.success).toBe(true);
        attempt = result.attempt;
      }
      expect(
        attempt.remoteDesktopOverlays[item.assetTag]?.completedScenarioIds,
      ).toContain(item.scenarioId);
    }
  });
});
