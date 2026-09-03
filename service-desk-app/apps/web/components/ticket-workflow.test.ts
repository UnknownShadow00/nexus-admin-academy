import { TicketStatus, type Ticket } from '@service-desk/shared';
import { describe, expect, it } from 'vitest';
import { ticketWorkflowState } from './ticket-workflow';

const ticket = { assignedTo: 'you', activity: [], escalated: false, notes: [], status: TicketStatus.InProgress } as unknown as Ticket;

describe('ticketWorkflowState', () => {
  it('derives stages from real ticket activity, notes, and status', () => {
    const stages = ticketWorkflowState({ ...ticket, activity: [
      { id: '1', label: 'Evidence inspected', detail: 'Account reviewed', timestamp: '2026-01-01' },
      { id: '2', label: 'Diagnosis recorded', detail: 'Root cause found', timestamp: '2026-01-01' },
    ], notes: [{ id: 'n', body: 'Documented', createdAt: '2026-01-01' }] });
    expect(stages.find((stage) => stage.key === 'investigate')?.complete).toBe(true);
    expect(stages.find((stage) => stage.key === 'diagnose')?.complete).toBe(true);
    expect(stages.find((stage) => stage.key === 'document')?.complete).toBe(true);
    expect(stages.find((stage) => stage.key === 'fix')?.current).toBe(true);
  });
});
