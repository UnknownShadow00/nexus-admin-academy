export const TEST_STUDENT_STORAGE_KEY = 'nexus-admin-test-students-v1';

export interface TestStudentSlot {
  assignedScenarioIds: string[];
  createdAt: string;
  id: string;
  name: string;
}

interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
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

function readSlots(): TestStudentSlot[] {
  try {
    const raw = storage()?.getItem(TEST_STUDENT_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as TestStudentSlot[]) : [];
  } catch {
    return [];
  }
}

function writeSlots(slots: readonly TestStudentSlot[]) {
  try {
    storage()?.setItem(TEST_STUDENT_STORAGE_KEY, JSON.stringify(slots));
  } catch {
    // Storage can be unavailable in privacy modes.
  }
}

function createId() {
  return `test-student-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

export function getTestAttemptStorageKey(slotId: string) {
  return `nexus-admin-test-attempt-${slotId}`;
}

export function listTestStudents(): TestStudentSlot[] {
  return readSlots().map((slot) => ({
    ...slot,
    assignedScenarioIds: [...slot.assignedScenarioIds],
  }));
}

export function getTestStudent(id: string): TestStudentSlot | null {
  return listTestStudents().find((slot) => slot.id === id) ?? null;
}

export function createTestStudent(name: string): TestStudentSlot {
  const slot: TestStudentSlot = {
    assignedScenarioIds: [],
    createdAt: new Date().toISOString(),
    id: createId(),
    name: name.trim() || 'Test Student',
  };
  writeSlots([...readSlots(), slot]);
  return slot;
}

export function renameTestStudent(id: string, name: string): TestStudentSlot {
  const slots = readSlots();
  const slot = slots.find((candidate) => candidate.id === id);
  if (!slot) {
    throw new Error('Test student slot not found.');
  }
  slot.name = name.trim() || slot.name;
  writeSlots(slots);
  return { ...slot, assignedScenarioIds: [...slot.assignedScenarioIds] };
}

export function deleteTestStudent(id: string): boolean {
  const slots = readSlots();
  const next = slots.filter((slot) => slot.id !== id);
  if (next.length === slots.length) {
    return false;
  }
  writeSlots(next);
  return true;
}

export function setTestStudentScenarioAssignment(
  slotId: string,
  scenarioId: string,
  assigned: boolean,
): TestStudentSlot {
  const slots = readSlots();
  const slot = slots.find((candidate) => candidate.id === slotId);
  if (!slot) {
    throw new Error('Test student slot not found.');
  }
  const ids = new Set(slot.assignedScenarioIds);
  if (assigned) {
    ids.add(scenarioId);
  } else {
    ids.delete(scenarioId);
  }
  slot.assignedScenarioIds = [...ids];
  writeSlots(slots);
  return { ...slot, assignedScenarioIds: [...slot.assignedScenarioIds] };
}
