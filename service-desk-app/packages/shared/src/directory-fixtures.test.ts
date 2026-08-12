import { describe, expect, it } from 'vitest';

import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  DIRECTORY_GROUP_NAMES,
  DIRECTORY_USER_FIXTURES,
  SLOANE_RIVERA_DIRECTORY_USER_ID,
} from './directory-fixtures';
import { TICKET_FIXTURES } from './ticket-fixtures';

describe('directory fixtures', () => {
  it('contains the directory roster and seven groups', () => {
    expect(DIRECTORY_USER_FIXTURES).toHaveLength(40);
    expect(DIRECTORY_GROUP_NAMES).toHaveLength(7);
    expect(new Set(DIRECTORY_USER_FIXTURES.map((user) => user.id)).size).toBe(
      40,
    );
    expect(
      new Set(DIRECTORY_USER_FIXTURES.map((user) => user.username)).size,
    ).toBe(40);
  });

  it.each([
    {
      directoryUserId: 'directory-user-taylor-morgan',
      ticketId: 'INC2511',
    },
    {
      directoryUserId: 'directory-user-jordan-lee',
      ticketId: 'INC2512',
    },
    {
      directoryUserId: 'directory-user-camille-reyes',
      ticketId: 'INC2513',
    },
    {
      directoryUserId: AVERY_BROOKS_DIRECTORY_USER_ID,
      ticketId: 'INC2401',
    },
    {
      directoryUserId: SLOANE_RIVERA_DIRECTORY_USER_ID,
      ticketId: 'INC2405',
    },
  ])(
    'matches $directoryUserId to the current $ticketId requester',
    ({ directoryUserId, ticketId }) => {
      const user = DIRECTORY_USER_FIXTURES.find(
        (candidate) => candidate.id === directoryUserId,
      );
      const ticket = TICKET_FIXTURES.find(
        (candidate) => candidate.id === ticketId,
      );

      expect(user?.fullName).toBe(ticket?.requester.name);
      expect(user?.department).toBe(ticket?.requester.department);
    },
  );
});
