import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { getToolBySlug } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { toolContextMatchesTicket } from './ActiveToolPane';
import { EscalationForm } from './EscalateDialog';
import { EvidencePanel } from './EvidencePanel';
import { HintPanel } from './HintPanel';
import { ResolutionNotePanel } from './ResolutionNotePanel';
import { CloseReviewNotice, DocumentationSummary } from './ResolveDialog';
import { ticketFromSearch } from './RemoteDesktopTool';
import { WorkflowRail } from './WorkflowRail';
import type { NexusWorkspaceView } from '../lib/nexus-service-desk-client';

/**
 * A theme-locked colour is any raw Tailwind palette utility. They cannot follow
 * `data-theme`, so one of them inside a student surface is a dark island in
 * light mode (and a light island in dark mode).
 */
const RAW_PALETTE =
  /\b(?:bg|text|border|ring|divide|from|to|via|accent|placeholder:text|hover:bg|hover:text)-(?:zinc|slate|gray|neutral|stone|sky|blue|emerald|green|amber|yellow|orange|red|rose)-\d{2,3}\b/g;

const workspaceView: NexusWorkspaceView = {
  documentation_target: 'remote_desktop',
  escalation: { available: true },
  evidence: [{ id: 'ip-configuration-checked', label: 'IP configuration checked' }],
  stages: [
    { key: 'understand', status: 'complete' },
    { key: 'investigate', needs_more_evidence: true, status: 'current' },
    { key: 'diagnose', status: 'not_started' },
    { key: 'fix', mode: 'fix', status: 'not_started' },
    { key: 'verify', status: 'not_started' },
    { key: 'document', status: 'not_started' },
  ],
};

const SURFACES: Array<[string, React.ReactElement]> = [
  [
    'workflow rail',
    <WorkflowRail experienceMode="guided" stages={workspaceView.stages} />,
  ],
  ['evidence panel', <EvidencePanel workspaceView={workspaceView} />],
  [
    'hint panel',
    <HintPanel
      experienceMode="guided"
      hints={['An authored hint']}
      onReveal={() => {}}
    />,
  ],
  [
    'resolution notes',
    <ResolutionNotePanel
      experienceMode="guided"
      notes={[]}
      onSubmit={() => ({ success: true })}
    />,
  ],
  ['resolve documentation', <DocumentationSummary note="A closure note." />],
  [
    'resolve review',
    <CloseReviewNotice review={{ kind: 'ready', message: 'All good.' }} />,
  ],
  [
    'escalate form',
    <EscalationForm
      context=""
      onContextChange={() => {}}
      onReasonChange={() => {}}
      onRouteTeamChange={() => {}}
      reason=""
      ready
      routeTeam=""
    />,
  ],
];

describe('light mode covers the core student surfaces', () => {
  it.each(SURFACES)('%s paints only with theme tokens', (_name, element) => {
    const markup = renderToStaticMarkup(element);
    expect(markup.match(RAW_PALETTE) ?? []).toEqual([]);
  });
});

/**
 * The queue, the workspace chrome and the embedded tool bodies cannot be
 * rendered without a provider here, so they are guarded at the source level.
 */
const SOURCE_GUARDED = [
  'ApplicationShell.tsx',
  'Header.tsx',
  'Footer.tsx',
  'NavCluster.tsx',
  'TicketQueue.tsx',
  'TicketQueueSection.tsx',
  'TicketQueueFilters.tsx',
  'TicketRow.tsx',
  'DashboardQueueCard.tsx',
  'DashboardStats.tsx',
  'TicketWorkspace.tsx',
  'TicketContextBar.tsx',
  'TicketIssueDetails.tsx',
  'RequesterCard.tsx',
  'RelatedDevicePanel.tsx',
  'ActivityTimeline.tsx',
  'TicketActionBar.tsx',
  'WorkspaceToolLauncher.tsx',
  'ToolsPanel.tsx',
  'ActiveToolPane.tsx',
  'OutcomeBar.tsx',
  'TicketDebrief.tsx',
  'DirectoryTool.tsx',
  'CompanyChatTool.tsx',
  'DocumentationTool.tsx',
  'AssetManagementTool.tsx',
];

describe('core student files hold no theme-locked colours', () => {
  it.each(SOURCE_GUARDED)('%s', (file) => {
    const source = readFileSync(join(process.cwd(), 'components', file), 'utf8');
    expect(source.match(RAW_PALETTE) ?? []).toEqual([]);
  });
});

describe('embedded tool context survives a reload', () => {
  it('restores the requested tool and keeps the ticket id', () => {
    const search = new URLSearchParams('tool=remote-desktop&ticket=INC2405');
    expect(getToolBySlug(search.get('tool') ?? '')?.slug).toBe(
      'remote-desktop',
    );
    expect(ticketFromSearch(`?${search.toString()}`)).toBe('INC2405');
    expect(toolContextMatchesTicket(search, 'INC2405')).toBe(true);
  });

  it('never lets another ticket claim the reloaded tool pane', () => {
    const search = new URLSearchParams('tool=remote-desktop&ticket=INC2405');
    expect(toolContextMatchesTicket(search, 'INC2402')).toBe(false);
    expect(ticketFromSearch('?tool=remote-desktop&ticket=UNKNOWN')).toBeNull();
  });

  it('ignores an unknown tool slug rather than guessing one', () => {
    expect(getToolBySlug('not-a-tool')).toBeUndefined();
  });
});
