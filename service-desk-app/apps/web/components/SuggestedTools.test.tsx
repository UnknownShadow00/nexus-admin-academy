import { TicketCategory } from '@service-desk/shared';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { SuggestedTools, suggestedToolSearchParams } from './SuggestedTools';

describe('SuggestedTools ticket context', () => {
  it('renders buttons instead of navigation links', () => {
    const markup = renderToStaticMarkup(
      <SuggestedTools
        experienceMode="guided"
        onSelectTool={vi.fn()}
        ticketCategory={TicketCategory.Network}
        ticketId="INC2510"
        toolSlugs={['remote-desktop', 'documentation']}
      />,
    );

    expect(markup).toContain('<button');
    expect(markup).not.toContain('<a');
    expect(markup).not.toContain('/tools/');
  });

  it('keeps the actual ticket id and tool-specific query hints', () => {
    expect(
      suggestedToolSearchParams(
        'documentation',
        TicketCategory.Network,
        'INC2510',
      ).toString(),
    ).toBe('category=network-connectivity&ticket=INC2510');
    expect(
      suggestedToolSearchParams(
        'company-chat',
        TicketCategory.Access,
        'INC2401',
      ).toString(),
    ).toBe('contact=directory-user-avery-brooks&ticket=INC2401');
  });
});
