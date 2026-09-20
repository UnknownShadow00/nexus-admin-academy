import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  SLOANE_RIVERA_DIRECTORY_USER_ID,
  TicketCategory,
  TOOL_CATALOG,
  getToolBySlug,
  type SuggestedToolSlug,
  type ToolSlug,
} from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import { IconChevronRight, IconTool } from '@tabler/icons-react';
import React from 'react';

import { TOOL_ICONS } from './tool-icons';

const DOCUMENTATION_CATEGORY_BY_TICKET_CATEGORY: Readonly<
  Record<TicketCategory, string>
> = {
  [TicketCategory.Access]: 'credentials-access',
  [TicketCategory.Hardware]: 'hardware-assets',
  [TicketCategory.Network]: 'network-connectivity',
  [TicketCategory.Software]: 'software-licensing',
};

const CHAT_CONTACT_BY_TICKET_ID: Readonly<Record<string, string>> = {
  INC2401: AVERY_BROOKS_DIRECTORY_USER_ID,
  INC2405: SLOANE_RIVERA_DIRECTORY_USER_ID,
  INC2406: 'directory-user-harper-kim',
  INC2511: 'directory-user-taylor-morgan',
  INC2512: 'directory-user-jordan-lee',
  INC2513: 'directory-user-camille-reyes',
  INC3001: 'directory-user-morgan-ellis',
  INC3002: 'directory-user-hr-adebayo-coker',
};

export type ToolSelectionHandler = (
  slug: ToolSlug,
  queryHints?: URLSearchParams,
) => void;

export function suggestedToolSearchParams(
  slug: ToolSlug,
  ticketCategory: TicketCategory,
  ticketId: string,
): URLSearchParams {
  const params = new URLSearchParams();

  if (slug === 'documentation') {
    params.set(
      'category',
      DOCUMENTATION_CATEGORY_BY_TICKET_CATEGORY[ticketCategory],
    );
  }

  if (slug === 'company-chat' && CHAT_CONTACT_BY_TICKET_ID[ticketId]) {
    params.set('contact', CHAT_CONTACT_BY_TICKET_ID[ticketId]);
  }

  params.set('ticket', ticketId);
  return params;
}

export function SuggestedTools({
  experienceMode,
  onSelectTool,
  ticketCategory,
  ticketId,
  toolSlugs,
}: {
  experienceMode: 'guided' | 'practice' | 'assessment';
  onSelectTool: ToolSelectionHandler;
  ticketCategory: TicketCategory;
  ticketId: string;
  toolSlugs: readonly SuggestedToolSlug[];
}) {
  const tools =
    experienceMode === 'guided'
      ? toolSlugs
          .map((slug) => getToolBySlug(slug))
          .filter((tool) => tool !== undefined)
      : TOOL_CATALOG;

  return (
    <Card>
      <CardHeader
        meta={experienceMode === 'guided' ? 'Ticket context' : 'Standard suite'}
        title={
          <span className="flex items-center gap-2">
            <IconTool aria-hidden="true" className="h-5 w-5 text-accent" />
            {experienceMode === 'guided'
              ? 'Recommended places to start'
              : 'Available technician tools'}
          </span>
        }
      />
      <nav aria-label="Suggested tools" className="divide-y divide-border">
        {tools.map((tool) => {
          const ToolIcon = TOOL_ICONS[tool.slug];

          return (
            <button
              className="sd-focus-ring group flex min-w-0 items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus"
              key={tool.slug}
              onClick={() =>
                onSelectTool(
                  tool.slug,
                  suggestedToolSearchParams(
                    tool.slug,
                    ticketCategory,
                    ticketId,
                  ),
                )
              }
              type="button"
            >
              <ToolIcon
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-accent"
              />
              <span className="min-w-0 flex-1 text-sm font-semibold text-text">
                {tool.menuLabel}
              </span>
              <IconChevronRight
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-text-muted group-hover:text-accent"
              />
            </button>
          );
        })}
      </nav>
    </Card>
  );
}
