import { describe, expect, it } from 'vitest';

import inventory from '../../../../docs/service_desk_v2_assessment_inventory.json';
import { applyAction } from './apply-action';
import { createAttempt } from './attempt';

function exerciseCurriculumRows() {
  return inventory.rows.map((row) => {
    const noted = applyAction(createAttempt(), 'p0-student', {
      type: 'ticket.add_note' as const,
      payload: {
        ticketId: row.ticket_id,
        body: 'Restarted computer and issue resolved.',
      },
    });
    const connected = applyAction(createAttempt(), 'p0-student', {
      type: 'remote_desktop.connect' as const,
      payload: {
        ticketId: row.ticket_id,
        assetTag: row.asset_tag,
      },
    });
    const login = applyAction(connected.attempt, 'p0-student', {
      type: 'remote_desktop.begin_login' as const,
      payload: {
        ticketId: row.ticket_id,
        assetTag: row.asset_tag,
      },
    });
    const authenticated = applyAction(login.attempt, 'p0-student', {
      type: 'remote_desktop.authenticate' as const,
      payload: {
        ticketId: row.ticket_id,
        assetTag: row.asset_tag,
        passwordEntered: true,
        usernameEntered: true,
      },
    });
    const opened = applyAction(authenticated.attempt, 'p0-student', {
      type: 'remote_desktop.open_app' as const,
      payload: { assetTag: row.asset_tag, appId: 'terminal' as const },
    });
    return { row, noted, opened };
  });
}

describe('P0 Finding B — V2 curriculum scenario operability', () => {
  it('records the exact note-only engine rejection baseline', () => {
    const failures = exerciseCurriculumRows().filter(
      ({ noted, opened }) => !noted.event.success || !opened.event.success,
    );

    expect(failures.map(({ row }) => row.assessment_key)).toEqual(
      inventory.rows
        .filter((row) => !row.browser_operable)
        .map((row) => row.assessment_key),
    );
    expect(failures).toHaveLength(6);
    for (const { noted, opened } of failures) {
      expect(noted.event.rejectReason).toBe(
        'The requested ticket does not exist in this simulation.',
      );
      expect(opened.event.rejectReason).toBe(
        'The requested workstation does not exist in this simulation.',
      );
    }
  });

  it(
    'applies a ticket note and Remote Desktop open action for every available curriculum assessment',
    () => {
      const failures: string[] = [];

      for (const { row, noted, opened } of exerciseCurriculumRows().filter(
        ({ row }) => row.active,
      )) {
        if (!noted.event.success || !opened.event.success) {
          failures.push(
            `${row.assessment_key}: ${[
              noted.event.rejectReason,
              opened.event.rejectReason,
            ]
              .filter(Boolean)
              .join(' / ')}`,
          );
        }
        expect(row.browser_operable).toBe(
          noted.event.success && opened.event.success,
        );
      }

      expect(inventory.rows.filter((row) => row.active)).toHaveLength(6);
      expect(failures).toEqual([]);
    },
  );
});
