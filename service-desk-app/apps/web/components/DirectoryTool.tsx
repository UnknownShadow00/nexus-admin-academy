'use client';

import type { ActionEvent } from '@service-desk/simulation-engine';
import { Badge, Input, PanelFrame, Select } from '@service-desk/ui';
import { IconArrowLeft, IconSearch, IconUsers } from '@tabler/icons-react';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

import { DirectoryUserDetail } from './DirectoryUserDetail';
import { DirectoryUserList } from './DirectoryUserList';
import { useDirectorySession } from './TicketSessionProvider';

type AccountFilter = 'all' | 'disabled' | 'locked' | 'mfa-reset';

function eventMessage(event: ActionEvent) {
  if (!event.success) {
    return event.rejectReason ?? 'The simulation rejected this action.';
  }

  switch (event.type) {
    case 'directory.inspect_account':
      return 'Account state reviewed. Use the evidence to distinguish lock, password, and MFA conditions.';
    case 'directory.verify_identity':
      return 'Approved training identity check recorded. No real secret was collected.';
    case 'directory.test_primary_auth':
      return event.payload.result === 'succeeds'
        ? 'Primary password authentication succeeds; continue with the second-factor evidence.'
        : 'Primary authentication is blocked; inspect the account and password state.';
    case 'directory.record_diagnosis':
      return 'Diagnosis recorded from the reviewed account evidence.';
    case 'directory.verify_access':
      return 'The original sign-in path has been verified after remediation.';
    case 'directory.unlock_account':
      return 'Account unlocked. New sign-in attempts are now allowed.';
    case 'directory.reset_password':
      return 'Temporary password issued. No real password value was stored.';
    case 'directory.enable_account':
      return 'Account enabled. Sign-in access has been restored.';
    case 'directory.disable_account':
      return 'Account disabled. Sign-in access is now blocked.';
    case 'directory.reset_mfa':
      return 'MFA registration cleared. The user must enroll again.';
    case 'directory.update_groups':
      return 'Group membership updated for this attempt.';
    default:
      return 'Directory action recorded.';
  }
}

export function DirectoryTool() {
  const { directoryUsers, isHydrated } = useDirectorySession();
  const [accountFilter, setAccountFilter] = useState<AccountFilter>('all');
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);
  const [query, setQuery] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const filteredUsers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return directoryUsers.filter((user) => {
      const matchesQuery =
        normalizedQuery.length === 0 ||
        user.fullName.toLowerCase().includes(normalizedQuery) ||
        user.username.toLowerCase().includes(normalizedQuery) ||
        user.department.toLowerCase().includes(normalizedQuery);
      const matchesAccountFilter =
        accountFilter === 'all' ||
        (accountFilter === 'locked' &&
          user.locked &&
          (!user.supportIssue || user.accountInspected)) ||
        (accountFilter === 'disabled' && user.disabled) ||
        (accountFilter === 'mfa-reset' && !user.mfaEnrolled);

      return matchesQuery && matchesAccountFilter;
    });
  }, [accountFilter, directoryUsers, query]);
  const selectedUser =
    directoryUsers.find((user) => user.id === selectedUserId) ?? null;

  useEffect(() => {
    if (
      selectedUserId &&
      !directoryUsers.some((user) => user.id === selectedUserId)
    ) {
      setSelectedUserId(null);
    }
  }, [directoryUsers, selectedUserId]);

  return (
    <PanelFrame
      aria-labelledby="directory-title"
      className="mx-auto w-full max-w-7xl p-0"
      variant="ad"
    >
      <header className="border-b border-zinc-800 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 self-start rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-900 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/"
          >
            <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
            Dashboard
          </Link>
          <Badge variant="sky">{directoryUsers.length} user records</Badge>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconUsers aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Identity administration
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="directory-title"
            >
              Directory
            </h1>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-400">
          Search the practice organization, review identity access, and apply
          account or group changes to the current simulation attempt.
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

      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[minmax(19rem,0.85fr)_minmax(0,1.4fr)]">
        <section aria-label="Directory user list">
          <div className="mb-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_12rem] lg:grid-cols-1 xl:grid-cols-[minmax(0,1fr)_12rem]">
            <label className="relative block">
              <span className="sr-only">
                Search by name, username, or department
              </span>
              <IconSearch
                aria-hidden="true"
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
              />
              <Input
                className="pl-9"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search name, username, or department"
                type="search"
                value={query}
              />
            </label>
            <label>
              <span className="sr-only">Filter directory accounts</span>
              <Select
                onChange={(event) =>
                  setAccountFilter(event.target.value as AccountFilter)
                }
                value={accountFilter}
              >
                <option value="all">All accounts</option>
                <option value="locked">Locked</option>
                <option value="disabled">Disabled</option>
                <option value="mfa-reset">MFA reset</option>
              </Select>
            </label>
          </div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
            {isHydrated
              ? `${filteredUsers.length} matching users`
              : 'Restoring directory state…'}
          </p>
          <DirectoryUserList
            isLoading={!isHydrated}
            onSelect={setSelectedUserId}
            selectedUserId={selectedUserId}
            users={filteredUsers}
          />
        </section>

        {selectedUser ? (
          <DirectoryUserDetail onAction={setLastEvent} user={selectedUser} />
        ) : (
          <section className="flex min-h-72 flex-col items-center justify-center rounded-md border border-dashed border-zinc-800 bg-zinc-900/40 p-8 text-center">
            <IconUsers aria-hidden="true" className="h-10 w-10 text-zinc-600" />
            <h2 className="mt-4 text-base font-bold text-zinc-100">
              Select a directory user
            </h2>
            <p className="mt-2 max-w-sm text-sm text-zinc-400">
              Open a row to review account status, groups, devices, licenses,
              and available identity actions.
            </p>
          </section>
        )}
      </div>
    </PanelFrame>
  );
}
