'use client';

import type { DirectoryUserTemplate } from '@service-desk/shared';
import { Badge, Card } from '@service-desk/ui';
import { IconFilterOff, IconUser } from '@tabler/icons-react';

interface DirectoryUserListProps {
  isLoading: boolean;
  onSelect: (directoryUserId: string) => void;
  selectedUserId: string | null;
  users: readonly DirectoryUserTemplate[];
}

export function DirectoryUserList({
  isLoading,
  onSelect,
  selectedUserId,
  users,
}: DirectoryUserListProps) {
  if (isLoading) {
    return (
      <Card
        aria-label="Loading directory users"
        className="divide-y divide-zinc-800"
      >
        {Array.from({ length: 7 }, (_, index) => (
          <div
            className="animate-pulse px-4 py-3"
            key={`directory-skeleton-${index}`}
          >
            <div className="h-4 w-40 rounded-sm bg-zinc-800" />
            <div className="mt-2 h-3 w-28 rounded-sm bg-zinc-800/70" />
          </div>
        ))}
      </Card>
    );
  }

  if (users.length === 0) {
    return (
      <Card className="flex min-h-56 flex-col items-center justify-center px-5 py-10 text-center">
        <IconFilterOff aria-hidden="true" className="h-9 w-9 text-zinc-600" />
        <h2 className="mt-4 text-base font-bold text-zinc-100">
          No users match your search
        </h2>
        <p className="mt-2 max-w-md text-sm text-zinc-400">
          Try a broader name, username, or department filter to bring directory
          records back into view.
        </p>
      </Card>
    );
  }

  return (
    <Card className="max-h-[68vh] overflow-y-auto">
      <div className="divide-y divide-zinc-800">
        {users.map((user) => {
          const selected = selectedUserId === user.id;

          return (
            <button
              aria-pressed={selected}
              className={`sd-focus-ring flex w-full items-center gap-3 px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 ${
                selected ? 'bg-sky-400/10' : 'hover:bg-zinc-800/70'
              }`}
              key={user.id}
              onClick={() => onSelect(user.id)}
              type="button"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm border border-zinc-700 bg-zinc-950 text-zinc-400">
                <IconUser aria-hidden="true" className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold text-zinc-100">
                  {user.fullName}
                </span>
                <span className="mt-0.5 block truncate text-xs text-zinc-500">
                  {user.username} · {user.department}
                </span>
              </span>
              {user.supportIssue && !user.accountInspected ? (
                <Badge variant="default">Review</Badge>
              ) : user.disabled ? (
                <Badge variant="amber">Disabled</Badge>
              ) : user.locked ? (
                <Badge variant="amber">Locked</Badge>
              ) : null}
            </button>
          );
        })}
      </div>
    </Card>
  );
}
