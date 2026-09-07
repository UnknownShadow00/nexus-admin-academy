'use client';

import {
  TOOL_CATALOG,
  TOOL_CATEGORIES,
  getToolBySlug,
  type ToolSlug,
  type TicketCategory,
  type SuggestedToolSlug,
} from '@service-desk/shared';
import React, { useId, useRef, useState } from 'react';
import {
  suggestedToolSearchParams,
  type ToolSelectionHandler,
} from './SuggestedTools';
import { TOOL_ICONS } from './tool-icons';

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
  const [open, setOpen] = useState(false);
  const [recent, setRecent] = useState<ToolSlug[]>([]);
  const trigger = useRef<HTMLButtonElement>(null);
  const catalogId = useId();
  const visible = [
    ...new Set([
      ...(activeToolSlug && getToolBySlug(activeToolSlug)
        ? [activeToolSlug as ToolSlug]
        : []),
      ...recent,
      ...(experienceMode === 'guided' ? toolSlugs : []),
    ]),
  ].slice(0, 4);
  const select = (slug: ToolSlug) => {
    setRecent((previous) =>
      [slug, ...previous.filter((item) => item !== slug)].slice(0, 4),
    );
    setOpen(false);
    onSelectTool(
      slug,
      suggestedToolSearchParams(slug, ticketCategory, ticketId),
    );
    trigger.current?.focus();
  };
  const toolButton = (slug: ToolSlug) => {
    const tool = getToolBySlug(slug)!;
    const Icon = TOOL_ICONS[slug];
    return (
      <button
        aria-pressed={activeToolSlug === slug}
        className="sd-focus-ring flex min-h-11 min-w-0 items-center gap-2 rounded-sm px-3 py-2 text-left text-sm font-semibold text-text hover:bg-surface-muted aria-pressed:bg-surface-muted aria-pressed:underline"
        key={slug}
        onClick={() => select(slug)}
        type="button"
      >
        <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-text-muted" />
        {tool.menuLabel}
      </button>
    );
  };
  return (
    <section
      aria-label="Tool switcher"
      className="min-w-0 border-b border-border pb-3"
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          event.preventDefault();
          setOpen(false);
          trigger.current?.focus();
        }
      }}
    >
      <div className="flex flex-wrap items-center gap-1">
        <nav
          aria-label={
            experienceMode === 'guided' ? 'Suggested tools' : 'Recent tools'
          }
          className="flex min-w-0 flex-wrap gap-1"
        >
          {visible.map(toolButton)}
        </nav>
        <button
          aria-controls={catalogId}
          aria-expanded={open}
          className="sd-focus-ring min-h-11 rounded-sm border border-border px-3 py-2 text-sm font-semibold text-text hover:bg-surface-muted"
          onClick={() => setOpen((value) => !value)}
          ref={trigger}
          type="button"
        >
          All tools
        </button>
      </div>
      <nav
        aria-label="Workspace tools"
        className={`${open ? 'grid' : 'hidden'} mt-3 gap-3 rounded-sm bg-surface-raised p-3 sm:grid-cols-2`}
        hidden={!open}
        id={catalogId}
      >
        {[...TOOL_CATEGORIES, 'communication'].map((category) => (
          <section key={category}>
            <h3 className="mb-1 px-3 text-xs font-semibold capitalize text-text-muted">
              {category}
            </h3>
            {TOOL_CATALOG.filter(
              (tool) =>
                ('category' in tool ? tool.category : 'communication') ===
                category,
            ).map((tool) => toolButton(tool.slug))}
          </section>
        ))}
      </nav>
    </section>
  );
}
