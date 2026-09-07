import { TOOL_CATALOG, TicketCategory } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';

import { WorkspaceToolLauncher } from './WorkspaceToolLauncher';

describe('WorkspaceToolLauncher', () => {
  it('puts compact guided suggestions before the collapsed complete catalog', () => {
    const markup = renderToStaticMarkup(
      <WorkspaceToolLauncher
        activeToolSlug={null}
        experienceMode="guided"
        onSelectTool={vi.fn()}
        ticketCategory={TicketCategory.Network}
        ticketId="INC2510"
        toolSlugs={['remote-desktop', 'documentation']}
      />,
    );

    expect(markup.indexOf('Suggested tools')).toBeLessThan(
      markup.indexOf('All tools'),
    );
    for (const tool of TOOL_CATALOG) {
      expect(markup).toContain(tool.menuLabel);
    }
    expect(markup).toContain('aria-expanded="false"');
    expect(markup).toContain('hidden=""');
  });

  it('exposes recent tools without recommendations in assessment mode', () => {
    const markup = renderToStaticMarkup(
      <WorkspaceToolLauncher
        activeToolSlug="directory"
        experienceMode="assessment"
        onSelectTool={vi.fn()}
        ticketCategory={TicketCategory.Access}
        ticketId="INC2511"
        toolSlugs={['directory']}
      />,
    );

    expect(markup).toContain('Recent tools');
    expect(markup).toContain('aria-expanded="false"');
    expect(markup).not.toContain('Suggested tools');
    expect(markup).not.toContain('Recommended places to start');
  });
});
