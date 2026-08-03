'use client';

import {
  isChatThreadUnread,
  type ChatThreadOverlay,
} from '@service-desk/simulation-engine';
import {
  Badge,
  Input,
  PanelFrame,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@service-desk/ui';
import { IconArrowLeft, IconMessages, IconSearch } from '@tabler/icons-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { CompanyChatContactList } from './CompanyChatContactList';
import { CompanyChatThread } from './CompanyChatThread';
import {
  useCompanyChatSession,
  useDirectorySession,
} from './TicketSessionProvider';

type ChatTab = 'contacts' | 'pinned' | 'recent';

function lastMessageTime(thread: ChatThreadOverlay | undefined): number {
  const createdAt = thread?.messages.at(-1)?.createdAt;
  return createdAt ? new Date(createdAt).getTime() : 0;
}

export function CompanyChatTool() {
  const searchParams = useSearchParams();
  const requestedContactId = searchParams.get('contact');
  const { directoryUsers } = useDirectorySession();
  const { chatThreads, isHydrated, openThread, unreadThreadCount } =
    useCompanyChatSession();
  const [activeTab, setActiveTab] = useState<ChatTab>('recent');
  const [query, setQuery] = useState('');
  const [selectedContactId, setSelectedContactId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    if (
      requestedContactId &&
      directoryUsers.some((contact) => contact.id === requestedContactId)
    ) {
      setSelectedContactId(requestedContactId);
    }
  }, [directoryUsers, requestedContactId]);

  useEffect(() => {
    if (isHydrated && selectedContactId) {
      openThread(selectedContactId);
    }
  }, [isHydrated, openThread, selectedContactId]);

  const normalizedQuery = query.trim().toLowerCase();
  const tabContacts = useMemo(() => {
    const contacts = directoryUsers
      .filter((contact) => {
        const thread = chatThreads[contact.id];

        if (activeTab === 'recent') {
          return Boolean(thread?.messages.length);
        }
        if (activeTab === 'pinned') {
          return thread?.pinned === true;
        }
        return true;
      })
      .filter(
        (contact) =>
          !normalizedQuery ||
          contact.fullName.toLowerCase().includes(normalizedQuery) ||
          contact.department.toLowerCase().includes(normalizedQuery) ||
          contact.jobTitle.toLowerCase().includes(normalizedQuery),
      );

    if (activeTab === 'recent') {
      return contacts.sort(
        (left, right) =>
          lastMessageTime(chatThreads[right.id]) -
          lastMessageTime(chatThreads[left.id]),
      );
    }

    return contacts;
  }, [activeTab, chatThreads, directoryUsers, normalizedQuery]);
  const selectedContact =
    directoryUsers.find((contact) => contact.id === selectedContactId) ?? null;
  const pinnedCount = Object.values(chatThreads).filter(
    (thread) => thread.pinned,
  ).length;
  const recentUnreadCount =
    Object.values(chatThreads).filter(isChatThreadUnread).length;
  const emptyCopy = normalizedQuery
    ? {
        title: 'No contacts match your search',
        description:
          'Try a broader name, department, or role to bring directory contacts back into view.',
      }
    : activeTab === 'recent'
      ? {
          title: 'No conversations yet',
          description:
            'Choose a directory contact to begin a company chat for this practice attempt.',
        }
      : activeTab === 'pinned'
        ? {
            title: 'No pinned conversations',
            description:
              'Pin an important support conversation to keep it easy to reach.',
          }
        : {
            title: 'No contacts available',
            description:
              'Directory contacts will appear here when the practice roster is available.',
          };

  return (
    <PanelFrame
      aria-labelledby="company-chat-title"
      className="mx-auto w-full max-w-7xl p-0"
      variant="default"
    >
      <header className="border-b border-zinc-800 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 self-start rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-800 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/"
          >
            <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
            Dashboard
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="sky">{directoryUsers.length} contacts</Badge>
            {unreadThreadCount > 0 ? (
              <Badge variant="amber">
                {unreadThreadCount}{' '}
                {unreadThreadCount === 1 ? 'unread chat' : 'unread chats'}
              </Badge>
            ) : null}
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconMessages aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Scripted employee messaging
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="company-chat-title"
            >
              Company Chat
            </h1>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-400">
          Contact employees for ticket context. Conversations and read state
          remain scoped to the current simulation attempt.
        </p>
      </header>

      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[minmax(19rem,0.85fr)_minmax(0,1.4fr)]">
        <section aria-label="Company chat contacts">
          <label className="relative mb-3 block">
            <span className="sr-only">
              Search contacts by name, department, or role
            </span>
            <IconSearch
              aria-hidden="true"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
            />
            <Input
              className="pl-9"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search contacts"
              type="search"
              value={query}
            />
          </label>
          <Tabs
            onValueChange={(value) => setActiveTab(value as ChatTab)}
            value={activeTab}
          >
            <TabsList aria-label="Company chat views">
              <TabsTrigger value="recent">
                <span className="inline-flex items-center gap-1.5">
                  Recent
                  {recentUnreadCount > 0 ? (
                    <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-sky-500 px-1.5 py-0.5 text-[10px] text-zinc-950">
                      {recentUnreadCount}
                    </span>
                  ) : null}
                </span>
              </TabsTrigger>
              <TabsTrigger value="contacts">Contacts</TabsTrigger>
              <TabsTrigger value="pinned">Pinned ({pinnedCount})</TabsTrigger>
            </TabsList>
            {(['recent', 'contacts', 'pinned'] as const).map((tab) => (
              <TabsContent className="py-3" key={tab} value={tab}>
                <CompanyChatContactList
                  contacts={tab === activeTab ? tabContacts : []}
                  emptyDescription={emptyCopy.description}
                  emptyTitle={emptyCopy.title}
                  isLoading={!isHydrated}
                  onSelect={setSelectedContactId}
                  selectedContactId={selectedContactId}
                  threads={chatThreads}
                />
              </TabsContent>
            ))}
          </Tabs>
        </section>

        <CompanyChatThread
          contact={selectedContact}
          key={selectedContact?.id ?? 'no-chat-contact'}
          thread={selectedContact ? chatThreads[selectedContact.id] : undefined}
        />
      </div>
    </PanelFrame>
  );
}
