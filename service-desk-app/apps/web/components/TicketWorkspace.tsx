'use client';

import { IconArrowLeft, IconUserCheck } from '@tabler/icons-react';
import Link from 'next/link';

import { ActivityTimeline } from './ActivityTimeline';
import { NotesSection } from './NotesSection';
import { RelatedDevicePanel } from './RelatedDevicePanel';
import { RequesterCard } from './RequesterCard';
import { SuggestedTools } from './SuggestedTools';
import { TicketActionBar } from './TicketActionBar';
import { TicketDetailHeader } from './TicketDetailHeader';
import { TicketIssueDetails } from './TicketIssueDetails';
import { useSessionHydrated, useTicketSession } from './TicketSessionProvider';
import { ticketWorkflowState } from './ticket-workflow';
import { useEffect, useState } from 'react';

const ORIENTATION_KEY = 'sd:first-guided-orientation-seen';

export function TicketWorkspace({ ticketId }: { ticketId: string }) {
  const { addNote, assignmentByTicket, getTicket } = useTicketSession();
  const isHydrated = useSessionHydrated();
  const ticket = getTicket(ticketId);
  const assignment = assignmentByTicket[ticketId];
  const [orientationSeen, setOrientationSeen] = useState<boolean | null>(null);
  useEffect(() => {
    try { setOrientationSeen(localStorage.getItem(ORIENTATION_KEY) === '1'); }
    catch { setOrientationSeen(false); }
  }, []);

  if (!isHydrated) {
    return (
      <div
        className="mx-auto h-64 max-w-7xl animate-pulse rounded-sm bg-zinc-900"
        aria-label="Loading ticket"
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
    return <section className="mx-auto max-w-2xl rounded-md border border-sky-400/30 bg-zinc-900 p-6 sm:p-8" aria-labelledby="first-ticket-title"><p className="text-xs font-extrabold uppercase tracking-wide text-sky-400">Your first guided ticket</p><h1 className="mt-2 text-2xl font-bold text-zinc-100" id="first-ticket-title">Before you open the ticket</h1><ul className="mt-5 space-y-3 text-sm leading-relaxed text-zinc-300"><li>• This is a practice ticket from a user.</li><li>• Investigate before changing anything.</li><li>• Evidence gathered after a fix may not count as investigation.</li><li>• You cannot damage a real computer here.</li><li>• Escalating can be the correct professional decision.</li></ul><button className="sd-button sd-button--primary sd-focus-ring mt-6 inline-flex min-h-10 items-center justify-center px-4 py-2 font-bold" onClick={() => { try { localStorage.setItem(ORIENTATION_KEY, '1'); } catch { /* Browser storage is optional; keep the current session usable. */ } setOrientationSeen(true); }} type="button">Open ticket</button><p className="mt-3 text-xs text-zinc-500">This orientation is saved in this browser.</p></section>;
  }

  const workflow = ticketWorkflowState(ticket);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-4 sm:space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          className="sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-semibold text-zinc-400 transition-colors hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          href="/"
        >
          <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
          Back to queue
        </Link>
        <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
          <IconUserCheck aria-hidden="true" className="h-4 w-4 text-sky-400" />
          {ticket.assignedTo === 'you'
            ? 'Assigned to you'
            : 'Shared queue incident'}
        </span>
      </div>

      <TicketDetailHeader
        assignment={assignment}
        ticket={ticket}
      />
      <section
        aria-label="Professional ticket workflow"
        className="rounded-md border border-zinc-800 bg-zinc-950/60 px-3 py-3 sm:px-4"
      >
        <p className="text-[11px] font-extrabold uppercase tracking-wide text-zinc-500">
          Work the case
        </p>
        <ol className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {workflow.map((step) => (
            <li className={`rounded-sm border p-3 ${step.current ? 'border-sky-400 bg-sky-400/10' : step.complete ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-zinc-800 bg-zinc-900/50'}`} key={step.key} aria-current={step.current ? 'step' : undefined}>
              <div className="flex items-center gap-2 text-xs font-bold text-zinc-200">
              <span aria-hidden="true">{step.complete ? '✓' : step.current ? '→' : '○'}</span><span>{step.label}</span></div>
              {assignment?.experience_mode === 'guided' ? <p className="mt-1 text-[11px] leading-relaxed text-zinc-400">{step.help}</p> : null}
            </li>
          ))}
        </ol>
      </section>
      <TicketActionBar ticket={ticket} />

      <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(18rem,0.85fr)]">
        <div className="min-w-0 space-y-4">
          <TicketIssueDetails description={ticket.description} />
          <NotesSection
            notes={ticket.notes}
            onAddNote={(body) => addNote(ticket.id, body)}
          />
        </div>
        <aside
          aria-label="Requester and related context"
          className="min-w-0 space-y-4"
        >
          <RequesterCard requester={ticket.requester} />
          <RelatedDevicePanel device={ticket.device} />
          <SuggestedTools
            experienceMode={
              assignmentByTicket[ticket.id]?.experience_mode ?? 'guided'
            }
            ticketCategory={ticket.category}
            ticketId={ticket.id}
            toolSlugs={ticket.suggestedTools}
          />
        </aside>
      </div>

      <ActivityTimeline events={ticket.activity} />
    </div>
  );
}
