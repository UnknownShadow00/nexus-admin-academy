import {
  Priority,
  TicketCategory,
  type ScenarioRecord,
  type ScenarioVersion,
  type ScenarioVersionDraftData,
} from '@service-desk/shared';

interface ServerVersion {
  created_at: string;
  definition_json: Record<string, unknown>;
  id: number;
  published_at: string | null;
  scenario_id: number;
  status: 'draft' | 'published' | 'disabled';
  validation_errors: string[];
  validation_status: string;
  version_number: number;
}

interface ServerScenario {
  category: string;
  created_at: string;
  description: string | null;
  difficulty: number;
  id: number;
  stable_key: string;
  status: string;
  title: string;
  versions: ServerVersion[];
}

export class ScenarioApiError extends Error {
  constructor(
    message: string,
    public readonly validationErrors: readonly string[] = [],
  ) {
    super(message);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function difficulty(value: unknown, fallback: number): ScenarioVersion['difficulty'] {
  if (value === 'easy' || value === 'medium' || value === 'hard') return value;
  return fallback >= 3 ? 'hard' : fallback === 2 ? 'medium' : 'easy';
}

function category(value: unknown, fallback: string): TicketCategory {
  return Object.values(TicketCategory).includes(value as TicketCategory)
    ? (value as TicketCategory)
    : Object.values(TicketCategory).includes(fallback as TicketCategory)
      ? (fallback as TicketCategory)
      : TicketCategory.Software;
}

function priority(value: unknown): Priority {
  return Object.values(Priority).includes(value as Priority)
    ? (value as Priority)
    : Priority.Medium;
}

function toVersion(server: ServerVersion, scenario: ServerScenario): ScenarioVersion {
  const value = server.definition_json;
  const description = isRecord(value.description) ? value.description : {};
  const requester = isRecord(value.requester) ? value.requester : {};
  const device = isRecord(value.device) ? value.device : {};
  const sla = isRecord(value.sla) ? value.sla : {};
  const world = isRecord(value.initialWorldState) ? value.initialWorldState : {};
  const rawHints = Array.isArray(value.hints) ? value.hints : [];

  return {
    description: {
      businessImpact: text(description.businessImpact),
      issue: text(description.issue, scenario.description ?? ''),
      reportedByLine: text(description.reportedByLine),
      troubleshooting: stringList(description.troubleshooting),
    },
    device: {
      assetTag: text(device.assetTag),
      deviceName: text(device.deviceName),
      kind: ['desktop', 'laptop', 'mobile', 'peripheral'].includes(text(device.kind))
        ? (text(device.kind) as ScenarioVersion['device']['kind'])
        : 'laptop',
      operatingSystem: text(device.operatingSystem),
      state: ['active', 'attention', 'offline'].includes(text(device.state))
        ? (text(device.state) as ScenarioVersion['device']['state'])
        : 'active',
    },
    difficulty: difficulty(value.difficulty, scenario.difficulty),
    explanation: text(value.explanation),
    forbiddenActions: Array.isArray(value.forbiddenActions)
      ? (value.forbiddenActions as ScenarioVersion['forbiddenActions'])
      : [],
    hints: rawHints.map((hint, index) =>
      isRecord(hint)
        ? {
            id: text(hint.id, `hint-${server.id}-${index + 1}`),
            order: typeof hint.order === 'number' ? hint.order : index + 1,
            pointPenalty:
              typeof hint.pointPenalty === 'number' ? hint.pointPenalty : index === 0 ? 0 : 5,
            text: text(hint.text),
          }
        : {
            id: `hint-${server.id}-${index + 1}`,
            order: index + 1,
            pointPenalty: index === 0 ? 0 : 5,
            text: text(hint),
          },
    ),
    id: String(server.id),
    initialWorldState: {
      assetOverlaySeeds: isRecord(world.assetOverlaySeeds)
        ? (world.assetOverlaySeeds as ScenarioVersion['initialWorldState']['assetOverlaySeeds'])
        : {},
      chatMessageSeeds: Array.isArray(world.chatMessageSeeds)
        ? (world.chatMessageSeeds as ScenarioVersion['initialWorldState']['chatMessageSeeds'])
        : [],
      directoryOverlaySeeds: isRecord(world.directoryOverlaySeeds)
        ? (world.directoryOverlaySeeds as ScenarioVersion['initialWorldState']['directoryOverlaySeeds'])
        : {},
    },
    objectives: Array.isArray(value.objectives)
      ? (value.objectives as ScenarioVersion['objectives'])
      : [],
    pointValue: typeof value.pointValue === 'number' ? value.pointValue : 100,
    publishedAt: server.published_at,
    requester: {
      contact: text(requester.contact),
      department: text(requester.department),
      email: text(requester.email),
      location: text(requester.location),
      name: text(requester.name),
    },
    requiredActions: Array.isArray(value.requiredActions)
      ? (value.requiredActions as ScenarioVersion['requiredActions'])
      : [],
    scenarioId: String(scenario.id),
    sla: { dueAt: text(sla.dueAt), target: text(sla.target) },
    version: server.version_number,
  };
}

function toRecord(scenario: ServerScenario): ScenarioRecord {
  const published = [...scenario.versions]
    .reverse()
    .find((version) => version.status === 'published');
  const firstDefinition = scenario.versions.at(-1)?.definition_json ?? {};
  return {
    template: {
      activeVersionId: published ? String(published.id) : null,
      category: category(firstDefinition.category, scenario.category),
      createdAt: scenario.created_at,
      id: String(scenario.id),
      priority: priority(firstDefinition.priority),
      slug: scenario.stable_key,
      title: scenario.title,
    },
    versions: scenario.versions.map((version) => toVersion(version, scenario)),
  };
}

async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: 'same-origin',
      headers: { 'content-type': 'application/json', ...init.headers },
    });
  } catch {
    throw new ScenarioApiError('Could not reach Nexus. Check the connection and try again.');
  }
  if (response.status === 204) return null;
  const result: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = isRecord(result) ? result.detail : null;
    const detailRecord = isRecord(detail) ? detail : null;
    const errors = detailRecord && Array.isArray(detailRecord.errors)
      ? detailRecord.errors.filter((item): item is string => typeof item === 'string')
      : [];
    const message = typeof detail === 'string'
      ? detail
      : detailRecord && typeof detailRecord.message === 'string'
        ? detailRecord.message
        : `Scenario request failed (${response.status}).`;
    throw new ScenarioApiError(message, errors);
  }
  return result;
}

function metadata(draft: ScenarioVersionDraftData) {
  return {
    stable_key: draft.slug,
    title: draft.title,
    description: draft.description.issue,
    category: draft.category,
    difficulty: draft.difficulty === 'hard' ? 3 : draft.difficulty === 'medium' ? 2 : 1,
    definition_json: draft,
  };
}

export async function listServerScenarios(): Promise<ScenarioRecord[]> {
  const result = await request('/api/admin/service-desk/scenarios');
  return Array.isArray(result) ? (result as ServerScenario[]).map(toRecord) : [];
}

export async function getServerScenario(id: string): Promise<ScenarioRecord> {
  const result = await request(`/api/admin/service-desk/scenarios/${encodeURIComponent(id)}`);
  return toRecord(result as ServerScenario);
}

export async function saveServerScenario(
  scenarioId: string | null,
  draft: ScenarioVersionDraftData,
  draftVersionId?: string,
): Promise<ScenarioRecord> {
  if (!scenarioId) {
    const result = await request('/api/admin/service-desk/scenarios', {
      body: JSON.stringify(metadata(draft)), method: 'POST',
    });
    return toRecord(result as ServerScenario);
  }
  if (draftVersionId) {
    const result = await request(
      `/api/admin/service-desk/scenarios/${encodeURIComponent(scenarioId)}/versions/${encodeURIComponent(draftVersionId)}`,
      { body: JSON.stringify(metadata(draft)), method: 'PUT' },
    );
    return toRecord(result as ServerScenario);
  }
  await request(
    `/api/admin/service-desk/scenarios/${encodeURIComponent(scenarioId)}/versions`,
    { body: JSON.stringify({ definition_json: draft }), method: 'POST' },
  );
  return getServerScenario(scenarioId);
}

export async function validateServerScenario(
  scenarioId: string,
  versionId: string,
): Promise<{ errors: string[]; valid: boolean }> {
  return request(
    `/api/admin/service-desk/scenarios/${encodeURIComponent(scenarioId)}/versions/${encodeURIComponent(versionId)}/validate`,
    { method: 'POST' },
  ) as Promise<{ errors: string[]; valid: boolean }>;
}

export async function publishServerScenario(
  scenarioId: string,
  versionId: string,
): Promise<ScenarioRecord> {
  await request(
    `/api/admin/service-desk/scenarios/${encodeURIComponent(scenarioId)}/versions/${encodeURIComponent(versionId)}/publish`,
    { method: 'POST' },
  );
  return getServerScenario(scenarioId);
}

export async function deleteServerScenario(id: string): Promise<void> {
  await request(`/api/admin/service-desk/scenarios/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
