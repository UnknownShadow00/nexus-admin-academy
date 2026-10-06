const TRANSIENT_PARAMS = [
  'tool',
  'ticket',
  'article',
  'category',
  'computer',
  'contact',
  'user',
];

export interface V2LaunchContext {
  moduleKey: string;
  assessmentKey: string;
}

/** Freeze credit context when an action is queued, before navigation can change. */
export function captureV2LaunchContextForTicket(ticketId: string): V2LaunchContext | null {
  if (typeof window === 'undefined') return null;
  const { pathname, search } = window.location;
  const params = new URLSearchParams(search);
  const moduleKey = params.get('v2ModuleKey');
  const assessmentKey = params.get('v2AssessmentKey');
  if (!moduleKey || !assessmentKey || !launchContextAppliesToCurrentTicket(pathname, search)) {
    return null;
  }

  const launchTicket = params.get('v2LaunchTicket');
  const routeTicket = pathname.match(/\/service-desk\/tickets\/([^/]+)\/?$/)?.[1];
  let currentTicket: string | null;
  try {
    currentTicket = routeTicket ? decodeURIComponent(routeTicket) : null;
  } catch {
    return null;
  }
  if (!currentTicket && /\/tools\/[^/]+\/?$/.test(pathname)) {
    currentTicket = params.get('ticket');
  }
  if ((launchTicket ?? currentTicket) !== ticketId || currentTicket !== ticketId) return null;
  return { moduleKey, assessmentKey };
}

/** Keep the curriculum launch attached to its original ticket while browsing. */
export function workspaceHref(
  path: string,
  currentQuery: string,
  currentTicketId?: string,
): string {
  const params = new URLSearchParams(currentQuery);
  for (const key of TRANSIENT_PARAMS) params.delete(key);
  if (
    currentTicketId &&
    params.has('v2ModuleKey') &&
    params.has('v2AssessmentKey') &&
    !params.has('v2LaunchTicket')
  ) {
    params.set('v2LaunchTicket', currentTicketId);
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

/** A reused legacy assignment must not receive another ticket's V2 context. */
export function launchContextAppliesToCurrentTicket(
  pathname: string,
  query: string,
): boolean {
  const params = new URLSearchParams(query);
  const launchTicket = params.get('v2LaunchTicket');
  if (!launchTicket) return true;
  return (
    pathname.endsWith(`/tickets/${encodeURIComponent(launchTicket)}`) ||
    (/\/tools\/[^/]+\/?$/.test(pathname) && params.get('ticket') === launchTicket)
  );
}
