export type NexusSyncStatus = 'saved' | 'saving' | 'problem';

export interface NexusOutboxItem {
  assignmentId: string | number;
  attemptId?: string | number;
  completion?: { idempotency_key: string };
  event: {
    event_type: string;
    idempotency_key: string;
    payload: Readonly<Record<string, unknown>>;
    resulting_state: Readonly<Record<string, unknown>>;
    success: boolean;
    tool: string;
  };
  isHint: boolean;
  /** A resume-only write: no simulation action is submitted to Nexus. */
  isSnapshot?: boolean;
  ticketId: string;
}

export interface NexusOutbox {
  items: NexusOutboxItem[];
}

const OUTBOX_VERSION = 1;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isItem(value: unknown): value is NexusOutboxItem {
  return isRecord(value) &&
    (typeof value.assignmentId === 'string' || typeof value.assignmentId === 'number') &&
    typeof value.ticketId === 'string' &&
    typeof value.isHint === 'boolean' &&
    (value.isSnapshot === undefined || typeof value.isSnapshot === 'boolean') &&
    isRecord(value.event) && typeof value.event.idempotency_key === 'string' &&
    typeof value.event.event_type === 'string' && typeof value.event.tool === 'string' &&
    isRecord(value.event.payload) && isRecord(value.event.resulting_state) &&
    typeof value.event.success === 'boolean';
}

export function readNexusOutbox(storage: Storage, key: string): NexusOutbox {
  try {
    const value: unknown = JSON.parse(storage.getItem(key) ?? '');
    if (!isRecord(value) || value.version !== OUTBOX_VERSION || !Array.isArray(value.items)) {
      return { items: [] };
    }
    return { items: value.items.filter(isItem) };
  } catch {
    return { items: [] };
  }
}

export function writeNexusOutbox(storage: Storage, key: string, outbox: NexusOutbox): void {
  storage.setItem(key, JSON.stringify({ version: OUTBOX_VERSION, items: outbox.items }));
}

export function outboxStatus(outbox: NexusOutbox, failed: boolean): NexusSyncStatus {
  if (outbox.items.length === 0) return 'saved';
  return failed ? 'problem' : 'saving';
}
