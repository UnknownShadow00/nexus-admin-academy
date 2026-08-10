'use client';

import { AssetStatus } from '@service-desk/shared';
import type { ActionEvent } from '@service-desk/simulation-engine';
import { Badge, Button, Input, PanelFrame, Select } from '@service-desk/ui';
import {
  IconArrowLeft,
  IconPackage,
  IconRefresh,
  IconSearch,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { AssetDetail } from './AssetDetail';
import { AssetList, type AssetView } from './AssetList';
import { useAssetManagementSession } from './TicketSessionProvider';

type StatusFilter = AssetStatus | 'all';

function eventMessage(event: ActionEvent) {
  if (!event.success) {
    return event.rejectReason ?? 'The simulation rejected this action.';
  }

  switch (event.type) {
    case 'asset.assign':
      return 'Asset assignment updated across Asset Management and PC Shelf.';
    case 'asset.unassign':
      return 'Asset returned to the unassigned inventory pool.';
    case 'asset.change_status':
      return `Asset status changed to ${String(event.payload.status)}.`;
    case 'asset.record_isolation':
      return 'Hardware isolation check recorded.';
    default:
      return 'Asset action recorded.';
  }
}

export function AssetManagementTool() {
  const { assets, directoryUsers, isHydrated } = useAssetManagementSession();
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);
  const [query, setQuery] = useState('');
  const [selectedAssetTag, setSelectedAssetTag] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [syncMessage, setSyncMessage] = useState('');
  const [view, setView] = useState<AssetView>('users');
  const filteredAssets = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return assets
      .filter((asset) => {
        const owner =
          directoryUsers.find(
            (user) => user.id === asset.assignedDirectoryUserId,
          ) ?? null;
        const matchesQuery =
          normalizedQuery.length === 0 ||
          asset.assetTag.toLowerCase().includes(normalizedQuery) ||
          owner?.fullName.toLowerCase().includes(normalizedQuery) ||
          owner?.department.toLowerCase().includes(normalizedQuery);
        const matchesStatus =
          statusFilter === 'all' || asset.status === statusFilter;

        return Boolean(matchesQuery && matchesStatus);
      })
      .sort((left, right) => {
        if (view === 'assets') {
          return left.assetTag.localeCompare(right.assetTag);
        }

        const leftOwner =
          directoryUsers.find(
            (user) => user.id === left.assignedDirectoryUserId,
          )?.fullName ?? 'ZZZ Unassigned';
        const rightOwner =
          directoryUsers.find(
            (user) => user.id === right.assignedDirectoryUserId,
          )?.fullName ?? 'ZZZ Unassigned';
        return (
          leftOwner.localeCompare(rightOwner) ||
          left.assetTag.localeCompare(right.assetTag)
        );
      });
  }, [assets, directoryUsers, query, statusFilter, view]);
  const selectedAsset =
    assets.find((asset) => asset.assetTag === selectedAssetTag) ?? null;

  useEffect(() => {
    if (
      selectedAssetTag &&
      !assets.some((asset) => asset.assetTag === selectedAssetTag)
    ) {
      setSelectedAssetTag(null);
    }
  }, [assets, selectedAssetTag]);

  return (
    <PanelFrame
      aria-labelledby="asset-management-title"
      className="mx-auto w-full max-w-7xl p-0"
      variant="assets"
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
          <Badge variant="sky">{assets.length} inventory records</Badge>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconPackage aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Equipment lifecycle
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="asset-management-title"
            >
              Asset Management
            </h1>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-400">
          Review ownership, assignment, lifecycle status, and shelf computers
          against the live Directory identity roster.
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

      <div className="sd-assets-toolbar border-b border-zinc-800 p-4 sm:p-5">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div
            aria-label="Asset view"
            className="flex rounded-sm border border-zinc-700 bg-zinc-950 p-1"
            role="group"
          >
            {(['users', 'assets'] as const).map((option) => (
              <Button
                aria-pressed={view === option}
                className="flex-1"
                key={option}
                onClick={() => setView(option)}
                variant={view === option ? 'primary' : 'ghost'}
              >
                By {option}
              </Button>
            ))}
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              onClick={() => {
                setSyncMessage(
                  `Directory state synchronized at ${new Date().toLocaleTimeString(
                    [],
                    {
                      hour: '2-digit',
                      minute: '2-digit',
                    },
                  )}.`,
                );
              }}
              variant="soft"
            >
              <IconRefresh aria-hidden="true" className="h-4 w-4" />
              Sync from AD
            </Button>
            {syncMessage ? (
              <span
                className="self-center text-xs text-emerald-400"
                role="status"
              >
                {syncMessage}
              </span>
            ) : null}
          </div>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_13rem]">
          <label className="relative block">
            <span className="sr-only">
              Search by asset tag, owner name, or department
            </span>
            <IconSearch
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
            />
            <Input
              className="pl-9"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search assets"
              type="search"
              value={query}
            />
          </label>
          <label>
            <span className="sr-only">Filter by asset status</span>
            <Select
              onChange={(event) =>
                setStatusFilter(event.target.value as StatusFilter)
              }
              value={statusFilter}
            >
              <option value="all">All statuses</option>
              {Object.values(AssetStatus).map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </Select>
          </label>
        </div>
      </div>

      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[minmax(22rem,1.1fr)_minmax(20rem,0.9fr)]">
        <section aria-label="Asset inventory list">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            {isHydrated
              ? `${filteredAssets.length} of ${assets.length}`
              : 'Restoring asset state…'}
          </p>
          <AssetList
            assets={filteredAssets}
            directoryUsers={directoryUsers}
            isLoading={!isHydrated}
            onSelect={setSelectedAssetTag}
            selectedAssetTag={selectedAssetTag}
            view={view}
          />
          <p className="mt-2 text-right font-mono text-xs text-zinc-500">
            {filteredAssets.length} of {assets.length}
          </p>
        </section>

        {selectedAsset ? (
          <AssetDetail
            asset={selectedAsset}
            directoryUsers={directoryUsers}
            onAction={setLastEvent}
          />
        ) : (
          <section className="flex min-h-72 flex-col items-center justify-center rounded-md border border-dashed border-zinc-700 bg-zinc-950/40 p-8 text-center">
            <IconPackage
              aria-hidden="true"
              className="h-10 w-10 text-zinc-600"
            />
            <h2 className="mt-4 text-base font-bold text-zinc-100">
              Select an asset
            </h2>
            <p className="mt-2 max-w-sm text-sm text-zinc-400">
              Open a row to review ownership, location, serial number, and
              available inventory actions.
            </p>
          </section>
        )}
      </div>
    </PanelFrame>
  );
}
