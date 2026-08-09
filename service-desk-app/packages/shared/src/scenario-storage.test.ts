import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Priority, TicketCategory } from './enums';
import {
  SCENARIO_STORAGE_KEY,
  getScenario,
  publishVersion,
  saveDraftVersion,
} from './scenario-storage';
import type { ScenarioVersionDraftData } from './scenario-types';

class MemoryStorage {
  private values = new Map<string, string>();
  getItem(key: string) {
    return this.values.get(key) ?? null;
  }
  removeItem(key: string) {
    this.values.delete(key);
  }
  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

function draft(title = 'VPN outage'): ScenarioVersionDraftData {
  return {
    category: TicketCategory.Network,
    description: {
      businessImpact: 'Remote work is blocked.',
      issue: 'VPN will not connect.',
      reportedByLine: 'Reported through the portal.',
      troubleshooting: ['Restarted the client.'],
    },
    device: {
      assetTag: 'NX-1000',
      deviceName: 'Finance laptop',
      kind: 'laptop',
      operatingSystem: 'Windows 11',
      state: 'active',
    },
    difficulty: 'medium',
    explanation: 'Repair the account state before closing.',
    forbiddenActions: [],
    hints: [],
    initialWorldState: {
      assetOverlaySeeds: {},
      chatMessageSeeds: [],
      directoryOverlaySeeds: {},
    },
    objectives: [],
    pointValue: 100,
    priority: Priority.High,
    requester: {
      contact: '555-0100',
      department: 'Finance',
      email: 'user@example.test',
      location: 'Remote',
      name: 'Taylor Reed',
    },
    requiredActions: [],
    sla: { dueAt: '2026-08-01T12:00:00.000Z', target: '4 hours' },
    slug: 'vpn-outage',
    title,
  };
}

beforeEach(() => {
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: new MemoryStorage(),
  });
});

afterEach(() => {
  Reflect.deleteProperty(globalThis, 'localStorage');
});

describe('scenario storage versioning', () => {
  it('updates the same unpublished draft', () => {
    const first = saveDraftVersion('scenario-1', draft());
    const second = saveDraftVersion('scenario-1', draft('Updated title'));

    expect(second.versions).toHaveLength(1);
    expect(second.versions[0]?.id).toBe(first.versions[0]?.id);
    expect(second.template.title).toBe('Updated title');
  });

  it('publishes immutably and creates a new version for later edits', () => {
    saveDraftVersion('scenario-1', draft());
    const published = publishVersion('scenario-1');
    const immutable = structuredClone(published.versions[0]);
    const edited = saveDraftVersion('scenario-1', draft('Version two'));

    expect(edited.versions).toHaveLength(2);
    expect(edited.versions[0]).toEqual(immutable);
    expect(edited.versions[0]?.publishedAt).not.toBeNull();
    expect(edited.versions[1]).toMatchObject({
      publishedAt: null,
      version: 2,
    });
    expect(edited.template.activeVersionId).toBe(immutable?.id);
    expect(getScenario('scenario-1')?.versions[0]).toEqual(immutable);
  });

  it('falls back safely when stored JSON is invalid', () => {
    globalThis.localStorage.setItem(SCENARIO_STORAGE_KEY, '{broken');
    expect(getScenario('missing')).toBeNull();
  });
});
