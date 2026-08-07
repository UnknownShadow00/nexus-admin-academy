import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  completeAttempt,
  getAttempt,
  listAssignments,
  persistAttemptSnapshot,
  recordAttemptEvent,
  recordAttemptHint,
  startOrResumeAttempt,
} from './nexus-service-desk-client';

// IDs are plain integers on the wire (SQLAlchemy primary keys serialized as
// JSON numbers), not strings - these fixtures intentionally mirror that.
const attempt = {
  attempt_number: 1,
  completed_at: null,
  current_state: { status: 'open' },
  current_state_hash: 'hash',
  id: 101,
  mode: 'practice',
  passed: null,
  score: null,
  started_at: '2026-08-02T00:00:00Z',
  state_version: 1,
  status: 'in_progress',
};

const grade = {
  attempt_id: 101,
  critical_failure: false,
  feedback_summary: 'Complete',
  id: 201,
  overall_score: 100,
  passed: true,
  rubric_version: 'sim-engine-v1',
  scenario_version_id: 1,
  technical_complete: true,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Nexus service desk client', () => {
  it('calls all persistence endpoints with same-origin JSON requests', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const body = init?.body ? JSON.parse(String(init.body)) : undefined;
      const response = path.endsWith('/assignments')
        ? [
            {
              id: 1,
              is_required: true,
              latest_published_version: { id: 1, version_number: 1 },
              mode: 'practice',
              most_recent_attempt: null,
              maximum_attempts: null,
              scenario: { stable_key: 'INC2401', title: 'VPN' },
              scenario_id: 1,
            },
          ]
        : path.endsWith('/events') || path.endsWith('/hints')
          ? { accepted: true, body }
          : path.endsWith('/complete')
            ? grade
            : attempt;
      return Promise.resolve(
        new Response(JSON.stringify(response), { status: 200 }),
      );
    });
    vi.stubGlobal('fetch', fetchMock);

    await expect(listAssignments()).resolves.toHaveLength(1);
    await expect(startOrResumeAttempt(1)).resolves.toMatchObject({
      id: 101,
    });
    await expect(getAttempt(101)).resolves.toMatchObject({
      id: 101,
    });
    await expect(
      recordAttemptEvent(101, {
        event_type: 'ticket.assign',
        idempotency_key: 'event-1',
        payload: { ticketId: 'INC2401' },
        resulting_state: { status: 'open' },
        success: true,
        tool: 'ticket',
      }),
    ).resolves.toBe(true);
    await expect(
      recordAttemptHint(101, {
        idempotency_key: 'event-2',
        payload: { ticketId: 'INC2401', step: 1 },
        tool: 'ticket',
      }),
    ).resolves.toBe(true);
    await expect(
      persistAttemptSnapshot(101, {
        idempotency_key: 'snapshot-1',
        snapshot: { schema_version: 1, nexus_service_desk_attempt: {} },
      }),
    ).resolves.toBe(true);
    await expect(
      completeAttempt(101, {
        idempotency_key: 'event-3',
      }),
    ).resolves.toMatchObject({ id: 201, attempt_id: 101 });

    const completeCall = fetchMock.mock.calls.find(([input]) =>
      String(input).endsWith('/complete'),
    );
    expect(completeCall?.[1]?.body).toBe(
      JSON.stringify({ idempotency_key: 'event-3' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/service-desk/attempts/101/events',
      expect.objectContaining({ credentials: 'same-origin', method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/service-desk/attempts/101/snapshot',
      expect.objectContaining({ credentials: 'same-origin', method: 'POST' }),
    );
  });

  it('returns safe failure values for non-2xx responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('nope', { status: 503 })),
    );

    await expect(listAssignments()).resolves.toEqual([]);
    await expect(startOrResumeAttempt(1)).resolves.toBeNull();
    await expect(
      recordAttemptEvent(101, {
        event_type: 'ticket.assign',
        idempotency_key: 'event-1',
        payload: {},
        resulting_state: {},
        success: true,
        tool: 'ticket',
      }),
    ).resolves.toBe(false);
  });

  it('returns safe failure values when the network rejects', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('network down')),
    );

    await expect(getAttempt(101)).resolves.toBeNull();
    await expect(
      recordAttemptHint(101, {
        idempotency_key: 'event-1',
        payload: {},
        tool: 'ticket',
      }),
    ).resolves.toBe(false);
    await expect(
      completeAttempt(101, {
        idempotency_key: 'event-1',
      }),
    ).resolves.toBeNull();
  });
});
