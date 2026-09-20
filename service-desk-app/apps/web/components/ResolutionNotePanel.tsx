'use client';

import type { TicketNote } from '@service-desk/shared';
import { Button, Card, CardHeader, Textarea } from '@service-desk/ui';
import { IconNote, IconPlus } from '@tabler/icons-react';
import React, { useState, type FormEvent } from 'react';

import { formatActivityTimestamp } from './ticket-labels';

const NOTE_PROMPTS =
  'What did the requester report? What did you check? What did you find? Likely cause? Action taken? How did you verify?';

export function ResolutionNotePanel({
  experienceMode,
  notes,
  onSubmit,
}: {
  experienceMode: 'guided' | 'practice' | 'assessment';
  notes: readonly TicketNote[];
  onSubmit: (
    body: string,
  ) => { success: boolean } | Promise<{ success: boolean }>;
}) {
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const showPrompts = experienceMode !== 'assessment';

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const note = body.trim();
    if (note.length < 20) return;
    setSubmitting(true);
    setError('');
    try {
      const result = await onSubmit(body);
      if (result.success) setBody('');
      else
        setError(
          'Your note needs enough detail to identify what you tested and what happened.',
        );
    } catch {
      setError(
        'Your note could not be saved. Your text is still here; please try again.',
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader
        meta={`${notes.length} private`}
        title={
          <span className="flex items-center gap-2">
            <IconNote aria-hidden="true" className="h-5 w-5 text-accent" />
            Resolution notes
          </span>
        }
      />
      <div className="p-4 sm:p-5">
        {notes.length ? (
          <ul className="mb-5 space-y-3">
            {[...notes].reverse().map((note) => (
              <li
                className="rounded-sm border border-border bg-surface p-3"
                key={note.id}
              >
                <p className="whitespace-pre-wrap text-sm text-text">
                  {note.body}
                </p>
                <time
                  className="mt-2 block text-[11px] text-text-muted"
                  dateTime={note.createdAt}
                >
                  Added {formatActivityTimestamp(note.createdAt)}
                </time>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mb-4 text-sm text-text-muted">
            No internal notes yet. Notes stay within this practice session.
          </p>
        )}
        <form onSubmit={handleSubmit}>
          <label
            className="text-xs font-extrabold uppercase tracking-wide text-text-muted"
            htmlFor="resolution-note"
          >
            Add a note
          </label>
          <Textarea
            aria-describedby={
              showPrompts ? 'resolution-note-prompts' : undefined
            }
            className="mt-2"
            disabled={submitting}
            id="resolution-note"
            onChange={(event) => setBody(event.target.value)}
            placeholder={showPrompts ? NOTE_PROMPTS : 'Write an internal note…'}
            value={body}
          />
          {showPrompts ? (
            <p
              className="mt-2 text-xs leading-5 text-text-muted"
              id="resolution-note-prompts"
            >
              {NOTE_PROMPTS}
            </p>
          ) : null}
          {error ? (
            <p className="mt-2 text-sm text-warning" role="alert">
              {error}
            </p>
          ) : null}
          <Button
            className="mt-3 w-full sm:w-auto"
            disabled={submitting || body.trim().length < 20}
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
