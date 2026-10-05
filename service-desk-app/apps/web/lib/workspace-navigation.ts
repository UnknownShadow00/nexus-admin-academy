const TRANSIENT_PARAMS = [
  'tool',
  'ticket',
  'article',
  'category',
  'computer',
  'contact',
  'user',
];

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
