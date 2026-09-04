'use client';

import { getToolBySlug } from '@service-desk/shared';
import { IconToolsOff } from '@tabler/icons-react';
import { useSearchParams } from 'next/navigation';

import { renderTool } from './tool-registry';

export function toolContextMatchesTicket(
  searchParams: Pick<URLSearchParams, 'get'>,
  activeTicketId: string,
): boolean {
  const toolTicketId = searchParams.get('ticket');
  return (
    !toolTicketId || toolTicketId.toUpperCase() === activeTicketId.toUpperCase()
  );
}

export function ActiveToolPane({
  activeTicketId,
  activeToolSlug,
}: {
  activeTicketId: string;
  activeToolSlug: string | null;
}) {
  const searchParams = useSearchParams();

  if (!activeToolSlug) {
    return (
      <section
        className="rounded-md border border-dashed border-border bg-surface-raised/50 p-8 text-center"
        role="status"
      >
        <IconToolsOff
          aria-hidden="true"
          className="mx-auto h-8 w-8 text-text-muted"
        />
        <p className="mt-3 text-sm text-text">
          Open a tool from the right to start working. Your ticket stays here.
        </p>
      </section>
    );
  }

  const tool = getToolBySlug(activeToolSlug);
  if (!tool) {
    return (
      <section
        className="rounded-md border border-border bg-surface-raised p-8 text-center"
        role="status"
      >
        <h2 className="text-lg font-bold text-text">Tool unavailable</h2>
        <p className="mt-2 text-sm text-text-muted">
          Choose another tool from the workspace launcher.
        </p>
      </section>
    );
  }

  if (!toolContextMatchesTicket(searchParams, activeTicketId)) {
    return (
      <section
        className="rounded-md border border-border bg-surface-raised p-8 text-center"
        role="status"
      >
        <IconToolsOff
          aria-hidden="true"
          className="mx-auto h-8 w-8 text-text-muted"
        />
        <h2 className="mt-3 text-lg font-bold text-text">
          {tool.displayName} is not part of this ticket
        </h2>
        <p className="mt-2 text-sm text-text-muted">
          Open it again from this ticket so the correct case context is used.
        </p>
      </section>
    );
  }

  return <div className="min-w-0">{renderTool(activeToolSlug)}</div>;
}
