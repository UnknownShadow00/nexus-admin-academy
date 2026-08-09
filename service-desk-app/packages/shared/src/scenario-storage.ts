import type {
  ScenarioRecord,
  ScenarioTemplate,
  ScenarioVersion,
  ScenarioVersionDraftData,
} from './scenario-types';

export const SCENARIO_STORAGE_KEY = 'nexus-admin-scenarios-v1';

interface StorageLike {
  getItem(key: string): string | null;
  removeItem(key: string): void;
  setItem(key: string, value: string): void;
}

interface ScenarioStore {
  templates: ScenarioTemplate[];
  versions: ScenarioVersion[];
}

const EMPTY_STORE: ScenarioStore = { templates: [], versions: [] };

function storage(): StorageLike | null {
  return (
    (
      globalThis as unknown as {
        localStorage?: StorageLike;
      }
    ).localStorage ?? null
  );
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function createId(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 10)}`;
}

function readStore(): ScenarioStore {
  try {
    const raw = storage()?.getItem(SCENARIO_STORAGE_KEY);
    if (!raw) {
      return clone(EMPTY_STORE);
    }
    const parsed = JSON.parse(raw) as Partial<ScenarioStore>;
    if (!Array.isArray(parsed.templates) || !Array.isArray(parsed.versions)) {
      return clone(EMPTY_STORE);
    }
    return {
      templates: clone(parsed.templates),
      versions: clone(parsed.versions),
    };
  } catch {
    return clone(EMPTY_STORE);
  }
}

function writeStore(store: ScenarioStore) {
  try {
    storage()?.setItem(SCENARIO_STORAGE_KEY, JSON.stringify(store));
  } catch {
    // localStorage can be unavailable or full; callers keep their in-memory form.
  }
}

function toRecord(
  template: ScenarioTemplate,
  versions: readonly ScenarioVersion[],
): ScenarioRecord {
  return {
    template: clone(template),
    versions: clone(
      versions
        .filter((version) => version.scenarioId === template.id)
        .sort((left, right) => left.version - right.version),
    ),
  };
}

export function listScenarios(): ScenarioRecord[] {
  const store = readStore();
  return store.templates
    .map((template) => toRecord(template, store.versions))
    .sort((left, right) =>
      left.template.createdAt.localeCompare(right.template.createdAt),
    );
}

export function getScenario(id: string): ScenarioRecord | null {
  const store = readStore();
  const template = store.templates.find((candidate) => candidate.id === id);
  return template ? toRecord(template, store.versions) : null;
}

export function saveDraftVersion(
  scenarioId: string,
  versionData: ScenarioVersionDraftData,
): ScenarioRecord {
  const store = readStore();
  let template = store.templates.find(
    (candidate) => candidate.id === scenarioId,
  );

  if (!template) {
    template = {
      activeVersionId: null,
      category: versionData.category,
      createdAt: new Date().toISOString(),
      id: scenarioId,
      priority: versionData.priority,
      slug: versionData.slug,
      title: versionData.title,
    };
    store.templates.push(template);
  } else {
    Object.assign(template, {
      category: versionData.category,
      priority: versionData.priority,
      slug: versionData.slug,
      title: versionData.title,
    });
  }

  const versions = store.versions.filter(
    (version) => version.scenarioId === scenarioId,
  );
  const draft = versions.find((version) => version.publishedAt === null);
  const nextVersionNumber =
    Math.max(0, ...versions.map((version) => version.version)) + 1;
  const nextVersion: ScenarioVersion = {
    ...clone(versionData),
    id: draft?.id ?? createId('scenario-version'),
    publishedAt: null,
    scenarioId,
    version: draft?.version ?? nextVersionNumber,
  };

  if (draft) {
    store.versions = store.versions.map((version) =>
      version.id === draft.id ? nextVersion : version,
    );
  } else {
    store.versions.push(nextVersion);
  }

  writeStore(store);
  return toRecord(template, store.versions);
}

export function publishVersion(scenarioId: string): ScenarioRecord {
  const store = readStore();
  const template = store.templates.find(
    (candidate) => candidate.id === scenarioId,
  );
  const draft = store.versions.find(
    (version) =>
      version.scenarioId === scenarioId && version.publishedAt === null,
  );

  if (!template || !draft) {
    throw new Error('A saved draft is required before publishing.');
  }

  const published: ScenarioVersion = {
    ...draft,
    publishedAt: new Date().toISOString(),
  };
  store.versions = store.versions.map((version) =>
    version.id === draft.id ? published : version,
  );
  template.activeVersionId = published.id;
  writeStore(store);
  return toRecord(template, store.versions);
}

export function deleteScenario(id: string): boolean {
  const store = readStore();
  const exists = store.templates.some((template) => template.id === id);
  if (!exists) {
    return false;
  }
  store.templates = store.templates.filter((template) => template.id !== id);
  store.versions = store.versions.filter(
    (version) => version.scenarioId !== id,
  );
  writeStore(store);
  return true;
}
