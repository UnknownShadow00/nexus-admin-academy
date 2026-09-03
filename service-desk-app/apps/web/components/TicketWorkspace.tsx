'use client';

import { getToolBySlug, type ToolSlug } from '@service-desk/shared';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@service-desk/ui';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { ActiveToolPane } from './ActiveToolPane';
import { ActivityTimeline } from './ActivityTimeline';
import { NotesSection } from './NotesSection';
import { OutcomeBar } from './OutcomeBar';
import { RelatedDevicePanel } from './RelatedDevicePanel';
import { RequesterCard } from './RequesterCard';
import type { ToolSelectionHandler } from './SuggestedTools';
import { TicketActionBar } from './TicketActionBar';
import { TicketContextBar } from './TicketContextBar';
import { TicketIssueDetails } from './TicketIssueDetails';
import { useSessionHydrated, useTicketSession } from './TicketSessionProvider';
import { WorkspaceToolLauncher } from './WorkspaceToolLauncher';

const ORIENTATION_KEY = 'sd:first-guided-orientation-seen';
const TOOL_HINT_KEYS = ['article', 'category', 'computer', 'contact'] as const;

type PhonePane = 'case' | 'tool' | 'rail';

export function TicketWorkspace({ ticketId }: { ticketId: string }) {
  const { addNote, assignmentByTicket, getTicket } = useTicketSession();
  const isHydrated = useSessionHydrated();
  const ticket = getTicket(ticketId);
  const assignment = assignmentByTicket[ticketId];
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedToolSlug = searchParams.get('tool');
  const [activeToolSlug, setActiveToolSlug] = useState<string | null>(null);
  const [phonePane, setPhonePane] = useState<PhonePane>('case');
  const [orientationSeen, setOrientationSeen] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      setOrientationSeen(localStorage.getItem(ORIENTATION_KEY) === '1');
    } catch {
      setOrientationSeen(false);
    }
  }, []);

  useEffect(() => {
    const nextTool =
      requestedToolSlug && getToolBySlug(requestedToolSlug)
        ? requestedToolSlug
        : null;
    setActiveToolSlug(nextTool);
    if (nextTool) setPhonePane('tool');

    if (nextTool && !searchParams.get('ticket')) {
      const params = new URLSearchParams(searchParams.toString());
      params.set('ticket', ticketId);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    }
  }, [pathname, requestedToolSlug, router, searchParams, ticketId]);

  const setActiveTool = useCallback<ToolSelectionHandler>(
    (slug: ToolSlug, queryHints?: URLSearchParams) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const key of TOOL_HINT_KEYS) params.delete(key);
      params.set('tool', slug);
      params.set('ticket', ticketId);
      queryHints?.forEach((value, key) => params.set(key, value));

      setActiveToolSlug(slug);
      setPhonePane('tool');
      router.push(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [pathname, router, searchParams, ticketId],
  );

  if (!isHydrated) {
    return (
      <div
        aria-label="Loading ticket"
        className="mx-auto h-64 max-w-7xl animate-pulse rounded-sm bg-zinc-900"
      />
    );
  }

  if (!ticket) {
    return (
      <div className="mx-auto max-w-xl py-16 text-center">
        <h1 className="text-xl font-bold text-zinc-100">Case unavailable</h1>
        <p className="mt-2 text-sm text-zinc-400">
          This case is not assigned or unlocked for your current training.
          Return to the queue to continue an available case.
        </p>
        <Link
          className="sd-button sd-button--default sd-focus-ring mt-5 inline-flex min-h-10 items-center justify-center rounded-sm border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm font-extrabold uppercase text-zinc-200 hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          href="/"
        >
          Back to queue
        </Link>
      </div>
    );
  }

  if (assignment?.experience_mode === 'guided' && orientationSeen === false) {
    return (
      <section
        aria-labelledby="first-ticket-title"
        className="mx-auto max-w-2xl rounded-md border border-sky-400/30 bg-zinc-900 p-6 sm:p-8"
      >
        <p className="text-xs font-extrabold uppercase tracking-wide text-sky-400">
          Your first guided ticket
        </p>
        <h1
          className="mt-2 text-2xl font-bold text-zinc-100"
          id="first-ticket-title"
        >
          Before you open the ticket
        </h1>
        <ul className="mt-5 space-y-3 text-sm leading-relaxed text-zinc-300">
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
        <p className="mt-3 text-xs text-zinc-500">
          This orientation is saved in this browser.
        </p>
      </section>
    );
  }

  const experienceMode = assignment?.experience_mode ?? 'guided';

  return (
    <div className="mx-auto w-full max-w-[1540px] space-y-4 sm:space-y-5">
      <TicketContextBar assignment={assignment} ticket={ticket} />

      {/* GROUP 2 owns the authoritative WorkflowRail implementation. */}
      <section
        aria-label="Workflow rail placeholder"
        className="rounded-md border border-dashed border-zinc-700 bg-zinc-950/60 px-4 py-3"
        data-group-2-slot="workflow-rail"
      >
        <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
          Workflow progress
        </p>
        <p className="mt-1 text-xs text-zinc-400">
          Authoritative workflow stages will appear in this pinned rail.
        </p>
      </section>

      <Tabs
        onValueChange={(value) => setPhonePane(value as PhonePane)}
        value={phonePane}
      >
        <TabsList
          aria-label="Ticket workspace panes"
          className="grid grid-cols-3 sm:hidden"
        >
          <TabsTrigger value="case">Case</TabsTrigger>
          <TabsTrigger value="tool">Tool</TabsTrigger>
          <TabsTrigger value="rail">Rail</TabsTrigger>
        </TabsList>

        <div className="min-w-0 gap-4 lg:grid lg:grid-cols-[minmax(0,1.65fr)_minmax(18rem,0.85fr)]">
          <div className="min-w-0 space-y-4">
            <TabsContent
              className="m-0 data-[state=inactive]:hidden sm:!block sm:py-0"
              forceMount
              value="case"
            >
              <div className="space-y-4">
                <TicketIssueDetails description={ticket.description} />
                <div className="grid gap-4 md:grid-cols-2">
                  <RequesterCard requester={ticket.requester} />
                  <RelatedDevicePanel device={ticket.device} />
                </div>
              </div>
            </TabsContent>

            <TabsContent
              className="m-0 data-[state=inactive]:hidden sm:!block sm:py-0"
              forceMount
              value="tool"
            >
              <ActiveToolPane
                activeTicketId={ticket.id}
                activeToolSlug={activeToolSlug}
              />
            </TabsContent>
          </div>

          <TabsContent
            className="m-0 min-w-0 data-[state=inactive]:hidden sm:mt-4 sm:!block sm:py-0 lg:mt-0"
            forceMount
            value="rail"
          >
            <aside
              aria-label="Ticket workspace rail"
              className="min-w-0 space-y-4"
            >
              <WorkspaceToolLauncher
                activeToolSlug={activeToolSlug}
                experienceMode={experienceMode}
                onSelectTool={setActiveTool}
                ticketCategory={ticket.category}
                ticketId={ticket.id}
                toolSlugs={ticket.suggestedTools}
              />
              <TicketActionBar ticket={ticket} />
              <NotesSection
                notes={ticket.notes}
                onAddNote={(body) => addNote(ticket.id, body)}
              />
              {/* GROUP 2 replaces the retained NotesSection/HintDialog surfaces here. */}
            </aside>
          </TabsContent>
        </div>
      </Tabs>

      <OutcomeBar ticket={ticket} />
      <ActivityTimeline events={ticket.activity} />
    </div>
  );
}
