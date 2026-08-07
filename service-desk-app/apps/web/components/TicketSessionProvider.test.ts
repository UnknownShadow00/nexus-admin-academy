import { createAttempt } from '@service-desk/simulation-engine';
import { describe, expect, it } from 'vitest';

import {
  getNexusActionSyncDetails,
  normalizeTicketKey,
} from './TicketSessionProvider';

describe('Nexus evidence attribution', () => {
  const attempt = createAttempt({ id: 'attempt-1' });

  it.each([
    ['directory-user-avery-brooks', 'INC2401'],
    ['directory-user-sloane-rivera', 'INC2405'],
  ])(
    'attributes known directory user %s to %s',
    (directoryUserId, ticketId) => {
      const details = getNexusActionSyncDetails(
        {
          type: 'directory.unlock_account',
          payload: { directoryUserId },
        },
        attempt,
      );

      expect(details).toMatchObject({ ticketId, tool: 'directory' });
      expect(details?.resultingState).toEqual({});
    },
  );

  it('keeps unrelated directory users local-only', () => {
    expect(
      getNexusActionSyncDetails(
        {
          type: 'directory.reset_password',
          payload: { directoryUserId: 'directory-user-unrelated' },
        },
        attempt,
      ),
    ).toBeNull();
  });

  it('uses the ticketId on Remote Desktop ticket-payload actions', () => {
    const details = getNexusActionSyncDetails(
      {
        type: 'remote_desktop.add_internal_note',
        payload: {
          assetTag: 'NX-2047',
          ticketId: 'inc2406',
          text: 'Found it.',
        },
      },
      attempt,
    );

    expect(details).toMatchObject({
      ticketId: 'inc2406',
      tool: 'remote_desktop',
    });
    expect(details?.resultingState).toEqual(
      attempt.remoteDesktopOverlays['NX-2047'],
    );
  });

  it('uses the asset reverse lookup for substantive asset-only actions', () => {
    const details = getNexusActionSyncDetails(
      {
        type: 'remote_desktop.run_terminal_command',
        payload: { assetTag: 'NX-2047', command: 'ipconfig' },
      },
      attempt,
    );

    expect(details).toMatchObject({
      ticketId: 'INC2406',
      tool: 'remote_desktop',
    });
  });

  it('keeps asset-only actions local-only when the asset has no scenario', () => {
    expect(
      getNexusActionSyncDetails(
        {
          type: 'remote_desktop.run_terminal_command',
          payload: { assetTag: 'NX-unknown', command: 'whoami' },
        },
        attempt,
      ),
    ).toBeNull();
  });

  it.each([
    'remote_desktop.open_app',
    'remote_desktop.close_app',
    'remote_desktop.focus_app',
    'remote_desktop.minimize_app',
    'remote_desktop.toggle_training_mode',
    'remote_desktop.set_learning_mode',
    'remote_desktop.cancel_connection',
  ] as const)('excludes UI-chrome action %s', (type) => {
    const payload =
      type === 'remote_desktop.open_app' ||
      type === 'remote_desktop.close_app' ||
      type === 'remote_desktop.focus_app' ||
      type === 'remote_desktop.minimize_app'
        ? { appId: 'terminal' as const, assetTag: 'NX-2047' }
        : type === 'remote_desktop.toggle_training_mode'
          ? { assetTag: 'NX-2047', enabled: true }
          : type === 'remote_desktop.set_learning_mode'
            ? { assetTag: 'NX-2047', mode: 'guided' as const }
            : { assetTag: 'NX-2047' };

    expect(
      getNexusActionSyncDetails(
        { type, payload } as Parameters<typeof getNexusActionSyncDetails>[0],
        attempt,
      ),
    ).toBeNull();
  });

  it('normalizes ticket keys for Nexus assignment lookup', () => {
    expect(normalizeTicketKey('inc2406')).toBe('INC2406');
    expect(normalizeTicketKey(' Inc2406 ')).toBe(' INC2406 ');
  });
});
