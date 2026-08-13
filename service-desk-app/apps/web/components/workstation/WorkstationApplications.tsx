'use client';

import type { ActionEvent } from '@service-desk/simulation-engine';
import {
  REMOTE_DESKTOP_SCENARIOS,
  WORKSTATION_COMMAND_RECALL_LIMIT,
  WORKSTATION_TERMINAL_COMMAND_MAX_LENGTH,
  getDocumentationArticle,
  type RemoteDesktopAppId,
} from '@service-desk/shared';
import { Badge, Button, Input } from '@service-desk/ui';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconDatabase,
  IconDeviceDesktop,
  IconFile,
  IconFolder,
  IconNetwork,
  IconRefresh,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useRef, useState, type ReactNode } from 'react';

import {
  type RemoteDesktopWorkstationRecord,
  useCompanyChatSession,
  useDirectorySession,
  useRemoteDesktopSession,
  useTicketSession,
} from '../TicketSessionProvider';
import { CredentialManagerApp } from './apps/CredentialManagerApp';
import { MapNetworkDriveDialog } from './apps/MapNetworkDriveDialog';

function ScenarioAction({
  children,
  performed,
  repeatable = false,
  runStep,
  scenarioComplete,
  stepId,
}: {
  children: ReactNode;
  performed: ReadonlySet<string>;
  repeatable?: boolean;
  runStep: (stepId: string) => void;
  scenarioComplete: boolean;
  stepId: string;
}) {
  const recorded = performed.has(stepId);
  return (
    <button
      className="rounded-sm bg-sky-600 px-3 py-2 text-xs font-bold text-white hover:bg-sky-700 disabled:bg-zinc-300"
      disabled={(recorded && !repeatable) || scenarioComplete}
      onClick={() => runStep(stepId)}
      type="button"
    >
      {recorded && !repeatable ? 'Recorded' : children}
    </button>
  );
}

export function WorkstationApplicationContent({
  appId,
  navigateExplorer,
  onEvent,
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
          mapDrive={(values) =>
            remote.mapDrive(
              workstation.assetTag,
              values.letter,
              values.uncPath,
              values.reconnectAtSignIn,
              values.credentialTarget,
            )
          }
          navigate={navigateExplorer}
          refresh={refreshExplorer}
          workstation={workstation}
        />
      );
    case 'credential-manager':
      return (
        <CredentialManagerApp
          credentials={Object.values(workstation.workstation.credentials)}
          onAdd={(target, username) =>
            remote.addCredential(workstation.assetTag, target, username)
          }
          onDelete={(target) => {
            onEvent(remote.deleteCredential(workstation.assetTag, target));
          }}
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
          {Object.keys(scenario.actionLabels).some((stepId) =>
            stepId.startsWith('scenario.'),
          ) ? (
            <section className="mt-6 rounded border border-zinc-200 bg-zinc-50 p-4">
              <h4 className="font-semibold text-zinc-900">
                Case investigation workspace
              </h4>
              <p className="mt-1 text-sm text-zinc-600">
                Record the evidence you establish, then apply the specific safe
                remediation and retest the original request.
              </p>
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
  const profileId = workstation.workstation.network.vpn.selectedProfileId;
  const profile = profileId
    ? workstation.workstation.network.vpn.profiles[profileId]
    : null;
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
          <h3 className="text-lg font-bold">
            {profile?.name ?? 'VPN profiles'}
          </h3>
          <p className="mt-1 text-sm text-zinc-600">
            Gateway: {profile?.serverAddress ?? 'No profile configured'}
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
              {profile?.name ?? 'Company network'}
            </p>
            <p className="mt-1 text-xs text-zinc-500">
              {profile
                ? `${profile.tunnelType.toUpperCase()} · ${profile.authenticationMethod} · device ${workstation.workstation.machine.compliance}`
                : 'Add an approved VPN profile before connecting.'}
            </p>
          </div>
          {workstation.vpnStatus === 'connected' ? (
            <Button onClick={disconnect} variant="light">
              Disconnect
            </Button>
          ) : (
            <Button
              disabled={!profile || workstation.vpnStatus === 'connecting'}
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

      {profile ? (
        <dl className="mt-4 grid gap-3 rounded border border-zinc-200 p-4 text-xs sm:grid-cols-2">
          <div>
            <dt className="font-semibold text-zinc-500">DNS policy</dt>
            <dd className="mt-1 font-mono text-zinc-800">
              {profile.dnsServers.join(', ')}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-zinc-500">Private routes</dt>
            <dd className="mt-1 font-mono text-zinc-800">
              {profile.routes
                .map((route) => `${route.destination}/${route.prefixLength}`)
                .join(', ')}
            </dd>
          </div>
        </dl>
      ) : null}

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
            repeatable
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
            repeatable
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
  mapDrive,
  navigate,
  refresh,
  workstation,
}: {
  mapDrive: (values: {
    letter: string;
    uncPath: string;
    reconnectAtSignIn: boolean;
    credentialTarget: string | null;
  }) => ActionEvent;
  navigate: (path: string) => void;
  refresh: () => void;
  workstation: RemoteDesktopWorkstationRecord;
}) {
  const [mapDialogFor, setMapDialogFor] = useState<string | null | undefined>(
    undefined,
  );
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
    <div className="relative flex h-full min-h-[22rem] flex-col bg-white text-zinc-900">
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
        <button
          className="inline-flex items-center gap-1 rounded px-2 py-1.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-200"
          onClick={() => setMapDialogFor(null)}
          type="button"
        >
          <IconNetwork aria-hidden="true" className="h-4 w-4" />
          <span className="max-sm:sr-only">Map network drive</span>
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
          className="hidden w-44 shrink-0 overflow-y-auto border-r border-zinc-200 bg-zinc-50 p-2 sm:block"
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
              error={workstation.explorerError}
              openMapDialog={() =>
                setMapDialogFor(currentDrive?.letter ?? null)
              }
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
      {mapDialogFor !== undefined ? (
        <MapNetworkDriveDialog
          credentials={Object.values(workstation.workstation.credentials)}
          currentMapping={
            mapDialogFor
              ? (workstation.workstation.mappedDrives[mapDialogFor] ?? null)
              : null
          }
          onCancel={() => setMapDialogFor(undefined)}
          onMap={mapDrive}
        />
      ) : null}
    </div>
  );
}

function ExplorerErrorState({
  error,
  openMapDialog,
}: {
  error: NonNullable<RemoteDesktopWorkstationRecord['explorerError']>;
  openMapDialog: () => void;
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
      <button
        className={`mt-4 rounded px-3 py-2 text-xs font-bold text-white ${permissionError ? 'bg-red-700 hover:bg-red-800' : 'bg-amber-700 hover:bg-amber-800'}`}
        onClick={openMapDialog}
        type="button"
      >
        Open Map Network Drive
      </button>
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
  const [historyCursor, setHistoryCursor] = useState<number | null>(null);
  const [historyDraft, setHistoryDraft] = useState('');
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
    setHistoryCursor(null);
    setHistoryDraft('');
  };
  const commandHistory = history
    .map((entry) => entry.command)
    .slice(-WORKSTATION_COMMAND_RECALL_LIMIT);

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
          maxLength={WORKSTATION_TERMINAL_COMMAND_MAX_LENGTH}
          onChange={(event) => {
            setCommand(event.target.value);
            setHistoryCursor(null);
          }}
          onKeyDown={(event) => {
            if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return;
            event.preventDefault();
            if (commandHistory.length === 0) return;
            if (event.key === 'ArrowUp') {
              const nextCursor = Math.max(
                0,
                (historyCursor ?? commandHistory.length) - 1,
              );
              if (historyCursor === null) setHistoryDraft(command);
              setHistoryCursor(nextCursor);
              setCommand(commandHistory[nextCursor] ?? '');
              return;
            }
            const nextCursor = (historyCursor ?? commandHistory.length) + 1;
            if (nextCursor >= commandHistory.length) {
              setHistoryCursor(null);
              setCommand(historyDraft);
            } else {
              setHistoryCursor(nextCursor);
              setCommand(commandHistory[nextCursor] ?? '');
            }
          }}
          placeholder="Type help for supported commands"
          spellCheck={false}
          value={command}
        />
      </form>
    </div>
  );
}
