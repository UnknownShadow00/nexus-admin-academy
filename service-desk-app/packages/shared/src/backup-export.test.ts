import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  ATTEMPT_STORAGE_KEY,
  applyBackup,
  exportBackup,
  validateBackup,
  type AttemptCodec,
} from './backup-export';
import {
  SCENARIO_STORAGE_KEY,
  listScenarios,
  saveDraftVersion,
} from './scenario-storage';
import {
  TEST_STUDENT_STORAGE_KEY,
  getTestAttemptStorageKey,
  listTestStudents,
} from './test-student-storage';
import { Priority, TicketCategory } from './enums';
import type { ScenarioVersionDraftData } from './scenario-types';

interface TestAttempt {
  attemptId: string;
  points: number;
}

class MemoryStorage {
  private values = new Map<string, string>();

  clear() {
    this.values.clear();
  }

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

const attemptCodec: AttemptCodec<TestAttempt> = {
  restoreAttempt(serialized) {
    try {
      const parsed = JSON.parse(serialized) as Partial<TestAttempt>;
      return typeof parsed.attemptId === 'string' &&
        typeof parsed.points === 'number'
        ? (parsed as TestAttempt)
        : null;
    } catch {
      return null;
    }
  },
  serializeAttempt: JSON.stringify,
};

function draft(): ScenarioVersionDraftData {
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
    title: 'VPN outage',
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

describe('backup export and import', () => {
  it('round-trips the main attempt, scenarios, test students, and slot attempts', () => {
    const mainAttempt = { attemptId: 'main-attempt', points: 450 };
    const testAttempt = { attemptId: 'slot-attempt', points: 125 };
    const slot = {
      assignedScenarioIds: ['scenario-1'],
      createdAt: '2026-07-29T12:00:00.000Z',
      id: 'slot-1',
      name: 'Test Student',
    };

    globalThis.localStorage.setItem(
      ATTEMPT_STORAGE_KEY,
      attemptCodec.serializeAttempt(mainAttempt),
    );
    saveDraftVersion('scenario-1', draft());
    globalThis.localStorage.setItem(
      TEST_STUDENT_STORAGE_KEY,
      JSON.stringify([slot]),
    );
    globalThis.localStorage.setItem(
      getTestAttemptStorageKey(slot.id),
      attemptCodec.serializeAttempt(testAttempt),
    );

    const backup = exportBackup(attemptCodec);
    const serializedBackup = JSON.stringify(backup);
    expect(validateBackup(serializedBackup, attemptCodec)).toMatchObject({
      adminScenarioCount: 1,
      formatVersion: 1,
      studentAttempt: true,
      testAttemptCount: 1,
      testStudentCount: 1,
    });

    globalThis.localStorage.clear();
    applyBackup(serializedBackup, attemptCodec);

    expect(
      attemptCodec.restoreAttempt(
        globalThis.localStorage.getItem(ATTEMPT_STORAGE_KEY) ?? '',
      ),
    ).toEqual(mainAttempt);
    expect(listScenarios()).toEqual(backup.adminScenarios);
    expect(listTestStudents()).toEqual([slot]);
    expect(
      attemptCodec.restoreAttempt(
        globalThis.localStorage.getItem(getTestAttemptStorageKey(slot.id)) ??
          '',
      ),
    ).toEqual(testAttempt);
  });

  it('uses null attempts safely and replaces stale imported stores', () => {
    globalThis.localStorage.setItem(
      ATTEMPT_STORAGE_KEY,
      attemptCodec.serializeAttempt({ attemptId: 'old', points: 1 }),
    );
    globalThis.localStorage.setItem(
      TEST_STUDENT_STORAGE_KEY,
      JSON.stringify([
        {
          assignedScenarioIds: [],
          createdAt: '2026-07-29T12:00:00.000Z',
          id: 'old-slot',
          name: 'Old Student',
        },
      ]),
    );
    globalThis.localStorage.setItem(
      getTestAttemptStorageKey('old-slot'),
      attemptCodec.serializeAttempt({ attemptId: 'old-slot', points: 1 }),
    );

    const backup = {
      adminScenarios: [],
      exportedAt: '2026-07-29T13:00:00.000Z',
      formatVersion: 1,
      studentAttempt: null,
      testStudents: [],
    };

    applyBackup(JSON.stringify(backup), attemptCodec);

    expect(globalThis.localStorage.getItem(ATTEMPT_STORAGE_KEY)).toBeNull();
    expect(globalThis.localStorage.getItem(SCENARIO_STORAGE_KEY)).toBe(
      JSON.stringify({ templates: [], versions: [] }),
    );
    expect(listTestStudents()).toEqual([]);
    expect(
      globalThis.localStorage.getItem(getTestAttemptStorageKey('old-slot')),
    ).toBeNull();
  });

  it.each([
    ['malformed JSON', '{not-json'],
    [
      'unsupported version',
      JSON.stringify({
        adminScenarios: [],
        exportedAt: '2026-07-29T13:00:00.000Z',
        formatVersion: 2,
        studentAttempt: null,
        testStudents: [],
      }),
    ],
    [
      'malformed attempt',
      JSON.stringify({
        adminScenarios: [],
        exportedAt: '2026-07-29T13:00:00.000Z',
        formatVersion: 1,
        studentAttempt: { points: 'invalid' },
        testStudents: [],
      }),
    ],
  ])('rejects a %s payload without writing', (_label, payload) => {
    globalThis.localStorage.setItem('sentinel', 'unchanged');

    expect(() => validateBackup(payload, attemptCodec)).toThrow();
    expect(() => applyBackup(payload, attemptCodec)).toThrow();
    expect(globalThis.localStorage.getItem('sentinel')).toBe('unchanged');
  });
});
