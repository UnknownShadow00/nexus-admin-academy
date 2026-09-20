'use client';

import { getToolBySlug } from '@service-desk/shared';
import { IconToolsOff } from '@tabler/icons-react';
import { useSearchParams } from 'next/navigation';

import { IntegratedToolContext } from './IntegratedToolContext';
import { useTicketSession } from './TicketSessionProvider';
import { renderTool } from './tool-registry';
import { useNexusReturnTarget } from './useNexusReturnTarget';
import type { ToolSelectionHandler } from './SuggestedTools';

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
  onBack,
  onSelectTool,
}: {
  activeTicketId: string;
  activeToolSlug: string | null;
  onBack?: () => void;
  onSelectTool?: ToolSelectionHandler;
}) {
  const searchParams = useSearchParams();
  const returnTarget = useNexusReturnTarget();
  const { getTicket, getAttemptIdentity, assignmentByTicket } =
    useTicketSession();
  const ticket = getTicket(activeTicketId);

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
          Choose a tool above to start working. Your ticket stays here.
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

  if (!ticket) return null;
  const attemptNumber =
    assignmentByTicket[activeTicketId]?.most_recent_attempt?.attempt_number;
  return (
    <IntegratedToolContext.Provider
      value={{
        ticket,
        ticketId: ticket.id,
        assignmentId: assignmentByTicket[activeTicketId]?.id,
        attemptId: getAttemptIdentity(activeTicketId)?.attemptId,
        experienceMode: assignmentByTicket[activeTicketId]?.experience_mode,
        attemptNumber,
        returnDestination: returnTarget?.href ?? null,
        onBack,
        onSelectTool,
      }}
    >
      <div className="min-w-0">
        <button
          className="sd-focus-ring mb-3 min-h-11 rounded-sm px-2 text-sm font-semibold text-text-muted hover:text-text"
          onClick={onBack}
          type="button"
        >
          Back to ticket {activeTicketId}
        </button>
        {renderTool(activeToolSlug, activeTicketId)}
      </div>
    </IntegratedToolContext.Provider>
  );
}
