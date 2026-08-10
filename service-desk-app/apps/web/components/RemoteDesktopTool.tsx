'use client';

import type {
  ActionEvent,
  RemoteDesktopScenarioProgress,
} from '@service-desk/simulation-engine';
import {
  REMOTE_DESKTOP_APP_IDS,
  REMOTE_DESKTOP_SCENARIOS,
  getDocumentationArticle,
  getRemoteDesktopScenarioByTicket,
  type RemoteDesktopAppId,
} from '@service-desk/shared';
import { Badge, Button, Input } from '@service-desk/ui';
import {
  IconAppWindow,
  IconAlertTriangle,
  IconArrowLeft,
  IconBrandWindows,
  IconCheck,
  IconChevronDown,
  IconDatabase,
  IconDeviceDesktop,
  IconFolder,
  IconFile,
  IconKey,
  IconLock,
  IconMail,
  IconMaximize,
  IconMessageCircle,
  IconMinus,
  IconNetwork,
  IconRefresh,
  IconSearch,
  IconSettings,
  IconShieldCheck,
  IconTerminal2,
  IconTrash,
  IconWifi,
  IconWorld,
  IconX,
} from '@tabler/icons-react';
import Link from 'next/link';
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';

import {
  type RemoteDesktopWorkstationRecord,
  useCompanyChatSession,
  useDirectorySession,
  useRemoteDesktopSession,
  useSessionIdentity,
  useTicketSession,
} from './TicketSessionProvider';
import {
  canInspectScenarioRequirements,
  hasAnotherHint,
  mentorScenarioRequirements,
  progressiveHints,
  scenarioActionLabel,
  shouldProactivelyRevealHint,
  studentFeedbackMessage,
} from '../lib/remote-desktop-learning';

const APP_META: Record<
  RemoteDesktopAppId,
  { label: string; Icon: typeof IconAppWindow; tint: string }
> = {
  explorer: {
    label: 'File Explorer',
    Icon: IconFolder,
    tint: 'text-amber-300',
  },
  vpn: { label: 'VPN Client', Icon: IconShieldCheck, tint: 'text-emerald-300' },
  settings: { label: 'Settings', Icon: IconSettings, tint: 'text-zinc-100' },
  services: {
    label: 'Services',
    Icon: IconTerminal2,
    tint: 'text-orange-300',
  },
  chat: {
    label: 'Company Chat',
    Icon: IconMessageCircle,
    tint: 'text-sky-300',
  },
  mail: { label: 'Mail', Icon: IconMail, tint: 'text-blue-300' },
  browser: { label: 'Web Browser', Icon: IconWorld, tint: 'text-cyan-300' },
  updates: {
    label: 'System Update',
    Icon: IconRefresh,
    tint: 'text-violet-300',
  },
  trash: { label: 'Trash', Icon: IconTrash, tint: 'text-zinc-300' },
  system: { label: 'System Tools', Icon: IconTerminal2, tint: 'text-lime-300' },
  terminal: {
    label: 'Terminal',
    Icon: IconTerminal2,
    tint: 'text-emerald-300',
  },
};

const TICKET_TOOL_LABELS: Record<string, string> = {
  'asset-management': 'Asset records',
  'company-chat': 'Company Chat',
  directory: 'Directory',
  documentation: 'Knowledge base',
  'remote-desktop': 'Remote Desktop',
  'server-room': 'Server Room',
};

function initialTicketFromUrl() {
  if (typeof window === 'undefined') return 'INC2406';
  const value = new URLSearchParams(window.location.search).get('ticket');
  return value && getRemoteDesktopScenarioByTicket(value) ? value : 'INC2406';
}

function replaceLocation(ticketId: string, assetTag: string | null) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  url.searchParams.set('ticket', ticketId);
  if (assetTag) url.searchParams.set('computer', assetTag);
  else url.searchParams.delete('computer');
  window.history.replaceState(null, '', url);
}

function pushLocation(ticketId: string, assetTag: string) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  url.searchParams.set('ticket', ticketId);
  url.searchParams.set('computer', assetTag);
  window.history.pushState(null, '', url);
}

export function RemoteDesktopTool() {
  const remote = useRemoteDesktopSession();
  const tickets = useTicketSession();
  const identity = useSessionIdentity();
  const [ticketId, setTicketId] = useState(initialTicketFromUrl);
  const [computer, setComputer] = useState<string | null>(() =>
    typeof window === 'undefined'
      ? null
      : new URLSearchParams(window.location.search).get('computer'),
  );
  const [query, setQuery] = useState('');
  const consoleLabel =
    ticketId === 'INC2402' ? 'Managed Device Console' : 'Remote Desktop';
  const [ticketOpen, setTicketOpen] = useState(true);
  const [toast, setToast] = useState<ActionEvent | null>(null);
  const scenario =
    getRemoteDesktopScenarioByTicket(ticketId) ?? REMOTE_DESKTOP_SCENARIOS[0]!;
  const ticket = tickets.getTicket(scenario.ticketId);
  const workstation =
    remote.workstations.find((item) => item.assetTag === computer) ?? null;
  const learningMode = workstation?.learningMode ?? 'guided';
  const hintsRevealed = ticket?.hintsRevealedCount ?? 0;
  const canReviewScenario = canInspectScenarioRequirements(identity);
  const scenarioComplete =
    workstation?.completedScenarioIds.includes(scenario.id) ?? false;
  const revealedHints = progressiveHints(
    scenario,
    hintsRevealed,
    learningMode,
    scenarioComplete,
  );
  const workflowProgress = workstation?.scenarioProgress[scenario.id];

  useEffect(() => replaceLocation(ticketId, computer), [computer, ticketId]);
  useEffect(() => {
    const onPopState = () => {
      const params = new URLSearchParams(window.location.search);
      const nextTicketId = params.get('ticket');
      setTicketId(
        nextTicketId && getRemoteDesktopScenarioByTicket(nextTicketId)
          ? nextTicketId
          : 'INC2406',
      );
      setComputer(params.get('computer'));
    };

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);
  useEffect(() => {
    if (!workstation || workstation.connectionState !== 'connecting') return;
    const timer = window.setTimeout(() => {
      setToast(remote.beginLogin(workstation.assetTag, scenario.ticketId));
    }, 650);
    return () => window.clearTimeout(timer);
  }, [remote, scenario.ticketId, workstation]);
  useEffect(() => {
    if (
      ticket &&
      shouldProactivelyRevealHint(
        scenario,
        hintsRevealed,
        learningMode,
        scenarioComplete,
      )
    ) {
      tickets.recordHintReveal(ticket.id, 1);
    }
  }, [
    hintsRevealed,
    learningMode,
    scenario,
    scenarioComplete,
    ticket,
    tickets,
  ]);

  const selectScenario = (nextTicketId: string) => {
    setComputer(null);
    setTicketId(nextTicketId);
    setToast(null);
  };
  const report = (event: ActionEvent) => {
    if (
      event.type === 'remote_desktop.run_terminal_command' ||
      event.type === 'remote_desktop.explorer_navigate' ||
      event.type === 'remote_desktop.explorer_refresh'
    )
      return;
    if (scenarioComplete && !event.success) return;
    if (
      !event.success &&
      learningMode === 'guided' &&
      ticket &&
      hasAnotherHint(scenario, hintsRevealed, learningMode, scenarioComplete)
    ) {
      tickets.recordHintReveal(ticket.id, hintsRevealed + 1);
    }
    setToast(event);
  };
  const revealNextHint = () => {
    if (
      !ticket ||
      !hasAnotherHint(scenario, hintsRevealed, learningMode, scenarioComplete)
    )
      return;
    tickets.recordHintReveal(ticket.id, hintsRevealed + 1);
  };

  return (
    <section
      className="mx-auto min-w-0 w-full max-w-[1540px]"
      aria-labelledby="remote-desktop-title"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 px-1">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-[0.16em] text-sky-400">
            Support simulation
          </p>
          <h1
            id="remote-desktop-title"
            className="font-display text-2xl font-bold text-zinc-100"
          >
            {consoleLabel}
          </h1>
        </div>
        {canReviewScenario ? (
          <label className="flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-950/70 px-3 py-1.5 text-xs font-semibold text-zinc-300">
            <span className="text-sky-300">Learning mode</span>
            <select
              aria-label="Learning mode"
              className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-zinc-100"
              disabled={!workstation}
              onChange={(event) =>
                workstation &&
                report(
                  remote.setLearningMode(
                    workstation.assetTag,
                    event.target.value as 'guided' | 'practice' | 'assessment',
                  ),
                )
              }
              value={learningMode}
            >
              <option value="guided">Guided</option>
              <option value="practice">Practice</option>
              <option value="assessment">Assessment</option>
            </select>
          </label>
        ) : null}
      </div>

      {toast && !(scenarioComplete && !toast.success) ? (
        <Feedback
          event={toast}
          learningMode={learningMode}
          onDismiss={() => setToast(null)}
        />
      ) : null}

      <div className="grid min-w-0 gap-3 xl:min-h-[calc(100dvh-12rem)] xl:grid-cols-[minmax(17rem,0.72fr)_minmax(0,1.65fr)] xl:items-stretch">
        <aside
          className={`min-w-0 overflow-hidden border border-sky-900/30 bg-zinc-950 shadow-sm ${ticketOpen ? '' : 'max-xl:hidden'}`}
        >
          <button
            aria-expanded={ticketOpen}
            className="flex w-full items-center justify-between border-b border-sky-900/30 bg-zinc-900 px-4 py-3 text-left xl:pointer-events-none"
            onClick={() => setTicketOpen((open) => !open)}
            type="button"
          >
            <span className="font-label text-xs font-extrabold uppercase tracking-[0.14em] text-sky-300">
              Ticket workspace
            </span>
            <IconChevronDown
              aria-hidden="true"
              className={`h-4 w-4 text-zinc-400 transition-transform ${ticketOpen ? '' : '-rotate-90'}`}
            />
          </button>
          <div className="space-y-5 p-5 text-zinc-200">
            <label className="block">
              <span className="sr-only">Choose a ticket</span>
              <select
                aria-label="Choose a ticket"
                className="w-full rounded-sm border border-zinc-700/80 bg-zinc-900 px-3 py-2.5 text-sm font-medium text-zinc-100"
                onChange={(event) => selectScenario(event.target.value)}
                value={scenario.ticketId}
              >
                {REMOTE_DESKTOP_SCENARIOS.map((item) => (
                  <option key={item.id} value={item.ticketId}>
                    {tickets.getTicket(item.ticketId)?.title ?? item.title}
                  </option>
                ))}
              </select>
            </label>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-sky-300">
                {ticket?.priority ?? 'High'} priority
              </p>
              <h2 className="mt-2 text-xl font-bold leading-snug text-zinc-50">
                {ticket?.title ?? 'Support request'}
              </h2>
              <p className="mt-3 text-sm leading-6 text-zinc-200">
                <span className="font-semibold text-zinc-100">Requester:</span>{' '}
                {ticket?.requester.name ?? 'Employee'} ·{' '}
                {ticket?.requester.department ?? 'Support'}
              </p>
            </section>

            <section className="space-y-3 border-y border-zinc-800/80 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">
                  Issue
                </p>
                <p className="mt-1.5 text-sm leading-6 text-zinc-100">
                  {ticket?.description.issue ??
                    'Review the reported issue on the affected device.'}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">
                  Business impact
                </p>
                <p className="mt-1.5 text-sm leading-6 text-zinc-200">
                  {ticket?.description.businessImpact ??
                    'The requester needs service restored.'}
                </p>
              </div>
              <div className="rounded-sm bg-zinc-900/70 px-3 py-2.5 text-sm text-zinc-300">
                <span className="font-semibold text-zinc-100">
                  Affected device:
                </span>{' '}
                <span className="font-mono text-sky-200">
                  {ticket?.device.deviceName ?? scenario.assetTag}
                </span>
              </div>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">
                Already tried
              </p>
              <ul className="mt-2 space-y-2 text-sm leading-6 text-zinc-200">
                {(ticket?.description.troubleshooting ?? []).map((entry) => (
                  <li className="flex gap-2" key={entry}>
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400" />
                    {entry}
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-500">
                Available tools
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(ticket?.suggestedTools ?? ['remote-desktop']).map((tool) => (
                  <span
                    className="rounded-full bg-sky-400/10 px-2.5 py-1 text-xs font-medium text-sky-200"
                    key={tool}
                  >
                    {TICKET_TOOL_LABELS[tool] ?? tool}
                  </span>
                ))}
              </div>
            </section>

            <ProgressiveHints
              canReveal={hasAnotherHint(
                scenario,
                hintsRevealed,
                learningMode,
                scenarioComplete,
              )}
              completed={scenarioComplete}
              hints={revealedHints}
              learningMode={learningMode}
              onReveal={revealNextHint}
            />

            {scenario.workflow && workstation && !scenarioComplete ? (
              <WorkflowClosure
                onClose={() =>
                  ticket &&
                  workflowProgress?.internalNote &&
                  tickets.closeTicket(ticket.id, {
                    resolutionNote: workflowProgress.internalNote,
                    verifiedResolved: true,
                  })
                }
                onSaveNote={(text) =>
                  report(
                    remote.addInternalNote(
                      workstation.assetTag,
                      scenario.ticketId,
                      text,
                    ),
                  )
                }
                progress={workflowProgress}
                scenario={scenario}
              />
            ) : null}

            {workstation?.completedScenarioIds.includes(scenario.id) ? (
              <CompletionSummary
                hintsUsed={hintsRevealed}
                hintTexts={scenario.studentHints.slice(0, hintsRevealed)}
                onClose={
                  scenario.workflow
                    ? undefined
                    : () =>
                        ticket &&
                        tickets.closeTicket(ticket.id, {
                          resolutionNote: '',
                          verifiedResolved: true,
                        })
                }
                progress={workflowProgress}
                scenario={scenario}
                workstation={workstation}
              />
            ) : null}

            {canReviewScenario ? (
              <MentorScenarioReview scenario={scenario} />
            ) : null}
          </div>
        </aside>

        <main className="flex min-w-0 min-h-[calc(100dvh-12rem)] bg-zinc-100 shadow-[0_18px_50px_rgba(0,0,0,.22)] xl:min-h-0">
          {workstation ? (
            <RemoteSurface
              onBack={() => setComputer(null)}
              onEvent={report}
              remote={remote}
              scenario={scenario}
              workstation={workstation}
            />
          ) : (
            <ComputerPicker
              isHydrated={remote.isHydrated}
              onConnect={(assetTag) => {
                pushLocation(scenario.ticketId, assetTag);
                setComputer(assetTag);
                report(remote.connect(assetTag, scenario.ticketId));
              }}
              onQueryChange={setQuery}
              query={query}
              scenario={scenario}
              workstations={remote.workstations}
            />
          )}
        </main>
      </div>
    </section>
  );
}

function Feedback({
  event,
  learningMode,
  onDismiss,
}: {
  event: ActionEvent;
  learningMode: 'guided' | 'practice' | 'assessment';
  onDismiss: () => void;
}) {
  return (
    <div
      className={`mb-3 flex items-start justify-between gap-3 border px-4 py-3 text-sm ${event.success ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100' : 'border-amber-400/35 bg-amber-400/10 text-amber-100'}`}
      role={event.success ? 'status' : 'alert'}
    >
      <span>
        <strong>
          {event.success
            ? 'Saved.'
            : learningMode === 'assessment'
              ? 'Not accepted.'
              : 'Try another approach.'}
        </strong>{' '}
        {studentFeedbackMessage(event, learningMode)}
      </span>
      <button
        aria-label="Dismiss message"
        className="text-current"
        onClick={onDismiss}
        type="button"
      >
        <IconX aria-hidden="true" className="h-4 w-4" />
      </button>
    </div>
  );
}

function ProgressiveHints({
  canReveal,
  completed,
  hints,
  learningMode,
  onReveal,
}: {
  canReveal: boolean;
  completed: boolean;
  hints: readonly string[];
  learningMode: 'guided' | 'practice' | 'assessment';
  onReveal: () => void;
}) {
  const hasHints = hints.length > 0;
  return (
    <section className="rounded-sm bg-sky-500/[0.07] p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-sky-300">
            {learningMode === 'guided'
              ? 'Guided support'
              : learningMode === 'practice'
                ? 'Practice hints'
                : 'Assessment mode'}
          </p>
          <p className="mt-1 text-sm leading-5 text-sky-100/80">
            {learningMode === 'guided'
              ? 'The first hint appears proactively; reveal more as you work.'
              : learningMode === 'practice'
                ? 'Hints are available on request.'
                : completed
                  ? 'Hints are now available because the assessment is complete.'
                  : 'Hints remain unavailable until this assessment is complete.'}
          </p>
        </div>
      </div>
      {hasHints ? (
        <ol className="mt-3 space-y-2 text-sm leading-5 text-sky-50">
          {hints.map((hint, index) => (
            <li className="flex gap-2" key={hint}>
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-sky-400/20 text-xs font-bold text-sky-200">
                {index + 1}
              </span>
              <span>{hint}</span>
            </li>
          ))}
        </ol>
      ) : null}
      {canReveal ? (
        <button
          className="mt-3 text-sm font-semibold text-sky-200 underline decoration-sky-400/60 underline-offset-4 hover:text-white"
          onClick={onReveal}
          type="button"
        >
          Reveal another hint
        </button>
      ) : hasHints && learningMode !== 'assessment' ? (
        <p className="mt-3 text-xs text-sky-100/65">
          No more hints are available.
        </p>
      ) : null}
    </section>
  );
}

function WorkflowClosure({
  onClose,
  onSaveNote,
  progress,
  scenario,
}: {
  onClose: () => void;
  onSaveNote: (text: string) => void;
  progress: RemoteDesktopScenarioProgress | undefined;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
}) {
  const [note, setNote] = useState(progress?.internalNote ?? '');
  const minimumLength = scenario.workflow?.note.minimumLength ?? 20;
  const readyToClose = Boolean(
    progress?.phases.diagnosed &&
      progress.phases.fixed &&
      progress.phases.verified &&
      progress.phases.noted,
  );

  useEffect(() => {
    setNote(progress?.internalNote ?? '');
  }, [progress?.internalNote]);

  const phases = [
    ['Diagnosis evidence', progress?.phases.diagnosed],
    ['Correct fix', progress?.phases.fixed],
    ['Post-fix verification', progress?.phases.verified],
    ['Internal note', progress?.phases.noted],
  ] as const;

  return (
    <section className="rounded-sm border border-sky-400/30 bg-sky-500/[0.07] p-4">
      <p className="font-display text-lg font-bold text-sky-100">
        Resolution workflow
      </p>
      <ul className="mt-3 grid gap-2 text-sm text-sky-50 sm:grid-cols-2">
        {phases.map(([label, complete]) => (
          <li className="flex items-center gap-2" key={label}>
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold ${complete ? 'bg-emerald-400/20 text-emerald-200' : 'bg-zinc-700 text-zinc-300'}`}
            >
              {complete ? '✓' : '•'}
            </span>
            {label}
          </li>
        ))}
      </ul>
      <form
        className="mt-4"
        onSubmit={(event) => {
          event.preventDefault();
          onSaveNote(note);
        }}
      >
        <label className="block text-sm font-semibold text-sky-100">
          Student-authored internal note
          <textarea
            aria-describedby="internal-note-help"
            className="mt-2 min-h-24 w-full rounded-sm border border-zinc-700 bg-zinc-950 p-3 text-sm font-normal text-zinc-100"
            maxLength={1000}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Describe the evidence, root cause, fix, and verification in your own words."
            value={note}
          />
        </label>
        <p className="mt-1 text-xs text-sky-100/70" id="internal-note-help">
          Minimum {minimumLength} characters. Document the diagnosis, repair,
          and verification in your own words; the note is never autofilled.
        </p>
        <Button
          className="mt-3"
          disabled={note.trim().length < minimumLength}
          type="submit"
          variant="light"
        >
          Save internal note
        </Button>
      </form>
      <div className="mt-4 border-t border-sky-300/20 pt-4">
        <Button disabled={!readyToClose} onClick={onClose} variant="soft">
          Close ticket
        </Button>
        {!readyToClose ? (
          <p className="mt-2 text-xs leading-5 text-sky-100/70">
            Close stays blocked until diagnosis, fix, verification, and a saved
            internal note are complete.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function CompletionSummary({
  hintTexts,
  hintsUsed,
  onClose,
  progress,
  scenario,
  workstation,
}: {
  hintTexts: readonly string[];
  hintsUsed: number;
  onClose?: () => void;
  progress: RemoteDesktopScenarioProgress | undefined;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const complete = new Set(workstation.scenarioSteps[scenario.id] ?? []);
  const evidence = progress
    ? [
        ...progress.diagnosisEvidence,
        ...progress.fixEvidence,
        ...progress.verificationEvidence,
      ]
    : scenario.requiredSteps;
  const performed = new Set([
    ...complete,
    ...(progress?.diagnosisEvidence ?? []),
    ...(progress?.fixEvidence ?? []),
    ...(progress?.verificationEvidence ?? []),
  ]);
  const missedOptional = scenario.optionalSteps.filter(
    (step) => !performed.has(step),
  );
  return (
    <section className="rounded-sm border border-emerald-400/35 bg-emerald-400/[0.08] p-4">
      <IconCheck aria-hidden="true" className="h-7 w-7 text-emerald-300" />
      <p className="mt-2 font-display text-xl font-bold text-emerald-100">
        Solution complete
      </p>
      <div className="mt-4 space-y-3 text-sm leading-6 text-emerald-50/90">
        <p>
          <span className="font-semibold text-emerald-200">Root cause:</span>{' '}
          {scenario.completion.rootCause}
        </p>
        <p>
          <span className="font-semibold text-emerald-200">Fix performed:</span>{' '}
          {scenario.completion.whatFixed}
        </p>
        <p>
          <span className="font-semibold text-emerald-200">Why it worked:</span>{' '}
          {scenario.completion.whyItWorked}
        </p>
      </div>
      <div className="mt-4 border-t border-emerald-300/20 pt-3 text-sm">
        <p className="font-semibold text-emerald-100">Evidence gathered</p>
        <ul className="mt-1.5 space-y-1 text-emerald-50/85">
          {evidence.map((step) => (
            <li key={step}>• {scenarioActionLabel(scenario, step)}</li>
          ))}
        </ul>
        <p className="mt-3 font-semibold text-emerald-100">
          Missed useful actions
        </p>
        <p className="mt-1 text-emerald-50/85">
          {missedOptional.length
            ? missedOptional
                .map((step) => scenarioActionLabel(scenario, step))
                .join(', ')
            : 'None.'}
        </p>
        <p className="mt-3 font-semibold text-emerald-100">
          Hints used: {hintsUsed}
        </p>
        <p className="mt-1 text-emerald-50/85">
          {hintTexts.length ? hintTexts.join(' · ') : 'None.'}
        </p>
        <p className="mt-3 text-emerald-50/85">
          <span className="font-semibold text-emerald-100">Final score:</span>{' '}
          {progress?.finalScore ?? 100}/100
        </p>
        <p className="mt-1 text-emerald-50/85">
          <span className="font-semibold text-emerald-100">Feedback:</span>{' '}
          {progress?.feedback ?? 'The reported service is working again.'}
        </p>
      </div>
      {onClose ? (
        <Button className="mt-4" onClick={onClose} variant="soft">
          Close ticket
        </Button>
      ) : null}
    </section>
  );
}

function MentorScenarioReview({
  scenario,
}: {
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
}) {
  return (
    <details className="rounded-sm border border-violet-400/20 bg-violet-500/[0.05] p-3">
      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.12em] text-violet-200">
        Mentor scenario review
      </summary>
      <p className="mt-3 text-sm text-violet-50/80">Required grading checks</p>
      <ul className="mt-2 space-y-2 text-sm text-violet-50">
        {mentorScenarioRequirements(scenario).map((step) => (
          <li key={step.stepId}>
            <span>{step.label}</span>{' '}
            <code className="ml-1 text-xs text-violet-200">{step.stepId}</code>
          </li>
        ))}
      </ul>
    </details>
  );
}

function ComputerPicker({
  isHydrated,
  onConnect,
  onQueryChange,
  query,
  scenario,
  workstations,
}: {
  isHydrated: boolean;
  onConnect: (assetTag: string) => void;
  onQueryChange: (query: string) => void;
  query: string;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  workstations: readonly RemoteDesktopWorkstationRecord[];
}) {
  const filtered = useMemo(() => {
    const value = query.trim().toLowerCase();
    return workstations.filter(
      (item) =>
        !value ||
        [item.assetTag, item.employeeName, item.hostname].some((entry) =>
          entry.toLowerCase().includes(value),
        ),
    );
  }, [query, workstations]);
  return (
    <div className="flex min-h-0 flex-1 items-center bg-[#f7f8fb] px-4 py-8 sm:px-10">
      <div className="mx-auto max-w-[560px] overflow-hidden border border-sky-200 bg-white shadow-[0_7px_24px_rgba(14,165,233,.14)]">
        <div className="border-b border-sky-100 px-6 py-6 text-center">
          <h2 className="font-mono text-xl font-bold tracking-[0.12em] text-zinc-900">
            REMOTE DESKTOP
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            Select a computer to connect
          </p>
        </div>
        <div className="p-4">
          <label className="relative block">
            <IconSearch
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
            />
            <Input
              className="border-sky-400 bg-white pl-9 text-zinc-900 shadow-[0_0_0_3px_rgba(56,189,248,.14)]"
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Search by asset tag, hostname, or owner"
              type="search"
              value={query}
            />
          </label>
        </div>
        <div
          aria-label="Remote Desktop workstation list"
          className="max-h-[520px] overflow-y-auto px-4 pb-3"
        >
          {!isHydrated ? (
            <p className="p-6 text-center text-sm text-zinc-500">
              Restoring your simulated computers…
            </p>
          ) : (
            filtered.map((item) => {
              const isAffected = item.assetTag === scenario.assetTag;
              return (
                <div
                  className={`flex items-center gap-3 border-b px-3 py-3 ${isAffected ? 'border-sky-300 bg-sky-50' : 'border-sky-100'}`}
                  key={item.assetTag}
                >
                  <IconDeviceDesktop
                    aria-hidden="true"
                    className="h-5 w-5 shrink-0 text-zinc-500"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-xs font-semibold text-zinc-700">
                      {item.assetTag}
                    </p>
                    <p className="truncate text-sm text-zinc-700">
                      {item.employeeName}
                    </p>
                  </div>
                  <button
                    className="font-label text-xs font-extrabold uppercase tracking-wide text-sky-600 hover:text-sky-800"
                    onClick={() => onConnect(item.assetTag)}
                    type="button"
                  >
                    Connect
                  </button>
                </div>
              );
            })
          )}
          {isHydrated && filtered.length === 0 ? (
            <p className="p-6 text-center text-sm text-zinc-500">
              No computer matches that search.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function RemoteSurface({
  onBack,
  onEvent,
  remote,
  scenario,
  workstation,
}: {
  onBack: () => void;
  onEvent: (event: ActionEvent) => void;
  remote: ReturnType<typeof useRemoteDesktopSession>;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const [showDomain, setShowDomain] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [startOpen, setStartOpen] = useState(false);
  const status = workstation.connectionState;
  const sessionHeader = status !== 'disconnected';
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[#f7f8fb]">
      {sessionHeader ? (
        <div className="flex h-7 items-center justify-between border-b border-zinc-300 bg-white px-4 text-xs text-zinc-700">
          <span className="truncate">
            <IconDeviceDesktop
              aria-hidden="true"
              className="mr-1 inline h-3.5 w-3.5"
            />
            <span className="font-mono">{workstation.assetTag}</span> ·{' '}
            {workstation.employeeName}
          </span>
          <button
            className="font-semibold uppercase text-zinc-700 hover:text-red-700"
            onClick={() => {
              onEvent(remote.disconnect(workstation.assetTag));
              onBack();
            }}
            type="button"
          >
            Disconnect
          </button>
        </div>
      ) : null}
      {status === 'connecting' ? (
        <ConnectingScreen
          workstation={workstation}
          onCancel={() => {
            onEvent(remote.cancelConnection(workstation.assetTag));
            onBack();
          }}
        />
      ) : null}
      {status === 'login' || status === 'error' ? (
        <LoginGate
          domainOpen={showDomain}
          error={workstation.lastError}
          hintOpen={showHint}
          onCancel={() => {
            onEvent(remote.cancelConnection(workstation.assetTag));
            onBack();
          }}
          onDomain={() => setShowDomain((open) => !open)}
          onHint={() => setShowHint((open) => !open)}
          onRetry={() =>
            onEvent(remote.beginLogin(workstation.assetTag, scenario.ticketId))
          }
          onSubmit={() =>
            onEvent(
              remote.authenticate(
                workstation.assetTag,
                scenario.ticketId,
                username.trim().length > 0,
                password.trim().length > 0,
              ),
            )
          }
          password={password}
          setPassword={setPassword}
          setUsername={setUsername}
          username={username}
          workstation={workstation}
        />
      ) : null}
      {status === 'connected' ? (
        <SimulatedDesktop
          onEvent={onEvent}
          remote={remote}
          scenario={scenario}
          startOpen={startOpen}
          setStartOpen={setStartOpen}
          workstation={workstation}
        />
      ) : null}
    </div>
  );
}

function ConnectingScreen({
  onCancel,
  workstation,
}: {
  onCancel: () => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  return (
    <div className="flex min-h-0 flex-1 items-center justify-center bg-[#bdbdbd]">
      <div className="text-center">
        <span className="mx-auto block h-10 w-10 animate-spin rounded-full border-4 border-sky-500 border-t-transparent" />
        <p className="mt-4 font-semibold text-zinc-700">
          Connecting to {workstation.assetTag}…
        </p>
        <Button className="mt-4" onClick={onCancel} variant="light">
          Cancel
        </Button>
      </div>
    </div>
  );
}

function LoginGate({
  domainOpen,
  error,
  hintOpen,
  onCancel,
  onDomain,
  onHint,
  onRetry,
  onSubmit,
  password,
  setPassword,
  setUsername,
  username,
  workstation,
}: {
  domainOpen: boolean;
  error: string | null;
  hintOpen: boolean;
  onCancel: () => void;
  onDomain: () => void;
  onHint: () => void;
  onRetry: () => void;
  onSubmit: () => void;
  password: string;
  setPassword: (value: string) => void;
  setUsername: (value: string) => void;
  username: string;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  return (
    <div className="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-[#bdbdbd] p-4">
      <div className="w-full max-w-[430px] overflow-hidden border border-[#0d315c] bg-[#112f56] shadow-2xl">
        <div className="bg-white px-3 py-1.5 text-sm font-medium text-zinc-900">
          Remote Login
        </div>
        <div className="px-8 py-7 text-center text-white">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded bg-sky-700/40 text-sky-200">
            <IconDeviceDesktop aria-hidden="true" className="h-7 w-7" />
          </span>
          <p className="mt-3 font-bold">{workstation.assetTag}</p>
          <p className="mt-1 text-xs text-sky-100/65">
            Enter your simulated admin credentials for the remote computer
          </p>
          <button
            className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-sky-200 hover:text-white"
            onClick={onHint}
            type="button"
          >
            <IconKey aria-hidden="true" className="h-3.5 w-3.5" />
            {hintOpen ? 'Hide hint' : 'Hint'}
          </button>
          {hintOpen ? (
            <p className="mt-2 rounded border border-sky-300/20 bg-sky-950/30 p-2 text-xs text-sky-100">
              Any non-empty simulated administrator credentials are accepted for
              the affected machine.
            </p>
          ) : null}
          {error ? (
            <div
              className="mt-3 rounded border border-amber-300/40 bg-amber-200/10 p-2 text-xs text-amber-100"
              role="alert"
            >
              <p>{error}</p>
              <button
                className="mt-2 font-bold underline"
                onClick={onRetry}
                type="button"
              >
                Return to login
              </button>
            </div>
          ) : null}
          <div className="mt-4 space-y-2.5 text-left">
            <label className="flex items-center gap-2">
              <IconKey aria-hidden="true" className="h-5 w-5 text-white/80" />
              <input
                className="min-w-0 flex-1 border border-zinc-500 bg-white px-2 py-1.5 text-sm text-zinc-900"
                onChange={(event) => setUsername(event.target.value)}
                placeholder="e.g. jdoe"
                value={username}
              />
            </label>
            <label className="flex items-center gap-2">
              <IconLock aria-hidden="true" className="h-5 w-5 text-white/80" />
              <input
                className="min-w-0 flex-1 border border-zinc-500 bg-white px-2 py-1.5 text-sm text-zinc-900"
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Domain password"
                type="password"
                value={password}
              />
            </label>
            {domainOpen ? (
              <label className="flex items-center gap-2">
                <IconNetwork
                  aria-hidden="true"
                  className="h-5 w-5 text-white/80"
                />
                <input
                  className="min-w-0 flex-1 border border-zinc-500 bg-white px-2 py-1.5 text-sm italic text-zinc-900"
                  defaultValue="nexus-simulator"
                  readOnly
                />
              </label>
            ) : null}
            <button
              aria-expanded={domainOpen}
              aria-label={
                domainOpen ? 'Hide domain options' : 'Show domain options'
              }
              className="float-right p-1 text-white/75 hover:text-white"
              onClick={onDomain}
              type="button"
            >
              <IconChevronDown
                aria-hidden="true"
                className={`h-4 w-4 ${domainOpen ? 'rotate-180' : ''}`}
              />
            </button>
          </div>
          <div className="clear-both mt-8 flex justify-center gap-3">
            <button
              className="min-w-32 border border-sky-300 bg-sky-600 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/10 disabled:text-white/40"
              disabled={Boolean(error) || !username.trim() || !password.trim()}
              onClick={onSubmit}
              type="button"
            >
              OK
            </button>
            <button
              className="min-w-32 border border-white/35 px-4 py-2 text-sm font-semibold hover:bg-white/10"
              onClick={onCancel}
              type="button"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SimulatedDesktop({
  onEvent,
  remote,
  scenario,
  setStartOpen,
  startOpen,
  workstation,
}: {
  onEvent: (event: ActionEvent) => void;
  remote: ReturnType<typeof useRemoteDesktopSession>;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  setStartOpen: (value: boolean) => void;
  startOpen: boolean;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const visibleApps = workstation.openApps.filter(
    (appId) => !workstation.minimizedApps.includes(appId),
  );
  const scenarioComplete = workstation.completedScenarioIds.includes(
    scenario.id,
  );
  const runStep = (stepId: string) =>
    !scenarioComplete &&
    onEvent(
      remote.performScenarioStep(
        workstation.assetTag,
        scenario.ticketId,
        stepId,
      ),
    );
  return (
    <div className="relative flex min-h-0 flex-1 overflow-hidden bg-[radial-gradient(circle_at_76%_16%,rgba(91,234,208,.54),transparent_25%),radial-gradient(circle_at_18%_80%,rgba(44,146,197,.38),transparent_32%),linear-gradient(135deg,#0a3854,#096761_51%,#103d68)] pb-11 text-white">
      <div className="absolute inset-0 opacity-[0.14] [background-image:linear-gradient(rgba(255,255,255,.16)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.16)_1px,transparent_1px)] [background-size:44px_44px]" />
      <div className="relative z-10 grid w-24 gap-3 p-3 sm:w-28 sm:gap-4 sm:p-4">
        {REMOTE_DESKTOP_APP_IDS.map((appId) => (
          <DesktopIcon
            appId={appId}
            key={appId}
            onOpen={() => onEvent(remote.openApp(workstation.assetTag, appId))}
          />
        ))}
      </div>
      {visibleApps.map((appId, index) => (
        <DesktopWindow
          appId={appId}
          focused={workstation.focusedApp === appId}
          index={index}
          key={appId}
          onClose={() => onEvent(remote.closeApp(workstation.assetTag, appId))}
          onFocus={() => onEvent(remote.focusApp(workstation.assetTag, appId))}
          onMinimize={() =>
            onEvent(remote.minimizeApp(workstation.assetTag, appId))
          }
        >
          <AppContent
            appId={appId}
            navigateExplorer={(path) =>
              onEvent(remote.navigateExplorer(workstation.assetTag, path))
            }
            reconnectExplorerDrive={(driveLetter) =>
              onEvent(
                remote.reconnectExplorerDrive(
                  workstation.assetTag,
                  driveLetter,
                ),
              )
            }
            refreshExplorer={() =>
              onEvent(remote.refreshExplorer(workstation.assetTag))
            }
            onEvent={onEvent}
            remote={remote}
            runStep={runStep}
            runTerminalCommand={(command) =>
              onEvent(remote.runTerminalCommand(workstation.assetTag, command))
            }
            scenarioComplete={scenarioComplete}
            scenario={scenario}
            workstation={workstation}
          />
        </DesktopWindow>
      ))}
      {startOpen ? (
        <StartMenu
          onOpen={(appId) => {
            onEvent(remote.openApp(workstation.assetTag, appId));
            setStartOpen(false);
          }}
        />
      ) : null}
      <div className="absolute inset-x-0 bottom-0 z-50 flex h-11 items-center border-t border-white/15 bg-[#102735]/95 px-2 shadow-[0_-6px_20px_rgba(2,14,24,.2)] backdrop-blur">
        <button
          aria-expanded={startOpen}
          aria-label="Open Start menu"
          className="flex h-8 w-9 items-center justify-center rounded-sm hover:bg-white/15"
          onClick={() => setStartOpen(!startOpen)}
          type="button"
        >
          <IconBrandWindows aria-hidden="true" className="h-5 w-5" />
        </button>
        {workstation.openApps.map((appId) => {
          const Meta = APP_META[appId];
          return (
            <button
              aria-label={`Focus ${Meta.label}`}
              className={`mx-0.5 flex h-8 w-9 items-center justify-center rounded-sm border-b-2 ${workstation.focusedApp === appId ? 'border-sky-300 bg-white/15' : 'border-transparent hover:bg-white/10'}`}
              key={appId}
              onClick={() =>
                onEvent(remote.focusApp(workstation.assetTag, appId))
              }
              type="button"
            >
              <Meta.Icon
                aria-hidden="true"
                className={`h-4 w-4 ${Meta.tint}`}
              />
            </button>
          );
        })}
        <div className="ml-auto flex items-center gap-3 px-2 text-[11px] tabular-nums text-sky-50/90">
          <IconWifi aria-hidden="true" className="h-4 w-4" />
          <span>10:30</span>
        </div>
      </div>
    </div>
  );
}

function DesktopIcon({
  appId,
  onOpen,
}: {
  appId: RemoteDesktopAppId;
  onOpen: () => void;
}) {
  const Meta = APP_META[appId];
  return (
    <button
      className="flex flex-col items-center gap-1 rounded p-1.5 text-center text-xs font-medium drop-shadow hover:bg-white/15 focus:bg-white/15"
      onClick={onOpen}
      type="button"
    >
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-md bg-zinc-950/25 ${Meta.tint}`}
      >
        <Meta.Icon aria-hidden="true" className="h-7 w-7" />
      </span>
      <span className="leading-tight">{Meta.label}</span>
    </button>
  );
}

function StartMenu({
  onOpen,
}: {
  onOpen: (appId: RemoteDesktopAppId) => void;
}) {
  return (
    <div className="absolute bottom-11 left-1 z-40 w-[min(18rem,calc(100%-0.5rem))] border border-white/15 bg-[#142f41]/95 p-3 shadow-2xl backdrop-blur">
      <p className="px-2 pb-2 text-xs font-bold uppercase tracking-widest text-sky-200">
        Start
      </p>
      <div className="grid grid-cols-2 gap-1">
        {REMOTE_DESKTOP_APP_IDS.map((appId) => {
          const Meta = APP_META[appId];
          return (
            <button
              className="flex items-center gap-2 rounded px-2 py-2 text-left text-xs hover:bg-white/10"
              key={appId}
              onClick={() => onOpen(appId)}
              type="button"
            >
              <Meta.Icon
                aria-hidden="true"
                className={`h-4 w-4 ${Meta.tint}`}
              />
              {Meta.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function DesktopWindow({
  appId,
  children,
  focused,
  index,
  onClose,
  onFocus,
  onMinimize,
}: {
  appId: RemoteDesktopAppId;
  children: ReactNode;
  focused: boolean;
  index: number;
  onClose: () => void;
  onFocus: () => void;
  onMinimize: () => void;
}) {
  const Meta = APP_META[appId];
  const [maximized, setMaximized] = useState(false);
  return (
    <section
      className={`absolute z-20 flex min-h-0 flex-col overflow-hidden border bg-zinc-100 text-zinc-900 shadow-2xl ${maximized ? 'inset-x-2 top-2 bottom-14' : 'inset-x-2 top-14 bottom-14 sm:inset-x-auto sm:left-[12%] sm:top-[12%] sm:bottom-14 sm:w-[min(680px,76%)] sm:translate-x-[var(--window-offset-x)] sm:translate-y-[var(--window-offset-y)]'} ${focused ? 'border-sky-300 ring-2 ring-sky-300/30' : 'border-zinc-500'}`}
      onMouseDown={() => {
        if (!focused) onFocus();
      }}
      style={
        {
          '--window-offset-x': `${index * 8}px`,
          '--window-offset-y': `${index * 8}px`,
          zIndex: focused ? 40 : 20 + index,
        } as CSSProperties
      }
    >
      <header className="flex items-center justify-between border-b border-zinc-300 bg-[#e7edf2] px-3 py-1.5 shadow-[0_1px_0_rgba(255,255,255,.8)_inset]">
        <span className="flex items-center gap-2 text-xs font-semibold">
          <Meta.Icon aria-hidden="true" className={`h-4 w-4 ${Meta.tint}`} />
          {Meta.label}
        </span>
        <span className="flex">
          <button
            aria-label={`Minimize ${Meta.label}`}
            className="rounded-sm p-1 hover:bg-zinc-300"
            onClick={onMinimize}
            type="button"
          >
            <IconMinus aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
          <button
            aria-label={`${maximized ? 'Restore' : 'Maximize'} ${Meta.label}`}
            className="rounded-sm p-1 hover:bg-zinc-300"
            onClick={() => setMaximized((value) => !value)}
            type="button"
          >
            <IconMaximize aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
          <button
            aria-label={`Close ${Meta.label}`}
            className="rounded-sm p-1 hover:bg-red-500 hover:text-white"
            onClick={onClose}
            type="button"
          >
            <IconX aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
        </span>
      </header>
      <div className="min-h-0 flex-1 overflow-auto bg-white">{children}</div>
    </section>
  );
}

function ScenarioAction({
  children,
  performed,
  runStep,
  scenarioComplete,
  stepId,
}: {
  children: ReactNode;
  performed: ReadonlySet<string>;
  runStep: (stepId: string) => void;
  scenarioComplete: boolean;
  stepId: string;
}) {
  const recorded = performed.has(stepId);
  return (
    <button
      className="rounded-sm bg-sky-600 px-3 py-2 text-xs font-bold text-white hover:bg-sky-700 disabled:bg-zinc-300"
      disabled={recorded || scenarioComplete}
      onClick={() => runStep(stepId)}
      type="button"
    >
      {recorded ? 'Recorded' : children}
    </button>
  );
}

function AppContent({
  appId,
  navigateExplorer,
  onEvent,
  reconnectExplorerDrive,
  refreshExplorer,
  remote,
  runStep,
  runTerminalCommand,
  scenario,
  scenarioComplete,
  workstation,
}: {
  appId: RemoteDesktopAppId;
  navigateExplorer: (path: string) => void;
  onEvent: (event: ActionEvent) => void;
  reconnectExplorerDrive: (driveLetter: string) => void;
  refreshExplorer: () => void;
  remote: ReturnType<typeof useRemoteDesktopSession>;
  runStep: (stepId: string) => void;
  runTerminalCommand: (command: string) => void;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  scenarioComplete: boolean;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const performed = new Set(workstation.scenarioSteps[scenario.id] ?? []);
  const action = (stepId: string, children: ReactNode) => (
    <ScenarioAction
      performed={performed}
      runStep={runStep}
      scenarioComplete={scenarioComplete}
      stepId={stepId}
    >
      {children}
    </ScenarioAction>
  );

  switch (appId) {
    case 'vpn':
      return (
        <VpnClientWindow
          connect={() => onEvent(remote.connectVpn(workstation.assetTag))}
          disconnect={() => onEvent(remote.disconnectVpn(workstation.assetTag))}
          finishConnection={() =>
            onEvent(remote.completeVpnConnection(workstation.assetTag))
          }
          workstation={workstation}
        />
      );
    case 'explorer':
      return (
        <FileExplorerWindow
          navigate={navigateExplorer}
          reconnectDrive={reconnectExplorerDrive}
          refresh={refreshExplorer}
          workstation={workstation}
        />
      );
    case 'settings':
      return (
        <SettingsWindow
          canRepairNetwork={Boolean(
            scenario.actionLabels['settings.repair-network'],
          )}
          clearProfileStorage={() => runStep('settings.clear-profile-storage')}
          completeUpdate={() =>
            onEvent(remote.completeUpdateInstall(workstation.assetTag))
          }
          installUpdate={() =>
            onEvent(remote.installUpdate(workstation.assetTag))
          }
          restartAfterUpdate={() =>
            onEvent(remote.restartAfterUpdate(workstation.assetTag))
          }
          repairNetwork={() => runStep('settings.repair-network')}
          networkRepaired={performed.has('settings.repair-network')}
          scenarioComplete={scenarioComplete}
          updateDns={(primaryDns, secondaryDns) =>
            onEvent(
              remote.updateDns(workstation.assetTag, primaryDns, secondaryDns),
            )
          }
          workstation={workstation}
        />
      );
    case 'services':
      return (
        <ServicesWindow
          restartService={(serviceName) =>
            onEvent(remote.restartService(workstation.assetTag, serviceName))
          }
          startService={(serviceName) =>
            onEvent(remote.startService(workstation.assetTag, serviceName))
          }
          stopService={(serviceName) =>
            onEvent(remote.stopService(workstation.assetTag, serviceName))
          }
          workstation={workstation}
        />
      );
    case 'browser':
      return (
        <BrowserWindow
          performed={performed}
          runStep={runStep}
          scenario={scenario}
          scenarioComplete={scenarioComplete}
        />
      );
    case 'updates':
      return (
        <SystemUpdateWindow
          completeUpdate={() =>
            onEvent(remote.completeUpdateInstall(workstation.assetTag))
          }
          installUpdate={() =>
            onEvent(remote.installUpdate(workstation.assetTag))
          }
          restartAfterUpdate={() =>
            onEvent(remote.restartAfterUpdate(workstation.assetTag))
          }
          workstation={workstation}
        />
      );
    case 'system': {
      const serviceProgress = workstation.scenarioProgress[scenario.id];
      const printResult = serviceProgress?.verificationEvidence.includes(
        'printer.test-succeeded',
      )
        ? 'The simulated test page printed successfully.'
        : serviceProgress?.diagnosisEvidence.includes('printer.test-failed')
          ? 'The simulated test page failed because the print queue is unavailable.'
          : null;
      return (
        <div className="p-5">
          <h3 className="text-lg font-bold">System tools</h3>
          <div className="mt-4 flex flex-wrap gap-2">
            {action('system.restart-pdf-helper', 'Restart PDF helper')}
            {action('system.renew-address', 'Renew network address')}
            {action('system.view-network', 'View network diagnostics')}
            {scenario.id === 'service-failure' ? (
              <button
                className="rounded-sm bg-sky-600 px-3 py-2 text-xs font-bold text-white hover:bg-sky-700"
                onClick={() => runStep('printer.test-page')}
                type="button"
              >
                Print simulated test page
              </button>
            ) : null}
          </div>
          {Object.keys(scenario.actionLabels).some((stepId) => stepId.startsWith('scenario.')) ? (
            <section className="mt-6 rounded border border-zinc-200 bg-zinc-50 p-4">
              <h4 className="font-semibold text-zinc-900">Case investigation workspace</h4>
              <p className="mt-1 text-sm text-zinc-600">Record the evidence you establish, then apply the specific safe remediation and retest the original request.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(scenario.actionLabels)
                  .filter(([stepId]) => stepId.startsWith('scenario.'))
                  .map(([stepId, label]) => action(stepId, label))}
              </div>
            </section>
          ) : null}
          {printResult ? (
            <p
              className={`mt-4 rounded border p-3 text-sm ${serviceProgress?.verificationEvidence.includes('printer.test-succeeded') ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-900'}`}
              role="status"
            >
              {printResult}
            </p>
          ) : null}
        </div>
      );
    }
    case 'terminal':
      return (
        <TerminalWindow
          history={workstation.terminalHistory}
          hostname={workstation.hostname}
          onRunCommand={runTerminalCommand}
        />
      );
    case 'chat':
      return (
        <ChatMailWindow
          mode="chat"
          performed={performed}
          runStep={runStep}
          scenario={scenario}
        />
      );
    case 'mail':
      return (
        <ChatMailWindow
          mode="mail"
          performed={performed}
          runStep={runStep}
          scenario={scenario}
        />
      );
    case 'trash':
      return (
        <div className="p-5">
          <h3 className="text-lg font-bold">Recycle Bin</h3>
          <p className="mt-2 text-sm text-zinc-600">
            No repair files are staged here.
          </p>
          <div className="mt-4">
            {action('trash.empty', 'Empty recycle bin')}
          </div>
        </div>
      );
  }
}

function VpnClientWindow({
  connect,
  disconnect,
  finishConnection,
  workstation,
}: {
  connect: () => void;
  disconnect: () => void;
  finishConnection: () => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  useEffect(() => {
    if (workstation.vpnStatus !== 'connecting') return;
    const timer = window.setTimeout(finishConnection, 650);
    return () => window.clearTimeout(timer);
  }, [finishConnection, workstation.vpnStatus]);

  const statusLabel =
    workstation.vpnStatus === 'connected'
      ? 'Connected'
      : workstation.vpnStatus === 'connecting'
        ? 'Connecting'
        : workstation.vpnStatus === 'error'
          ? 'Error'
          : 'Disconnected';

  return (
    <div className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">Nexus Secure VPN</h3>
          <p className="mt-1 text-sm text-zinc-600">
            Gateway: vpn.nexus.internal
          </p>
        </div>
        <Badge
          variant={
            workstation.vpnStatus === 'connected'
              ? 'success'
              : workstation.vpnStatus === 'error'
                ? 'amber'
                : 'amber'
          }
        >
          {statusLabel}
        </Badge>
      </div>

      <div className="mt-5 rounded border border-zinc-200 bg-zinc-50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-zinc-900">
              Company network
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              Secure access to internal services and mapped drives
            </p>
          </div>
          {workstation.vpnStatus === 'connected' ? (
            <Button onClick={disconnect} variant="light">
              Disconnect
            </Button>
          ) : (
            <Button
              disabled={workstation.vpnStatus === 'connecting'}
              onClick={connect}
            >
              {workstation.vpnStatus === 'connecting'
                ? 'Connecting…'
                : workstation.vpnStatus === 'error'
                  ? 'Retry connection'
                  : 'Connect'}
            </Button>
          )}
        </div>
        {workstation.vpnError ? (
          <p
            className="mt-3 rounded border border-red-200 bg-red-50 p-3 text-xs text-red-800"
            role="alert"
          >
            {workstation.vpnError}
          </p>
        ) : null}
      </div>

      <section aria-labelledby="vpn-log-title" className="mt-5">
        <h4
          className="text-xs font-bold uppercase tracking-wider text-zinc-500"
          id="vpn-log-title"
        >
          Connection log
        </h4>
        <div
          aria-live="polite"
          className="mt-2 max-h-40 overflow-y-auto rounded bg-zinc-950 p-3 font-mono text-[11px] leading-5 text-emerald-200"
        >
          {workstation.vpnLog.length ? (
            workstation.vpnLog.map((entry, index) => (
              <p key={`${entry.timestamp}-${index}`}>
                [{new Date(entry.timestamp).toLocaleTimeString()}]{' '}
                {entry.message}
              </p>
            ))
          ) : (
            <p className="text-zinc-500">No connection attempts recorded.</p>
          )}
        </div>
      </section>
    </div>
  );
}

type SettingsTab = 'network' | 'storage' | 'applications' | 'updates';

function SettingsWindow({
  canRepairNetwork,
  clearProfileStorage,
  completeUpdate,
  installUpdate,
  networkRepaired,
  repairNetwork,
  restartAfterUpdate,
  scenarioComplete,
  updateDns,
  workstation,
}: {
  canRepairNetwork: boolean;
  clearProfileStorage: () => void;
  completeUpdate: () => void;
  installUpdate: () => void;
  networkRepaired: boolean;
  repairNetwork: () => void;
  restartAfterUpdate: () => void;
  scenarioComplete: boolean;
  updateDns: (primaryDns: string, secondaryDns: string) => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const [tab, setTab] = useState<SettingsTab>('network');
  const [primaryDns, setPrimaryDns] = useState(workstation.dnsServers[0] ?? '');
  const [secondaryDns, setSecondaryDns] = useState(
    workstation.dnsServers[1] ?? '',
  );
  const tabs: readonly { id: SettingsTab; label: string }[] = [
    { id: 'network', label: 'Network' },
    { id: 'storage', label: 'Storage' },
    { id: 'applications', label: 'Applications' },
    { id: 'updates', label: 'Updates' },
  ];

  useEffect(() => {
    setPrimaryDns(workstation.dnsServers[0] ?? '');
    setSecondaryDns(workstation.dnsServers[1] ?? '');
  }, [workstation.dnsServers]);

  return (
    <div className="min-h-[24rem] sm:grid sm:grid-cols-[9rem_minmax(0,1fr)]">
      <nav
        aria-label="Settings sections"
        className="flex overflow-x-auto border-b border-zinc-200 bg-zinc-50 p-2 sm:flex-col sm:border-b-0 sm:border-r"
      >
        {tabs.map((item) => (
          <button
            aria-current={tab === item.id ? 'page' : undefined}
            className={`whitespace-nowrap rounded px-3 py-2 text-left text-sm font-semibold ${tab === item.id ? 'bg-sky-100 text-sky-900' : 'text-zinc-600 hover:bg-zinc-200'}`}
            key={item.id}
            onClick={() => setTab(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>
      <div className="p-5">
        {tab === 'network' ? (
          <section aria-labelledby="settings-network-title">
            <h3 className="text-lg font-bold" id="settings-network-title">
              Network
            </h3>
            <p className="mt-1 text-sm text-zinc-600">
              Ethernet adapter · {workstation.networkStatus}
            </p>
            {canRepairNetwork ? (
              <Button
                className="mt-4"
                disabled={networkRepaired || scenarioComplete}
                onClick={repairNetwork}
                type="button"
              >
                {networkRepaired
                  ? 'Network profile repaired'
                  : 'Repair network profile'}
              </Button>
            ) : null}
            <form
              className="mt-5 max-w-md space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                updateDns(primaryDns, secondaryDns);
              }}
            >
              <label className="block text-sm font-semibold text-zinc-700">
                Primary DNS server
                <Input
                  className="mt-1 bg-white text-zinc-900"
                  onChange={(event) => setPrimaryDns(event.target.value)}
                  value={primaryDns}
                />
              </label>
              <label className="block text-sm font-semibold text-zinc-700">
                Secondary DNS server
                <Input
                  className="mt-1 bg-white text-zinc-900"
                  onChange={(event) => setSecondaryDns(event.target.value)}
                  value={secondaryDns}
                />
              </label>
              <Button type="submit">Save DNS settings</Button>
            </form>
          </section>
        ) : null}

        {tab === 'storage' ? (
          <section aria-labelledby="settings-storage-title">
            <h3 className="text-lg font-bold" id="settings-storage-title">
              Storage
            </h3>
            <p className="mt-1 text-sm text-zinc-600">
              The same disk figures shown in File Explorer.
            </p>
            <div className="mt-4 space-y-3">
              {workstation.drives.map((drive) => {
                const usedGb = drive.totalGb - drive.freeGb;
                const usedPercent = Math.round((usedGb / drive.totalGb) * 100);
                return (
                  <div
                    className="rounded border border-zinc-200 p-3"
                    key={drive.letter}
                  >
                    <div className="flex justify-between gap-3 text-sm">
                      <span className="font-semibold">
                        {drive.label} ({drive.letter})
                      </span>
                      <span className="text-zinc-500">
                        {drive.freeGb} GB free of {drive.totalGb} GB
                      </span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-200">
                      <span
                        className="block h-full bg-sky-600"
                        style={{ width: `${usedPercent}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ) : null}

        {tab === 'applications' ? (
          <section aria-labelledby="settings-applications-title">
            <h3 className="text-lg font-bold" id="settings-applications-title">
              Installed applications
            </h3>
            <ul className="mt-4 divide-y divide-zinc-200 rounded border border-zinc-200 text-sm">
              {[
                'Nexus Secure VPN 6.4',
                'Northstar Office Suite',
                'Nexus Support Browser',
                'PDF Export Helper 4.4',
              ].map((application) => (
                <li className="px-3 py-2.5" key={application}>
                  {application}
                </li>
              ))}
            </ul>
            <Button
              className="mt-4"
              onClick={clearProfileStorage}
              variant="light"
            >
              Clear support browser profile storage
            </Button>
          </section>
        ) : null}

        {tab === 'updates' ? (
          <UpdateControls
            completeUpdate={completeUpdate}
            installUpdate={installUpdate}
            restartAfterUpdate={restartAfterUpdate}
            workstation={workstation}
          />
        ) : null}
      </div>
    </div>
  );
}

function ServicesWindow({
  restartService,
  startService,
  stopService,
  workstation,
}: {
  restartService: (serviceName: string) => void;
  startService: (serviceName: string) => void;
  stopService: (serviceName: string) => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const [selectedService, setSelectedService] = useState(
    workstation.services[0]?.name ?? '',
  );
  const status = workstation.serviceStates[selectedService] ?? 'stopped';

  return (
    <div className="p-5">
      <h3 className="text-lg font-bold">Services</h3>
      <p className="mt-1 text-sm text-zinc-600">
        Local services on {workstation.hostname}. Terminal commands read this
        same state.
      </p>
      <div className="mt-4 overflow-x-auto rounded border border-zinc-200">
        <table className="w-full min-w-[28rem] text-left text-sm">
          <thead className="bg-zinc-100 text-xs uppercase text-zinc-500">
            <tr>
              <th className="px-3 py-2">Service</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200">
            {workstation.services.map((service) => {
              const serviceStatus =
                workstation.serviceStates[service.name] ?? service.state;
              return (
                <tr
                  className={
                    selectedService === service.name ? 'bg-sky-50' : ''
                  }
                  key={service.name}
                >
                  <td className="p-0">
                    <button
                      className="w-full px-3 py-3 text-left font-medium"
                      onClick={() => setSelectedService(service.name)}
                      type="button"
                    >
                      {service.name}
                    </button>
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={
                        serviceStatus === 'running'
                          ? 'font-semibold text-emerald-700'
                          : 'font-semibold text-red-700'
                      }
                    >
                      {serviceStatus === 'running' ? 'Running' : 'Stopped'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="mr-auto text-sm font-semibold text-zinc-700">
          {selectedService || 'Select a service'}
        </span>
        {status === 'stopped' ? (
          <Button onClick={() => startService(selectedService)}>Start</Button>
        ) : (
          <>
            <Button
              onClick={() => restartService(selectedService)}
              variant="light"
            >
              Restart
            </Button>
            <Button
              className="border-red-700 bg-red-700 text-white hover:bg-red-800"
              onClick={() => stopService(selectedService)}
            >
              Stop
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function UpdateControls({
  completeUpdate,
  installUpdate,
  restartAfterUpdate,
  workstation,
}: {
  completeUpdate: () => void;
  installUpdate: () => void;
  restartAfterUpdate: () => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const updateTitle = workstation.pendingUpdate
    ? `${workstation.pendingUpdate.title} (${workstation.pendingUpdate.id})`
    : 'Windows reliability updates';
  const copy = {
    pending: ['Update available', `${updateTitle} is ready to install.`],
    installing: [
      'Installing',
      'The update package is staged. Complete installation to continue.',
    ],
    'restart-required': [
      'Restart required',
      'Installation is complete, but the update is not applied until restart.',
    ],
    applied: ['Up to date', `${updateTitle} is applied.`],
  } as const;
  const [title, description] = copy[workstation.updateState];

  return (
    <section aria-labelledby="update-status-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold" id="update-status-title">
            Windows Update
          </h3>
          <p className="mt-1 text-sm font-semibold text-zinc-800">{title}</p>
          <p className="mt-1 max-w-md text-sm text-zinc-600">{description}</p>
        </div>
        <Badge
          variant={
            workstation.updateState === 'applied'
              ? 'success'
              : workstation.updateState === 'restart-required'
                ? 'amber'
                : 'amber'
          }
        >
          {workstation.updateState.replace('-', ' ')}
        </Badge>
      </div>
      <div className="mt-5">
        {workstation.updateState === 'pending' ? (
          <Button onClick={installUpdate}>Install</Button>
        ) : workstation.updateState === 'installing' ? (
          <Button onClick={completeUpdate}>Complete installation</Button>
        ) : workstation.updateState === 'restart-required' ? (
          <Button
            className="border-red-700 bg-red-700 text-white hover:bg-red-800"
            onClick={restartAfterUpdate}
          >
            Restart now
          </Button>
        ) : (
          <p className="text-sm text-emerald-700">
            Applied
            {workstation.updateInstalledAt
              ? ` at ${new Date(workstation.updateInstalledAt).toLocaleTimeString()}`
              : ''}
          </p>
        )}
      </div>
    </section>
  );
}

function SystemUpdateWindow({
  completeUpdate,
  installUpdate,
  restartAfterUpdate,
  workstation,
}: {
  completeUpdate: () => void;
  installUpdate: () => void;
  restartAfterUpdate: () => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  return (
    <div className="p-5">
      <UpdateControls
        completeUpdate={completeUpdate}
        installUpdate={installUpdate}
        restartAfterUpdate={restartAfterUpdate}
        workstation={workstation}
      />
    </div>
  );
}

function BrowserWindow({
  performed,
  runStep,
  scenario,
  scenarioComplete,
}: {
  performed: ReadonlySet<string>;
  runStep: (stepId: string) => void;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  scenarioComplete: boolean;
}) {
  const articles = scenario.documentationArticleIds
    .map(getDocumentationArticle)
    .filter((article) => article !== undefined);

  return (
    <div className="p-5">
      <div className="rounded border bg-zinc-50 p-2 font-mono text-xs text-zinc-600">
        nexus.internal/documentation/{scenario.ticketId}
      </div>
      <h3 className="mt-4 text-lg font-bold">Ticket documentation</h3>
      <p className="mt-1 text-sm text-zinc-600">
        Curated internal articles for the active ticket. General web navigation
        is disabled.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {articles.map((article) => (
          <Link
            className="rounded border border-zinc-200 p-3 hover:border-sky-400 hover:bg-sky-50"
            href={`/tools/documentation?article=${article.id}`}
            key={article.id}
            target="_blank"
          >
            <span className="text-xs font-semibold uppercase text-sky-700">
              {article.category}
            </span>
            <span className="mt-1 block text-sm font-bold text-zinc-900">
              {article.title}
            </span>
          </Link>
        ))}
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        {scenario.actionLabels['browser.retry-export'] ? (
          <ScenarioAction
            performed={performed}
            runStep={runStep}
            scenarioComplete={scenarioComplete}
            stepId="browser.retry-export"
          >
            Retry PDF export
          </ScenarioAction>
        ) : null}
        {scenario.actionLabels['browser.retry-sign-in'] ? (
          <ScenarioAction
            performed={performed}
            runStep={runStep}
            scenarioComplete={scenarioComplete}
            stepId="browser.retry-sign-in"
          >
            Retry portal sign-in
          </ScenarioAction>
        ) : null}
      </div>
    </div>
  );
}

function ChatMailWindow({
  mode,
  performed,
  runStep,
  scenario,
}: {
  mode: 'chat' | 'mail';
  performed: ReadonlySet<string>;
  runStep: (stepId: string) => void;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
}) {
  const tickets = useTicketSession();
  const { directoryUsers } = useDirectorySession();
  const chat = useCompanyChatSession();
  const ticket = tickets.getTicket(scenario.ticketId);
  const contact = directoryUsers.find(
    (candidate) => candidate.fullName === ticket?.requester.name,
  );
  const thread = contact ? chat.chatThreads[contact.id] : undefined;
  const [message, setMessage] = useState(
    `Update for ${scenario.ticketId}: I am reviewing the reported issue.`,
  );

  if (mode === 'mail') {
    return (
      <div className="p-5">
        <h3 className="text-lg font-bold">Ticket mail</h3>
        <article className="mt-4 rounded border border-zinc-200 p-4 text-sm">
          <p className="font-semibold">To: {ticket?.requester.email}</p>
          <p className="mt-1 text-zinc-500">
            Subject: {scenario.ticketId} support update
          </p>
          <p className="mt-4 leading-6 text-zinc-700">
            {ticket?.description.issue}
          </p>
        </article>
        <div className="mt-4 flex flex-wrap gap-2">
          {scenario.actionLabels['mail.review-alert'] ? (
            <ScenarioAction
              performed={performed}
              runStep={runStep}
              scenarioComplete={false}
              stepId="mail.review-alert"
            >
              Mark support alert reviewed
            </ScenarioAction>
          ) : null}
          {contact ? (
            <Link
              className="rounded-sm bg-zinc-200 px-3 py-2 text-xs font-bold text-zinc-800 hover:bg-zinc-300"
              href={`/tools/company-chat?contact=${contact.id}`}
              target="_blank"
            >
              Continue in Company Chat
            </Link>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="p-5">
      <h3 className="text-lg font-bold">Company Chat</h3>
      {contact ? (
        <>
          <p className="mt-1 text-sm text-zinc-600">
            Ticket-linked conversation with {contact.fullName}. Messages are
            stored in the real Company Chat thread.
          </p>
          <div className="mt-4 max-h-36 space-y-2 overflow-y-auto rounded bg-zinc-50 p-3 text-sm">
            {thread?.messages.length ? (
              thread.messages.slice(-4).map((entry) => (
                <p
                  className={
                    entry.fromStudent
                      ? 'text-right text-sky-800'
                      : 'text-zinc-700'
                  }
                  key={entry.id}
                >
                  <span className="inline-block rounded bg-white px-2 py-1 shadow-sm">
                    {entry.body}
                  </span>
                </p>
              ))
            ) : (
              <p className="text-zinc-500">No messages yet for this attempt.</p>
            )}
          </div>
          <form
            className="mt-3 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const sent = chat.sendMessage(contact.id, message);
              if (
                sent.success &&
                scenario.actionLabels['chat.confirm-restored']
              ) {
                runStep('chat.confirm-restored');
              }
              if (sent.success) setMessage('');
            }}
          >
            <Input
              className="bg-white text-zinc-900"
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Write a ticket update"
              value={message}
            />
            <Button disabled={!message.trim()} type="submit">
              Send
            </Button>
          </form>
          <Link
            className="mt-3 inline-block text-xs font-semibold text-sky-700 underline"
            href={`/tools/company-chat?contact=${contact.id}`}
            target="_blank"
          >
            Open full Company Chat
          </Link>
        </>
      ) : (
        <div className="mt-4 rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {ticket?.requester.name} is not in the company chat directory. Use the
          ticket-linked Mail app instead.
        </div>
      )}
    </div>
  );
}

function parentExplorerPath(path: string) {
  if (path === 'This PC' || /^[A-Z]:\\$/i.test(path)) return 'This PC';
  const separator = path.lastIndexOf('\\');
  return separator <= 2 ? `${path.slice(0, 2)}\\` : path.slice(0, separator);
}

function driveStatusLabel(status: string) {
  if (status === 'connected') return 'Connected';
  if (status === 'permission-error') return 'Access denied';
  if (status === 'network-path-error') return 'Network path unavailable';
  return 'Disconnected';
}

function FileExplorerWindow({
  navigate,
  reconnectDrive,
  refresh,
  workstation,
}: {
  navigate: (path: string) => void;
  reconnectDrive: (driveLetter: string) => void;
  refresh: () => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const currentDrive = workstation.drives.find(
    (drive) =>
      workstation.explorerCurrentPath !== 'This PC' &&
      workstation.explorerCurrentPath
        .toUpperCase()
        .startsWith(drive.letter.toUpperCase()),
  );
  const entries =
    currentDrive?.entries.filter(
      (entry) =>
        parentExplorerPath(entry.path) === workstation.explorerCurrentPath,
    ) ?? [];

  return (
    <div className="flex h-full min-h-[22rem] flex-col bg-white text-zinc-900">
      <div className="flex items-center gap-2 border-b border-zinc-200 bg-zinc-50 px-2 py-2">
        <button
          aria-label="Go back"
          className="rounded p-1.5 text-zinc-600 hover:bg-zinc-200 disabled:text-zinc-300"
          disabled={workstation.explorerCurrentPath === 'This PC'}
          onClick={() =>
            navigate(parentExplorerPath(workstation.explorerCurrentPath))
          }
          type="button"
        >
          <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
        </button>
        <div
          aria-label="Current File Explorer location"
          className="min-w-0 flex-1 truncate border border-zinc-300 bg-white px-3 py-1.5 text-xs text-zinc-700"
        >
          {workstation.explorerCurrentPath}
        </div>
        <button
          aria-label="Refresh File Explorer"
          className="inline-flex items-center gap-1 rounded px-2 py-1.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-200"
          onClick={refresh}
          type="button"
        >
          <IconRefresh aria-hidden="true" className="h-4 w-4" />
          <span className="max-sm:sr-only">Refresh</span>
        </button>
      </div>

      <div className="flex min-h-0 flex-1">
        <nav
          aria-label="File Explorer navigation"
          className="w-28 shrink-0 overflow-y-auto border-r border-zinc-200 bg-zinc-50 p-2 sm:w-44"
        >
          <button
            className={`flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs font-semibold ${workstation.explorerCurrentPath === 'This PC' ? 'bg-sky-100 text-sky-900' : 'text-zinc-700 hover:bg-zinc-200'}`}
            onClick={() => navigate('This PC')}
            type="button"
          >
            <IconDeviceDesktop
              aria-hidden="true"
              className="h-4 w-4 shrink-0"
            />
            This PC
          </button>
          <p className="px-2 pb-1 pt-4 text-[10px] font-bold uppercase tracking-wider text-zinc-400">
            Drives
          </p>
          {workstation.drives.map((drive) => (
            <button
              className={`flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs ${currentDrive?.letter === drive.letter ? 'bg-sky-100 text-sky-900' : 'text-zinc-700 hover:bg-zinc-200'}`}
              key={drive.letter}
              onClick={() => navigate(drive.rootPath)}
              type="button"
            >
              {drive.kind === 'local' ? (
                <IconDatabase aria-hidden="true" className="h-4 w-4 shrink-0" />
              ) : (
                <IconNetwork aria-hidden="true" className="h-4 w-4 shrink-0" />
              )}
              <span className="truncate">
                {drive.label} ({drive.letter})
              </span>
            </button>
          ))}
        </nav>

        <main className="min-w-0 flex-1 overflow-y-auto p-3 sm:p-5">
          {workstation.explorerError ? (
            <ExplorerErrorState
              driveLetter={currentDrive?.letter ?? null}
              error={workstation.explorerError}
              reconnectDrive={reconnectDrive}
            />
          ) : workstation.explorerCurrentPath === 'This PC' ? (
            <section aria-labelledby="explorer-drives-title">
              <h3
                id="explorer-drives-title"
                className="text-base font-semibold"
              >
                Devices and drives
              </h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {workstation.drives.map((drive) => {
                  const status =
                    workstation.driveStates[drive.letter] ??
                    drive.initialStatus;
                  const usedPercent = Math.round(
                    ((drive.totalGb - drive.freeGb) / drive.totalGb) * 100,
                  );
                  return (
                    <button
                      aria-label={`Open ${drive.label} (${drive.letter})`}
                      className="rounded border border-zinc-200 p-3 text-left hover:border-sky-400 hover:bg-sky-50"
                      key={drive.letter}
                      onClick={() => navigate(drive.rootPath)}
                      type="button"
                    >
                      <div className="flex items-start gap-3">
                        {drive.kind === 'local' ? (
                          <IconDatabase
                            aria-hidden="true"
                            className="h-8 w-8 shrink-0 text-zinc-500"
                          />
                        ) : (
                          <IconNetwork
                            aria-hidden="true"
                            className="h-8 w-8 shrink-0 text-sky-600"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold">
                            {drive.label} ({drive.letter})
                          </p>
                          <p
                            className={`mt-0.5 text-xs ${status === 'connected' ? 'text-zinc-500' : status === 'permission-error' ? 'font-semibold text-red-700' : 'font-semibold text-amber-700'}`}
                          >
                            {driveStatusLabel(status)}
                          </p>
                          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-200">
                            <span
                              className="block h-full bg-sky-600"
                              style={{ width: `${usedPercent}%` }}
                            />
                          </div>
                          <p className="mt-1 text-[11px] text-zinc-500">
                            {drive.freeGb} GB free of {drive.totalGb} GB
                          </p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          ) : (
            <section aria-labelledby="explorer-folder-title">
              <div className="flex flex-wrap items-end justify-between gap-2 border-b border-zinc-200 pb-2">
                <div>
                  <h3
                    id="explorer-folder-title"
                    className="text-base font-semibold"
                  >
                    {currentDrive?.label ?? 'Folder'}
                  </h3>
                  {currentDrive ? (
                    <p className="mt-0.5 text-xs text-zinc-500">
                      {currentDrive.freeGb} GB free of {currentDrive.totalGb} GB
                    </p>
                  ) : null}
                </div>
                {currentDrive?.kind === 'network' ? (
                  <span className="text-xs font-semibold text-emerald-700">
                    Connected
                  </span>
                ) : null}
              </div>
              <div className="mt-2" role="list">
                {entries.map((entry) =>
                  entry.kind === 'folder' ? (
                    <button
                      className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-zinc-100 px-2 py-2.5 text-left text-xs hover:bg-sky-50"
                      key={entry.path}
                      onClick={() => navigate(entry.path)}
                      role="listitem"
                      type="button"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <IconFolder
                          aria-hidden="true"
                          className="h-5 w-5 shrink-0 text-amber-500"
                        />
                        <span className="truncate font-medium">
                          {entry.name}
                        </span>
                      </span>
                      <span className="text-zinc-400">{entry.modifiedAt}</span>
                    </button>
                  ) : (
                    <div
                      className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-zinc-100 px-2 py-2.5 text-xs"
                      key={entry.path}
                      role="listitem"
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <IconFile
                          aria-hidden="true"
                          className="h-5 w-5 shrink-0 text-sky-600"
                        />
                        <span className="truncate">{entry.name}</span>
                      </span>
                      <span className="text-zinc-400">{entry.size}</span>
                    </div>
                  ),
                )}
                {entries.length === 0 ? (
                  <p className="py-8 text-center text-sm text-zinc-500">
                    This folder is empty.
                  </p>
                ) : null}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

function ExplorerErrorState({
  driveLetter,
  error,
  reconnectDrive,
}: {
  driveLetter: string | null;
  error: NonNullable<RemoteDesktopWorkstationRecord['explorerError']>;
  reconnectDrive: (driveLetter: string) => void;
}) {
  const permissionError = error.kind === 'permission-error';
  return (
    <div
      className={`mx-auto mt-5 max-w-md rounded border p-5 ${permissionError ? 'border-red-300 bg-red-50 text-red-950' : 'border-amber-300 bg-amber-50 text-amber-950'}`}
      role="alert"
    >
      <IconAlertTriangle
        aria-hidden="true"
        className={`h-8 w-8 ${permissionError ? 'text-red-600' : 'text-amber-600'}`}
      />
      <h3 className="mt-3 text-base font-bold">
        {permissionError ? 'Access denied' : 'Network path unavailable'}
      </h3>
      <p className="mt-2 text-sm leading-5">{error.message}</p>
      {driveLetter ? (
        <button
          className={`mt-4 rounded px-3 py-2 text-xs font-bold text-white ${permissionError ? 'bg-red-700 hover:bg-red-800' : 'bg-amber-700 hover:bg-amber-800'}`}
          onClick={() => reconnectDrive(driveLetter)}
          type="button"
        >
          Reconnect {driveLetter}
        </button>
      ) : null}
    </div>
  );
}

function TerminalWindow({
  history,
  hostname,
  onRunCommand,
}: {
  history: readonly {
    command: string;
    output: readonly string[];
    timestamp: string;
  }[];
  hostname: string;
  onRunCommand: (command: string) => void;
}) {
  const [command, setCommand] = useState('');
  const [clearedCount, setClearedCount] = useState(0);
  const scrollbackRef = useRef<HTMLDivElement>(null);
  const visibleHistory = history.slice(clearedCount);

  useEffect(() => {
    scrollbackRef.current?.scrollTo({
      top: scrollbackRef.current.scrollHeight,
    });
  }, [visibleHistory.length]);

  const submit = () => {
    const value = command.trim();
    if (!value) return;
    if (value.toLowerCase() === 'cls') {
      setClearedCount(history.length);
    } else {
      onRunCommand(value);
    }
    setCommand('');
  };

  return (
    <div className="flex h-full min-h-[20rem] flex-col bg-[#0d1510] font-mono text-sm text-emerald-100">
      <div
        aria-live="polite"
        className="min-h-0 flex-1 overflow-y-auto p-4 leading-6"
        ref={scrollbackRef}
      >
        <p className="mb-3 text-emerald-300">
          Nexus Terminal — simulated command environment
        </p>
        {visibleHistory.map((entry, index) => (
          <div
            className="mb-3 whitespace-pre-wrap break-words"
            key={`${entry.timestamp}-${index}`}
          >
            <p className="text-emerald-400">
              {hostname}&gt; {entry.command}
            </p>
            {entry.output.map((line, lineIndex) => (
              <p key={`${entry.timestamp}-${lineIndex}`}>{line || '\u00a0'}</p>
            ))}
          </div>
        ))}
      </div>
      <form
        className="flex items-center border-t border-emerald-900 bg-[#101c14] px-4 py-3 text-emerald-300"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <label className="sr-only" htmlFor="terminal-command">
          Terminal command
        </label>
        <span aria-hidden="true">{hostname}&gt;&nbsp;</span>
        <input
          autoComplete="off"
          className="min-w-0 flex-1 bg-transparent text-emerald-100 outline-none placeholder:text-emerald-700"
          id="terminal-command"
          onChange={(event) => setCommand(event.target.value)}
          placeholder="Type help for supported commands"
          spellCheck={false}
          value={command}
        />
      </form>
    </div>
  );
}
