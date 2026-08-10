import { TICKET_FIXTURES, TicketStatus } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import type { SimulationAction } from './actions';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';
import { evaluateObjectives } from './evaluate-objectives';
import type { Attempt } from './types';

const ACTOR = 'quality-pass-student';
const NOTE =
  'Captured evidence, identified the root cause, applied the repair, and verified the original user symptom.';

function apply(attempt: Attempt, action: SimulationAction) {
  return applyAction(attempt, ACTOR, action);
}

function run(attempt: Attempt, actions: readonly SimulationAction[]) {
  return actions.reduce(
    (current, action) => apply(current, action).attempt,
    attempt,
  );
}

function connected(assetTag: string, ticketId: string) {
  return run(createAttempt(), [
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
  ]);
}

function note(assetTag: string, ticketId: string): SimulationAction {
  return {
    type: 'remote_desktop.add_internal_note',
    payload: { assetTag, ticketId, text: NOTE },
  };
}

function close(ticketId: string): SimulationAction {
  return {
    type: 'ticket.close',
    payload: { ticketId, resolutionNote: NOTE, verifiedResolved: true },
  };
}

function score(attempt: Attempt, assetTag: string, scenarioId: string) {
  return attempt.remoteDesktopOverlays[assetTag]?.scenarioProgress[scenarioId]
    ?.finalScore;
}

describe('Service Desk quality pass', () => {
  it('INC2401 rejects unrelated account remediation, requires browser verification, and accepts profile repair', () => {
    const unrelated = apply(createAttempt(), {
      type: 'directory.unlock_account',
      payload: { directoryUserId: 'directory-user-avery-brooks' },
    });
    expect(unrelated.event.success).toBe(false);

    const repaired = run(connected('NX-4831', 'INC2401'), [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4831',
          ticketId: 'INC2401',
          stepId: 'settings.clear-profile-storage',
        },
      },
      note('NX-4831', 'INC2401'),
    ]);
    expect(apply(repaired, close('INC2401')).event.success).toBe(false);

    const verified = run(repaired, [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4831',
          ticketId: 'INC2401',
          stepId: 'browser.retry-sign-in',
        },
      },
      close('INC2401'),
    ]);
    expect(verified.ticketOverlays.INC2401?.status).toBe(TicketStatus.Resolved);
    expect(score(verified, 'NX-4831', 'profile-storage')).toBe(60);
  });

  it('INC2401 allows the portal check before and after repair for full process credit', () => {
    const attempt = run(connected('NX-4831', 'INC2401'), [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4831',
          ticketId: 'INC2401',
          stepId: 'mail.review-alert',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4831',
          ticketId: 'INC2401',
          stepId: 'browser.retry-sign-in',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4831',
          ticketId: 'INC2401',
          stepId: 'settings.clear-profile-storage',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-4831',
          ticketId: 'INC2401',
          stepId: 'browser.retry-sign-in',
        },
      },
      note('NX-4831', 'INC2401'),
      close('INC2401'),
    ]);

    expect(attempt.ticketOverlays.INC2401?.status).toBe(TicketStatus.Resolved);
    expect(score(attempt, 'NX-4831', 'profile-storage')).toBe(100);
  });

  it('INC2405 only credits the obsolete calendar mapping diagnosis and repair', () => {
    const attempt = run(connected('NX-6128', 'INC2405'), [
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-6128', command: 'net use' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-6128',
          ticketId: 'INC2405',
          stepId: 'explorer.repair-mapping',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-6128',
          ticketId: 'INC2405',
          stepId: 'explorer.verify-share',
        },
      },
      note('NX-6128', 'INC2405'),
      close('INC2405'),
    ]);
    expect(score(attempt, 'NX-6128', 'facilities-calendar-mapping')).toBe(100);
    expect(attempt.remoteDesktopOverlays['NX-6128']?.driveStates['Y:']).toBe(
      'connected',
    );
  });

  it('INC2402 scopes the wireless fault to the managed scanner before repairing its profile', () => {
    const attempt = run(connected('NX-7714', 'INC2402'), [
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-7714', command: 'ipconfig' },
      },
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-7714', command: 'ping 10.77.14.1' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-7714',
          ticketId: 'INC2402',
          stepId: 'settings.repair-network',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-7714',
          ticketId: 'INC2402',
          stepId: 'system.renew-address',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-7714',
          ticketId: 'INC2402',
          stepId: 'chat.confirm-restored',
        },
      },
      note('NX-7714', 'INC2402'),
      close('INC2402'),
    ]);
    expect(score(attempt, 'NX-7714', 'network-configuration')).toBe(100);
  });

  it('INC2403 requires reproducible evidence, update inspection, repair, and export verification', () => {
    const attempt = run(connected('NX-3560', 'INC2403'), [
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-3560',
          ticketId: 'INC2403',
          stepId: 'browser.retry-export',
        },
      },
      {
        type: 'remote_desktop.open_app',
        payload: { assetTag: 'NX-3560', appId: 'updates' },
      },
      {
        type: 'remote_desktop.explorer_navigate',
        payload: { assetTag: 'NX-3560', path: 'C:\\' },
      },
      {
        type: 'remote_desktop.update_install',
        payload: { assetTag: 'NX-3560' },
      },
      {
        type: 'remote_desktop.update_complete_install',
        payload: { assetTag: 'NX-3560' },
      },
      {
        type: 'remote_desktop.update_restart',
        payload: { assetTag: 'NX-3560' },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-3560',
          ticketId: 'INC2403',
          stepId: 'system.restart-pdf-helper',
        },
      },
      {
        type: 'remote_desktop.perform_scenario_step',
        payload: {
          assetTag: 'NX-3560',
          ticketId: 'INC2403',
          stepId: 'browser.retry-export',
        },
      },
      note('NX-3560', 'INC2403'),
      close('INC2403'),
    ]);
    expect(score(attempt, 'NX-3560', 'pdf-export-update')).toBe(100);
  });

  it('INC2406 teaches a disconnected VPN rather than device compliance', () => {
    const attempt = run(connected('NX-2047', 'INC2406'), [
      {
        type: 'remote_desktop.explorer_navigate',
        payload: { assetTag: 'NX-2047', path: 'Z:\\' },
      },
      {
        type: 'remote_desktop.open_app',
        payload: { assetTag: 'NX-2047', appId: 'vpn' },
      },
      { type: 'remote_desktop.vpn_connect', payload: { assetTag: 'NX-2047' } },
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
    expect(score(attempt, 'NX-2047', 'vpn-shared-drive')).toBe(100);
  });

  it('INC2407 gives a memorized DNS repair less credit than evidence-led isolation', () => {
    const guessed = run(connected('NX-8892', 'INC2407'), [
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
    const investigated = run(connected('NX-8892', 'INC2407'), [
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
    expect(score(guessed, 'NX-8892', 'dns-configuration-failure')).toBe(60);
    expect(score(investigated, 'NX-8892', 'dns-configuration-failure')).toBe(
      100,
    );
    expect(
      evaluateObjectives(guessed, 'INC2407', TICKET_FIXTURES).pointsAwarded,
    ).toBeLessThan(
      evaluateObjectives(investigated, 'INC2407', TICKET_FIXTURES)
        .pointsAwarded,
    );
  });

  it('INC2408 gives a blind spooler restart less credit than evidence-led repair', () => {
    const blind = run(connected('NX-4419', 'INC2408'), [
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
    const investigated = run(connected('NX-4419', 'INC2408'), [
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
    expect(score(blind, 'NX-4419', 'service-failure')).toBe(60);
    expect(score(investigated, 'NX-4419', 'service-failure')).toBe(100);
  });
});
