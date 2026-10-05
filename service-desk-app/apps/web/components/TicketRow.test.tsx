import { TICKET_FIXTURES } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { NexusAssignment } from '../lib/nexus-service-desk-client';
import { TicketRow } from './TicketRow';

const ticket = TICKET_FIXTURES[0]!;

describe('TicketRow', () => {
  it('does not invent an assessment mode without an assignment', () => {
    const markup = renderToStaticMarkup(<TicketRow ticket={ticket} />);
    expect(markup).toContain(ticket.id);
    expect(markup).not.toContain('Independent assessment');
    expect(markup).not.toContain('Due in');
  });

  it('names the actual assignment mode', () => {
    const assignment = {
      experience_mode: 'guided',
      required_this_week: true,
    } as NexusAssignment;
    const markup = renderToStaticMarkup(
      <TicketRow assignment={assignment} ticket={ticket} />,
    );
    expect(markup).toContain('Guided practice');
    expect(markup).toContain('Required this week');
  });
});
