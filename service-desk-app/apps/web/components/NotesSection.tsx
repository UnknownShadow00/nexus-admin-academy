'use client';

import type { TicketNote } from '@service-desk/shared';
import { Button, Card, CardHeader, Textarea } from '@service-desk/ui';
import { IconNote, IconPlus } from '@tabler/icons-react';
import { useState, type FormEvent } from 'react';

import { formatActivityTimestamp } from './ticket-labels';

interface NotesSectionProps {
  notes: readonly TicketNote[];
  onAddNote: (body: string) => void;
}

export function NotesSection({ notes, onAddNote }: NotesSectionProps) {
  const [body, setBody] = useState('');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!body.trim()) {
      return;
    }

    onAddNote(body);
    setBody('');
  }

  return (
    <Card>
      <CardHeader
        meta={`${notes.length} private`}
        title={
          <span className="flex items-center gap-2">
            <IconNote aria-hidden="true" className="h-5 w-5 text-sky-400" />
            Internal notes
          </span>
        }
      />
      <div className="p-4 sm:p-5">
        {notes.length > 0 ? (
          <ul className="mb-5 space-y-3">
            {[...notes].reverse().map((note) => (
              <li
                className="rounded-sm border border-zinc-800 bg-zinc-950 p-3"
                key={note.id}
              >
                <p className="whitespace-pre-wrap text-sm text-zinc-300">
                  {note.body}
                </p>
                <time
                  className="mt-2 block text-[11px] text-zinc-500"
                  dateTime={note.createdAt}
                >
                  Added {formatActivityTimestamp(note.createdAt)}
                </time>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mb-4 text-sm text-zinc-500">
            No internal notes yet. Notes stay within this practice session.
          </p>
        )}
        <form onSubmit={handleSubmit}>
          <label
            className="text-xs font-extrabold uppercase tracking-wide text-zinc-500"
            htmlFor="internal-note"
          >
            Add a note
          </label>
          <Textarea
            className="mt-2"
            id="internal-note"
            onChange={(event) => setBody(event.target.value)}
            placeholder="Record what you checked or what should happen next…"
            value={body}
          />
          <Button
            className="mt-3 w-full sm:w-auto"
            disabled={!body.trim()}
            type="submit"
            variant="soft"
          >
            <IconPlus aria-hidden="true" className="h-4 w-4" />
            Add internal note
          </Button>
        </form>
      </div>
    </Card>
  );
}
