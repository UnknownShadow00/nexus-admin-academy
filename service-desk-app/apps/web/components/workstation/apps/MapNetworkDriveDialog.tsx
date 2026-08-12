'use client';

import React from 'react';
import type {
  WorkstationCredential,
  WorkstationMappedDrive,
} from '@service-desk/shared';
import { Button, Input } from '@service-desk/ui';
import { IconNetwork, IconX } from '@tabler/icons-react';
import { useState } from 'react';

const DRIVE_LETTERS = Array.from({ length: 23 }, (_, index) =>
  String.fromCharCode('D'.charCodeAt(0) + index).concat(':'),
);

export function MapNetworkDriveDialog({
  credentials,
  currentMapping,
  onCancel,
  onMap,
}: {
  credentials: readonly WorkstationCredential[];
  currentMapping: WorkstationMappedDrive | null;
  onCancel: () => void;
  onMap: (values: {
    letter: string;
    uncPath: string;
    reconnectAtSignIn: boolean;
    credentialTarget: string | null;
  }) => { success: boolean; rejectReason: string | null };
}) {
  const [letter, setLetter] = useState(currentMapping?.letter ?? 'Z:');
  const [uncPath, setUncPath] = useState(currentMapping?.uncPath ?? '\\\\');
  const [reconnectAtSignIn, setReconnectAtSignIn] = useState(
    currentMapping?.reconnectAtSignIn ?? true,
  );
  const [credentialTarget, setCredentialTarget] = useState(
    currentMapping?.credentialTarget ?? '',
  );
  const [error, setError] = useState<string | null>(null);

  return (
    <div
      aria-labelledby="map-drive-title"
      aria-modal="true"
      className="absolute inset-0 z-20 flex items-center justify-center bg-zinc-950/35 p-3"
      role="dialog"
    >
      <form
        className="w-full max-w-lg border border-zinc-400 bg-zinc-50 shadow-2xl"
        onSubmit={(event) => {
          event.preventDefault();
          const result = onMap({
            letter,
            uncPath: uncPath.trim(),
            reconnectAtSignIn,
            credentialTarget: credentialTarget || null,
          });
          if (result.success) onCancel();
          else
            setError(result.rejectReason ?? 'The drive could not be mapped.');
        }}
      >
        <header className="flex items-center justify-between border-b border-zinc-300 bg-white px-4 py-3">
          <span className="flex items-center gap-2">
            <IconNetwork aria-hidden="true" className="h-5 w-5 text-sky-700" />
            <h3 className="font-semibold" id="map-drive-title">
              Map Network Drive
            </h3>
          </span>
          <button
            aria-label="Close Map Network Drive"
            className="rounded p-1 hover:bg-zinc-200"
            onClick={onCancel}
            type="button"
          >
            <IconX aria-hidden="true" className="h-4 w-4" />
          </button>
        </header>
        <div className="space-y-4 p-5">
          <p className="text-sm text-zinc-600">
            Choose a drive letter and enter the approved UNC folder path.
          </p>
          <label className="block text-sm font-semibold">
            Drive
            <select
              className="mt-1 block w-full border border-zinc-300 bg-white px-3 py-2 font-normal"
              onChange={(event) => setLetter(event.target.value)}
              value={letter}
            >
              {DRIVE_LETTERS.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-semibold">
            Folder
            <Input
              aria-describedby="unc-help"
              className="mt-1 bg-white font-mono font-normal"
              onChange={(event) => setUncPath(event.target.value)}
              placeholder="\\server\\share"
              spellCheck={false}
              value={uncPath}
            />
          </label>
          <p className="text-xs text-zinc-500" id="unc-help">
            UNC paths begin with two backslashes and include a server and share.
          </p>
          <label className="flex items-center gap-2 text-sm">
            <input
              checked={reconnectAtSignIn}
              onChange={(event) => setReconnectAtSignIn(event.target.checked)}
              type="checkbox"
            />
            Reconnect at sign-in
          </label>
          <label className="block text-sm font-semibold">
            Stored Windows credential
            <select
              className="mt-1 block w-full border border-zinc-300 bg-white px-3 py-2 font-normal"
              onChange={(event) => setCredentialTarget(event.target.value)}
              value={credentialTarget}
            >
              <option value="">Use current sign-in</option>
              {credentials.map((credential) => (
                <option key={credential.id} value={credential.target}>
                  {credential.target} — {credential.username}
                </option>
              ))}
            </select>
          </label>
          {error ? (
            <p
              className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800"
              role="alert"
            >
              {error}
            </p>
          ) : null}
        </div>
        <footer className="flex justify-end gap-2 border-t border-zinc-300 bg-white px-5 py-3">
          <Button onClick={onCancel} type="button" variant="light">
            Cancel
          </Button>
          <Button type="submit">Finish</Button>
        </footer>
      </form>
    </div>
  );
}
