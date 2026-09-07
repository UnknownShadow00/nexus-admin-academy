import {
  EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
  NEXUS_SERVICE_DESK_CONTRACT_HEADER,
  contractIsCompatible,
} from './service-desk-contract';

export interface NexusAssignmentAttemptSummary {
  attempt_number: number;
  experience_mode: 'guided' | 'practice' | 'assessment';
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
  guided_completed: boolean;
  most_recent_attempt: NexusAssignmentAttemptSummary | null;
  maximum_attempts: number | null;
  pack_key?: string;
  pack_name?: string;
  pack_order?: number;
  queue_type?: 'assigned' | 'practice' | 'earlier';
  required_this_week: boolean;
  scenario: {
    stable_key: string;
    title: string;
  };
  scenario_id: string | number;
  workspace_view?: NexusWorkspaceView | null;
}

export type NexusWorkflowStageKey =
  | 'understand'
  | 'investigate'
  | 'diagnose'
  | 'fix'
  | 'verify'
  | 'document';

export interface NexusWorkflowStage {
  key: NexusWorkflowStageKey;
  // Always the literal 'fix'. The server never sends an "escalate" outcome
  // signal before completion (see service_desk_workspace_view.process_progress);
  // retained only so the stage shape is stable.
  mode?: 'fix';
  needs_more_evidence?: boolean;
  status: 'complete' | 'current' | 'not_started';
}

export interface NexusWorkspaceView {
  documentation_target: 'ticket' | 'remote_desktop';
  // Route-free and identical for every ticket: escalation is a professional
  // option everywhere and the server decides whether it was appropriate.
  escalation: { available: boolean } | null;
  evidence: readonly { id: string; label: string }[];
  stages: readonly NexusWorkflowStage[];
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
    required_module_id?: string | null;
    required_module_title?: string | null;
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
  grade?: NexusGrade | null;
  id: string | number;
  mode: string;
  experience_mode: 'guided' | 'practice' | 'assessment';
  passed: boolean | null;
  score: number | null;
  started_at: string;
  state_version: number;
  status: string;
  updated_at: string;
  workspace_view?: NexusWorkspaceView;
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

export interface NexusDebriefCategory {
  key: string;
  label: string;
  points: number;
  max: number;
  status: 'full' | 'partial' | 'missed' | 'not_applicable';
  explanation: string;
}

export interface NexusDebrief {
  // 'limited' when the attempt failed with a graded attempt still remaining:
  // no ordered path, no correct escalation route, no verdict.
  coaching_tier: 'full' | 'limited';
  result: {
    passed: boolean;
    score: number;
    attempts_remaining: number | null;
    outcome: 'resolved' | 'escalated' | 'needs_another_try';
  };
  categories: readonly NexusDebriefCategory[];
  student_note: string;
  note_dimensions: { cause: boolean; action: boolean; verification: boolean };
  stronger_path: readonly string[];
  escalation_feedback: { appropriate: boolean; text: string } | null;
}

export interface NexusGrade {
  attempt_id: string | number;
  critical_failure: boolean;
  debrief?: NexusDebrief | null;
  feedback_summary: string;
  id: string | number;
  overall_score: number;
  passed: boolean;
  rubric_version: string;
  scenario_version_id: string | number;
  learner_outcome?: 'pass' | 'escalated_successfully' | 'needs_another_attempt' | 'awaiting_review';
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
    typeof value.updated_at === 'string' &&
    (value.workspace_view === undefined || isWorkspaceView(value.workspace_view))
  );
}

function isWorkspaceView(value: unknown): value is NexusWorkspaceView {
  if (!isRecord(value) || !Array.isArray(value.stages)) return false;
  return (
    (value.documentation_target === 'ticket' ||
      value.documentation_target === 'remote_desktop') &&
    (value.escalation === null || isRecord(value.escalation)) &&
    Array.isArray(value.evidence) &&
    value.stages.every(
      (stage) =>
        isRecord(stage) &&
        typeof stage.key === 'string' &&
        (stage.status === 'complete' ||
          stage.status === 'current' ||
          stage.status === 'not_started'),
    )
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
    typeof value.guided_completed === 'boolean' &&
    (value.most_recent_attempt === null ||
      (isRecord(value.most_recent_attempt) &&
        typeof value.most_recent_attempt.attempt_number === 'number' &&
        (value.most_recent_attempt.experience_mode === 'guided' ||
          value.most_recent_attempt.experience_mode === 'practice' ||
          value.most_recent_attempt.experience_mode === 'assessment') &&
        isId(value.most_recent_attempt.id) &&
        typeof value.most_recent_attempt.status === 'string')) &&
    (typeof value.maximum_attempts === 'number' ||
      value.maximum_attempts === null) &&
    typeof value.required_this_week === 'boolean' &&
    typeof value.scenario.stable_key === 'string' &&
    typeof value.scenario.title === 'string' &&
    isId(value.scenario_id) &&
    (value.workspace_view === undefined ||
      value.workspace_view === null ||
      isWorkspaceView(value.workspace_view))
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
    const contract = await fetch('/api/service-desk/contract', {
      credentials: 'same-origin',
      cache: 'no-store',
    });
    const contractBody: unknown = contract.ok ? await contract.json() : null;
    if (!contract.ok || !contractIsCompatible(contractBody)) {
      console.error(
        `Nexus Service Desk contract mismatch; expected ${EXPECTED_NEXUS_SERVICE_DESK_CONTRACT}.`,
      );
      return null;
    }
    const headers = new Headers(init.headers);
    headers.set(
      NEXUS_SERVICE_DESK_CONTRACT_HEADER,
      EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
    );
    headers.set('content-type', 'application/json');
    const response = await fetch(path, {
      ...init,
      credentials: 'same-origin',
      headers,
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
  const query = v2LaunchContextQuery();
  const result = await request(`/api/service-desk/assignments${query}`, {
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
  const suffix = v2LaunchContextQuery();
  const result = await request(
    `/api/service-desk/assignments/${encodeURIComponent(assignmentId)}/attempts${suffix}`,
    { method: 'POST' },
  );

  return isAttempt(result) ? result : null;
}

function v2LaunchContextQuery(): string {
  const query = new URLSearchParams();
  if (typeof window !== 'undefined') {
    const launch = new URLSearchParams(window.location.search);
    const moduleKey = launch.get('v2ModuleKey');
    const assessmentKey = launch.get('v2AssessmentKey');
    if (moduleKey && assessmentKey) {
      query.set('v2_module_key', moduleKey);
      query.set('v2_assessment_key', assessmentKey);
    }
  }
  return query.size ? `?${query.toString()}` : '';
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
