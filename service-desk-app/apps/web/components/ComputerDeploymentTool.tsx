'use client';

import {
  DEPLOYMENT_BOOT_SOURCES,
  DEPLOYMENT_CABLES,
  DEPLOYMENT_DOMAIN,
  DEPLOYMENT_PORTS,
  type DeploymentBootSource,
  type DeploymentCable,
  type DeploymentPort,
} from '@service-desk/shared';
import type {
  ActionEvent,
  DeploymentRun,
} from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  Input,
  Modal,
  PanelFrame,
  Select,
} from '@service-desk/ui';
import {
  IconArrowLeft,
  IconBolt,
  IconBook2,
  IconCircleCheck,
  IconCloud,
  IconDeviceDesktop,
  IconHelpCircle,
  IconKey,
  IconNetwork,
  IconPower,
  IconServer,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useComputerDeploymentSession } from './TicketSessionProvider';

const STEP_HINTS = [
  'The server image in this lab targets a desktop workstation.',
  'Match connector names to the labels on the rear I/O panel.',
  'Wait until firmware initialization finishes before pressing F12.',
  'The deployment server advertises its task sequence over IPv4 PXE.',
  'Use the deployment-share password from the imaging SOP.',
  'Computer names use SD followed by four digits.',
  'Let the task sequence contact its distribution point and finish.',
  'Reboot only after the automated actions are complete.',
  `Use the imaging technician account on ${DEPLOYMENT_DOMAIN}.`,
] as const;

export function ComputerDeploymentTool() {
  const { isHydrated, run, startDeployment } = useComputerDeploymentSession();
  const [aboutOpen, setAboutOpen] = useState(false);
  const [hintsEnabled, setHintsEnabled] = useState(true);
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);

  if (!run) {
    return (
      <DeploymentFrame aboutOpen={aboutOpen} onAboutOpenChange={setAboutOpen}>
        <div className="p-4 sm:p-6">
          <Link
            className="sd-focus-ring flex items-center justify-between gap-4 rounded-sm border border-sky-400/30 bg-sky-400/10 px-4 py-4 text-sm font-extrabold uppercase text-sky-300 hover:bg-sky-400/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/tools/documentation"
          >
            <span>
              Not sure which setup a PC needs? Check the documentation
            </span>
            <IconBook2 aria-hidden="true" className="h-5 w-5 shrink-0" />
          </Link>

          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            <MethodCard
              copy="Deploy a computer using PXE boot and an imaging server task sequence."
              icon={<IconServer aria-hidden="true" className="h-7 w-7" />}
              title="Server Imaging"
            >
              <Button
                disabled={!isHydrated}
                onClick={() => setLastEvent(startDeployment())}
                variant="primary"
              >
                Start
              </Button>
            </MethodCard>
            <MethodCard
              copy="Configure a workstation by hand and join it to the corporate directory."
              icon={
                <IconDeviceDesktop aria-hidden="true" className="h-7 w-7" />
              }
              title="Manual Domain Enrollment"
            >
              <Badge variant="default">Under development</Badge>
            </MethodCard>
            <MethodCard
              copy="Provision a device through cloud enrollment during first-time setup."
              icon={<IconCloud aria-hidden="true" className="h-7 w-7" />}
              title="Cloud Provisioning"
            >
              <Badge variant="default">Under development</Badge>
            </MethodCard>
          </div>

          <HintsToggle enabled={hintsEnabled} onChange={setHintsEnabled} />
          {lastEvent && !lastEvent.success ? (
            <RejectedAction event={lastEvent} />
          ) : null}
        </div>
      </DeploymentFrame>
    );
  }

  return (
    <DeploymentFrame aboutOpen={aboutOpen} onAboutOpenChange={setAboutOpen}>
      <div className="p-4 sm:p-6">
        <div className="flex flex-col gap-3 border-b border-zinc-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Server Imaging · Step {run.currentStepIndex + 1} of 11
            </p>
            <h2 className="mt-1 text-xl font-bold text-zinc-100">
              {run.steps[run.currentStepIndex]?.title}
            </h2>
          </div>
          <Badge variant={run.completedAt ? 'success' : 'sky'}>
            {run.completedAt ? 'Complete' : 'In progress'}
          </Badge>
        </div>

        <div className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-800">
          <div
            className="h-full rounded-full bg-sky-500 transition-all"
            style={{ width: `${((run.currentStepIndex + 1) / 11) * 100}%` }}
          />
        </div>

        {lastEvent && !lastEvent.success ? (
          <RejectedAction event={lastEvent} />
        ) : null}
        {hintsEnabled && !run.completedAt ? (
          <div className="mt-4 rounded-sm border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
            <span className="font-extrabold uppercase">Hint:</span>{' '}
            {STEP_HINTS[run.currentStepIndex] ??
              'Review the imaging SOP before continuing.'}
          </div>
        ) : null}

        <DeploymentStepView run={run} onEvent={setLastEvent} />
        {!run.completedAt ? (
          <HintsToggle enabled={hintsEnabled} onChange={setHintsEnabled} />
        ) : null}
      </div>
    </DeploymentFrame>
  );
}

function DeploymentFrame({
  aboutOpen,
  children,
  onAboutOpenChange,
}: {
  aboutOpen: boolean;
  children: React.ReactNode;
  onAboutOpenChange: (open: boolean) => void;
}) {
  return (
    <PanelFrame
      aria-labelledby="computer-deployment-title"
      className="mx-auto w-full max-w-6xl p-0"
      variant="contained"
    >
      <header className="border-b border-zinc-700 px-4 py-4 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          <Link
            className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/"
          >
            <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
            Dashboard
          </Link>
          <Modal
            description="Practice the workstation imaging sequence from hardware setup through domain verification."
            onOpenChange={onAboutOpenChange}
            open={aboutOpen}
            title="About this tool"
            trigger={
              <Button variant="ghost">
                <IconHelpCircle aria-hidden="true" className="h-5 w-5" />
                About this tool
              </Button>
            }
          >
            <p className="text-sm leading-relaxed text-zinc-300">
              Computer Deployment records every accepted and rejected action in
              the current attempt. A completed image creates a real PC Shelf
              device that can be shipped in the next tool.
            </p>
          </Modal>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconBolt aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Endpoint staging
            </p>
            <h1
              className="font-display text-2xl font-bold uppercase text-zinc-100"
              id="computer-deployment-title"
            >
              Computer Deployment
            </h1>
          </div>
        </div>
      </header>
      {children}
    </PanelFrame>
  );
}

function MethodCard({
  children,
  copy,
  icon,
  title,
}: {
  children: React.ReactNode;
  copy: string;
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <Card className="flex min-h-64 flex-col p-5">
      <span className="text-sky-400">{icon}</span>
      <h2 className="mt-4 text-lg font-bold text-zinc-100">{title}</h2>
      <p className="mt-2 flex-1 text-sm font-semibold uppercase leading-relaxed text-zinc-400">
        {copy}
      </p>
      <div className="mt-5">{children}</div>
    </Card>
  );
}

function HintsToggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
}) {
  return (
    <div className="mt-5 flex flex-col gap-3 rounded-sm border border-zinc-800 bg-zinc-950/40 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-xs font-extrabold uppercase tracking-widest text-zinc-200">
          Hints
        </p>
        <p className="mt-1 text-sm text-zinc-400">
          We recommend disabling hints and using the SOP for the best learning
          experience.
        </p>
      </div>
      <label className="inline-flex items-center gap-2 text-sm font-bold text-zinc-200">
        <input
          checked={enabled}
          className="h-4 w-4 accent-sky-500"
          onChange={(event) => onChange(event.target.checked)}
          type="checkbox"
        />
        {enabled ? 'On' : 'Off'}
      </label>
    </div>
  );
}

function RejectedAction({ event }: { event: ActionEvent }) {
  return (
    <div
      className="mt-4 rounded-sm border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200"
      role="alert"
    >
      <span className="font-extrabold uppercase">Action rejected.</span>{' '}
      {event.rejectReason ?? 'Review the current step and try again.'}
    </div>
  );
}

function DeploymentStepView({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  switch (run.currentStepIndex) {
    case 0:
      return <DeviceTypeStep onEvent={onEvent} run={run} />;
    case 1:
      return <CableStep onEvent={onEvent} run={run} />;
    case 2:
      return <PostStep onEvent={onEvent} run={run} />;
    case 3:
      return <BootSourceStep onEvent={onEvent} run={run} />;
    case 4:
      return <ShareAuthenticationStep onEvent={onEvent} run={run} />;
    case 5:
      return <HostnameStep onEvent={onEvent} run={run} />;
    case 6:
      return <TaskSequenceStep onEvent={onEvent} run={run} />;
    case 7:
      return <RebootStep onEvent={onEvent} run={run} />;
    case 8:
      return <DomainLoginStep onEvent={onEvent} run={run} />;
    default:
      return <DeploymentSuccess run={run} />;
  }
}

function DeviceTypeStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { selectDeviceType } = useComputerDeploymentSession();
  const [deviceType, setDeviceType] = useState('Desktop');
  return (
    <Card className="mt-5 p-5">
      <label className="text-xs font-extrabold uppercase text-zinc-400">
        Deployment profile
        <Select
          className="mt-2"
          onChange={(event) => setDeviceType(event.target.value)}
          value={deviceType}
        >
          <option>Desktop</option>
          <option>Laptop</option>
        </Select>
      </label>
      <Button
        className="mt-4"
        onClick={() => onEvent(selectDeviceType(run.id, deviceType))}
        variant="primary"
      >
        Confirm Desktop Deployment
      </Button>
    </Card>
  );
}

function CableStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { connectCable } = useComputerDeploymentSession();
  const [ports, setPorts] = useState<
    Partial<Record<DeploymentCable, DeploymentPort>>
  >({});
  return (
    <Card className="mt-5 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-bold text-zinc-100">Rear I/O panel</h3>
        <Badge variant={run.connectedCables.length === 5 ? 'success' : 'amber'}>
          {run.connectedCables.length}/5
        </Badge>
      </div>
      <div className="grid gap-3">
        {DEPLOYMENT_CABLES.map((cable) => {
          const connected = run.connectedCables.includes(cable);
          return (
            <div
              className="grid gap-2 rounded-sm border border-zinc-800 p-3 sm:grid-cols-[1fr_1.2fr_auto] sm:items-center"
              key={cable}
            >
              <span className="font-mono text-sm font-bold text-zinc-200">
                {cable}
              </span>
              <Select
                aria-label={`Port for ${cable}`}
                disabled={connected}
                onChange={(event) =>
                  setPorts((current) => ({
                    ...current,
                    [cable]: event.target.value as DeploymentPort,
                  }))
                }
                value={ports[cable] ?? ''}
              >
                <option value="">Select a port</option>
                {DEPLOYMENT_PORTS.map((port) => (
                  <option key={port}>{port}</option>
                ))}
              </Select>
              <Button
                disabled={connected || !ports[cable]}
                onClick={() =>
                  onEvent(connectCable(run.id, cable, ports[cable]!))
                }
                variant={connected ? 'soft' : 'default'}
              >
                {connected ? 'Connected' : 'Connect'}
              </Button>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function PostStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { pressF12 } = useComputerDeploymentSession();
  const startedAt = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(
      () => setElapsed(Date.now() - startedAt.current),
      100,
    );
    return () => window.clearInterval(timer);
  }, []);

  const press = useCallback(() => {
    const milliseconds = Date.now() - startedAt.current;
    const timing =
      milliseconds < 900 ? 'early' : milliseconds <= 4400 ? 'window' : 'late';
    const event = pressF12(run.id, timing);
    onEvent(event);
    if (timing === 'late') {
      startedAt.current = Date.now();
      setElapsed(0);
    }
  }, [onEvent, pressF12, run.id]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'F12') {
        event.preventDefault();
        press();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [press]);

  const promptVisible = elapsed >= 900 && elapsed <= 4400;
  return (
    <Card className="mt-5 overflow-hidden border-zinc-700 bg-black p-0">
      <div className="min-h-64 p-6 font-mono text-sm text-emerald-300">
        <p>NEXUS UEFI WORKSTATION FIRMWARE</p>
        <p className="mt-4 text-zinc-500">Initializing hardware…</p>
        <p className="mt-2">Memory check: OK</p>
        <p>Network adapter: detected</p>
        {promptVisible ? (
          <p className="mt-8 animate-pulse text-amber-300">
            Press F12 for the Boot Option Menu
          </p>
        ) : elapsed > 4400 ? (
          <p className="mt-8 text-zinc-500">Booting internal drive…</p>
        ) : null}
      </div>
      <div className="flex justify-end border-t border-zinc-800 p-4">
        <Button onClick={press} variant="primary">
          <IconKey aria-hidden="true" className="h-4 w-4" />
          Press F12
        </Button>
      </div>
    </Card>
  );
}

function BootSourceStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { selectBootSource } = useComputerDeploymentSession();
  return (
    <Card className="mt-5 p-5">
      <p className="font-mono text-xs font-bold uppercase text-emerald-300">
        Boot Option Menu
      </p>
      <div className="mt-4 grid gap-2">
        {DEPLOYMENT_BOOT_SOURCES.map((source) => (
          <Button
            className="justify-start text-left normal-case"
            key={source}
            onClick={() =>
              onEvent(selectBootSource(run.id, source as DeploymentBootSource))
            }
          >
            <IconNetwork aria-hidden="true" className="h-4 w-4" />
            {source}
          </Button>
        ))}
      </div>
    </Card>
  );
}

function ShareAuthenticationStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { authenticateShare } = useComputerDeploymentSession();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  return (
    <Modal
      description="Authenticate before the Task Sequence Wizard can read deployment content."
      onOpenChange={() => undefined}
      open
      title="Task Sequence Wizard"
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const actionEvent = authenticateShare(run.id, password);
          setError(actionEvent.rejectReason ?? '');
          onEvent(actionEvent);
        }}
      >
        <label className="text-xs font-extrabold uppercase text-zinc-400">
          Deployment share password
          <Input
            autoFocus
            className="mt-2"
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            value={password}
          />
        </label>
        {error ? (
          <p className="mt-3 text-sm font-semibold text-red-300" role="alert">
            Action rejected. {error}
          </p>
        ) : null}
        <Button className="mt-4 w-full" type="submit" variant="primary">
          Authenticate
        </Button>
      </form>
    </Modal>
  );
}

function HostnameStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { setHostname } = useComputerDeploymentSession();
  const [hostname, setComputerName] = useState('');
  const [error, setError] = useState('');
  return (
    <Modal
      description="Variable: OSDCOMPUTERNAME"
      onOpenChange={() => undefined}
      open
      title="Edit Task Sequence Variable"
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const actionEvent = setHostname(run.id, hostname);
          setError(actionEvent.rejectReason ?? '');
          onEvent(actionEvent);
        }}
      >
        <label className="text-xs font-extrabold uppercase text-zinc-400">
          Computer name
          <Input
            autoFocus
            className="mt-2 font-mono uppercase"
            maxLength={6}
            onChange={(event) => setComputerName(event.target.value)}
            placeholder="SD1042"
            value={hostname}
          />
        </label>
        <p className="mt-2 text-xs text-zinc-400">
          Use the corporate naming convention, e.g. SD1042, SD1108, SD1205
        </p>
        {error ? (
          <p className="mt-3 text-sm font-semibold text-red-300" role="alert">
            Action rejected. {error}
          </p>
        ) : null}
        <Button className="mt-4 w-full" type="submit" variant="primary">
          Save OSDCOMPUTERNAME
        </Button>
      </form>
    </Modal>
  );
}

function TaskSequenceStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { runTaskSequence } = useComputerDeploymentSession();
  return (
    <Card className="mt-5 p-6">
      <div className="flex items-center gap-3 text-sky-300">
        <IconServer aria-hidden="true" className="h-7 w-7 animate-pulse" />
        <div>
          <p className="font-bold text-zinc-100">Running: Task Sequence</p>
          <p className="text-sm">
            Running action: Contacting distribution point
          </p>
        </div>
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-zinc-800">
        <div className="h-full w-2/3 animate-pulse rounded-full bg-sky-500" />
      </div>
      <Button
        className="mt-5"
        onClick={() => onEvent(runTaskSequence(run.id))}
        variant="primary"
      >
        Complete task sequence
      </Button>
    </Card>
  );
}

function RebootStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { reboot } = useComputerDeploymentSession();
  return (
    <Card className="mt-5 flex min-h-64 flex-col items-center justify-center p-6 text-center">
      <IconPower aria-hidden="true" className="h-12 w-12 text-sky-400" />
      <h3 className="mt-4 text-lg font-bold text-zinc-100">
        Ready to boot the deployed OS
      </h3>
      <p className="mt-2 text-sm text-zinc-400">
        The task sequence has staged Windows and its domain configuration.
      </p>
      <Button
        className="mt-5"
        onClick={() => onEvent(reboot(run.id))}
        variant="primary"
      >
        Reboot workstation
      </Button>
    </Card>
  );
}

function DomainLoginStep({
  onEvent,
  run,
}: {
  onEvent: (event: ActionEvent) => void;
  run: DeploymentRun;
}) {
  const { domainLogin } = useComputerDeploymentSession();
  const [domain, setDomain] = useState(DEPLOYMENT_DOMAIN);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  return (
    <Card className="mx-auto mt-5 max-w-xl p-6">
      <div className="text-center">
        <IconDeviceDesktop
          aria-hidden="true"
          className="mx-auto h-10 w-10 text-sky-400"
        />
        <h3 className="mt-3 text-lg font-bold text-zinc-100">Domain login</h3>
      </div>
      <form
        className="mt-5 grid gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          onEvent(domainLogin(run.id, domain, username, password));
        }}
      >
        <Field label="Domain">
          <Input
            onChange={(event) => setDomain(event.target.value)}
            value={domain}
          />
        </Field>
        <Field label="Username">
          <Input
            onChange={(event) => setUsername(event.target.value)}
            value={username}
          />
        </Field>
        <Field label="Password">
          <Input
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            value={password}
          />
        </Field>
        <Button type="submit" variant="primary">
          Sign in and verify
        </Button>
      </form>
    </Card>
  );
}

function DeploymentSuccess({ run }: { run: DeploymentRun }) {
  const { startDeployment } = useComputerDeploymentSession();
  return (
    <Card className="mt-5 flex min-h-80 flex-col items-center justify-center p-6 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-300">
        <IconCircleCheck aria-hidden="true" className="h-9 w-9" />
      </span>
      <h2 className="mt-4 text-2xl font-bold text-zinc-100">
        Deployment Successful
      </h2>
      <p className="mt-2 font-mono text-sm text-zinc-300">
        {run.hostname} · Server Imaging · Desktop
      </p>
      <p className="mt-2 max-w-lg text-sm text-zinc-400">
        The provisioned computer is on the PC Shelf and ready for assignment or
        shipping.
      </p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Link
          className="sd-button sd-focus-ring inline-flex min-h-10 items-center justify-center rounded-sm border border-sky-500 bg-sky-600 px-4 py-2 text-sm font-extrabold uppercase text-white hover:bg-sky-500"
          href={`/tools/shipping-manager?computer=${run.hostname ?? ''}`}
        >
          Ship it from Ship Manager
        </Link>
        <Link
          className="sd-button sd-focus-ring inline-flex min-h-10 items-center justify-center rounded-sm border border-zinc-700 bg-zinc-900 px-4 py-2 text-sm font-extrabold uppercase text-zinc-200 hover:bg-zinc-800"
          href="/tools/pc-shelf"
        >
          Go to PC Shelf
        </Link>
      </div>
      <Button className="mt-4" onClick={startDeployment} variant="ghost">
        Deploy another computer
      </Button>
    </Card>
  );
}

function Field({
  children,
  label,
}: {
  children: React.ReactNode;
  label: string;
}) {
  return (
    <label className="text-xs font-extrabold uppercase text-zinc-400">
      {label}
      <div className="mt-2">{children}</div>
    </label>
  );
}
