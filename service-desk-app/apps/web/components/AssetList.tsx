'use client';

import { AssetStatus, type DirectoryUserTemplate } from '@service-desk/shared';
import { Badge, Card } from '@service-desk/ui';
import {
  IconDeviceDesktop,
  IconFilterOff,
  IconUserOff,
} from '@tabler/icons-react';

import type { AssetInventoryRecord } from './TicketSessionProvider';

export type AssetView = 'assets' | 'users';

interface AssetListProps {
  assets: readonly AssetInventoryRecord[];
  directoryUsers: readonly DirectoryUserTemplate[];
  isLoading: boolean;
  onSelect: (assetTag: string) => void;
  selectedAssetTag: string | null;
  view: AssetView;
}

const STATUS_VARIANTS = {
  [AssetStatus.Deployed]: 'success',
  [AssetStatus.Lost]: 'amber',
  [AssetStatus.Damaged]: 'amber',
  [AssetStatus.Repaired]: 'sky',
  [AssetStatus.Retired]: 'default',
} as const;

export function AssetList({
  assets,
  directoryUsers,
  isLoading,
  onSelect,
  selectedAssetTag,
  view,
}: AssetListProps) {
  if (isLoading) {
    return (
      <Card aria-label="Loading assets" className="divide-y divide-zinc-800">
        {Array.from({ length: 8 }, (_, index) => (
          <div
            className="animate-pulse px-4 py-3"
            key={`asset-skeleton-${index}`}
          >
            <div className="h-4 w-32 rounded-sm bg-zinc-800" />
            <div className="mt-2 h-3 w-48 rounded-sm bg-zinc-800/70" />
          </div>
        ))}
      </Card>
    );
  }

  if (assets.length === 0) {
    return (
      <Card className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
        <IconFilterOff aria-hidden="true" className="h-9 w-9 text-zinc-600" />
        <h2 className="mt-4 text-base font-bold text-zinc-100">
          No assets match your search
        </h2>
        <p className="mt-2 max-w-md text-sm text-zinc-400">
          Try a broader asset tag, employee, department, or status filter.
        </p>
      </Card>
    );
  }

  return (
    <Card className="sd-assets-layout max-h-[68vh] overflow-y-auto">
      <div className="sd-assets-table-header sticky top-0 z-10 hidden grid-cols-[1fr_1.3fr_1fr_auto] gap-3 border-b border-zinc-700 bg-zinc-800 px-4 py-2 text-xs font-extrabold uppercase text-zinc-400 sm:grid">
        <span>{view === 'users' ? 'Name' : 'Asset tag'}</span>
        <span>{view === 'users' ? 'Asset tag' : 'Name'}</span>
        <span>Department</span>
        <span>Status</span>
      </div>
      <div className="divide-y divide-zinc-800">
        {assets.map((asset) => {
          const owner =
            directoryUsers.find(
              (user) => user.id === asset.assignedDirectoryUserId,
            ) ?? null;
          const selected = selectedAssetTag === asset.assetTag;
          const primary = view === 'users' ? owner?.fullName : asset.assetTag;
          const secondary = view === 'users' ? asset.assetTag : owner?.fullName;

          return (
            <button
              aria-label={`View asset details for ${owner?.fullName ?? asset.assetTag}`}
              aria-pressed={selected}
              className={`sd-assets-row sd-focus-ring grid w-full gap-2 px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 sm:grid-cols-[1fr_1.3fr_1fr_auto] sm:items-center sm:gap-3 ${
                selected ? 'bg-sky-400/10' : 'hover:bg-zinc-800/70'
              }`}
              key={asset.assetTag}
              onClick={() => onSelect(asset.assetTag)}
              type="button"
            >
              <span className="flex min-w-0 items-center gap-2">
                {owner ? (
                  <IconDeviceDesktop
                    aria-hidden="true"
                    className="h-4 w-4 shrink-0 text-sky-400"
                  />
                ) : (
                  <IconUserOff
                    aria-hidden="true"
                    className="h-4 w-4 shrink-0 text-zinc-500"
                  />
                )}
                <span
                  className={`truncate text-sm font-bold text-zinc-100 ${
                    view === 'assets' ? 'font-mono' : ''
                  }`}
                >
                  {primary ?? 'Unassigned'}
                </span>
              </span>
              <span
                className={`truncate text-sm text-zinc-300 ${
                  view === 'users' ? 'font-mono' : ''
                }`}
              >
                {secondary ?? 'Unassigned'}
              </span>
              <span className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-zinc-500">
                <span className="truncate">
                  {owner?.department ?? 'Unassigned pool'}
                </span>
                {owner?.disabled ? (
                  <Badge variant="amber">Disabled in Directory</Badge>
                ) : owner?.locked ? (
                  <Badge variant="amber">Locked</Badge>
                ) : null}
              </span>
              <Badge variant={STATUS_VARIANTS[asset.status]}>
                {asset.status}
              </Badge>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
