'use client';

import type {
  DirectoryUserTemplate,
  IdentityVerificationMethod,
} from '@service-desk/shared';
import type {
  ActionEvent,
  ChatThreadOverlay,
} from '@service-desk/simulation-engine';
import { Badge, Button, Card, Select, Textarea } from '@service-desk/ui';
import {
  IconMessages,
  IconPin,
  IconPinnedOff,
  IconSend,
  IconUser,
} from '@tabler/icons-react';
import { useState, type FormEvent } from 'react';

import { useCompanyChatSession } from './TicketSessionProvider';

const MESSAGE_LIMIT = 500;
const IDENTITY_METHOD_LABELS: Readonly<
  Record<IdentityVerificationMethod, string>
> = {
  'employee-id-directory-match': 'Match employee ID to directory record',
  'manager-confirmation': 'Approved manager confirmation',
  'known-number-callback': 'Callback to known company number',
};

interface CompanyChatThreadProps {
  contact: DirectoryUserTemplate | null;
  thread: ChatThreadOverlay | undefined;
}

export function CompanyChatThread({ contact, thread }: CompanyChatThreadProps) {
  const {
    markPinned,
    openThread,
    requestResolutionConfirmation,
    sendMessage,
    verifyIdentity,
  } = useCompanyChatSession();
  const [body, setBody] = useState('');
  const [verificationMethod, setVerificationMethod] =
    useState<IdentityVerificationMethod>('employee-id-directory-match');
  const [lastEvent, setLastEvent] = useState<ActionEvent | null>(null);

  if (!contact) {
    return (
      <Card className="flex min-h-[32rem] flex-col items-center justify-center border-dashed px-6 py-10 text-center">
        <IconMessages aria-hidden="true" className="h-10 w-10 text-zinc-600" />
        <h2 className="mt-4 text-base font-bold text-zinc-100">
          Choose a contact
        </h2>
        <p className="mt-2 max-w-sm text-sm text-zinc-400">
          Select someone from the company directory to review or begin a
          scripted support conversation.
        </p>
      </Card>
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!contact) {
      return;
    }

    const result = sendMessage(contact.id, body);
    setLastEvent(result);

    if (result.success) {
      setBody('');
      openThread(contact.id);
    }
  }

  const pinned = thread?.pinned ?? false;
  const messages = thread?.messages ?? [];
  const ticketByContact: Readonly<Record<string, string>> = {
    'directory-user-camille-reyes': 'INC2513',
    'directory-user-harper-kim': 'INC2406',
    'directory-user-jordan-lee': 'INC2512',
    'directory-user-sloane-rivera': 'INC2405',
    'directory-user-taylor-morgan': 'INC2511',
  };
  const ticketId = ticketByContact[contact.id];
  const availableVerificationMethods =
    contact.availableIdentityVerificationMethods;
  const selectedVerificationMethod = availableVerificationMethods.includes(
    verificationMethod,
  )
    ? verificationMethod
    : availableVerificationMethods[0];

  return (
    <Card className="flex min-h-[32rem] flex-col overflow-hidden">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-800 px-4 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconUser aria-hidden="true" className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-base font-bold text-zinc-100">
              {contact.fullName}
            </h2>
            <p className="truncate text-xs text-zinc-500">
              {contact.jobTitle} · {contact.department}
            </p>
          </div>
        </div>
        <Button
          aria-pressed={pinned}
          className="px-3"
          onClick={() => {
            const result = markPinned(contact.id, !pinned);
            setLastEvent(result);
          }}
          variant={pinned ? 'soft' : 'ghost'}
        >
          {pinned ? (
            <IconPinnedOff aria-hidden="true" className="h-4 w-4" />
          ) : (
            <IconPin aria-hidden="true" className="h-4 w-4" />
          )}
          {pinned ? 'Unpin' : 'Pin'}
        </Button>
      </header>

      <div
        aria-live="polite"
        className="flex min-h-72 flex-1 flex-col gap-3 overflow-y-auto bg-zinc-950/40 p-4"
      >
        {messages.length === 0 ? (
          <div className="m-auto max-w-sm text-center">
            <IconMessages
              aria-hidden="true"
              className="mx-auto h-8 w-8 text-zinc-600"
            />
            <p className="mt-3 text-sm font-semibold text-zinc-300">
              No messages with {contact.fullName} yet
            </p>
            <p className="mt-1 text-xs leading-relaxed text-zinc-500">
              Ask for a support detail below. Replies are deterministic and stay
              within this training attempt.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              className={`flex ${
                message.fromStudent ? 'justify-end' : 'justify-start'
              }`}
              key={message.id}
            >
              <div
                className={`max-w-[85%] rounded-md border px-3 py-2 text-sm leading-relaxed ${
                  message.fromStudent
                    ? 'border-sky-500/40 bg-sky-600/20 text-sky-100'
                    : 'border-zinc-700 bg-zinc-900 text-zinc-200'
                }`}
              >
                <p>{message.body}</p>
                <p
                  className={`mt-1 text-[10px] font-bold uppercase tracking-wide ${
                    message.fromStudent ? 'text-sky-400' : 'text-zinc-500'
                  }`}
                >
                  {message.fromStudent ? 'You' : contact.fullName}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      {ticketId ? (
        <section className="space-y-3 border-t border-zinc-800 bg-zinc-900/70 p-4">
          {contact.supportIssue ? (
            <div className="space-y-2">
              <p className="text-xs leading-relaxed text-zinc-400">
                {contact.identityVerificationContext}
              </p>
              <div className="grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                <Select
                  aria-label="Approved identity verification method"
                  onChange={(event) =>
                    setVerificationMethod(
                      event.target.value as IdentityVerificationMethod,
                    )
                  }
                  value={selectedVerificationMethod}
                >
                  {availableVerificationMethods.map((method) => (
                    <option key={method} value={method}>
                      {IDENTITY_METHOD_LABELS[method]}
                    </option>
                  ))}
                </Select>
                <Button
                  disabled={!selectedVerificationMethod}
                  onClick={() => {
                    if (!selectedVerificationMethod) return;
                    const result = verifyIdentity(
                      contact.id,
                      ticketId,
                      selectedVerificationMethod,
                    );
                    setLastEvent(result);
                    if (result.success) openThread(contact.id);
                  }}
                  variant="soft"
                >
                  Run approved identity check
                </Button>
              </div>
            </div>
          ) : null}
          <Button
            onClick={() => {
              const result = requestResolutionConfirmation(
                contact.id,
                ticketId,
              );
              setLastEvent(result);
              if (result.success) openThread(contact.id);
            }}
            variant="soft"
          >
            Ask user to retest original symptom
          </Button>
          <p className="text-xs leading-relaxed text-zinc-500">
            Training interactions use approved company channels and never ask
            for passwords, recovery codes, security answers, or real personal
            data.
          </p>
        </section>
      ) : null}

      <form
        className="border-t border-zinc-800 bg-zinc-900 p-4"
        onSubmit={handleSubmit}
      >
        {lastEvent && !lastEvent.success ? (
          <div
            className="mb-3 rounded-sm border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-300"
            role="alert"
          >
            {lastEvent.rejectReason ?? 'The simulation rejected this message.'}
          </div>
        ) : null}
        <label className="sr-only" htmlFor={`chat-message-${contact.id}`}>
          Message {contact.fullName}
        </label>
        <Textarea
          id={`chat-message-${contact.id}`}
          maxLength={MESSAGE_LIMIT}
          onChange={(event) =>
            setBody(event.target.value.slice(0, MESSAGE_LIMIT))
          }
          placeholder={`Message ${contact.fullName}`}
          rows={3}
          value={body}
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Badge
              variant={body.length === MESSAGE_LIMIT ? 'amber' : 'default'}
            >
              {body.length}/{MESSAGE_LIMIT}
            </Badge>
            <span className="text-xs text-zinc-500">
              Scripted training replies
            </span>
          </div>
          <Button
            disabled={body.trim().length === 0}
            type="submit"
            variant="primary"
          >
            <IconSend aria-hidden="true" className="h-4 w-4" />
            Send
          </Button>
        </div>
      </form>
    </Card>
  );
}
