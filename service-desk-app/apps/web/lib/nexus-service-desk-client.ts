export interface NexusAssignmentAttemptSummary {
  attempt_number: number;
  id: string | number;
  status: string;
}

export interface NexusAssignment {
  difficulty_label?: string;
  difficulty_stars?: string;
  id: string | number;
  is_required: boolean;
  latest_published_version: {
    definition_json: Record<string, unknown>;
    id: string | number;
    version_number: number;
  } | null;
  mode: string;
  experience_mode: 'guided' | 'practice' | 'assessment';
  most_recent_attempt: NexusAssignmentAttemptSummary | null;
  maximum_attempts: number | null;
  pack_key?: string;
  pack_name?: string;
  pack_order?: number;
  queue_type?: 'assigned' | 'practice' | 'earlier';
  scenario: {
    stable_key: string;
    title: string;
  };
  scenario_id: string | number;
}

export interface NexusServiceDeskProgression {
  counts: {
    available: number;
    completed: number;
    in_progress: number;
    practice: number;
    earlier: number;
  };
  current_pack: { key: string; name: string } | null;
  current_week: number;
  next_pack: {
    key: string;
    name: string;
    reason: string;
    required_passes: number;
    required_week: number;
    source_pack_name: string;
    source_pack_passes: number;
    requirements: {
      week: { label: string; met: boolean };
      passes: {
        label: string;
        met: boolean;
        completed: number;
        required: number;
      } | null;
    };
  } | null;
}

export interface NexusAttempt {
  attempt_number: number;
  completed_at: string | null;
  current_state: Record<string, unknown>;
  current_state_hash: string;
  id: string | number;
  mode: string;
  experience_mode: 'guided' | 'practice' | 'assessment';
  passed: boolean | null;
  score: number | null;
  started_at: string;
  state_version: number;
  status: string;
  updated_at: string;
}

export interface NexusAttemptEventInput {
  event_type: string;
  idempotency_key: string;
  payload: Readonly<Record<string, unknown>>;
  resulting_state: Readonly<Record<string, unknown>>;
  success: boolean;
  tool: string;
}

export interface NexusAttemptHintInput {
  idempotency_key: string;
  payload: Readonly<Record<string, unknown>>;
  resulting_state?: Readonly<Record<string, unknown>>;
  tool: string;
}

export interface NexusAttemptCompletionInput {
  idempotency_key: string;
}

export interface NexusGrade {
  attempt_id: string | number;
  critical_failure: boolean;
  feedback_summary: string;
  id: string | number;
  overall_score: number;
  passed: boolean;
  rubric_version: string;
  scenario_version_id: string | number;
  technical_complete: boolean;
}

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isId(value: unknown): value is string | number {
  return typeof value === 'string' || typeof value === 'number';
}

function isAttempt(value: unknown): value is NexusAttempt {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.attempt_number === 'number' &&
    (typeof value.completed_at === 'string' || value.completed_at === null) &&
    isRecord(value.current_state) &&
    typeof value.current_state_hash === 'string' &&
    isId(value.id) &&
    typeof value.mode === 'string' &&
    (value.experience_mode === 'guided' ||
      value.experience_mode === 'practice' ||
      value.experience_mode === 'assessment') &&
    (typeof value.passed === 'boolean' || value.passed === null) &&
    (typeof value.score === 'number' || value.score === null) &&
    typeof value.started_at === 'string' &&
    typeof value.state_version === 'number' &&
    typeof value.status === 'string' &&
    typeof value.updated_at === 'string'
  );
}

function isGrade(value: unknown): value is NexusGrade {
  if (!isRecord(value)) {
    return false;
  }

  return (
    isId(value.attempt_id) &&
    typeof value.critical_failure === 'boolean' &&
    typeof value.feedback_summary === 'string' &&
    isId(value.id) &&
    typeof value.overall_score === 'number' &&
    typeof value.passed === 'boolean' &&
    typeof value.rubric_version === 'string' &&
    isId(value.scenario_version_id) &&
    typeof value.technical_complete === 'boolean'
  );
}

function isAssignment(value: unknown): value is NexusAssignment {
  if (!isRecord(value) || !isRecord(value.scenario)) {
    return false;
  }

  return (
    isId(value.id) &&
    typeof value.is_required === 'boolean' &&
    (value.latest_published_version === null ||
      (isRecord(value.latest_published_version) &&
        isId(value.latest_published_version.id) &&
        isRecord(value.latest_published_version.definition_json) &&
        typeof value.latest_published_version.version_number === 'number')) &&
    typeof value.mode === 'string' &&
    (value.experience_mode === 'guided' ||
      value.experience_mode === 'practice' ||
      value.experience_mode === 'assessment') &&
    (value.most_recent_attempt === null ||
      (isRecord(value.most_recent_attempt) &&
        typeof value.most_recent_attempt.attempt_number === 'number' &&
        isId(value.most_recent_attempt.id) &&
        typeof value.most_recent_attempt.status === 'string')) &&
    (typeof value.maximum_attempts === 'number' ||
      value.maximum_attempts === null) &&
    typeof value.scenario.stable_key === 'string' &&
    typeof value.scenario.title === 'string' &&
    isId(value.scenario_id)
  );
}

function isProgression(value: unknown): value is NexusServiceDeskProgression {
  if (
    !isRecord(value) ||
    !isRecord(value.counts) ||
    !(value.current_pack === null || isRecord(value.current_pack))
  ) {
    return false;
  }
  const counts = value.counts;
  return (
    typeof counts.available === 'number' &&
    typeof counts.completed === 'number' &&
    typeof counts.in_progress === 'number' &&
    typeof counts.practice === 'number' &&
    typeof counts.earlier === 'number' &&
    (value.current_pack === null ||
      (typeof value.current_pack.key === 'string' &&
        typeof value.current_pack.name === 'string')) &&
    typeof value.current_week === 'number' &&
    (value.next_pack === null || isRecord(value.next_pack))
  );
}

async function request(
  path: string,
  init: RequestInit,
): Promise<unknown | null> {
  try {
    const response = await fetch(path, {
      ...init,
      credentials: 'same-origin',
      headers: {
        'content-type': 'application/json',
        ...init.headers,
      },
    });

    if (!response.ok) {
      console.warn(
        `Nexus service desk request returned ${String(response.status)}.`,
      );
      return null;
    }

    return await response.json();
  } catch (error) {
    console.warn(
      'Nexus service desk request could not reach the server.',
      error,
    );
    return null;
  }
}

export async function listAssignments(): Promise<readonly NexusAssignment[]> {
  const result = await request('/api/service-desk/assignments', {
    method: 'GET',
  });

  return Array.isArray(result) ? result.filter(isAssignment) : [];
}

export async function getServiceDeskProgression(): Promise<NexusServiceDeskProgression | null> {
  const result = await request('/api/service-desk/progression', {
    method: 'GET',
  });

  return isProgression(result) ? result : null;
}

export async function startOrResumeAttempt(
  assignmentId: string | number,
): Promise<NexusAttempt | null> {
  const result = await request(
    `/api/service-desk/assignments/${encodeURIComponent(assignmentId)}/attempts`,
    { method: 'POST' },
  );

  return isAttempt(result) ? result : null;
}

export async function getAttempt(
  attemptId: string | number,
): Promise<NexusAttempt | null> {
  const result = await request(
    `/api/service-desk/attempts/${encodeURIComponent(attemptId)}`,
    { method: 'GET' },
  );

  return isAttempt(result) ? result : null;
}

export async function recordAttemptEvent(
  attemptId: string | number,
  input: NexusAttemptEventInput,
): Promise<boolean> {
  return (
    (await request(
      `/api/service-desk/attempts/${encodeURIComponent(attemptId)}/events`,
      { body: JSON.stringify(input), method: 'POST' },
    )) !== null
  );
}

/** Submit an action request. The server, not the browser, decides evidence. */
export async function requestAttemptAction(
  attemptId: string | number,
  input: Omit<NexusAttemptEventInput, 'success'>,
): Promise<boolean> {
  return (
    (await request(
      `/api/service-desk/attempts/${encodeURIComponent(attemptId)}/actions`,
      { body: JSON.stringify(input), method: 'POST' },
    )) !== null
  );
}

/** Persist untrusted resume data; this endpoint never creates grading evidence. */
export async function persistAttemptSnapshot(
  attemptId: string | number,
  input: {
    idempotency_key: string;
    snapshot: Readonly<Record<string, unknown>>;
  },
): Promise<boolean> {
  return (
    (await request(
      `/api/service-desk/attempts/${encodeURIComponent(attemptId)}/snapshot`,
      { body: JSON.stringify(input), method: 'POST' },
    )) !== null
  );
}

export async function recordAttemptHint(
  attemptId: string | number,
  input: NexusAttemptHintInput,
): Promise<boolean> {
  return (
    (await request(
      `/api/service-desk/attempts/${encodeURIComponent(attemptId)}/hints`,
      { body: JSON.stringify(input), method: 'POST' },
    )) !== null
  );
}

export async function completeAttempt(
  attemptId: string | number,
  input: NexusAttemptCompletionInput,
): Promise<NexusGrade | null> {
  const result = await request(
    `/api/service-desk/attempts/${encodeURIComponent(attemptId)}/complete`,
    { body: JSON.stringify(input), method: 'POST' },
  );

  return isGrade(result) ? result : null;
}
