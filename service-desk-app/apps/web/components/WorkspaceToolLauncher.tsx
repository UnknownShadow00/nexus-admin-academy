'use client';

import {
  TOOL_CATALOG,
  TOOL_CATEGORIES,
  getToolsByCategory,
  type ToolCategory,
  type ToolSlug,
  type TicketCategory,
  type SuggestedToolSlug,
} from '@service-desk/shared';
import { Card, CardHeader } from '@service-desk/ui';
import { IconChevronRight, IconTool } from '@tabler/icons-react';
import React from 'react';

import { SuggestedTools, type ToolSelectionHandler } from './SuggestedTools';
import { TOOL_ICONS } from './tool-icons';

const CATEGORY_LABELS: Record<ToolCategory, string> = {
  infrastructure: 'Infrastructure',
  knowledge: 'Knowledge',
  management: 'Management',
};

const UNCATEGORIZED_TOOLS = TOOL_CATALOG.filter(
  (tool) => !('category' in tool),
);

function ToolButton({
  active,
  onSelectTool,
  slug,
}: {
  active: boolean;
  onSelectTool: ToolSelectionHandler;
  slug: ToolSlug;
}) {
  const tool = TOOL_CATALOG.find((candidate) => candidate.slug === slug)!;
  const ToolIcon = TOOL_ICONS[tool.slug];

  return (
    <button
      aria-pressed={active}
      className="sd-focus-ring group flex min-w-0 items-center gap-3 rounded-sm px-3 py-3 text-left transition-colors hover:bg-zinc-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 aria-pressed:bg-sky-400/10"
      onClick={() => onSelectTool(tool.slug)}
      type="button"
    >
      <ToolIcon aria-hidden="true" className="h-4 w-4 shrink-0 text-sky-400" />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-bold text-zinc-100">
          {tool.menuLabel}
        </span>
        <span className="mt-0.5 block text-xs leading-snug text-zinc-400">
          {tool.description}
        </span>
      </span>
      <IconChevronRight
        aria-hidden="true"
        className="h-4 w-4 shrink-0 text-zinc-600 group-hover:text-sky-400"
      />
    </button>
  );
}

export function WorkspaceToolLauncher({
  activeToolSlug,
  experienceMode,
  onSelectTool,
  ticketCategory,
  ticketId,
  toolSlugs,
}: {
  activeToolSlug: string | null;
  experienceMode: 'guided' | 'practice' | 'assessment';
  onSelectTool: ToolSelectionHandler;
  ticketCategory: TicketCategory;
  ticketId: string;
  toolSlugs: readonly SuggestedToolSlug[];
}) {
  return (
    <div className="space-y-4">
      {experienceMode === 'guided' ? (
        <SuggestedTools
          experienceMode={experienceMode}
          onSelectTool={onSelectTool}
          ticketCategory={ticketCategory}
          ticketId={ticketId}
          toolSlugs={toolSlugs}
        />
      ) : null}

      <Card>
        <CardHeader
          meta="Full catalog"
          title={
            <span className="flex items-center gap-2">
              <IconTool aria-hidden="true" className="h-5 w-5 text-sky-400" />
              {experienceMode === 'guided' ? 'All tools' : 'Technician tools'}
            </span>
          }
        />
        <nav
          aria-label="Workspace tools"
          className="divide-y divide-zinc-800 p-1"
        >
          {TOOL_CATEGORIES.map((category) => (
            <section className="py-3" key={category}>
              <h3 className="px-3 text-xs font-extrabold uppercase tracking-wide text-zinc-500">
                {CATEGORY_LABELS[category]}
              </h3>
              <div className="mt-1 grid gap-1">
                {getToolsByCategory(category).map((tool) => (
                  <ToolButton
                    active={activeToolSlug === tool.slug}
                    key={tool.slug}
                    onSelectTool={onSelectTool}
                    slug={tool.slug}
                  />
                ))}
              </div>
            </section>
          ))}
          {UNCATEGORIZED_TOOLS.length ? (
            <section className="py-3">
              <h3 className="px-3 text-xs font-extrabold uppercase tracking-wide text-zinc-500">
                Communication
              </h3>
              <div className="mt-1 grid gap-1">
                {UNCATEGORIZED_TOOLS.map((tool) => (
                  <ToolButton
                    active={activeToolSlug === tool.slug}
                    key={tool.slug}
                    onSelectTool={onSelectTool}
                    slug={tool.slug}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </nav>
      </Card>
    </div>
  );
}
