/**
 * Fixed escalation reason taxonomy, mirrored from the authoritative backend
 * set in `backend/app/services/service_desk_escalation.py`. The server
 * re-validates every value; this list drives the student-facing dropdown.
 */

export const ESCALATION_REASONS = [
  'permissions-access',
  'security-incident',
  'policy-authorization',
  'change-approval-required',
  'hardware-replacement',
  'unknown-root-cause',
  'other-team-owns-system',
] as const;

export type EscalationReason = (typeof ESCALATION_REASONS)[number];

export const ESCALATION_REASON_LABELS: Record<EscalationReason, string> = {
  'permissions-access': 'Permissions / access request',
  'security-incident': 'Security incident',
  'policy-authorization': 'Policy / authorization required',
  'change-approval-required': 'Change approval required',
  'hardware-replacement': 'Hardware replacement',
  'unknown-root-cause': 'Root cause still unknown',
  'other-team-owns-system': 'Another team owns this system',
};

export const ESCALATION_REASON_DESCRIPTIONS: Record<EscalationReason, string> = {
  'permissions-access':
    'The user needs access that only the resource or data owner can grant.',
  'security-incident':
    'Suspected compromise, phishing, malware, or data exposure.',
  'policy-authorization':
    'An approval or authorization step outside the help desk is required.',
  'change-approval-required':
    'The fix is a change that must go through change management first.',
  'hardware-replacement':
    'Physical hardware must be repaired or swapped by another team.',
  'unknown-root-cause':
    'Investigation is complete but the cause needs specialist analysis.',
  'other-team-owns-system':
    'The affected system is operated by a different team.',
};

export function isEscalationReason(value: unknown): value is EscalationReason {
  return (
    typeof value === 'string' &&
    (ESCALATION_REASONS as readonly string[]).includes(value)
  );
}

/**
 * Fixed destination teams a student may route a ticket to. This is a plain
 * list of real teams the simulator recognises - not routing infrastructure.
 * The server decides whether the chosen destination was correct; the workspace
 * never pre-selects or highlights one. Mirrored by the backend canonical set in
 * `backend/app/services/service_desk_escalation.py` (`ESCALATION_ROUTES`).
 */
export const ESCALATION_ROUTES = [
  'Identity & Access',
  'Information Security',
  'Network Support',
  'Endpoint Support',
  'Hardware / Field Services',
  'Application Support',
  'Other / Mentor Review',
] as const;

export type EscalationRoute = (typeof ESCALATION_ROUTES)[number];

export function isEscalationRoute(value: unknown): value is EscalationRoute {
  return (
    typeof value === 'string' &&
    (ESCALATION_ROUTES as readonly string[]).includes(value)
  );
}
