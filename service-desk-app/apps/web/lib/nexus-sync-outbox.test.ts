import { describe, expect, it } from 'vitest';

import { outboxStatus, readNexusOutbox, writeNexusOutbox } from './nexus-sync-outbox';

function storage(): Storage {
  const values = new Map<string, string>();
  return {
    clear: () => values.clear(), getItem: (key) => values.get(key) ?? null,
    key: () => null, get length() { return values.size; },
    removeItem: (key) => { values.delete(key); }, setItem: (key, value) => { values.set(key, value); },
  } as Storage;
}

const item = {
  assignmentId: 4, ticketId: 'INC2401', isHint: false,
  event: { event_type: 'ticket.assign', idempotency_key: 'event-1', payload: {}, resulting_state: {}, success: true, tool: 'ticket' },
};

describe('Nexus durable sync outbox', () => {
  it('survives refresh with its original idempotency key and order', () => {
    const local = storage();
    writeNexusOutbox(local, 'outbox', { items: [item, { ...item, event: { ...item.event, idempotency_key: 'event-2' } }] });
    expect(readNexusOutbox(local, 'outbox').items.map((entry) => entry.event.idempotency_key)).toEqual(['event-1', 'event-2']);
  });

  it('reports saving, then a retryable sync problem, without claiming saved', () => {
    const pending = { items: [item] };
    expect(outboxStatus(pending, false)).toBe('saving');
    expect(outboxStatus(pending, true)).toBe('problem');
    expect(outboxStatus({ items: [] }, false)).toBe('saved');
  });

  it('rejects malformed persisted data safely', () => {
    const local = storage();
    local.setItem('outbox', '{bad json');
    expect(readNexusOutbox(local, 'outbox')).toEqual({ items: [] });
  });
});
