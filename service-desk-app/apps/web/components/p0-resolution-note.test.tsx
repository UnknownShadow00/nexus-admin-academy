/** @vitest-environment jsdom */

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ResolutionNotePanel } from './ResolutionNotePanel';

const NOTE = 'Restarted computer and issue resolved.';

let container: HTMLDivElement;
let root: Root;

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
});

async function submitRejectedNote(onSubmit: (body: string) => void) {
  await act(async () => {
    root.render(
      <ResolutionNotePanel
        experienceMode="guided"
        notes={[]}
        onSubmit={onSubmit}
      />,
    );
  });
  const textarea = container.querySelector('textarea');
  const form = container.querySelector('form');
  if (!textarea || !form) throw new Error('Resolution Note form is required');

  await act(async () => {
    const valueSetter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype,
      'value',
    )?.set;
    valueSetter?.call(textarea, NOTE);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await act(async () => {
    form.dispatchEvent(
      new SubmitEvent('submit', { bubbles: true, cancelable: true }),
    );
  });
  return textarea;
}

describe('P0 Finding D — rejected Resolution Note feedback', () => {
  it("records today's silent-disappearance baseline", async () => {
    const onSubmit = vi.fn();
    const textarea = await submitRejectedNote(onSubmit);

    expect(onSubmit).toHaveBeenCalledWith(NOTE);
    expect(textarea.value).toBe('');
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it.fails(
    'preserves the note and renders feedback when submission is rejected (fixed in Wave 6)',
    async () => {
      const textarea = await submitRejectedNote(() => {
        // The parent/engine rejects the note; the panel has no result channel.
      });

      expect(textarea.value).toBe(NOTE);
      expect(container.querySelector('[role="alert"]')).not.toBeNull();
    },
  );
});
