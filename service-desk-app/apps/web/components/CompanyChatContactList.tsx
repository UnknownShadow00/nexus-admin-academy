'use client';

import type { DirectoryUserTemplate } from '@service-desk/shared';
import {
  isChatThreadUnread,
  type ChatThreadOverlay,
} from '@service-desk/simulation-engine';
import { Card } from '@service-desk/ui';
import {
  IconMessageCircleOff,
  IconPin,
  IconSearchOff,
  IconUser,
} from '@tabler/icons-react';

interface CompanyChatContactListProps {
  contacts: readonly DirectoryUserTemplate[];
  emptyDescription: string;
  emptyTitle: string;
  isLoading: boolean;
  onSelect: (contactId: string) => void;
  selectedContactId: string | null;
  threads: Readonly<Record<string, ChatThreadOverlay>>;
}

export function CompanyChatContactList({
  contacts,
  emptyDescription,
  emptyTitle,
  isLoading,
  onSelect,
  selectedContactId,
  threads,
}: CompanyChatContactListProps) {
  if (isLoading) {
    return (
      <Card
        aria-label="Restoring company chat contacts"
        className="divide-y divide-zinc-800"
      >
        {Array.from({ length: 7 }, (_, index) => (
          <div
            className="animate-pulse px-4 py-3"
            key={`chat-contact-skeleton-${index}`}
          >
            <div className="h-4 w-40 rounded-sm bg-zinc-800" />
            <div className="mt-2 h-3 w-28 rounded-sm bg-zinc-800/70" />
          </div>
        ))}
      </Card>
    );
  }

  if (contacts.length === 0) {
    const isSearchEmpty = emptyTitle.toLowerCase().includes('match');
    const EmptyIcon = isSearchEmpty ? IconSearchOff : IconMessageCircleOff;

    return (
      <Card className="flex min-h-64 flex-col items-center justify-center px-5 py-10 text-center">
        <EmptyIcon aria-hidden="true" className="h-9 w-9 text-zinc-600" />
        <h2 className="mt-4 text-base font-bold text-zinc-100">{emptyTitle}</h2>
        <p className="mt-2 max-w-md text-sm text-zinc-400">
          {emptyDescription}
        </p>
      </Card>
    );
  }

  return (
    <Card className="max-h-[62vh] overflow-y-auto">
      <div className="divide-y divide-zinc-800">
        {contacts.map((contact) => {
          const thread = threads[contact.id];
          const selected = selectedContactId === contact.id;
          const unread = thread ? isChatThreadUnread(thread) : false;
          const lastMessage = thread?.messages.at(-1);

          return (
            <button
              aria-pressed={selected}
              className={`sd-focus-ring flex w-full items-center gap-3 px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400 ${
                selected ? 'bg-sky-400/10' : 'hover:bg-zinc-800/70'
              }`}
              key={contact.id}
              onClick={() => onSelect(contact.id)}
              type="button"
            >
              <span className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-sm border border-zinc-700 bg-zinc-950 text-zinc-400">
                <IconUser aria-hidden="true" className="h-5 w-5" />
                {unread ? (
                  <span
                    aria-label="Unread messages"
                    className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-zinc-950 bg-sky-400"
                  />
                ) : null}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="block truncate text-sm font-bold text-zinc-100">
                    {contact.fullName}
                  </span>
                  {thread?.pinned ? (
                    <IconPin
                      aria-label="Pinned conversation"
                      className="h-3.5 w-3.5 shrink-0 text-amber-400"
                    />
                  ) : null}
                </span>
                <span className="mt-0.5 block truncate text-xs text-zinc-500">
                  {lastMessage?.body ?? contact.department}
                </span>
              </span>
              {unread ? (
                <span className="sr-only">Unread conversation</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </Card>
  );
}
