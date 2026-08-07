'use client';

import {
  PcShelfDeviceState,
  PcShelfNetworkStatus,
  type DirectoryUserTemplate,
} from '@service-desk/shared';
import type { ActionEvent } from '@service-desk/simulation-engine';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  Modal,
  PanelFrame,
  Select,
} from '@service-desk/ui';
import {
  IconArrowLeft,
  IconDeviceDesktopPlus,
  IconDevicesPc,
  IconPlus,
  IconTrash,
  IconUserPlus,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { AssetActionDialog } from './AssetActionDialog';
import {
  type PcShelfComputerRecord,
  usePcShelfSession,
} from './TicketSessionProvider';

const NETWORK_VARIANTS = {
  [PcShelfNetworkStatus.Online]: 'success',
  [PcShelfNetworkStatus.Offline]: 'default',
  [PcShelfNetworkStatus.Unregistered]: 'amber',
} as const;

const STATE_VARIANTS = {
  [PcShelfDeviceState.OnShelf]: 'sky',
  [PcShelfDeviceState.Provisioning]: 'amber',
  [PcShelfDeviceState.Assigned]: 'success',
  [PcShelfDeviceState.Retired]: 'default',
} as const;

function eventMessage(event: ActionEvent) {
  if (!event.success) {
    return event.rejectReason ?? 'The simulation rejected this action.';
  }

  switch (event.type) {
    case 'pc_shelf.add':
      return `${String(event.payload.assetTag)} was added to the shelf.`;
    case 'pc_shelf.remove':
      return `${String(event.payload.assetTag)} was removed from the shelf.`;
    case 'pc_shelf.change_network_status':
      return `Network status changed to ${String(event.payload.networkStatus)}.`;
    case 'pc_shelf.change_device_state':
      return `Device state changed to ${String(event.payload.deviceState)}.`;
    case 'pc_shelf.assign':
      return 'Computer assigned and added to the employee’s Asset Management inventory.';
    case 'pc_shelf.unassign':
      return 'Computer returned to the unassigned shelf pool.';
    default:
      return 'PC Shelf action recorded.';
  }
}

export function PcShelfTool() {
  const { addComputer, catalog, computers, directoryUsers, isHydrated } =
    usePcShelfSession();
  const [addOpen, setAddOpen] = useState(false);
  const [assetTagToAdd, setAssetTagToAdd] = useState('');
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);
  const presentTags = useMemo(
    () => new Set(computers.map((computer) => computer.assetTag)),
    [computers],
  );
  const availableComputers = catalog.filter(
    (computer) => !presentTags.has(computer.assetTag),
  );

  useEffect(() => {
    if (
      assetTagToAdd &&
      !availableComputers.some(
        (computer) => computer.assetTag === assetTagToAdd,
      )
    ) {
      setAssetTagToAdd('');
    }
  }, [assetTagToAdd, availableComputers]);

  return (
    <PanelFrame
      aria-labelledby="pc-shelf-title"
      className="mx-auto w-full max-w-6xl p-0"
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
          <Modal
            description="Choose a known fixture-backed computer to place on this attempt’s shelf."
            onOpenChange={setAddOpen}
            open={addOpen}
            title="Add computer"
            trigger={
              <Button
                disabled={!isHydrated || availableComputers.length === 0}
                variant="primary"
              >
                <IconPlus aria-hidden="true" className="h-4 w-4" />
                {availableComputers.length === 0
                  ? 'Catalog fully added'
                  : 'Add computer'}
              </Button>
            }
          >
            <label
              className="text-xs font-extrabold uppercase text-zinc-400"
              htmlFor="pc-shelf-add-computer"
            >
              Available computer
            </label>
            <Select
              className="mt-2"
              id="pc-shelf-add-computer"
              onChange={(event) => setAssetTagToAdd(event.target.value)}
              value={assetTagToAdd}
            >
              <option value="">Select a catalog computer</option>
              {availableComputers.map((computer) => (
                <option key={computer.assetTag} value={computer.assetTag}>
                  {computer.assetTag} · {computer.operatingSystem}
                </option>
              ))}
            </Select>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button onClick={() => setAddOpen(false)}>Cancel</Button>
              <Button
                disabled={!assetTagToAdd}
                onClick={() => {
                  const event = addComputer(assetTagToAdd);
                  setLastEvent(event);
                  if (event.success) {
                    setAssetTagToAdd('');
                    setAddOpen(false);
                  }
                }}
                variant="primary"
              >
                Add to shelf
              </Button>
            </div>
          </Modal>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconDevicesPc aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Provisioned inventory
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="pc-shelf-title"
            >
              PC Shelf
            </h1>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-400">
          Track provisioned computers, network registration, hardware, and
          employee assignment for this simulation attempt.
        </p>
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

      <div className="p-4 sm:p-5">
        {!isHydrated ? (
          <Card
            aria-label="Loading PC Shelf"
            className="grid animate-pulse gap-4 p-5 sm:grid-cols-2"
          >
            {Array.from({ length: 4 }, (_, index) => (
              <div
                className="h-44 rounded-md bg-zinc-800"
                key={`pc-shelf-skeleton-${index}`}
              />
            ))}
          </Card>
        ) : computers.length === 0 ? (
          <Card className="flex min-h-72 flex-col items-center justify-center border-dashed p-8 text-center">
            <IconDeviceDesktopPlus
              aria-hidden="true"
              className="h-12 w-12 text-zinc-600"
            />
            <h2 className="mt-4 text-lg font-bold text-zinc-100">
              Set up a PC to add it to the shelf.
            </h2>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-zinc-400">
              Built computers wait here until you ship one out from the Ship
              Manager.
            </p>
            <Button
              className="mt-5"
              disabled={availableComputers.length === 0}
              onClick={() => setAddOpen(true)}
              variant="primary"
            >
              <IconPlus aria-hidden="true" className="h-4 w-4" />
              Add computer
            </Button>
          </Card>
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
                {computers.length} computers on this attempt
              </p>
              <Badge variant="sky">Refresh-safe shelf</Badge>
            </div>
            <div className="grid gap-4 xl:grid-cols-2">
              {computers.map((computer) => (
                <PcShelfComputerCard
                  computer={computer}
                  directoryUsers={directoryUsers}
                  key={computer.assetTag}
                  onAction={setLastEvent}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </PanelFrame>
  );
}

function PcShelfComputerCard({
  computer,
  directoryUsers,
  onAction,
}: {
  computer: PcShelfComputerRecord;
  directoryUsers: readonly DirectoryUserTemplate[];
  onAction: (event: ActionEvent) => void;
}) {
  const {
    assignComputer,
    changeDeviceState,
    changeNetworkStatus,
    removeComputer,
    unassignComputer,
  } = usePcShelfSession();
  const [employeeId, setEmployeeId] = useState('');
  const owner =
    directoryUsers.find(
      (user) => user.id === computer.assignedDirectoryUserId,
    ) ?? null;

  useEffect(() => {
    setEmployeeId('');
  }, [computer.assetTag, computer.assignedDirectoryUserId]);

  return (
    <Card>
      <CardHeader
        meta={
          <div className="flex gap-2">
            <Badge variant={NETWORK_VARIANTS[computer.networkStatus]}>
              {computer.networkStatus}
            </Badge>
            <Badge variant={STATE_VARIANTS[computer.deviceState]}>
              {computer.deviceState}
            </Badge>
          </div>
        }
        title={<span className="font-mono">{computer.assetTag}</span>}
      />
      <div className="p-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <ShelfField
            label="Operating system"
            value={computer.operatingSystem}
          />
          <ShelfField label="CPU" value={computer.cpu} />
          <ShelfField label="Memory" value={computer.ram} />
          <ShelfField label="Storage" value={computer.storage} />
          <ShelfField
            label="Serial number"
            value={computer.serialNumber}
            mono
          />
          <ShelfField label="Deployment" value={computer.deploymentMethod} />
        </div>

        <div className="mt-4 grid gap-3 border-t border-zinc-800 pt-4 sm:grid-cols-2">
          <label>
            <span className="text-xs font-extrabold uppercase text-zinc-500">
              Network status
            </span>
            <Select
              className="mt-1"
              onChange={(event) =>
                onAction(
                  changeNetworkStatus(
                    computer.assetTag,
                    event.target.value as PcShelfNetworkStatus,
                  ),
                )
              }
              value={computer.networkStatus}
            >
              {Object.values(PcShelfNetworkStatus).map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </Select>
          </label>
          <label>
            <span className="text-xs font-extrabold uppercase text-zinc-500">
              Device state
            </span>
            <Select
              className="mt-1"
              onChange={(event) =>
                onAction(
                  changeDeviceState(
                    computer.assetTag,
                    event.target.value as PcShelfDeviceState,
                  ),
                )
              }
              value={computer.deviceState}
            >
              {computer.deviceState === PcShelfDeviceState.Assigned ? (
                <option value={PcShelfDeviceState.Assigned}>assigned</option>
              ) : null}
              {[
                PcShelfDeviceState.OnShelf,
                PcShelfDeviceState.Provisioning,
                PcShelfDeviceState.Retired,
              ].map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </Select>
          </label>
        </div>

        <div className="mt-4 border-t border-zinc-800 pt-4">
          <p className="text-xs font-extrabold uppercase text-zinc-500">
            Assigned employee
          </p>
          {owner ? (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Link
                className="sd-focus-ring rounded-sm text-sm font-bold text-sky-400 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                href={`/tools/directory?user=${owner.id}`}
              >
                {owner.fullName}
              </Link>
              {owner.disabled ? (
                <Badge variant="amber">Disabled in Directory</Badge>
              ) : null}
              <AssetActionDialog
                confirmLabel="Return to shelf"
                description={`Unassign ${computer.assetTag} from ${owner.fullName} and return it to the on-shelf state.`}
                onConfirm={() => onAction(unassignComputer(computer.assetTag))}
                title="Unassign computer"
                trigger={
                  <Button className="ml-auto" variant="soft">
                    Unassign
                  </Button>
                }
              />
            </div>
          ) : (
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <label
                className="sr-only"
                htmlFor={`shelf-owner-${computer.assetTag}`}
              >
                Employee to assign
              </label>
              <Select
                id={`shelf-owner-${computer.assetTag}`}
                onChange={(event) => setEmployeeId(event.target.value)}
                value={employeeId}
              >
                <option value="">Select an employee</option>
                {directoryUsers.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.fullName} · {user.department}
                  </option>
                ))}
              </Select>
              <AssetActionDialog
                confirmLabel="Assign computer"
                description={`Assign ${computer.assetTag} to ${
                  directoryUsers.find((user) => user.id === employeeId)
                    ?.fullName ?? 'the selected employee'
                } and expose it in that employee’s Asset Management record.`}
                onConfirm={() => {
                  onAction(assignComputer(computer.assetTag, employeeId));
                  setEmployeeId('');
                }}
                title="Assign computer"
                trigger={
                  <Button
                    disabled={
                      !employeeId ||
                      computer.deviceState === PcShelfDeviceState.Retired
                    }
                    variant="primary"
                  >
                    <IconUserPlus aria-hidden="true" className="h-4 w-4" />
                    Assign
                  </Button>
                }
              />
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end border-t border-zinc-800 pt-4">
          <AssetActionDialog
            confirmLabel="Remove computer"
            description={`Remove ${computer.assetTag} from this attempt’s PC Shelf. It can be added again from the fixed catalog.`}
            onConfirm={() => onAction(removeComputer(computer.assetTag))}
            title="Remove computer"
            trigger={
              <Button
                disabled={computer.deviceState === PcShelfDeviceState.Assigned}
              >
                <IconTrash aria-hidden="true" className="h-4 w-4" />
                Remove
              </Button>
            }
          />
        </div>
      </div>
    </Card>
  );
}

function ShelfField({
  label,
  mono = false,
  value,
}: {
  label: string;
  mono?: boolean;
  value: string;
}) {
  return (
    <div>
      <p className="text-xs font-extrabold uppercase text-zinc-500">{label}</p>
      <p className={`mt-1 text-zinc-200 ${mono ? 'font-mono' : ''}`}>{value}</p>
    </div>
  );
}
