import { renderToStaticMarkup } from 'react-dom/server';
import React from 'react';
import { describe, expect, it } from 'vitest';

import { WorkflowRail } from './WorkflowRail';
import type { NexusWorkflowStage } from '../lib/nexus-service-desk-client';

const stages: NexusWorkflowStage[] = [
  { key: 'understand', status: 'complete' },
  { key: 'investigate', status: 'complete' },
  { key: 'diagnose', status: 'current' },
  { key: 'fix', mode: 'fix', status: 'not_started' },
  { key: 'verify', status: 'not_started' },
  { key: 'document', status: 'not_started' },
];

describe('WorkflowRail', () => {
  it('renders authoritative stages with text statuses and current semantics', () => {
    const markup = renderToStaticMarkup(
      <WorkflowRail experienceMode="guided" stages={stages} />,
    );
    expect(markup.match(/<li/g)).toHaveLength(6);
    expect(markup.match(/Completed/g)).toHaveLength(3);
    expect(markup).toContain('aria-current="step"');
    expect(markup).toContain('Fix / Escalate');
    expect(markup).toContain(
      'Read what the user reports and what work is affected.',
    );
  });

  it('never hints that escalation is the expected outcome', () => {
    const markup = renderToStaticMarkup(
      <WorkflowRail experienceMode="guided" stages={stages} />,
    );
    // The dead `mode === 'escalate'` branch is gone: the Fix stage always shows
    // the same neutral copy, so the rail cannot pre-announce the answer.
    expect(markup).toContain(
      'Make a safe change, or send the ticket to the right team.',
    );
    expect(markup).not.toContain('not yours to fix directly');
  });

  it('strips explanations in assessment mode', () => {
    const markup = renderToStaticMarkup(
      <WorkflowRail experienceMode="assessment" stages={stages} />,
    );
    expect(markup).toContain('Understand');
    expect(markup).not.toContain(
      'Read what the user reports and what work is affected.',
    );
  });
});
