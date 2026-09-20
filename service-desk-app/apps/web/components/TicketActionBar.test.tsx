import { getFixtureTicket } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { TicketActionBar } from './TicketActionBar';

let identity = { isAdmin: false, isMentor: false };
vi.mock('./TicketSessionProvider', () => ({
  useSessionIdentity: () => identity,
  useTicketSession: () => ({ assignTicket: vi.fn(), changeStatus: vi.fn(), unassignTicket: vi.fn() }),
}));
vi.mock('./AssignmentControls', () => ({ AssignmentControls: () => null }));
vi.mock('./StatusMenu', () => ({ StatusMenu: () => <select aria-label="Operational status" /> }));

describe('operational status editing', () => {
  it.each(['student', 'mentor', 'admin'])('preserves the %s boundary', (role) => {
    identity = { isAdmin: role === 'admin', isMentor: role === 'mentor' };
    const ticket = getFixtureTicket('INC2403')!;
    const html = renderToStaticMarkup(<TicketActionBar ticket={ticket} />);
    expect(html.includes('<select')).toBe(role !== 'student');
    if (role === 'student') expect(html).toContain('Operational status:');
  });
});
