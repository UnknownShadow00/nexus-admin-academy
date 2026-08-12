'use client';

import React from 'react';
import type { WorkstationCredential } from '@service-desk/shared';
import { Button, Input } from '@service-desk/ui';
import { IconKey, IconShieldCheck, IconTrash } from '@tabler/icons-react';
import { useState } from 'react';

export function CredentialManagerApp({
  credentials,
  onAdd,
  onDelete,
}: {
  credentials: readonly WorkstationCredential[];
  onAdd: (
    target: string,
    username: string,
  ) => { success: boolean; rejectReason: string | null };
  onDelete: (target: string) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [target, setTarget] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">Credential Manager</h3>
          <p className="mt-1 text-sm text-zinc-600">
            Manage synthetic Windows credential targets used by this training
            workstation.
          </p>
        </div>
        <Button onClick={() => setAdding((value) => !value)} variant="light">
          {adding ? 'Cancel' : 'Add Windows credential'}
        </Button>
      </div>

      <div className="mt-5 rounded border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
        Passwords are never entered, stored, shown, or written to the attempt
        log. The simulator keeps target and synthetic username metadata only.
      </div>

      {adding ? (
        <form
          className="mt-5 space-y-3 rounded border border-zinc-200 bg-zinc-50 p-4"
          onSubmit={(event) => {
            event.preventDefault();
            const result = onAdd(target.trim(), username.trim());
            if (!result.success) {
              setError(
                result.rejectReason ?? 'The credential could not be added.',
              );
              return;
            }
            setTarget('');
            setUsername('');
            setError(null);
            setAdding(false);
          }}
        >
          <label className="block text-sm font-semibold">
            Internet or network address
            <Input
              className="mt-1 bg-white font-mono font-normal"
              onChange={(event) => setTarget(event.target.value)}
              placeholder="server.nexus.internal"
              value={target}
            />
          </label>
          <label className="block text-sm font-semibold">
            Synthetic user name
            <Input
              className="mt-1 bg-white font-mono font-normal"
              onChange={(event) => setUsername(event.target.value)}
              placeholder="NEXUS\\user.name"
              value={username}
            />
          </label>
          {error ? (
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
          ) : null}
          <Button disabled={!target.trim() || !username.trim()} type="submit">
            Save metadata
          </Button>
        </form>
      ) : null}

      <section aria-labelledby="windows-credentials-title" className="mt-6">
        <h4
          className="flex items-center gap-2 font-semibold"
          id="windows-credentials-title"
        >
          <IconShieldCheck
            aria-hidden="true"
            className="h-5 w-5 text-sky-700"
          />
          Windows Credentials
        </h4>
        <div className="mt-3 divide-y divide-zinc-200 border border-zinc-200">
          {credentials.length ? (
            credentials.map((credential) => (
              <article
                className="flex flex-wrap items-center gap-3 bg-white p-4"
                key={credential.id}
              >
                <IconKey
                  aria-hidden="true"
                  className="h-6 w-6 text-amber-600"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-mono text-sm font-semibold">
                    {credential.target}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {credential.username} · {credential.persistence}
                  </p>
                </div>
                <button
                  aria-label={`Remove credential for ${credential.target}`}
                  className="inline-flex items-center gap-1 rounded px-2 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50"
                  onClick={() => onDelete(credential.target)}
                  type="button"
                >
                  <IconTrash aria-hidden="true" className="h-4 w-4" />
                  Remove
                </button>
              </article>
            ))
          ) : (
            <p className="bg-white p-6 text-center text-sm text-zinc-500">
              No Windows credentials are stored.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
