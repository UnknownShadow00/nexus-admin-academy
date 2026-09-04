'use client';

import type {
  ActionEvent,
  RemoteDesktopScenarioProgress,
} from '@service-desk/simulation-engine';
import {
  REMOTE_DESKTOP_APP_IDS,
  REMOTE_DESKTOP_SCENARIOS,
  getRemoteDesktopScenarioByTicket,
  type RemoteDesktopAppId,
} from '@service-desk/shared';
import { Button, Input } from '@service-desk/ui';
import {
  IconBrandWindows,
  IconCheck,
  IconChevronDown,
  IconDeviceDesktop,
  IconKey,
  IconLock,
  IconNetwork,
  IconSearch,
  IconWifi,
  IconX,
} from '@tabler/icons-react';
import React, { useEffect, useMemo, useState } from 'react';

import {
  type RemoteDesktopWorkstationRecord,
  useRemoteDesktopSession,
  useSessionIdentity,
  useTicketSession,
} from './TicketSessionProvider';
import type { NexusGrade } from '../lib/nexus-service-desk-client';
import {
  canInspectScenarioRequirements,
  mentorScenarioRequirements,
  scenarioActionLabel,
  studentFeedbackMessage,
} from '../lib/remote-desktop-learning';
import { WORKSTATION_APP_REGISTRY } from './workstation/app-registry';
import { WorkstationApplicationContent } from './workstation/WorkstationApplications';
import { WindowFrame } from './workstation/WindowFrame';

const TICKET_TOOL_LABELS: Record<string, string> = {
  'asset-management': 'Asset records',
  'company-chat': 'Company Chat',
  directory: 'Directory',
  documentation: 'Knowledge base',
  'remote-desktop': 'Remote Desktop',
  'server-room': 'Server Room',
};

export function ticketFromSearch(search: string): string | null {
  const value = new URLSearchParams(search).get('ticket');
  return value && getRemoteDesktopScenarioByTicket(value) ? value : null;
}

function initialTicketFromUrl(): string | null {
  return typeof window === 'undefined' ? null : ticketFromSearch(window.location.search);
}

function replaceLocation(ticketId: string | null, assetTag: string | null) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  if (ticketId) url.searchParams.set('ticket', ticketId);
  else url.searchParams.delete('ticket');
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
  const scenario = ticketId ? getRemoteDesktopScenarioByTicket(ticketId) : null;
  const ticket = scenario ? tickets.getTicket(scenario.ticketId) : undefined;
  const workstation =
    remote.workstations.find((item) => item.assetTag === computer) ?? null;
  const assignedExperienceMode =
    ticketId ? tickets.assignmentByTicket[ticketId]?.experience_mode : undefined;
  const learningMode =
    assignedExperienceMode ?? workstation?.learningMode ?? 'guided';
  const canReviewScenario = canInspectScenarioRequirements(identity);
  const scenarioComplete =
    scenario ? workstation?.completedScenarioIds.includes(scenario.id) ?? false : false;
  const workflowProgress = scenario ? workstation?.scenarioProgress[scenario.id] : undefined;

  useEffect(() => replaceLocation(ticketId, computer), [computer, ticketId]);
  useEffect(() => {
    const onPopState = () => {
      const params = new URLSearchParams(window.location.search);
      const nextTicketId = params.get('ticket');
      setTicketId(
        nextTicketId && getRemoteDesktopScenarioByTicket(nextTicketId)
          ? nextTicketId
          : null,
      );
      setComputer(params.get('computer'));
    };

    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);
  useEffect(() => {
    if (!scenario || !workstation || workstation.connectionState !== 'connecting') return;
    const timer = window.setTimeout(() => {
      setToast(remote.beginLogin(workstation.assetTag, scenario.ticketId));
    }, 650);
    return () => window.clearTimeout(timer);
  }, [remote, scenario, workstation]);

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
    setToast(event);
  };

  if (!scenario) return <section className="mx-auto max-w-2xl rounded-md border border-border bg-surface-raised p-8 text-center" role="status"><IconDeviceDesktop className="mx-auto h-10 w-10 text-text-muted" aria-hidden="true" /><h1 className="mt-4 text-xl font-bold text-text">Choose a ticket</h1><p className="mt-2 text-sm text-text-muted">Open Remote Desktop from a ticket so the correct customer and computer follow you.</p><a className="sd-button sd-button--default sd-focus-ring mt-5 inline-flex px-4 py-2" href="/">Back to ticket queue</a></section>;

  return (
    <section
      className="mx-auto min-w-0 w-full max-w-[1540px]"
      aria-labelledby="remote-desktop-title"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 px-1">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-[0.16em] text-accent">
            Support simulation
          </p>
          <h1
            id="remote-desktop-title"
            className="font-display text-2xl font-bold text-text"
          >
            {consoleLabel}
          </h1>
        </div>
        {assignedExperienceMode ? (
          <span className="rounded-full border border-border bg-surface/70 px-3 py-1.5 text-xs font-semibold text-accent">
            {assignedExperienceMode[0]?.toUpperCase()}
            {assignedExperienceMode.slice(1)} attempt
          </span>
        ) : canReviewScenario ? (
          <label className="flex items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1.5 text-xs font-semibold text-text">
            <span className="text-accent">Learning mode</span>
            <select
              aria-label="Learning mode"
              className="rounded border border-border bg-surface-raised px-2 py-1 text-text"
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
          className={`min-w-0 overflow-hidden border border-sky-900/30 bg-surface shadow-sm ${ticketOpen ? '' : 'max-xl:hidden'}`}
        >
          <button
            aria-expanded={ticketOpen}
            className="flex w-full items-center justify-between border-b border-sky-900/30 bg-surface-raised px-4 py-3 text-left xl:pointer-events-none"
            onClick={() => setTicketOpen((open) => !open)}
            type="button"
          >
            <span className="font-label text-xs font-extrabold uppercase tracking-[0.14em] text-accent">
              Ticket workspace
            </span>
            <IconChevronDown
              aria-hidden="true"
              className={`h-4 w-4 text-text-muted transition-transform ${ticketOpen ? '' : '-rotate-90'}`}
            />
          </button>
          <div className="space-y-5 p-5 text-text">
            <label className="block">
              <span className="sr-only">Choose a ticket</span>
              <select
                aria-label="Choose a ticket"
                className="w-full rounded-sm border border-border/80 bg-surface-raised px-3 py-2.5 text-sm font-medium text-text"
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
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">
                {ticket?.priority ?? 'High'} priority
              </p>
              <h2 className="mt-2 text-xl font-bold leading-snug text-text">
                {ticket?.title ?? 'Support request'}
              </h2>
              <p className="mt-3 text-sm leading-6 text-text">
                <span className="font-semibold text-text">Requester:</span>{' '}
                {ticket?.requester.name ?? 'Employee'} ·{' '}
                {ticket?.requester.department ?? 'Support'}
              </p>
            </section>

            <section className="space-y-3 border-y border-border/80 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Issue
                </p>
                <p className="mt-1.5 text-sm leading-6 text-text">
                  {ticket?.description.issue ??
                    'Review the reported issue on the affected device.'}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Business impact
                </p>
                <p className="mt-1.5 text-sm leading-6 text-text">
                  {ticket?.description.businessImpact ??
                    'The requester needs service restored.'}
                </p>
              </div>
              <div className="rounded-sm bg-surface-raised/70 px-3 py-2.5 text-sm text-text">
                <span className="font-semibold text-text">
                  Affected device:
                </span>{' '}
                <span className="font-mono text-accent">
                  {ticket?.device.deviceName ?? scenario.assetTag}
                </span>
              </div>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
                Already tried
              </p>
              <ul className="mt-2 space-y-2 text-sm leading-6 text-text">
                {(ticket?.description.troubleshooting ?? []).map((entry) => (
                  <li className="flex gap-2" key={entry}>
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                    {entry}
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
                Available tools
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {learningMode === 'assessment' ? (
                  <span className="text-sm text-text-muted">
                    Choose workstation applications from the ticket evidence.
                  </span>
                ) : (
                  (ticket?.suggestedTools ?? ['remote-desktop']).map((tool) => (
                    <span
                      className="rounded-full bg-accent/10 px-2.5 py-1 text-xs font-medium text-accent"
                      key={tool}
                    >
                      {TICKET_TOOL_LABELS[tool] ?? tool}
                    </span>
                  ))
                )}
              </div>
            </section>

            {workstation?.completedScenarioIds.includes(scenario.id) ? (
              <CompletionSummary
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
                serverGrade={tickets.authoritativeGradeByTicket[scenario.ticketId]}
                workstation={workstation}
              />
            ) : null}

            {canReviewScenario ? (
              <MentorScenarioReview scenario={scenario} />
            ) : null}
          </div>
        </aside>

        {/*
          Everything from here down is the SIMULATED WINDOWS DESKTOP - a
          screen-within-a-screen. It deliberately keeps its own light Windows
          palette in both console themes, exactly like a real remote session
          would. Do not convert these raw utilities to `--sd-*` tokens; the
          console chrome around it is already tokenized.
        */}
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
      className={`mb-3 flex items-start justify-between gap-3 border px-4 py-3 text-sm ${event.success ? 'border-success/30 bg-success/10 text-success' : 'border-warning/35 bg-warning/10 text-warning'}`}
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

export function CompletionSummary({
  onClose,
  progress,
  scenario,
  serverGrade,
  workstation,
}: {
  onClose?: () => void;
  progress: RemoteDesktopScenarioProgress | undefined;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  serverGrade: NexusGrade | undefined;
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
    <section className="rounded-sm border border-success/35 bg-success/[0.08] p-4">
      <IconCheck aria-hidden="true" className="h-7 w-7 text-success" />
      <p className="mt-2 font-display text-xl font-bold text-success">
        {serverGrade
          ? serverGrade.passed
            ? 'Server assessment complete'
            : 'Server assessment incomplete'
          : 'Grade is being confirmed'}
      </p>
      <div className="mt-4 space-y-3 text-sm leading-6 text-emerald-50/90">
        <p>
          <span className="font-semibold text-success">Root cause:</span>{' '}
          {scenario.completion.rootCause}
        </p>
        <p>
          <span className="font-semibold text-success">Fix performed:</span>{' '}
          {scenario.completion.whatFixed}
        </p>
        <p>
          <span className="font-semibold text-success">Why it worked:</span>{' '}
          {scenario.completion.whyItWorked}
        </p>
      </div>
      <div className="mt-4 border-t border-success/20 pt-3 text-sm">
        <p className="font-semibold text-success">Evidence gathered</p>
        <ul className="mt-1.5 space-y-1 text-emerald-50/85">
          {evidence.map((step) => (
            <li key={step}>• {scenarioActionLabel(scenario, step)}</li>
          ))}
        </ul>
        <p className="mt-3 font-semibold text-success">
          Missed useful actions
        </p>
        <p className="mt-1 text-emerald-50/85">
          {missedOptional.length
            ? missedOptional
                .map((step) => scenarioActionLabel(scenario, step))
                .join(', ')
            : 'None.'}
        </p>
        {serverGrade ? (
          <>
            <p className="mt-3 text-emerald-50/85">
              <span className="font-semibold text-success">Final score:</span>{' '}
              {serverGrade.overall_score}/100
            </p>
            <p className="mt-1 text-emerald-50/85">
              <span className="font-semibold text-success">Feedback:</span>{' '}
              {serverGrade.feedback_summary}
            </p>
          </>
        ) : (
          <p className="mt-3 text-emerald-50/85">
            Your ticket work is saved. The final pass/fail and score are still
            processing and will appear after the server confirms this attempt.
          </p>
        )}
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
          <p className="mt-1 text-sm text-text-muted">
            Select a computer to connect
          </p>
        </div>
        <div className="p-4">
          <label className="relative block">
            <IconSearch
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted"
            />
            <Input
              className="border-accent bg-white pl-9 text-zinc-900 shadow-[0_0_0_3px_rgba(56,189,248,.14)]"
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
            <p className="p-6 text-center text-sm text-text-muted">
              Restoring your simulated computers…
            </p>
          ) : (
            filtered.map((item) => {
              const isAffected = item.assetTag === scenario.assetTag;
              return (
                <div
                  className={`flex items-center gap-3 border-b px-3 py-3 ${isAffected ? 'border-accent bg-sky-50' : 'border-sky-100'}`}
                  key={item.assetTag}
                >
                  <IconDeviceDesktop
                    aria-hidden="true"
                    className="h-5 w-5 shrink-0 text-text-muted"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-xs font-semibold text-text-muted">
                      {item.assetTag}
                    </p>
                    <p className="truncate text-sm text-text-muted">
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
            <p className="p-6 text-center text-sm text-text-muted">
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
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const status = workstation.connectionState;
  const sessionHeader = status !== 'disconnected';
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[#f7f8fb]">
      {sessionHeader ? (
        <div className="flex h-7 items-center justify-between border-b border-zinc-300 bg-white px-4 text-xs text-text-muted">
          <span className="truncate">
            <IconDeviceDesktop
              aria-hidden="true"
              className="mr-1 inline h-3.5 w-3.5"
            />
            <span className="font-mono">{workstation.assetTag}</span> ·{' '}
            {workstation.employeeName}
          </span>
          <button
            className="font-semibold uppercase text-text-muted hover:text-red-700"
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
          onCancel={() => {
            onEvent(remote.cancelConnection(workstation.assetTag));
            onBack();
          }}
          onDomain={() => setShowDomain((open) => !open)}
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
        <span className="mx-auto block h-10 w-10 animate-spin rounded-full border-4 border-accent border-t-transparent" />
        <p className="mt-4 font-semibold text-text-muted">
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
  onCancel,
  onDomain,
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
  onCancel: () => void;
  onDomain: () => void;
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
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded bg-sky-700/40 text-accent">
            <IconDeviceDesktop aria-hidden="true" className="h-7 w-7" />
          </span>
          <p className="mt-3 font-bold">{workstation.assetTag}</p>
          <p className="mt-1 text-xs text-accent/65">
            Enter your simulated admin credentials for the remote computer
          </p>
          {error ? (
            <div
              className="mt-3 rounded border border-warning/40 bg-amber-200/10 p-2 text-xs text-warning"
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
              className="min-w-32 border border-accent bg-accent px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:border-white/10 disabled:bg-white/10 disabled:text-white/40"
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
  workstation,
}: {
  onEvent: (event: ActionEvent) => void;
  remote: ReturnType<typeof useRemoteDesktopSession>;
  scenario: (typeof REMOTE_DESKTOP_SCENARIOS)[number];
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const visibleApps = workstation.openApps.filter(
    (appId) => !workstation.minimizedApps.includes(appId),
  );
  const scenarioComplete = workstation.completedScenarioIds.includes(
    scenario.id,
  );
  const startOpen = workstation.workstation.desktop.startMenuOpen;
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
      {visibleApps.map((appId) => {
        const windowState = workstation.workstation.desktop.windows[appId];
        if (!windowState) return null;
        return (
          <WindowFrame
            appId={appId}
            focused={workstation.focusedApp === appId}
            key={appId}
            onClose={() =>
              onEvent(remote.closeApp(workstation.assetTag, appId))
            }
            onFocus={() =>
              onEvent(remote.focusApp(workstation.assetTag, appId))
            }
            onMinimize={() =>
              onEvent(remote.minimizeApp(workstation.assetTag, appId))
            }
            onMove={(bounds) =>
              onEvent(remote.moveWindow(workstation.assetTag, appId, bounds))
            }
            onToggleMaximize={() =>
              onEvent(remote.toggleWindowMaximize(workstation.assetTag, appId))
            }
            windowState={windowState}
          >
            <WorkstationApplicationContent
              appId={appId}
              navigateExplorer={(path) =>
                onEvent(remote.navigateExplorer(workstation.assetTag, path))
              }
              refreshExplorer={() =>
                onEvent(remote.refreshExplorer(workstation.assetTag))
              }
              onEvent={onEvent}
              remote={remote}
              runStep={runStep}
              runTerminalCommand={(command) =>
                onEvent(
                  remote.runTerminalCommand(workstation.assetTag, command),
                )
              }
              scenarioComplete={scenarioComplete}
              scenario={scenario}
              workstation={workstation}
            />
          </WindowFrame>
        );
      })}
      {startOpen ? (
        <StartMenu
          onOpen={(appId) => {
            onEvent(remote.openApp(workstation.assetTag, appId));
            onEvent(remote.setStartMenu(workstation.assetTag, false));
          }}
        />
      ) : null}
      <div className="absolute inset-x-0 bottom-0 z-50 flex h-11 items-center border-t border-white/15 bg-[#102735]/95 px-2 shadow-[0_-6px_20px_rgba(2,14,24,.2)] backdrop-blur">
        <button
          aria-expanded={startOpen}
          aria-label="Open Start menu"
          className="flex h-8 w-9 items-center justify-center rounded-sm hover:bg-white/15"
          onClick={() =>
            onEvent(remote.setStartMenu(workstation.assetTag, !startOpen))
          }
          type="button"
        >
          <IconBrandWindows aria-hidden="true" className="h-5 w-5" />
        </button>
        {workstation.openApps.map((appId) => {
          const Meta = WORKSTATION_APP_REGISTRY[appId];
          return (
            <button
              aria-label={`Focus ${Meta.label}`}
              className={`mx-0.5 flex h-8 w-9 items-center justify-center rounded-sm border-b-2 ${workstation.focusedApp === appId ? 'border-accent bg-white/15' : 'border-transparent hover:bg-white/10'}`}
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
  const Meta = WORKSTATION_APP_REGISTRY[appId];
  return (
    <button
      className="flex flex-col items-center gap-1 rounded p-1.5 text-center text-xs font-medium drop-shadow hover:bg-white/15 focus:bg-white/15"
      onClick={onOpen}
      type="button"
    >
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-md bg-surface/25 ${Meta.tint}`}
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
      <p className="px-2 pb-2 text-xs font-bold uppercase tracking-widest text-accent">
        Start
      </p>
      <div className="grid grid-cols-2 gap-1">
        {REMOTE_DESKTOP_APP_IDS.map((appId) => {
          const Meta = WORKSTATION_APP_REGISTRY[appId];
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
