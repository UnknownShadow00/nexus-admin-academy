'use client';

import type { ActionEvent } from '@service-desk/simulation-engine';
import { Badge, Button, Card, CardHeader, PanelFrame } from '@service-desk/ui';
import { IconArrowLeft, IconDeviceLaptop } from '@tabler/icons-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { useDeviceManagementSession } from './TicketSessionProvider';

interface EndpointScenario {
  assetTag: string;
  deviceId: string;
  deviceName: string;
  diagnosis: string;
  remediationLabel: string;
  verificationCheck: string;
}

const ENDPOINT_SCENARIOS: Readonly<Record<string, EndpointScenario>> = {
  INC3001: {
    assetTag: 'NX-2214',
    deviceId: 'device-nex-lt-2214',
    deviceName: 'NEX-LT-2214',
    diagnosis: 'firmware-update-triggered-recovery',
    remediationLabel: 'Reveal recovery key through approved channel',
    verificationCheck: 'boot-unlocked',
  },
  INC3002: {
    assetTag: 'NX-3390',
    deviceId: 'device-nex-lt-3390',
    deviceName: 'NEX-LT-3390',
    diagnosis: 'offboarding-authorized-access-revoked-data-reset-required',
    remediationLabel: 'Reset and reassign device',
    verificationCheck: 'ready-for-new-assignee',
  },
};

function actionMessage(event: ActionEvent) {
  if (!event.success)
    return event.rejectReason ?? 'The device action was rejected.';
  if (event.type === 'device.inspect_record')
    return 'Managed device record inspected.';
  if (event.type === 'device.record_diagnosis')
    return 'Endpoint diagnosis recorded.';
  if (event.type === 'device.verify_access')
    return 'Post-action device state verified.';
  if (event.type === 'device.reveal_recovery_key')
    return 'Recovery-key release recorded for server verification.';
  if (event.type === 'device.reassign_device')
    return 'Reset-and-reassignment action recorded for server verification.';
  return 'Device action recorded.';
}

export function DeviceManagementTool() {
  const searchParams = useSearchParams();
  const requestedTicket = searchParams.get('ticket')?.toUpperCase() ?? '';
  const ticketId = ENDPOINT_SCENARIOS[requestedTicket]
    ? requestedTicket
    : 'INC3001';
  const scenario = ENDPOINT_SCENARIOS[ticketId]!;
  const {
    inspectRecord,
    recordDiagnosis,
    reassignDevice,
    revealRecoveryKey,
    verifyAccess,
  } = useDeviceManagementSession();
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);

  function remediate() {
    setLastEvent(
      ticketId === 'INC3001'
        ? revealRecoveryKey(ticketId, scenario.deviceId)
        : reassignDevice(ticketId, scenario.deviceId),
    );
  }

  return (
    <PanelFrame
      aria-labelledby="device-management-title"
      className="mx-auto w-full max-w-5xl p-0"
      variant="ad"
    >
      <header className="border-b border-zinc-800 px-4 py-4 sm:px-5">
        <Link
          className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-900 hover:text-sky-300"
          href={`/tickets/${ticketId}`}
        >
          <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
          Back to {ticketId}
        </Link>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconDeviceLaptop aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Managed endpoint evidence
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="device-management-title"
            >
              Device Management
            </h1>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-400">
          This focused training surface supports the two endpoint cases only.
          Identity and authorization checks still happen through Company Chat.
        </p>
      </header>

      {lastEvent ? (
        <div
          className={`mx-4 mt-4 rounded-sm border px-4 py-3 text-sm ${lastEvent.success ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-amber-400/30 bg-amber-400/10 text-amber-300'}`}
          role={lastEvent.success ? 'status' : 'alert'}
        >
          {actionMessage(lastEvent)}
        </div>
      ) : null}

      <div className="grid gap-4 p-4 sm:p-5">
        <Card>
          <CardHeader meta={ticketId} title={scenario.deviceName} />
          <dl className="grid gap-3 p-4 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs font-bold uppercase text-zinc-500">
                Asset tag
              </dt>
              <dd className="mt-1 text-zinc-100">{scenario.assetTag}</dd>
            </div>
            <div>
              <dt className="text-xs font-bold uppercase text-zinc-500">
                Platform
              </dt>
              <dd className="mt-1 text-zinc-100">Windows 11 Enterprise</dd>
            </div>
            <div>
              <dt className="text-xs font-bold uppercase text-zinc-500">
                Management
              </dt>
              <dd className="mt-1">
                <Badge variant="sky">Intune managed</Badge>
              </dd>
            </div>
          </dl>
        </Card>

        <Card>
          <CardHeader
            meta="Investigate → diagnose → remediate → verify"
            title="Authorized endpoint workflow"
          />
          <div className="grid gap-3 p-4 sm:grid-cols-2">
            <Button
              onClick={() =>
                setLastEvent(inspectRecord(ticketId, scenario.deviceId))
              }
              variant="soft"
            >
              1. Inspect device record
            </Button>
            <Link
              className="sd-button sd-button--light sd-focus-ring inline-flex min-h-10 items-center justify-center rounded-sm border border-zinc-300 bg-zinc-100 px-4 py-2 text-sm font-extrabold uppercase text-zinc-900"
              href={`/tools/company-chat?contact=${ticketId === 'INC3001' ? 'directory-user-morgan-ellis' : 'directory-user-hr-adebayo-coker'}&ticket=${ticketId}`}
            >
              2. Verify requester / authorization
            </Link>
            <Button
              onClick={() =>
                setLastEvent(
                  recordDiagnosis(
                    ticketId,
                    scenario.deviceId,
                    scenario.diagnosis,
                  ),
                )
              }
              variant="soft"
            >
              3. Record evidence-based diagnosis
            </Button>
            <Button onClick={remediate} variant="soft">
              4. {scenario.remediationLabel}
            </Button>
            <Button
              onClick={() =>
                setLastEvent(
                  verifyAccess(
                    ticketId,
                    scenario.deviceId,
                    scenario.verificationCheck,
                  ),
                )
              }
              variant="soft"
            >
              5. Verify resulting device state
            </Button>
          </div>
          <p className="px-4 pb-4 text-xs leading-relaxed text-zinc-500">
            The Nexus API enforces this order. A recovery key or destructive
            reassignment attempted before investigation, identity/authorization
            verification, and diagnosis is rejected by server-authoritative
            state.
          </p>
        </Card>
      </div>
    </PanelFrame>
  );
}
