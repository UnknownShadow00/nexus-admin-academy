import { describe, expect, it } from 'vitest';

import {
  REMOTE_DESKTOP_SCENARIOS,
  getRemoteDesktopScenarioByTicket,
} from './remote-desktop-fixtures';
import { getFixtureTicket } from './ticket-fixtures';

describe('Phase 18 fixtures', () => {
  it('defines phase-aware objectives for the three complete tickets only', () => {
    for (const ticketId of ['INC2406', 'INC2407', 'INC2408']) {
      const scenario = getRemoteDesktopScenarioByTicket(ticketId);
      expect(scenario?.workflow).toMatchObject({
        close: { explicit: true },
        note: { minimumLength: 20 },
      });
      expect(scenario?.workflow?.diagnose.length).toBeGreaterThan(0);
      expect(scenario?.workflow?.fix.length).toBeGreaterThan(0);
      expect(scenario?.workflow?.verify.length).toBeGreaterThan(0);
    }

    for (const id of [
      'pdf-export-update',
      'profile-storage',
      'network-configuration',
      'mapped-drive-permissions',
    ]) {
      expect(
        REMOTE_DESKTOP_SCENARIOS.find((scenario) => scenario.id === id)
          ?.workflow,
      ).toBeUndefined();
    }
  });

  it('suggests Remote Desktop for every ticket wired to an existing legacy scenario', () => {
    for (const ticketId of ['INC2401', 'INC2402', 'INC2405']) {
      expect(getFixtureTicket(ticketId)?.suggestedTools).toContain(
        'remote-desktop',
      );
    }
  });
});
