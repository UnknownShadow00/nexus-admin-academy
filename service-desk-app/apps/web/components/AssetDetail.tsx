'use client';

import { AssetStatus, type DirectoryUserTemplate } from '@service-desk/shared';
import type { ActionEvent } from '@service-desk/simulation-engine';
import { Badge, Button, Card, CardHeader, Select } from '@service-desk/ui';
import {
  IconDeviceDesktop,
  IconPackageExport,
  IconUserMinus,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { AssetActionDialog } from './AssetActionDialog';
import {
  type AssetInventoryRecord,
  useAssetManagementSession,
} from './TicketSessionProvider';

interface AssetDetailProps {
  asset: AssetInventoryRecord;
  directoryUsers: readonly DirectoryUserTemplate[];
  onAction: (event: ActionEvent) => void;
}

export function AssetDetail({
  asset,
  directoryUsers,
  onAction,
}: AssetDetailProps) {
  const { assignAsset, changeAssetStatus, unassignAsset } =
    useAssetManagementSession();
  const [employeeId, setEmployeeId] = useState('');
  const [nextStatus, setNextStatus] = useState<AssetStatus>(asset.status);
  const owner =
    directoryUsers.find((user) => user.id === asset.assignedDirectoryUserId) ??
    null;

  useEffect(() => {
    setEmployeeId('');
    setNextStatus(asset.status);
  }, [asset.assetTag, asset.status]);

  return (
    <aside aria-labelledby="asset-detail-title" className="space-y-4">
      <Card>
        <CardHeader
          meta={
            asset.source === 'pc-shelf' ? 'PC Shelf' : 'Directory inventory'
          }
          title="Asset details"
        />
        <div className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
                Asset tag
              </p>
              <h2
                className="mt-1 font-mono text-xl font-bold text-zinc-100"
                id="asset-detail-title"
              >
                {asset.assetTag}
              </h2>
            </div>
            <Badge variant="sky">{asset.status}</Badge>
          </div>
          <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
            <DetailField label="Device type" value={asset.deviceType} />
            <DetailField label="Location" value={asset.location} />
            <DetailField
              label="Serial number"
              value={asset.serialNumber}
              mono
            />
            <DetailField
              label="Department"
              value={owner?.department ?? 'Unassigned pool'}
            />
          </dl>
          <div className="mt-5 border-t border-zinc-800 pt-4">
            <p className="text-xs font-extrabold uppercase text-zinc-500">
              Assigned employee
            </p>
            {owner ? (
              <div className="mt-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Link
                    className="sd-focus-ring rounded-sm text-sm font-bold text-sky-400 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                    href={`/tools/directory?user=${owner.id}`}
                  >
                    {owner.fullName}
                  </Link>
                  <span className="font-mono text-xs text-zinc-500">
                    {owner.id}
                  </span>
                  {owner.disabled ? (
                    <Badge variant="amber">Disabled in Directory</Badge>
                  ) : owner.locked ? (
                    <Badge variant="amber">Locked in Directory</Badge>
                  ) : null}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {owner.groups.map((group) => (
                    <Badge key={group} variant="sky">
                      {group}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="mt-2 text-sm text-zinc-400">
                This asset is ready for assignment.
              </p>
            )}
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="Assignment" />
        <div className="p-4">
          {owner ? (
            <AssetActionDialog
              confirmLabel="Unassign asset"
              description={`Return ${asset.assetTag} from ${owner.fullName} to the unassigned inventory pool.`}
              onConfirm={() => onAction(unassignAsset(asset.assetTag))}
              title="Unassign asset"
              trigger={
                <Button className="w-full">
                  <IconUserMinus aria-hidden="true" className="h-4 w-4" />
                  Unassign from {owner.fullName}
                </Button>
              }
            />
          ) : (
            <div className="flex flex-col gap-2 sm:flex-row">
              <label className="sr-only" htmlFor={`assign-${asset.assetTag}`}>
                Employee to assign
              </label>
              <Select
                id={`assign-${asset.assetTag}`}
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
                confirmLabel="Assign asset"
                description={`Assign ${asset.assetTag} to ${
                  directoryUsers.find((user) => user.id === employeeId)
                    ?.fullName ?? 'the selected employee'
                }.`}
                onConfirm={() => {
                  onAction(assignAsset(asset.assetTag, employeeId));
                  setEmployeeId('');
                }}
                title="Assign asset"
                trigger={
                  <Button disabled={!employeeId} variant="primary">
                    <IconPackageExport aria-hidden="true" className="h-4 w-4" />
                    Assign
                  </Button>
                }
              />
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Asset status" />
        <div className="flex flex-col gap-2 p-4 sm:flex-row">
          <label className="sr-only" htmlFor={`status-${asset.assetTag}`}>
            New asset status
          </label>
          <Select
            id={`status-${asset.assetTag}`}
            onChange={(event) =>
              setNextStatus(event.target.value as AssetStatus)
            }
            value={nextStatus}
          >
            {Object.values(AssetStatus).map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
          <AssetActionDialog
            confirmLabel={`Mark ${nextStatus}`}
            description={`Change ${asset.assetTag} from ${asset.status} to ${nextStatus}.`}
            onConfirm={() =>
              onAction(changeAssetStatus(asset.assetTag, nextStatus))
            }
            title="Change asset status"
            trigger={
              <Button disabled={nextStatus === asset.status} variant="soft">
                <IconDeviceDesktop aria-hidden="true" className="h-4 w-4" />
                Update status
              </Button>
            }
          />
        </div>
      </Card>
    </aside>
  );
}

function DetailField({
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
      <dt className="text-xs font-extrabold uppercase text-zinc-500">
        {label}
      </dt>
      <dd
        className={`mt-1 capitalize text-zinc-200 ${mono ? 'font-mono' : ''}`}
      >
        {value}
      </dd>
    </div>
  );
}
