import {
  AVERY_BROOKS_DIRECTORY_USER_ID,
  SLOANE_RIVERA_DIRECTORY_USER_ID,
  TicketCategory,
  getToolBySlug,
  type SuggestedToolSlug,
  type ToolDefinition,
} from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import { IconChevronRight, IconTool } from '@tabler/icons-react';
import Link from 'next/link';

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
};

function suggestedToolHref(
  tool: ToolDefinition,
  ticketCategory: TicketCategory,
  ticketId: string,
) {
  if (tool.slug === 'documentation') {
    return `${tool.path}?category=${DOCUMENTATION_CATEGORY_BY_TICKET_CATEGORY[ticketCategory]}`;
  }

  if (tool.slug === 'company-chat' && CHAT_CONTACT_BY_TICKET_ID[ticketId]) {
    return `${tool.path}?contact=${CHAT_CONTACT_BY_TICKET_ID[ticketId]}`;
  }

  return tool.path;
}

export function SuggestedTools({
  ticketCategory,
  ticketId,
  toolSlugs,
}: {
  ticketCategory: TicketCategory;
  ticketId: string;
  toolSlugs: readonly SuggestedToolSlug[];
}) {
  const tools = toolSlugs
    .map((slug) => getToolBySlug(slug))
    .filter((tool) => tool !== undefined);

  return (
    <Card>
      <CardHeader
        meta="Ticket context"
        title={
          <span className="flex items-center gap-2">
            <IconTool aria-hidden="true" className="h-5 w-5 text-sky-400" />
            Suggested tools
          </span>
        }
      />
      <nav aria-label="Suggested tools" className="divide-y divide-zinc-800">
        {tools.map((tool) => {
          const ToolIcon = TOOL_ICONS[tool.slug];

          return (
            <Link
              className="sd-focus-ring group flex min-w-0 items-center gap-3 px-4 py-3 transition-colors hover:bg-zinc-800/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400"
              href={suggestedToolHref(tool, ticketCategory, ticketId)}
              key={tool.slug}
            >
              <ToolIcon
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-sky-400"
              />
              <span className="min-w-0 flex-1 text-sm font-semibold text-zinc-200">
                {tool.menuLabel}
              </span>
              <IconChevronRight
                aria-hidden="true"
                className="h-4 w-4 shrink-0 text-zinc-600 group-hover:text-sky-400"
              />
            </Link>
          );
        })}
      </nav>
    </Card>
  );
}
