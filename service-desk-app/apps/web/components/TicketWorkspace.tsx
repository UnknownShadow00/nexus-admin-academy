'use client';

import { getToolBySlug, type ToolSlug } from '@service-desk/shared';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@service-desk/ui';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { ActiveToolPane } from './ActiveToolPane';
import { ActivityTimeline } from './ActivityTimeline';
import { EvidencePanel } from './EvidencePanel';
import { HintPanel } from './HintPanel';
import { OutcomeBar } from './OutcomeBar';
import { RelatedDevicePanel } from './RelatedDevicePanel';
import { RequesterCard } from './RequesterCard';
import { ResolutionNotePanel } from './ResolutionNotePanel';
import type { ToolSelectionHandler } from './SuggestedTools';
import { TicketActionBar } from './TicketActionBar';
import { TicketContextBar } from './TicketContextBar';
import { TicketDebrief } from './TicketDebrief';
import { TicketIssueDetails } from './TicketIssueDetails';
import { useSessionHydrated, useTicketSession } from './TicketSessionProvider';
import { WorkspaceToolLauncher } from './WorkspaceToolLauncher';
import { WorkspaceTicketQueue } from './WorkspaceTicketQueue';
import { WORKFLOW_COPY, WorkflowRail } from './WorkflowRail';
import { useNexusReturnTarget } from './useNexusReturnTarget';

const ORIENTATION_KEY = 'sd:first-guided-orientation-seen';
const TOOL_HINT_KEYS = [
  'article',
  'category',
  'computer',
  'contact',
  'user',
] as const;

type PhonePane = 'work' | 'evidence' | 'notes';

export function TicketWorkspace({ ticketId }: { ticketId: string }) {
  const nexusReturn = useNexusReturnTarget();
  const {
    assignmentByTicket,
    authoritativeGradeByTicket,
    awaitingGradeByTicket,
    getTicket,
    recordHintReveal,
    startNextAttempt,
    submitResolutionNote,
    tickets,
    workspaceViewByTicket,
  } = useTicketSession();
  const isHydrated = useSessionHydrated();
  const ticket = getTicket(ticketId);
  const assignment = assignmentByTicket[ticketId];
  const workspaceView = workspaceViewByTicket[ticketId];
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedToolSlug = searchParams.get('tool');
  const [activeTool, setActiveToolState] = useState<{
    ticketId: string;
    slug: string;
  } | null>(null);
  const activeToolSlug =
    activeTool?.ticketId === ticketId ? activeTool.slug : null;
  const [phonePane, setPhonePane] = useState<PhonePane>('work');
  const workHeading = useRef<HTMLHeadingElement>(null);
  const [orientationSeen, setOrientationSeen] = useState<boolean | null>(null);
  const previousTicketId = useRef(ticketId);

  useEffect(() => {
    if (previousTicketId.current === ticketId) return;
    previousTicketId.current = ticketId;
    // Next.js may reuse this component across ticket routes. A tool or mobile
    // pane selected for the previous case must not become the new case's work.
    setActiveToolState(null);
    setPhonePane('work');
  }, [ticketId]);

  useEffect(() => {
    try {
      setOrientationSeen(localStorage.getItem(ORIENTATION_KEY) === '1');
    } catch {
      setOrientationSeen(false);
    }
  }, []);

  useEffect(() => {
    // The embedded workspace is authoritative for which tool is open. A
    // `tool=` in the URL (deep link, reload, or the V2 curriculum launch URL)
    // seeds it, but a later searchParams change made by the tool itself — a
    // hint param, a ticket param — must NOT clear the active tool. Only ever
    // promote a valid slug; never reset to null from this effect.
    if (requestedToolSlug && getToolBySlug(requestedToolSlug)) {
      setActiveToolState({ ticketId, slug: requestedToolSlug });
      setPhonePane('work');

      if (!searchParams.get('ticket')) {
        const params = new URLSearchParams(searchParams.toString());
        params.set('ticket', ticketId);
        params.set('tool', requestedToolSlug);
        router.replace(`${pathname}?${params.toString()}`, { scroll: false });
      }
    }
  }, [pathname, requestedToolSlug, router, searchParams, ticketId]);

  const setActiveTool = useCallback<ToolSelectionHandler>(
    (slug: ToolSlug, queryHints?: URLSearchParams) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const key of TOOL_HINT_KEYS) params.delete(key);
      params.set('tool', slug);
      params.set('ticket', ticketId);
      queryHints?.forEach((value, key) => {
        if (
          TOOL_HINT_KEYS.includes(key as (typeof TOOL_HINT_KEYS)[number]) ||
          key === 'user'
        )
          params.set(key, value);
      });

      setActiveToolState({ ticketId, slug });
      setPhonePane('work');
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams, ticketId],
  );

  if (!isHydrated) {
    return (
      <div
        aria-label="Loading ticket"
        className="mx-auto h-64 max-w-7xl animate-pulse rounded-sm bg-surface-raised"
      />
    );
  }

  if (!ticket) {
    return (
      <div className="mx-auto max-w-xl py-16 text-center">
        <h1 className="text-xl font-bold text-text">Case unavailable</h1>
        <p className="mt-2 text-sm text-text-muted">
          This case is not assigned or unlocked for your current training.
          Return to the queue to continue an available case.
        </p>
        <Link
          className="sd-button sd-button--default sd-focus-ring mt-5 inline-flex min-h-10 items-center justify-center rounded-sm border border-border bg-surface-raised px-4 py-2 text-sm font-extrabold uppercase text-text hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          href="/"
        >
          Back to queue
        </Link>
        {nexusReturn ? (
          <a
            className="ml-3 inline-flex min-h-10 items-center text-sm font-semibold underline"
            href={nexusReturn.href}
          >
            {nexusReturn.label}
          </a>
        ) : null}
      </div>
    );
  }

  if (assignment?.experience_mode === 'guided' && orientationSeen === false) {
    return (
      <section
        aria-labelledby="first-ticket-title"
        className="mx-auto max-w-2xl rounded-md border border-accent/30 bg-surface-raised p-6 sm:p-8"
      >
        <p className="text-xs font-extrabold uppercase tracking-wide text-accent">
          Your first guided ticket
        </p>
        <h1
          className="mt-2 text-2xl font-bold text-text"
          id="first-ticket-title"
        >
          Before you open the ticket
        </h1>
        <ul className="mt-5 space-y-3 text-sm leading-relaxed text-text">
          <li>• This is a practice ticket from a user.</li>
          <li>• Investigate before changing anything.</li>
          <li>
            • Evidence gathered after a fix may not count as investigation.
          </li>
          <li>• You cannot damage a real computer here.</li>
          <li>• Escalating can be the correct professional decision.</li>
        </ul>
        <button
          className="sd-button sd-button--primary sd-focus-ring mt-6 inline-flex min-h-10 items-center justify-center px-4 py-2 font-bold"
          onClick={() => {
            try {
              localStorage.setItem(ORIENTATION_KEY, '1');
            } catch {
              // Browser storage is optional; keep the current session usable.
            }
            setOrientationSeen(true);
          }}
          type="button"
        >
          Open ticket
        </button>
        <p className="mt-3 text-xs text-text-muted">
          This orientation is saved in this browser.
        </p>
      </section>
    );
  }

  const experienceMode = assignment?.experience_mode ?? 'guided';
  const currentStage = workspaceView?.stages.find(
    (stage) => stage.status === 'current',
  );
  const authoritativeGrade = authoritativeGradeByTicket[ticketId];
  const ticketQueue = (
    <WorkspaceTicketQueue
      assignmentByTicket={assignmentByTicket}
      launchQuery={searchParams.toString()}
      selectedTicketId={ticketId}
      tickets={tickets}
    />
  );

  if (authoritativeGrade) {
    return (
      <div className="grid min-w-0 gap-5 lg:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[18rem_minmax(0,1fr)]">
        {ticketQueue}
        <div className="min-w-0 space-y-4 sm:space-y-5">
          <TicketContextBar
            assignment={assignment}
            completed
            launchQuery={searchParams.toString()}
            ticket={ticket}
          />
          <TicketDebrief
            assignment={assignment}
            grade={authoritativeGrade}
            onRetry={startNextAttempt}
            ticket={ticket}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className="grid min-w-0 gap-5 lg:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[18rem_minmax(0,1fr)]"
      data-testid="ticket-workspace"
    >
      {ticketQueue}
      <div className="min-w-0 space-y-4">
        <TicketContextBar
          assignment={assignment}
          launchQuery={searchParams.toString()}
          ticket={ticket}
        />
        {awaitingGradeByTicket[ticketId] ? (
          <p
            className="rounded-md border border-border p-4 text-lg font-bold"
            role="status"
          >
            Assessment result: AWAITING REVIEW — module credit pending.
          </p>
        ) : null}
        {workspaceView ? (
          <WorkflowRail
            experienceMode={experienceMode}
            stages={workspaceView.stages}
          />
        ) : null}
        <Tabs
          onValueChange={(value) => setPhonePane(value as PhonePane)}
          value={phonePane}
        >
          <TabsList
            aria-label="Ticket workspace panes"
            className="grid grid-cols-3 sm:hidden"
          >
            <TabsTrigger value="work">Work</TabsTrigger>
            <TabsTrigger value="evidence">
              Evidence ({workspaceView?.evidence.length ?? 0})
            </TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
          </TabsList>
          <div className="grid min-w-0 gap-4 sm:block lg:grid lg:gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] xl:grid-cols-[minmax(0,1fr)_22rem]">
            <TabsContent
              className="m-0 min-w-0 data-[state=inactive]:hidden sm:!block sm:py-0"
              forceMount
              value="work"
            >
              <div className="min-w-0 space-y-4">
                <h2 className="sr-only" ref={workHeading} tabIndex={-1}>
                  Ticket work area
                </h2>
                <section
                  aria-label="Current ticket work"
                  className="min-w-0 border-b border-border pb-4"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                    Current ticket work
                  </p>
                  <h2 className="mt-2 text-base font-semibold leading-snug text-text">
                    {currentStage
                      ? WORKFLOW_COPY[currentStage.key].label
                      : 'Ticket work'}
                  </h2>
                  {currentStage && experienceMode !== 'assessment' ? (
                    <p className="mt-1 max-w-prose text-sm leading-relaxed text-text-muted">
                      {WORKFLOW_COPY[currentStage.key].help}
                    </p>
                  ) : null}
                  <div className="mt-4 border-l-2 border-border pl-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                      Reported issue
                    </h3>
                    <p className="mt-1 max-w-prose break-words text-sm leading-relaxed text-text">
                      {ticket.description.issue}
                    </p>
                  </div>
                  {currentStage?.key === 'verify' ||
                  currentStage?.key === 'document' ? (
                    <button
                      className="sd-focus-ring mt-3 min-h-11 rounded-sm border border-border px-3 py-2 text-sm font-semibold text-text sm:hidden"
                      onClick={() =>
                        setPhonePane(
                          currentStage.key === 'verify' ? 'evidence' : 'notes',
                        )
                      }
                      type="button"
                    >
                      {currentStage.key === 'verify'
                        ? 'Review confirmed work'
                        : 'Open support notes'}
                    </button>
                  ) : null}
                  <details className="mt-3">
                    <summary className="sd-focus-ring min-h-11 cursor-pointer py-3 text-sm font-semibold text-accent">
                      Full report and prior checks
                    </summary>
                    <TicketIssueDetails description={ticket.description} />
                  </details>
                </section>
                <WorkspaceToolLauncher
                  key={ticket.id}
                  activeToolSlug={activeToolSlug}
                  experienceMode={experienceMode}
                  onSelectTool={setActiveTool}
                  ticketCategory={ticket.category}
                  ticketId={ticket.id}
                  toolSlugs={ticket.suggestedTools}
                />
                <ActiveToolPane
                  activeTicketId={ticket.id}
                  activeToolSlug={activeToolSlug}
                  onSelectTool={setActiveTool}
                  onBack={() => {
                    const params = new URLSearchParams(searchParams.toString());
                    params.delete('tool');
                    for (const key of TOOL_HINT_KEYS) params.delete(key);
                    setActiveToolState(null);
                    setPhonePane('work');
                    router.replace(`${pathname}?${params.toString()}`, {
                      scroll: false,
                    });
                    workHeading.current?.focus();
                  }}
                />
                <TicketActionBar ticket={ticket} />
              </div>
            </TabsContent>
            <aside
              aria-label="Ticket workspace rail"
              className="contents min-w-0 sm:block sm:space-y-4 sm:mt-4 lg:mt-0"
            >
              {experienceMode !== 'assessment' ? (
                <details className="order-first rounded-sm bg-surface-raised px-3 py-1 sm:order-none">
                  <summary className="sd-focus-ring min-h-11 cursor-pointer py-3 text-sm font-semibold text-text">
                    Hints
                  </summary>
                  <HintPanel
                    key={ticket.id}
                    experienceMode={experienceMode}
                    hints={ticket.hints}
                    onReveal={(step) => recordHintReveal(ticket.id, step)}
                    revealedCount={ticket.hintsRevealedCount}
                  />
                </details>
              ) : null}
              <TabsContent
                className="m-0 min-w-0 data-[state=inactive]:hidden sm:!block sm:py-0"
                forceMount
                value="evidence"
              >
                {workspaceView ? (
                  <EvidencePanel workspaceView={workspaceView} />
                ) : (
                  <p className="text-sm text-text-muted">
                    No evidence confirmed yet.
                  </p>
                )}
              </TabsContent>
              <TabsContent
                className="m-0 min-w-0 data-[state=inactive]:hidden sm:!block sm:py-0"
                forceMount
                value="notes"
              >
                <ResolutionNotePanel
                  key={ticket.id}
                  experienceMode={experienceMode}
                  notes={ticket.notes}
                  onSubmit={(body) => submitResolutionNote(ticket.id, body)}
                />
              </TabsContent>
            </aside>
          </div>
        </Tabs>
        <OutcomeBar ticket={ticket} />
        <details className="border-t border-border pt-2">
          <summary className="sd-focus-ring min-h-11 cursor-pointer py-3 text-sm font-semibold text-text-muted">
            Case and device details
          </summary>
          <div className="grid gap-4 md:grid-cols-2">
            <RequesterCard requester={ticket.requester} />
            <RelatedDevicePanel device={ticket.device} />
          </div>
          <p className="mt-3 text-xs text-text-muted">{ticket.sla.target}</p>
        </details>
        <details className="border-t border-border pt-2">
          <summary className="sd-focus-ring min-h-11 cursor-pointer py-3 text-sm font-semibold text-text-muted">
            Activity timeline ({ticket.activity.length})
          </summary>
          <ActivityTimeline events={ticket.activity} />
        </details>
      </div>
    </div>
  );
}
