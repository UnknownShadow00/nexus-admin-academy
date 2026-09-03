import { TicketStatus, type Ticket } from '@service-desk/shared';

export const WORKFLOW_COPY = [
  { key: 'understand', label: 'Understand', help: 'Read what the user reports and what work is affected.' },
  { key: 'investigate', label: 'Investigate', help: 'Find out what is actually happening before you change anything.' },
  { key: 'diagnose', label: 'Diagnose', help: 'Decide what is causing the problem based on your evidence.' },
  { key: 'fix', label: 'Fix / Escalate', help: 'Make a safe change, or send the ticket to the right team.' },
  { key: 'verify', label: 'Verify', help: 'Prove the original problem is gone.' },
  { key: 'document', label: 'Document', help: 'Write down what you found, changed, and verified.' },
] as const;

export function ticketWorkflowState(ticket: Ticket) {
  const activity = ticket.activity.map((event) => `${event.label} ${event.detail ?? ''}`.toLowerCase()).join(' ');
  const hasWork = ticket.activity.length > 0 || ticket.assignedTo === 'you';
  const done = {
    understand: hasWork,
    investigate: /inspect|investigat|connect|test|check|evidence|reviewed/.test(activity),
    diagnose: /diagnos|root cause/.test(activity),
    fix: ticket.escalated || /fix|repair|reset|unlock|changed|updated|remediat|escalat/.test(activity),
    verify: /verif|confirm|working outcome|original symptom/.test(activity),
    document: ticket.notes.length > 0,
  };
  if ([TicketStatus.Resolved, TicketStatus.Closed].includes(ticket.status)) {
    Object.keys(done).forEach((key) => { done[key as keyof typeof done] = true; });
  }
  const current = WORKFLOW_COPY.find((stage) => !done[stage.key])?.key ?? 'document';
  return WORKFLOW_COPY.map((stage) => ({ ...stage, complete: done[stage.key], current: stage.key === current && !done[stage.key] }));
}
