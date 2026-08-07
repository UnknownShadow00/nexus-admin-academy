'use client';

import {
  SERVER_ROOM_CONNECTIONS,
  SERVER_ROOM_NETWORK_LOAD_PERCENT,
  type ServerRoomNodeStatus,
} from '@service-desk/shared';
import type { ActionEvent } from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Modal,
  PanelFrame,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@service-desk/ui';
import {
  IconActivity,
  IconArrowLeft,
  IconFileText,
  IconNetwork,
  IconRefresh,
  IconServer,
  IconWorld,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { AssetActionDialog } from './AssetActionDialog';
import {
  type ServerRoomNodeRecord,
  useServerRoomSession,
} from './TicketSessionProvider';

const STATUS_VARIANTS = {
  degraded: 'amber',
  offline: 'default',
  online: 'success',
} as const;

function StatusBadge({ status }: { status: ServerRoomNodeStatus }) {
  return (
    <Badge variant={STATUS_VARIANTS[status]}>
      <span
        aria-hidden="true"
        className={`mr-1.5 h-2 w-2 rounded-full ${
          status === 'online'
            ? 'bg-emerald-500'
            : status === 'degraded'
              ? 'bg-amber-400'
              : 'bg-red-500'
        }`}
      />
      {status}
    </Badge>
  );
}

function eventMessage(event: ActionEvent) {
  if (!event.success) {
    return event.rejectReason ?? 'The simulation rejected this action.';
  }

  switch (event.type) {
    case 'server_room.restart_device':
      return `${String(event.payload.nodeId)} restarted and is online.`;
    case 'server_room.restart_service':
      return `${String(event.payload.serviceName)} restarted successfully.`;
    case 'server_room.restart_server':
      return `${String(event.payload.nodeId)} restarted and is online.`;
    default:
      return 'Server Room action recorded.';
  }
}

export function ServerRoomTool() {
  const { isHydrated, nodes, restartDevice, restartServer, restartService } =
    useServerRoomSession();
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);
  const devices = nodes.filter((node) => node.kind === 'device');
  const servers = nodes.filter((node) => node.kind === 'server');
  const onlineCount = nodes.filter((node) => node.status === 'online').length;

  return (
    <PanelFrame
      aria-labelledby="server-room-title"
      className="mx-auto w-full max-w-7xl p-0"
      variant="contained"
    >
      <header className="border-b border-zinc-700 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 self-start rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-800 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/"
          >
            <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
            Dashboard
          </Link>
          <Badge variant={onlineCount === nodes.length ? 'success' : 'amber'}>
            {onlineCount}/{nodes.length} nodes up
          </Badge>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconServer aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Infrastructure health
            </p>
            <h1
              className="font-display text-2xl font-bold uppercase text-zinc-100"
              id="server-room-title"
            >
              SERVER ROOM
            </h1>
          </div>
        </div>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <p className="max-w-3xl text-sm leading-relaxed text-zinc-400">
            Inspect deterministic network and server health, review logs, and
            record maintenance actions against this simulation attempt.
          </p>
          <Link
            className="sd-link-button sd-focus-ring shrink-0 rounded-sm text-sm font-bold text-sky-400 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/tools/documentation"
          >
            What is a server room?
          </Link>
        </div>
      </header>

      {lastEvent ? (
        <div
          className={`mx-4 mt-4 rounded-sm border px-4 py-3 text-sm ${
            lastEvent.success
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
              : 'border-amber-400/30 bg-amber-400/10 text-amber-300'
          }`}
          role={lastEvent.success ? 'status' : 'alert'}
        >
          <span className="font-bold">
            {lastEvent.success ? 'Action completed.' : 'Action rejected.'}
          </span>{' '}
          {eventMessage(lastEvent)}
        </div>
      ) : null}

      <Tabs className="px-4 sm:px-5" defaultValue="overview">
        <TabsList aria-label="Server Room views" className="overflow-x-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="topology">Topology</TabsTrigger>
          <TabsTrigger value="devices">Devices</TabsTrigger>
          <TabsTrigger value="servers">Servers</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab
            devices={devices}
            isHydrated={isHydrated}
            servers={servers}
          />
        </TabsContent>
        <TabsContent value="topology">
          <TopologyTab nodes={nodes} />
        </TabsContent>
        <TabsContent value="devices">
          <DeviceList
            devices={devices}
            onRestart={(nodeId) => setLastEvent(restartDevice(nodeId))}
          />
        </TabsContent>
        <TabsContent value="servers">
          <ServerList
            onRestartServer={(nodeId) => setLastEvent(restartServer(nodeId))}
            onRestartService={(nodeId, serviceName) =>
              setLastEvent(restartService(nodeId, serviceName))
            }
            servers={servers}
          />
        </TabsContent>
      </Tabs>
    </PanelFrame>
  );
}

function OverviewTab({
  devices,
  isHydrated,
  servers,
}: {
  devices: readonly ServerRoomNodeRecord[];
  isHydrated: boolean;
  servers: readonly ServerRoomNodeRecord[];
}) {
  const onlineDevices = devices.filter((node) => node.status === 'online');
  const healthyServers = servers.filter((node) => node.status === 'online');
  const isp = devices.find((node) => node.id === 'metro-isp');

  if (!isHydrated) {
    return (
      <Card className="grid animate-pulse gap-4 p-5 sm:grid-cols-2">
        {Array.from({ length: 4 }, (_, index) => (
          <div
            className="h-28 rounded-md bg-zinc-800"
            key={`server-room-skeleton-${index}`}
          />
        ))}
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          icon={<IconWorld aria-hidden="true" className="h-5 w-5" />}
          label="ISP status"
          value="Metro ISP"
        >
          <div className="mt-2 flex items-center justify-between gap-2">
            <StatusBadge status={isp?.status ?? 'offline'} />
            <span className="font-mono text-xs text-zinc-400">
              12ms latency
            </span>
          </div>
        </SummaryCard>
        <SummaryCard
          icon={<IconActivity aria-hidden="true" className="h-5 w-5" />}
          label="Network load"
          value={`${SERVER_ROOM_NETWORK_LOAD_PERCENT}% · All clear`}
        >
          <MetricBar value={SERVER_ROOM_NETWORK_LOAD_PERCENT} />
        </SummaryCard>
        <SummaryCard
          icon={<IconNetwork aria-hidden="true" className="h-5 w-5" />}
          label="Devices"
          value={`${onlineDevices.length} / 8 online`}
        />
        <SummaryCard
          icon={<IconServer aria-hidden="true" className="h-5 w-5" />}
          label="Servers"
          value={`${healthyServers.length} / 5 healthy`}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            meta={`${onlineDevices.length}/8`}
            title="Device status"
          />
          <div className="divide-y divide-zinc-800">
            {devices.map((device) => (
              <NodeSummaryRow key={device.id} node={device} />
            ))}
          </div>
        </Card>
        <Card>
          <CardHeader
            meta={`${healthyServers.length}/5`}
            title="Server status"
          />
          <div className="divide-y divide-zinc-800">
            {servers.map((server) => (
              <NodeSummaryRow key={server.id} node={server} />
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function SummaryCard({
  children,
  icon,
  label,
  value,
}: {
  children?: React.ReactNode;
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 text-sky-400">
        {icon}
        <p className="text-xs font-extrabold uppercase tracking-wide">
          {label}
        </p>
      </div>
      <p className="mt-3 font-display text-lg font-bold uppercase text-zinc-100">
        {value}
      </p>
      {children}
    </Card>
  );
}

function NodeSummaryRow({ node }: { node: ServerRoomNodeRecord }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <div>
        <p className="font-bold text-zinc-100">{node.name}</p>
        <p className="mt-0.5 text-xs uppercase text-zinc-500">
          {node.kind === 'server' ? node.role : node.location}
        </p>
      </div>
      <div className="flex items-center gap-3">
        {node.kind === 'server' ? (
          <span className="hidden font-mono text-xs text-zinc-400 sm:inline">
            CPU {node.cpuPercent}% · MEM {node.memoryPercent}%
          </span>
        ) : null}
        <StatusBadge status={node.status} />
      </div>
    </div>
  );
}

function DeviceList({
  devices,
  onRestart,
}: {
  devices: readonly ServerRoomNodeRecord[];
  onRestart: (nodeId: string) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {devices.map((device) => (
        <Card className="p-4" key={device.id}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-bold text-zinc-100">{device.name}</p>
              <p className="mt-1 text-xs font-semibold uppercase text-zinc-500">
                {device.location}
              </p>
            </div>
            <StatusBadge status={device.status} />
          </div>
          <div className="mt-4 flex justify-end border-t border-zinc-800 pt-4">
            <AssetActionDialog
              confirmLabel="Restart device"
              description={`Restart ${device.name}. The deterministic simulator will return it to online immediately.`}
              onConfirm={() => onRestart(device.id)}
              title={`Restart ${device.name}`}
              trigger={
                <Button variant="soft">
                  <IconRefresh aria-hidden="true" className="h-4 w-4" />
                  Restart device
                </Button>
              }
            />
          </div>
        </Card>
      ))}
    </div>
  );
}

function ServerList({
  onRestartServer,
  onRestartService,
  servers,
}: {
  onRestartServer: (nodeId: string) => void;
  onRestartService: (nodeId: string, serviceName: string) => void;
  servers: readonly ServerRoomNodeRecord[];
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {servers.map((server) =>
        server.kind === 'server' ? (
          <Card key={server.id}>
            <CardHeader
              meta={<StatusBadge status={server.status} />}
              title={<span className="font-mono">{server.name}</span>}
            />
            <div className="p-4">
              <p className="text-sm font-bold text-zinc-200">{server.role}</p>
              <p className="mt-1 text-xs uppercase text-zinc-500">
                {server.location}
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Metric label="CPU" value={server.cpuPercent} />
                <Metric label="Memory" value={server.memoryPercent} />
              </div>
              <div className="mt-4 flex items-center justify-between gap-3 rounded-sm border border-zinc-800 bg-zinc-950/50 p-3">
                <div>
                  <p className="text-xs font-extrabold uppercase text-zinc-500">
                    Service
                  </p>
                  <p className="mt-1 text-sm font-bold text-zinc-200">
                    {server.serviceName}
                  </p>
                </div>
                <Badge
                  variant={
                    server.serviceStates[server.serviceName] === 'running'
                      ? 'success'
                      : 'amber'
                  }
                >
                  {server.serviceStates[server.serviceName] ?? 'stopped'}
                </Badge>
              </div>
              <div className="mt-4 flex flex-wrap justify-end gap-2 border-t border-zinc-800 pt-4">
                <ServerLogsModal server={server} />
                <AssetActionDialog
                  confirmLabel="Restart service"
                  description={`Restart ${server.serviceName} on ${server.name} and return the service to running.`}
                  onConfirm={() =>
                    onRestartService(server.id, server.serviceName)
                  }
                  title={`Restart ${server.serviceName}`}
                  trigger={<Button variant="soft">Restart service</Button>}
                />
                <AssetActionDialog
                  confirmLabel="Restart server"
                  description={`Restart ${server.name}. The deterministic simulator will return the node and its service to online immediately.`}
                  onConfirm={() => onRestartServer(server.id)}
                  title={`Restart ${server.name}`}
                  trigger={
                    <Button>
                      <IconRefresh aria-hidden="true" className="h-4 w-4" />
                      Restart server
                    </Button>
                  }
                />
              </div>
            </div>
          </Card>
        ) : null,
      )}
    </div>
  );
}

function ServerLogsModal({
  server,
}: {
  server: Extract<ServerRoomNodeRecord, { kind: 'server' }>;
}) {
  return (
    <Modal
      description={`Deterministic recent events from ${server.name}. Viewing logs does not change simulation state.`}
      title={`${server.name} logs`}
      trigger={
        <Button variant="ghost">
          <IconFileText aria-hidden="true" className="h-4 w-4" />
          View logs
        </Button>
      }
    >
      <div className="rounded-sm border border-zinc-700 bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-300">
        {server.logs.map((line) => (
          <p className="border-b border-zinc-800 py-2 last:border-0" key={line}>
            {line}
          </p>
        ))}
      </div>
    </Modal>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs font-extrabold uppercase text-zinc-500">
        <span>{label}</span>
        <span className="font-mono text-zinc-300">{value}%</span>
      </div>
      <MetricBar value={value} />
    </div>
  );
}

function MetricBar({ value }: { value: number }) {
  return (
    <div
      aria-label={`${value}%`}
      className="mt-2 h-2 overflow-hidden rounded-sm bg-zinc-800"
      role="meter"
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={value}
    >
      <div className="h-full bg-sky-500" style={{ width: `${value}%` }} />
    </div>
  );
}

function TopologyTab({ nodes }: { nodes: readonly ServerRoomNodeRecord[] }) {
  const byId = useMemo(
    () => new Map(nodes.map((node) => [node.id, node])),
    [nodes],
  );
  const tiers = [
    ['metro-isp'],
    ['main-firewall', 'core-router'],
    [
      'floor-1-switch',
      'floor-2-switch',
      'floor-3-switch',
      'lobby-wifi-ap',
      'cafeteria-wifi-ap',
    ],
    ['dc01', 'dc02', 'fileserv01', 'mailsrv01', 'print01'],
  ] as const;

  return (
    <div className="space-y-4">
      <Card className="overflow-x-auto p-4">
        <div className="min-w-[44rem]">
          {tiers.map((tier, tierIndex) => (
            <div key={tier.join('-')}>
              {tierIndex > 0 ? (
                <div
                  aria-hidden="true"
                  className="mx-auto h-7 w-px bg-sky-400/40"
                />
              ) : null}
              <div
                className={`grid gap-3 ${
                  tier.length === 1
                    ? 'grid-cols-1'
                    : tier.length === 2
                      ? 'grid-cols-2'
                      : 'grid-cols-5'
                }`}
              >
                {tier.map((nodeId) => {
                  const node = byId.get(nodeId);
                  return node ? (
                    <TopologyNode key={node.id} node={node} />
                  ) : null;
                })}
              </div>
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <CardHeader
          meta={`${SERVER_ROOM_CONNECTIONS.length} links`}
          title="Connection map"
        />
        <div className="grid gap-x-6 gap-y-2 p-4 sm:grid-cols-2">
          {SERVER_ROOM_CONNECTIONS.map(([from, to]) => (
            <div
              className="flex items-center gap-2 font-mono text-xs text-zinc-400"
              key={`${from}-${to}`}
            >
              <span>{byId.get(from)?.name}</span>
              <span className="text-sky-400">→</span>
              <span>{byId.get(to)?.name}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function TopologyNode({ node }: { node: ServerRoomNodeRecord }) {
  return (
    <div className="rounded-md border border-zinc-700 bg-zinc-950 p-3 text-center">
      <span
        aria-hidden="true"
        className={`mx-auto block h-3 w-3 rounded-full ${
          node.status === 'online'
            ? 'bg-emerald-500'
            : node.status === 'degraded'
              ? 'bg-amber-400'
              : 'bg-red-500'
        }`}
      />
      <p className="mt-2 text-xs font-bold text-zinc-100">{node.name}</p>
      <p className="mt-1 text-[10px] uppercase text-zinc-500">
        {node.kind === 'server' ? node.role : node.location}
      </p>
    </div>
  );
}
