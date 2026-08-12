import { createAttempt } from '@service-desk/simulation-engine';
import { AssetStatus, TICKET_FIXTURES } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import {
  getNexusActionSyncDetails,
  normalizeTicketKey,
  ticketsForAssignments,
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

  it('attributes the damaged headset and its replacement shipment to INC2404', () => {
    expect(
      getNexusActionSyncDetails(
        {
          type: 'asset.change_status',
          payload: { assetTag: 'NX-9052', status: AssetStatus.Damaged },
        },
        attempt,
      ),
    ).toMatchObject({ ticketId: 'INC2404', tool: 'asset' });

    expect(
      getNexusActionSyncDetails(
        {
          type: 'shipping.create',
          payload: {
            recipientDirectoryUserId: 'directory-user-elliot-ward',
            recipientName: 'Elliot Ward',
            street: '120 Cedar Street',
            city: 'Seattle',
            state: 'WA',
            postalCode: '98101',
            senderDepartment: 'IT Department',
            equipment: [{ name: 'Headset', quantity: 1 }],
            computerAssetTag: null,
            speed: 'express',
            includeReturnLabel: true,
          },
        },
        attempt,
      ),
    ).toMatchObject({ ticketId: 'INC2404', tool: 'shipping' });
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

  it('attributes structured requester verification and drive mapping evidence', () => {
    expect(
      getNexusActionSyncDetails(
        {
          type: 'chat.verify_identity',
          payload: {
            contactId: 'directory-user-taylor-morgan',
            ticketId: 'INC2511',
            method: 'employee-id-directory-match',
          },
        },
        attempt,
      ),
    ).toMatchObject({ ticketId: 'INC2511', tool: 'chat' });

    expect(
      getNexusActionSyncDetails(
        {
          type: 'remote_desktop.map_drive',
          payload: {
            assetTag: 'NX-6128',
            letter: 'Y:',
            uncPath: '\\\\facilities.nexus.internal\\calendar',
            reconnectAtSignIn: true,
            credentialTarget: null,
          },
        },
        attempt,
      ),
    ).toMatchObject({ ticketId: 'INC2405', tool: 'remote_desktop' });
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

  it('renders the exact published assignment definition instead of stale bundled copy', () => {
    const definition = {
      ...structuredClone(TICKET_FIXTURES[1]),
      title: 'Published v2 title from Nexus',
    };
    const tickets = ticketsForAssignments([
      {
        id: 1,
        is_required: false,
        maximum_attempts: null,
      mode: 'simulation',
      experience_mode: 'assessment',
        most_recent_attempt: null,
        scenario_id: 2,
        scenario: { stable_key: 'inc2402', title: definition.title },
        latest_published_version: {
          definition_json: definition,
          id: 22,
          version_number: 2,
        },
      },
    ]);
    expect(tickets).toHaveLength(1);
    expect(tickets.find((ticket) => ticket.id === 'INC2402')?.title).toBe(
      definition.title,
    );
  });

  it('does not reconstruct locked bundled fixtures that were not assigned', () => {
    const definition = structuredClone(TICKET_FIXTURES[4]);
    const tickets = ticketsForAssignments([
      {
        id: 2,
        is_required: false,
        maximum_attempts: null,
      mode: 'simulation',
      experience_mode: 'assessment',
        most_recent_attempt: null,
        scenario_id: 5,
        scenario: { stable_key: 'inc2405', title: definition.title },
        latest_published_version: {
          definition_json: definition,
          id: 25,
          version_number: 2,
        },
      },
    ]);

    expect(tickets.map((ticket) => ticket.id)).toEqual(['INC2405']);
  });
});
