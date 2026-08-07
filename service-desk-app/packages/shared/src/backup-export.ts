import { SCENARIO_STORAGE_KEY, listScenarios } from './scenario-storage';
import {
  TEST_STUDENT_STORAGE_KEY,
  getTestAttemptStorageKey,
  listTestStudents,
  type TestStudentSlot,
} from './test-student-storage';
import type {
  ScenarioRecord,
  ScenarioTemplate,
  ScenarioVersion,
} from './scenario-types';

export const ATTEMPT_STORAGE_KEY = 'nexus-sd-attempt-v1';
export const BACKUP_FORMAT_VERSION = 1 as const;

interface StorageLike {
  getItem(key: string): string | null;
  removeItem(key: string): void;
  setItem(key: string, value: string): void;
}

export interface AttemptCodec<TAttempt> {
  restoreAttempt(serialized: string): TAttempt | null;
  serializeAttempt(attempt: TAttempt): string;
}

export interface BackupTestStudent<TAttempt> {
  attempt: TAttempt | null;
  slot: TestStudentSlot;
}

export interface ServiceDeskBackup<TAttempt> {
  formatVersion: typeof BACKUP_FORMAT_VERSION;
  exportedAt: string;
  studentAttempt: TAttempt | null;
  adminScenarios: ScenarioRecord[];
  testStudents: BackupTestStudent<TAttempt>[];
}

export interface BackupValidationReport {
  adminScenarioCount: number;
  exportedAt: string;
  formatVersion: typeof BACKUP_FORMAT_VERSION;
  studentAttempt: boolean;
  testAttemptCount: number;
  testStudentCount: number;
}

function storage(): StorageLike | null {
  return (
    (
      globalThis as unknown as {
        localStorage?: StorageLike;
      }
    ).localStorage ?? null
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function isIsoDate(value: unknown): value is string {
  return (
    typeof value === 'string' &&
    value.includes('T') &&
    Number.isFinite(new Date(value).getTime())
  );
}

function isStringArray(value: unknown): value is string[] {
  return (
    Array.isArray(value) && value.every((entry) => typeof entry === 'string')
  );
}

function isScenarioTemplate(value: unknown): value is ScenarioTemplate {
  return (
    isRecord(value) &&
    (value.activeVersionId === null ||
      typeof value.activeVersionId === 'string') &&
    typeof value.category === 'string' &&
    isIsoDate(value.createdAt) &&
    typeof value.id === 'string' &&
    typeof value.priority === 'string' &&
    typeof value.slug === 'string' &&
    typeof value.title === 'string'
  );
}

function isScenarioVersion(value: unknown): value is ScenarioVersion {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.scenarioId === 'string' &&
    Number.isInteger(value.version) &&
    (value.publishedAt === null || isIsoDate(value.publishedAt)) &&
    isRecord(value.description) &&
    isRecord(value.device) &&
    typeof value.difficulty === 'string' &&
    typeof value.explanation === 'string' &&
    Array.isArray(value.forbiddenActions) &&
    Array.isArray(value.hints) &&
    isRecord(value.initialWorldState) &&
    Array.isArray(value.objectives) &&
    typeof value.pointValue === 'number' &&
    isRecord(value.requester) &&
    Array.isArray(value.requiredActions) &&
    isRecord(value.sla)
  );
}

function isScenarioRecord(value: unknown): value is ScenarioRecord {
  if (
    !isRecord(value) ||
    !isScenarioTemplate(value.template) ||
    !Array.isArray(value.versions)
  ) {
    return false;
  }
  const templateId = value.template.id;
  return value.versions.every(
    (version) =>
      isScenarioVersion(version) && version.scenarioId === templateId,
  );
}

function isTestStudentSlot(value: unknown): value is TestStudentSlot {
  return (
    isRecord(value) &&
    isStringArray(value.assignedScenarioIds) &&
    isIsoDate(value.createdAt) &&
    typeof value.id === 'string' &&
    value.id.length > 0 &&
    typeof value.name === 'string'
  );
}

function parseInput(json: string | unknown): unknown {
  if (typeof json !== 'string') {
    return json;
  }

  try {
    return JSON.parse(json) as unknown;
  } catch {
    throw new Error('The selected file is not valid JSON.');
  }
}

function restorePortableAttempt<TAttempt>(
  value: unknown,
  codec: AttemptCodec<TAttempt>,
  label: string,
): TAttempt | null {
  if (value === null) {
    return null;
  }

  let restored: TAttempt | null = null;
  try {
    restored = codec.restoreAttempt(JSON.stringify(value));
  } catch {
    // The consistent validation error below is more useful than codec details.
  }

  if (!restored) {
    throw new Error(`${label} is not a valid serialized attempt.`);
  }
  return restored;
}

function portableAttempt<TAttempt>(
  attempt: TAttempt,
  codec: AttemptCodec<TAttempt>,
): TAttempt {
  return JSON.parse(codec.serializeAttempt(attempt)) as TAttempt;
}

function readAttempt<TAttempt>(
  key: string,
  codec: AttemptCodec<TAttempt>,
): TAttempt | null {
  const raw = storage()?.getItem(key);
  if (!raw) {
    return null;
  }

  try {
    return codec.restoreAttempt(raw);
  } catch {
    return null;
  }
}

function parseAndValidate<TAttempt>(
  json: string | unknown,
  codec: AttemptCodec<TAttempt>,
): ServiceDeskBackup<TAttempt> {
  const parsed = parseInput(json);
  if (!isRecord(parsed)) {
    throw new Error('The backup must be a JSON object.');
  }
  if (parsed.formatVersion !== BACKUP_FORMAT_VERSION) {
    throw new Error(
      `Unsupported backup format version: ${String(parsed.formatVersion)}.`,
    );
  }
  if (!isIsoDate(parsed.exportedAt)) {
    throw new Error('The backup has an invalid exportedAt timestamp.');
  }
  if (
    !Array.isArray(parsed.adminScenarios) ||
    !parsed.adminScenarios.every(isScenarioRecord)
  ) {
    throw new Error('The backup contains invalid admin scenario data.');
  }
  if (!Array.isArray(parsed.testStudents)) {
    throw new Error('The backup contains invalid test-student data.');
  }

  const testStudents = parsed.testStudents.map((entry, index) => {
    if (!isRecord(entry) || !isTestStudentSlot(entry.slot)) {
      throw new Error(`Test student ${index + 1} is invalid.`);
    }
    return {
      attempt: restorePortableAttempt(
        entry.attempt,
        codec,
        `Test student ${index + 1} attempt`,
      ),
      slot: {
        ...entry.slot,
        assignedScenarioIds: [...entry.slot.assignedScenarioIds],
      },
    };
  });

  const uniqueSlotIds = new Set(testStudents.map(({ slot }) => slot.id));
  if (uniqueSlotIds.size !== testStudents.length) {
    throw new Error('The backup contains duplicate test-student IDs.');
  }

  return {
    formatVersion: BACKUP_FORMAT_VERSION,
    exportedAt: parsed.exportedAt,
    studentAttempt: restorePortableAttempt(
      parsed.studentAttempt,
      codec,
      'Student attempt',
    ),
    adminScenarios: parsed.adminScenarios.map((record) => clone(record)),
    testStudents,
  };
}

function report<TAttempt>(
  backup: ServiceDeskBackup<TAttempt>,
): BackupValidationReport {
  return {
    adminScenarioCount: backup.adminScenarios.length,
    exportedAt: backup.exportedAt,
    formatVersion: backup.formatVersion,
    studentAttempt: backup.studentAttempt !== null,
    testAttemptCount: backup.testStudents.filter(
      ({ attempt }) => attempt !== null,
    ).length,
    testStudentCount: backup.testStudents.length,
  };
}

export function exportBackup<TAttempt>(
  codec: AttemptCodec<TAttempt>,
): ServiceDeskBackup<TAttempt> {
  const studentAttempt = readAttempt(ATTEMPT_STORAGE_KEY, codec);
  return {
    formatVersion: BACKUP_FORMAT_VERSION,
    exportedAt: new Date().toISOString(),
    studentAttempt: studentAttempt
      ? portableAttempt(studentAttempt, codec)
      : null,
    adminScenarios: listScenarios(),
    testStudents: listTestStudents().map((slot) => {
      const attempt = readAttempt(getTestAttemptStorageKey(slot.id), codec);
      return {
        attempt: attempt ? portableAttempt(attempt, codec) : null,
        slot,
      };
    }),
  };
}

export function validateBackup<TAttempt>(
  json: string | unknown,
  codec: AttemptCodec<TAttempt>,
): BackupValidationReport {
  return report(parseAndValidate(json, codec));
}

export function applyBackup<TAttempt>(
  json: string | unknown,
  codec: AttemptCodec<TAttempt>,
): BackupValidationReport {
  const backup = parseAndValidate(json, codec);
  const targetStorage = storage();
  if (!targetStorage) {
    throw new Error('Browser storage is not available.');
  }

  const previousSlots = listTestStudents();
  if (backup.studentAttempt) {
    targetStorage.setItem(
      ATTEMPT_STORAGE_KEY,
      codec.serializeAttempt(backup.studentAttempt),
    );
  } else {
    targetStorage.removeItem(ATTEMPT_STORAGE_KEY);
  }

  targetStorage.setItem(
    SCENARIO_STORAGE_KEY,
    JSON.stringify({
      templates: backup.adminScenarios.map(({ template }) => template),
      versions: backup.adminScenarios.flatMap(({ versions }) => versions),
    }),
  );

  for (const slot of previousSlots) {
    targetStorage.removeItem(getTestAttemptStorageKey(slot.id));
  }
  targetStorage.setItem(
    TEST_STUDENT_STORAGE_KEY,
    JSON.stringify(backup.testStudents.map(({ slot }) => slot)),
  );
  for (const { attempt, slot } of backup.testStudents) {
    const attemptKey = getTestAttemptStorageKey(slot.id);
    if (attempt) {
      targetStorage.setItem(attemptKey, codec.serializeAttempt(attempt));
    } else {
      targetStorage.removeItem(attemptKey);
    }
  }

  return report(backup);
}
