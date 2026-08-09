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
  /** Persisted data needed recovery; the UI must not claim everything is saved. */
  recoveryIssue?: boolean;
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
  const raw = storage.getItem(key);
  if (raw === null) return { items: [] };
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || value.version !== OUTBOX_VERSION || !Array.isArray(value.items)) {
      preserveCorruptOutbox(storage, key, raw);
      return { items: [], recoveryIssue: true };
    }
    const items = value.items.filter(isItem);
    if (items.length !== value.items.length) {
      preserveCorruptOutbox(storage, key, raw);
      return { items, recoveryIssue: true };
    }
    return { items };
  } catch (error) {
    preserveCorruptOutbox(storage, key, raw);
    console.error('Nexus preserved a corrupt sync outbox for recovery.', error);
    return { items: [], recoveryIssue: true };
  }
}

function preserveCorruptOutbox(storage: Storage, key: string, raw: string): void {
  const backupKey = `${key}:corrupt-backup`;
  try {
    if (storage.getItem(backupKey) === null) storage.setItem(backupKey, raw);
  } catch (error) {
    console.error('Nexus could not back up a corrupt sync outbox.', error);
  }
}

export function writeNexusOutbox(storage: Storage, key: string, outbox: NexusOutbox): void {
  storage.setItem(key, JSON.stringify({ version: OUTBOX_VERSION, items: outbox.items }));
}

export function outboxStatus(outbox: NexusOutbox, failed: boolean): NexusSyncStatus {
  if (outbox.recoveryIssue) return 'problem';
  if (outbox.items.length === 0) return 'saved';
  return failed ? 'problem' : 'saving';
}
