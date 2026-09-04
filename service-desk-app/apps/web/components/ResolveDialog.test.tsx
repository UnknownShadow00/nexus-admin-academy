import type { ActionEvent } from '@service-desk/simulation-engine';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ResolutionNotePanel } from './ResolutionNotePanel';
import {
  CloseReviewNotice,
  DocumentationSummary,
  closeRejectionMessage,
} from './ResolveDialog';

describe('ResolveDialog close feedback', () => {
  it('surfaces the exact trusted workflow rejection in the open dialog', () => {
    const event = { success: false, rejectReason: 'Verify the fix before closing.' } as ActionEvent;
    expect(closeRejectionMessage(event)).toBe('Verify the fix before closing.');
  });
});

describe('one editable documentation surface', () => {
  it('summarizes the workspace note instead of offering a second input', () => {
    const markup = renderToStaticMarkup(
      <DocumentationSummary note="Cleared the cached profile and the user signed in." />,
    );
    expect(markup).toContain('Documentation recorded');
    expect(markup).toContain('Cleared the cached profile');
    // Fix 5: Resolve can never create an ungraded duplicate note.
    expect(markup).not.toContain('<textarea');
    expect(markup).not.toContain('<input');
  });

  it('points a student with no note back to the graded notes panel', () => {
    const markup = renderToStaticMarkup(<DocumentationSummary note="   " />);
    expect(markup).toContain('Documentation required');
    expect(markup).toContain('Notes written there are the ones Nexus grades.');
    expect(markup).not.toContain('<textarea');
  });

  it('keeps exactly one editable note input across the workspace surfaces', () => {
    const panel = renderToStaticMarkup(
      <ResolutionNotePanel
        experienceMode="guided"
        notes={[]}
        onSubmit={() => {}}
      />,
    );
    const resolve = renderToStaticMarkup(
      <DocumentationSummary note="Existing note body." />,
    );
    const editable = [
      ...(panel.match(/<textarea/g) ?? []),
      ...(resolve.match(/<textarea/g) ?? []),
    ];
    expect(editable).toHaveLength(1);
  });
});

describe('close review never previews a score', () => {
  it('uses neutral server-authoritative copy for a ready close', () => {
    const markup = renderToStaticMarkup(
      <CloseReviewNotice
        review={{ kind: 'ready', message: 'Everything checks out.' }}
      />,
    );
    expect(markup).toContain('Ready to resolve');
    expect(markup).toContain(
      'Nexus will check your investigation, diagnosis, action, verification, and documentation after you submit.',
    );
    // Fix 6: no client-side points/pass prediction that the server may reject.
    expect(markup).not.toMatch(/\d+\s*(of|points)/);
    expect(markup).not.toContain('awards');
    expect(markup).not.toContain('deducts');
  });

  it('warns about an unresolved close without predicting a penalty total', () => {
    const markup = renderToStaticMarkup(
      <CloseReviewNotice
        review={{
          kind: 'unresolved-warning',
          message: 'You have not verified the outcome.',
        }}
      />,
    );
    expect(markup).toContain('Unresolved close warning');
    expect(markup).not.toMatch(/\d+\s*(of|points)/);
    expect(markup).not.toContain('deducts');
  });
});
