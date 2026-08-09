import { describe, expect, it } from 'vitest';

import { Priority } from './enums';
import { TICKET_FIXTURES } from './ticket-fixtures';
import {
  filterTickets,
  formatDueIndicator,
  formatRelativeTime,
  getCloseReview,
  getStatusTransitions,
  initialHintRevealCount,
  nextHintRevealCount,
} from './ticket-logic';
import { TicketStatus } from './ticket-types';

describe('ticket filtering', () => {
  it('matches incident IDs, titles, and requester names without case sensitivity', () => {
    expect(
      filterTickets(TICKET_FIXTURES, {
        priority: 'all',
        query: 'inc2402',
        status: 'all',
      }).map((ticket) => ticket.id),
    ).toEqual(['INC2402']);

    expect(
      filterTickets(TICKET_FIXTURES, {
        priority: 'all',
        query: 'harper',
        status: 'all',
      }).map((ticket) => ticket.id),
    ).toEqual(['INC2406']);
  });

  it('combines priority and status filters', () => {
    expect(
      filterTickets(TICKET_FIXTURES, {
        priority: Priority.High,
        query: '',
        status: TicketStatus.Open,
      }).map((ticket) => ticket.id),
    ).toEqual(['INC2406', 'INC2407', 'INC2408']);
  });
});

describe('ticket actions', () => {
  it('offers only declared status transitions', () => {
    expect(getStatusTransitions(TicketStatus.Resolved)).toEqual([
      TicketStatus.InProgress,
      TicketStatus.Closed,
    ]);
    expect(getStatusTransitions(TicketStatus.Closed)).toEqual([
      TicketStatus.Open,
    ]);
  });

  it('caps the progressive hint counter at the available step count', () => {
    expect(initialHintRevealCount(4)).toBe(1);
    expect(nextHintRevealCount(1, 4)).toBe(2);
    expect(nextHintRevealCount(4, 4)).toBe(4);
    expect(initialHintRevealCount(0)).toBe(0);
  });

  it('requires a warning review when an unresolved ticket is closed', () => {
    expect(getCloseReview(TicketStatus.InProgress, false).kind).toBe(
      'unresolved-warning',
    );
    expect(getCloseReview(TicketStatus.InProgress, true).kind).toBe('ready');
    expect(getCloseReview(TicketStatus.Resolved, false).kind).toBe('ready');
  });
});

describe('ticket timing labels', () => {
  it('formats stable relative and SLA labels', () => {
    expect(
      formatRelativeTime(
        '2026-07-28T09:30:00.000Z',
        '2026-07-28T10:30:00.000Z',
      ),
    ).toBe('1h ago');
    expect(
      formatDueIndicator(
        '2026-07-28T11:45:00.000Z',
        '2026-07-28T10:30:00.000Z',
      ),
    ).toBe('Due in 1h 15m');
  });
});
