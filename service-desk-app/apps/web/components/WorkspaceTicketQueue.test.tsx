import { TICKET_FIXTURES } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { WorkspaceTicketQueue } from './WorkspaceTicketQueue';

const tickets = TICKET_FIXTURES.slice(0, 2);

describe('WorkspaceTicketQueue', () => {
  it('shows real ticket data with one selected ticket and route links', () => {
    const markup = renderToStaticMarkup(
      <WorkspaceTicketQueue
        assignmentByTicket={{}}
        selectedTicketId={tickets[1]!.id}
        tickets={tickets}
      />,
    );
    expect(markup).toContain('aria-label="Ticket queue"');
    expect(markup.match(/aria-current="page"/g)).toHaveLength(1);
    for (const ticket of tickets) {
      expect(markup).toContain(ticket.id);
      expect(markup).toContain(ticket.title);
      expect(markup).toContain(ticket.requester.name);
      expect(markup).toContain(`/tickets/${ticket.id}`);
    }
    expect(markup).not.toContain('SLA clock');
  });

  it('keeps an empty queue distinct from a selected ticket', () => {
    const markup = renderToStaticMarkup(
      <WorkspaceTicketQueue
        assignmentByTicket={{}}
        selectedTicketId="INC9999"
        tickets={[]}
      />,
    );
    expect(markup).toContain('No tickets available.');
    expect(markup).not.toContain('aria-current="page"');
  });
});
