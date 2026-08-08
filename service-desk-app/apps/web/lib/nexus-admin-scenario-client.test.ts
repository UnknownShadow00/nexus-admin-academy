import { afterEach, describe, expect, it, vi } from 'vitest';

import { Priority, TicketCategory, type ScenarioVersionDraftData } from '@service-desk/shared';

import {
  getServerScenario,
  listServerScenarios,
  publishServerScenario,
  saveServerScenario,
  validateServerScenario,
} from './nexus-admin-scenario-client';

const definition: ScenarioVersionDraftData = {
  category: TicketCategory.Software,
  description: {
    businessImpact: 'Onboarding packs cannot be printed.',
    issue: 'Print jobs disappear.',
    reportedByLine: 'Employee portal.',
    troubleshooting: ['A second PC can print.'],
  },
  device: {
    assetTag: 'NX-1', deviceName: 'PC-1', kind: 'desktop',
    operatingSystem: 'Windows 11', state: 'active',
  },
  difficulty: 'easy',
  explanation: 'The local spooler failed.',
  forbiddenActions: [],
  hints: [
    { id: 'h1', order: 1, pointPenalty: 0, text: 'Localize the fault.' },
    { id: 'h2', order: 2, pointPenalty: 5, text: 'Check services.' },
    { id: 'h3', order: 3, pointPenalty: 5, text: 'Check Print Spooler.' },
  ],
  initialWorldState: { assetOverlaySeeds: {}, chatMessageSeeds: [], directoryOverlaySeeds: {} },
  objectives: [{
    description: 'Restart spooler', id: 'o1', order: 1, pointValue: 100,
    predicateParams: { actionType: 'ticket.add_note', payloadMatch: { ticketId: 'PRINTER-QUEUE' } },
    predicateType: 'action_event_occurred', required: true,
  }],
  pointValue: 100,
  priority: Priority.Medium,
  requester: {
    contact: 'Ext 1', department: 'HR', email: 'a@example.test',
    location: 'HQ', name: 'Avery',
  },
  requiredActions: [],
  sla: { dueAt: '2026-08-08T12:00:00Z', target: '4 hours' },
  slug: 'printer-queue',
  title: 'Printer queue',
};

function scenario(status: 'draft' | 'published' = 'draft') {
  return {
    category: 'software', created_at: '2026-08-08T00:00:00Z', description: definition.description.issue,
    difficulty: 1, id: 7, stable_key: definition.slug, status: 'active', title: definition.title,
    versions: [{
      created_at: '2026-08-08T00:00:00Z', definition_json: definition,
      definition_hash: 'a'.repeat(64),
      id: 11, published_at: status === 'published' ? '2026-08-08T01:00:00Z' : null,
      scenario_id: 7, status, validation_errors: [], validation_status: 'valid', version_number: 1,
    }],
  };
}

afterEach(() => vi.unstubAllGlobals());

describe('admin scenario client', () => {
  it('persists, reloads, validates, and publishes through admin APIs', async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      const body = init?.body ? JSON.parse(String(init.body)) : null;
      if (path.endsWith('/validate')) return Promise.resolve(Response.json({ valid: true, errors: [] }));
      if (path.endsWith('/publish')) return Promise.resolve(Response.json({ ok: true }));
      if (init?.method === 'POST' && path.endsWith('/scenarios')) {
        expect(body.definition_json.title).toBe('Printer queue');
        return Promise.resolve(Response.json(scenario(), { status: 201 }));
      }
      return Promise.resolve(Response.json(path.endsWith('/scenarios') ? [scenario()] : scenario('published')));
    });
    vi.stubGlobal('fetch', fetchMock);

    const saved = await saveServerScenario(null, definition);
    expect(saved.template.id).toBe('7');
    await expect(listServerScenarios()).resolves.toHaveLength(1);
    await expect(getServerScenario('7')).resolves.toMatchObject({ template: { title: 'Printer queue' } });
    await expect(validateServerScenario('7', '11')).resolves.toEqual({ valid: true, errors: [] });
    const published = await publishServerScenario('7', '11');
    expect(published.template.activeVersionId).toBe('11');
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/admin/service-desk/scenarios/7/versions/11/publish',
      expect.objectContaining({ credentials: 'same-origin', method: 'POST' }),
    );
  });
});
