/** @vitest-environment jsdom */

import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ResolutionNotePanel } from './ResolutionNotePanel';

const NOTE = '  Restarted computer and issue resolved.\n  ';

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

async function submitRejectedNote(
  onSubmit: (
    body: string,
  ) => { success: boolean } | Promise<{ success: boolean }>,
) {
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
  it('preserves exact rejected text and shows safe feedback', async () => {
    const onSubmit = vi.fn(() => ({ success: false }));
    const textarea = await submitRejectedNote(onSubmit);
    expect(onSubmit).toHaveBeenCalledWith(NOTE);
    expect(textarea.value).toBe(NOTE);
    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      'what you tested',
    );
  });

  it('clears the editor only after success', async () => {
    const textarea = await submitRejectedNote(() => ({ success: true }));
    expect(textarea.value).toBe('');
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });
  it('preserves the note if asynchronous persistence fails', async () => {
    const textarea = await submitRejectedNote(async () => {
      throw new Error('network');
    });
    expect(textarea.value).toBe(NOTE);
    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      'could not be saved',
    );
  });
});
