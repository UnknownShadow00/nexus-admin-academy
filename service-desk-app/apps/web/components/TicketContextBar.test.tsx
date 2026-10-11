import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { getFixtureTicket, TicketStatus } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';
import { TicketContextBar } from './TicketContextBar';
import type { NexusAssignment } from '../lib/nexus-service-desk-client';

const ticket = getFixtureTicket('INC2501')!;
const assignment = {
  experience_mode: 'practice',
  guided_completed: true,
  maximum_attempts: null,
  most_recent_attempt: {
    id: 12,
    experience_mode: 'assessment',
    attempt_number: 1,
    status: 'completed',
  },
} as NexusAssignment;

describe('result header uses completed attempt mode', () => {
  it('labels the historical assessment even when future launches are practice', () => {
    const markup = renderToStaticMarkup(
      <TicketContextBar
        assignment={assignment}
        ticket={ticket}
        completed
        resultExperienceMode="assessment"
      />,
    );
    expect(markup).toContain('Independent assessment');
    expect(markup).not.toContain('Independent replay');
    expect(markup).not.toContain('Complete it independently');
  });
  it.each(['practice', 'guided'] as const)(
    'keeps %s results distinct',
    (mode) => {
      const markup = renderToStaticMarkup(
        <TicketContextBar
          assignment={assignment}
          ticket={ticket}
          completed
          resultExperienceMode={mode}
        />,
      );
      expect(markup).toContain(
        mode === 'guided' ? 'Guided Practice' : 'Independent replay',
      );
      expect(markup).not.toContain('Independent assessment');
    },
  );
  it('does not guess an unknown completed mode but preserves the active practice mode', () => {
    expect(
      renderToStaticMarkup(
        <TicketContextBar assignment={assignment} ticket={ticket} completed />,
      ),
    ).not.toContain('Independent replay');
    expect(
      renderToStaticMarkup(
        <TicketContextBar assignment={assignment} ticket={ticket} />,
      ),
    ).toContain('Independent replay');
  });
  it('uses stored result status rather than the initial scenario status after reload', () => {
    const markup = renderToStaticMarkup(
      <TicketContextBar
        ticket={{ ...ticket, status: TicketStatus.Open }}
        completed
        resultStatus={TicketStatus.Resolved}
      />,
    );
    expect(markup).toContain('>Resolved<');
    expect(markup).not.toContain('>Open<');
    expect(
      renderToStaticMarkup(<TicketContextBar ticket={ticket} completed />),
    ).not.toContain('Ticket status');
    expect(
      renderToStaticMarkup(
        <TicketContextBar
          ticket={{ ...ticket, status: TicketStatus.Pending }}
        />,
      ),
    ).toContain('>Pending<');
  });
});
