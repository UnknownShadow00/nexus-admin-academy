'use client';

import {
  TOOL_CATEGORIES,
  getToolsByCategory,
  type ToolCategory,
} from '@service-desk/shared';
import { IconChevronRight, IconTool } from '@tabler/icons-react';
import { Modal, Button } from '@service-desk/ui';
import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { TOOL_ICONS } from './tool-icons';

const CATEGORY_LABELS: Record<ToolCategory, string> = {
  infrastructure: 'Infrastructure',
  knowledge: 'Knowledge',
  management: 'Management',
};

interface ToolsPanelProps {
  activePath: string;
}

export function ToolsPanel({ activePath }: ToolsPanelProps) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeToolSlug = searchParams.get('tool');

  function setActiveTool(slug: string) {
    const ticketMatch = activePath.match(/^\/tickets\/(INC\d+)$/i);
    if (!ticketMatch) {
      router.push(`/tools/${slug}`);
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set('tool', slug);
    params.set('ticket', ticketMatch[1]!.toUpperCase());
    router.push(`${activePath}?${params.toString()}`);
  }

  return (
    <Modal
      className="h-[100dvh] max-h-none w-screen max-w-none rounded-none border-0 sm:h-auto sm:max-h-[85vh] sm:w-[calc(100%-2rem)] sm:max-w-2xl sm:rounded-md sm:border"
      closeLabel="Close"
      description="Choose a support workspace."
      onOpenChange={setOpen}
      open={open}
      title="Tools"
      trigger={
        <Button
          aria-current={activePath.startsWith('/tools/') ? 'page' : undefined}
          aria-label="Open Tools"
          className="px-2.5 text-xs sm:px-3"
          variant="ghost"
        >
          <IconTool aria-hidden="true" className="h-4 w-4" />
          Tools
        </Button>
      }
    >
      <nav aria-label="Available tools" className="divide-y divide-border">
        {TOOL_CATEGORIES.map((category) => (
          <section className="py-4 first:pt-0 last:pb-0" key={category}>
            <h2 className="font-label text-xs font-extrabold uppercase tracking-widest text-accent">
              {CATEGORY_LABELS[category]}
            </h2>
            <div className="mt-2 grid gap-1 sm:grid-cols-2">
              {getToolsByCategory(category).map((tool) => {
                const ToolIcon = TOOL_ICONS[tool.slug];
                const active =
                  activeToolSlug === tool.slug || activePath === tool.path;

                return (
                  <button
                    aria-current={active ? 'page' : undefined}
                    className="sd-focus-ring group flex min-w-0 items-center gap-3 rounded-md px-3 py-3 text-left transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus aria-[current=page]:bg-accent/10"
                    key={tool.path}
                    onClick={() => {
                      setOpen(false);
                      setActiveTool(tool.slug);
                    }}
                    type="button"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-border bg-surface text-accent">
                      <ToolIcon aria-hidden="true" className="h-5 w-5" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-bold text-text">
                        {tool.menuLabel}
                      </span>
                      <span className="mt-0.5 block text-xs leading-snug text-text-muted">
                        {tool.description}
                      </span>
                    </span>
                    <IconChevronRight
                      aria-hidden="true"
                      className="h-4 w-4 shrink-0 text-text-muted transition-colors group-hover:text-accent"
                    />
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </nav>
    </Modal>
  );
}
