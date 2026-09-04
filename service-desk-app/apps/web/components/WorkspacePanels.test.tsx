import { renderToStaticMarkup } from 'react-dom/server';
import React from 'react';
import { describe, expect, it } from 'vitest';

import { EvidencePanel } from './EvidencePanel';
import { HintPanel } from './HintPanel';
import { ResolutionNotePanel } from './ResolutionNotePanel';
import type { NexusWorkspaceView } from '../lib/nexus-service-desk-client';

const workspaceView: NexusWorkspaceView = {
  documentation_target: 'remote_desktop',
  escalation: null,
  evidence: [{ id: 'ip-checked', label: 'IP configuration checked' }],
  stages: [
    { key: 'understand', status: 'complete' },
    { key: 'investigate', needs_more_evidence: true, status: 'current' },
  ],
};

describe('workspace panels', () => {
  it('renders only server-confirmed evidence with no mutation control', () => {
    const markup = renderToStaticMarkup(
      <EvidencePanel workspaceView={workspaceView} />,
    );
    expect(markup).toContain('IP configuration checked');
    expect(markup).toContain('Confirmed');
    expect(markup).toContain('Investigation still needs more evidence.');
    expect(markup).not.toContain('<button');
    expect(markup).not.toContain('<textarea');
  });

  it('keeps authored hints collapsed until an explicit click', () => {
    const markup = renderToStaticMarkup(
      <HintPanel
        experienceMode="guided"
        hints={['First authored hint', 'Second authored hint']}
        onReveal={() => {}}
      />,
    );
    expect(markup).toContain('Open hints');
    expect(markup).not.toContain('First authored hint');
    expect(markup).not.toContain('Second authored hint');
  });

  it('disables assessment hints and removes note prompts', () => {
    const hintMarkup = renderToStaticMarkup(
      <HintPanel
        experienceMode="assessment"
        hints={['Hidden answer']}
        onReveal={() => {}}
      />,
    );
    expect(hintMarkup).toContain(
      'Hints are not available during an assessment.',
    );
    expect(hintMarkup).not.toContain('Hidden answer');

    const noteMarkup = renderToStaticMarkup(
      <ResolutionNotePanel
        experienceMode="assessment"
        notes={[]}
        onSubmit={() => {}}
      />,
    );
    expect(noteMarkup).toContain('placeholder="Write an internal note…"');
    expect(noteMarkup).not.toContain('What did the requester report');
  });
});
