import { REMOTE_DESKTOP_SCENARIOS } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import {
  canInspectScenarioRequirements,
  hasAnotherHint,
  mentorScenarioRequirements,
  progressiveHints,
  scenarioActionLabel,
  shouldProactivelyRevealHint,
  studentFeedbackMessage,
} from './remote-desktop-learning';

const VPN_SCENARIO = REMOTE_DESKTOP_SCENARIOS[0]!;

describe('remote desktop learning presentation', () => {
  it('reveals Practice hints only on request without exposing requirements', () => {
    expect(progressiveHints(VPN_SCENARIO, 0)).toEqual([]);
    expect(progressiveHints(VPN_SCENARIO, 1)).toEqual([
      'Think about how a remote employee reaches company-only resources from home.',
    ]);
    expect(progressiveHints(VPN_SCENARIO, 2)).toHaveLength(2);
    expect(progressiveHints(VPN_SCENARIO, 1)).not.toContain(
      VPN_SCENARIO.workflow?.diagnose[0]?.anyOf[0],
    );
    expect(hasAnotherHint(VPN_SCENARIO, 2)).toBe(true);
    expect(hasAnotherHint(VPN_SCENARIO, 3)).toBe(false);
  });

  it('surfaces the first Guided hint proactively and keeps progressive reveal available', () => {
    expect(shouldProactivelyRevealHint(VPN_SCENARIO, 0, 'guided', false)).toBe(
      true,
    );
    expect(shouldProactivelyRevealHint(VPN_SCENARIO, 1, 'guided', false)).toBe(
      false,
    );
    expect(progressiveHints(VPN_SCENARIO, 1, 'guided', false)).toHaveLength(1);
    expect(hasAnotherHint(VPN_SCENARIO, 1, 'guided', false)).toBe(true);
  });

  it('blocks Assessment hints until completion, then exposes student-safe hints', () => {
    expect(progressiveHints(VPN_SCENARIO, 3, 'assessment', false)).toEqual([]);
    expect(hasAnotherHint(VPN_SCENARIO, 0, 'assessment', false)).toBe(false);
    expect(progressiveHints(VPN_SCENARIO, 0, 'assessment', true)).toEqual(
      VPN_SCENARIO.studentHints,
    );
  });

  it('keeps raw requirements for the mentor review while student labels stay natural', () => {
    expect(
      canInspectScenarioRequirements({ isAdmin: false, isMentor: false }),
    ).toBe(false);
    expect(
      canInspectScenarioRequirements({ isAdmin: false, isMentor: true }),
    ).toBe(true);
    expect(
      canInspectScenarioRequirements({ isAdmin: true, isMentor: false }),
    ).toBe(true);
    expect(mentorScenarioRequirements(VPN_SCENARIO)).toContainEqual({
      label: 'Inspected the VPN connection state',
      stepId: 'vpn.state-inspected',
    });
    expect(scenarioActionLabel(VPN_SCENARIO, 'vpn.connect')).toBe(
      'Connected the company VPN',
    );
  });

  it('does not echo raw engine rejection details in either student mode', () => {
    const rejected = {
      actorId: 'student-you',
      attemptId: 'attempt-1',
      createdAt: '2026-07-30T18:00:00.000Z',
      id: 'event-1',
      payload: {},
      rejectReason: 'Complete “vpn.connect” before attempting another repair.',
      success: false,
      type: 'remote_desktop.perform_scenario_step' as const,
    };

    expect(studentFeedbackMessage(rejected, true)).not.toContain('vpn.connect');
    expect(studentFeedbackMessage(rejected, false)).toBe(
      'That action was not accepted. You can review the ticket and try another approach.',
    );
    expect(studentFeedbackMessage(rejected, 'assessment')).toBe(
      'That action was not accepted.',
    );
  });

  it('keeps every internal objective and action key out of all student hint modes', () => {
    const internalKeys = [
      ...(VPN_SCENARIO.workflow?.diagnose ?? []),
      ...(VPN_SCENARIO.workflow?.fix ?? []),
      ...(VPN_SCENARIO.workflow?.verify ?? []),
    ].flatMap((objective) => objective.anyOf);

    for (const mode of ['guided', 'practice', 'assessment'] as const) {
      const studentCopy = progressiveHints(VPN_SCENARIO, 3, mode, true).join(
        ' ',
      );
      for (const key of internalKeys) expect(studentCopy).not.toContain(key);
    }
    expect(
      canInspectScenarioRequirements({ isAdmin: false, isMentor: false }),
    ).toBe(false);
  });
});
