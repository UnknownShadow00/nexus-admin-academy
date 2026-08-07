'use client';

import type { DocumentationCategory } from '@service-desk/shared';
import { Card } from '@service-desk/ui';
import { IconBooks, IconChevronRight } from '@tabler/icons-react';

interface DocumentationCategoryGridProps {
  categories: readonly DocumentationCategory[];
  onSelect: (categoryId: string) => void;
}

export function DocumentationCategoryGrid({
  categories,
  onSelect,
}: DocumentationCategoryGridProps) {
  return (
    <section aria-labelledby="documentation-categories-title">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
            Browse the library
          </p>
          <h2
            className="mt-1 font-display text-xl font-bold text-zinc-100"
            id="documentation-categories-title"
          >
            All categories
          </h2>
        </div>
        <span className="text-xs font-semibold uppercase text-zinc-500">
          {categories.length} sections
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {categories.map((category) => (
          <Card className="overflow-hidden" key={category.id}>
            <button
              className="sd-focus-ring group flex min-h-32 w-full items-center gap-4 p-4 text-left transition-colors hover:bg-zinc-800/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400"
              onClick={() => onSelect(category.id)}
              type="button"
            >
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
                <IconBooks aria-hidden="true" className="h-5 w-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-extrabold uppercase leading-snug text-zinc-100">
                  {category.name}
                </span>
                <span className="mt-2 block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                  {category.articles.length}{' '}
                  {category.articles.length === 1 ? 'article' : 'articles'}
                </span>
              </span>
              <IconChevronRight
                aria-hidden="true"
                className="h-5 w-5 shrink-0 text-zinc-600 transition-colors group-hover:text-sky-400"
              />
            </button>
          </Card>
        ))}
      </div>
    </section>
  );
}
