import { applyAction, createAttempt } from '@service-desk/simulation-engine';
import {
  AssetStatus,
  TicketStatus,
  TICKET_FIXTURES,
} from '@service-desk/shared';
import { describe, expect, it } from 'vitest';

import {
  documentationTargetForTicket,
  getNexusActionSyncDetails,
  normalizeTicketKey,
  resolutionNoteAction,
  resetTicketStateForRetry,
  selectAssignmentsByTicket,
  ticketsForAssignments,
} from './TicketSessionProvider';
import type { NexusAssignment } from '../lib/nexus-service-desk-client';

function assignmentForMode(
  id: number,
  mode: 'learning' | 'simulation',
  guidedCompleted: boolean,
): NexusAssignment {
  return {
    id,
    is_required: true,
    latest_published_version: {
      definition_json: structuredClone(TICKET_FIXTURES[0]),
      id: 10,
      version_number: 2,
    },
    mode,
    experience_mode: mode === 'learning' ? 'guided' : 'assessment',
    guided_completed: guidedCompleted,
    most_recent_attempt: null,
    maximum_attempts: 3,
    required_this_week: true,
    scenario: { stable_key: TICKET_FIXTURES[0].id, title: TICKET_FIXTURES[0].title },
    scenario_id: 1,
  };
}

describe('resolution note routing', () => {
  it('uses the scenario workflow only when no server target is available', () => {
    expect(documentationTargetForTicket('INC2406')).toBe('remote_desktop');
    expect(documentationTargetForTicket('INC2511')).toBe('ticket');
    expect(documentationTargetForTicket('INC2406', 'ticket')).toBe('ticket');
  });

  it('routes each server documentation target to its graded event', () => {
    expect(
      resolutionNoteAction(
        'INC2511',
        'A sufficiently detailed note.',
        'ticket',
      ),
    ).toEqual({
      type: 'ticket.add_note',
      payload: { ticketId: 'INC2511', body: 'A sufficiently detailed note.' },
    });
    expect(
      resolutionNoteAction(
        'INC2401',
        'A sufficiently detailed note.',
        'remote_desktop',
        'NX-4831',
      ),
    ).toEqual({
      type: 'remote_desktop.add_internal_note',
      payload: {
        assetTag: 'NX-4831',
        ticketId: 'INC2401',
        text: 'A sufficiently detailed note.',
      },
    });
  });
});

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
    expect(details?.resultingState).toEqual({});
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
        guided_completed: false,
        most_recent_attempt: null,
        required_this_week: false,
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

  it('projects current authored scenarios with a valid runtime ticket status', () => {
    const definition = {
      id: 'SD.APLUS.WINDOWS_ADMIN.PROJECT_SHARE_AFTER_VPN',
      title: 'Project Share Fails After VPN Reconnect',
      category: 'service_desk',
      priority: 'medium',
      description: {
        issue: 'Mapped drive fails',
        reportedByLine: 'Jordan Lee',
        businessImpact: 'Project folder unavailable',
        troubleshooting: [],
      },
      requester: {
        name: 'Jordan Lee',
        department: 'Project Operations',
        email: 'jordan@example.test',
        contact: 'Chat',
        location: 'Remote',
      },
      device: {
        assetTag: 'PROJ-LT-22',
        deviceName: 'PROJ-LT-22',
        kind: 'laptop',
        operatingSystem: 'Windows 11 Pro',
        state: 'active',
      },
      sla: { dueAt: 'Today', target: 'medium' },
      hints: [{ id: 'hint-01', order: 1, text: 'Inspect the mapping.' }],
    };
    const [ticket] = ticketsForAssignments([
      {
        id: 11,
        is_required: true,
        maximum_attempts: null,
        mode: 'learning',
        experience_mode: 'guided',
        guided_completed: false,
        most_recent_attempt: null,
        required_this_week: false,
        scenario_id: 11,
        scenario: {
          stable_key: 'sd.aplus.windows_admin.project_share_after_vpn',
          title: definition.title,
        },
        latest_published_version: {
          definition_json: definition,
          id: 111,
          version_number: 1,
        },
      },
    ]);

    expect(ticket?.status).toBe(TicketStatus.Open);
    expect(ticket?.hints).toEqual(['Inspect the mapping.']);
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
        guided_completed: false,
        most_recent_attempt: null,
        required_this_week: false,
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

describe('assignment mode selection', () => {
  it('selects guided learning before completion regardless of row order', () => {
    const learning = assignmentForMode(2, 'learning', false);
    const simulation = assignmentForMode(1, 'simulation', false);

    expect(selectAssignmentsByTicket([learning, simulation])).toEqual([learning]);
    expect(selectAssignmentsByTicket([simulation, learning])).toEqual([learning]);
  });

  it('selects assessment/practice after guided completion regardless of row order', () => {
    const learning = assignmentForMode(2, 'learning', true);
    const simulation = assignmentForMode(1, 'simulation', true);

    expect(selectAssignmentsByTicket([learning, simulation])).toEqual([simulation]);
    expect(selectAssignmentsByTicket([simulation, learning])).toEqual([simulation]);
  });
});

describe('retry state isolation', () => {
  it('clears ticket-owned directory and device state without clobbering another ticket', () => {
    let attempt = createAttempt({ id: 'retry-state' });
    attempt = applyAction(attempt, 'student', {
      type: 'directory.inspect_account',
      payload: { directoryUserId: 'directory-user-taylor-morgan' },
    }).attempt;
    attempt = applyAction(attempt, 'student', {
      type: 'directory.inspect_account',
      payload: { directoryUserId: 'directory-user-jordan-lee' },
    }).attempt;
    attempt = applyAction(attempt, 'student', {
      type: 'device.inspect_record',
      payload: { ticketId: 'INC3001', deviceId: 'device-nex-lt-2214' },
    }).attempt;

    const directoryReset = resetTicketStateForRetry(attempt, 'INC2511');
    expect(
      directoryReset.directoryOverlays['directory-user-taylor-morgan'],
    ).toBeUndefined();
    expect(
      directoryReset.directoryOverlays['directory-user-jordan-lee'],
    ).toBeDefined();

    const deviceReset = resetTicketStateForRetry(directoryReset, 'INC3001');
    expect(deviceReset.ticketOverlays.INC3001).toBeUndefined();
    expect(
      deviceReset.directoryOverlays['directory-user-jordan-lee'],
    ).toBeDefined();
  });
});
