'use client';

import type { DocumentationArticle } from '@service-desk/shared';
import { Card } from '@service-desk/ui';
import {
  IconChevronRight,
  IconFileText,
  IconFilterOff,
} from '@tabler/icons-react';

interface DocumentationArticleListProps {
  articles: readonly DocumentationArticle[];
  heading: string;
  onSelect: (articleId: string) => void;
}

export function DocumentationArticleList({
  articles,
  heading,
  onSelect,
}: DocumentationArticleListProps) {
  if (articles.length === 0) {
    return (
      <Card className="flex min-h-64 flex-col items-center justify-center px-5 py-10 text-center">
        <IconFilterOff aria-hidden="true" className="h-9 w-9 text-zinc-600" />
        <h2 className="mt-4 text-base font-bold text-zinc-100">
          No articles match your search
        </h2>
        <p className="mt-2 max-w-md text-sm text-zinc-400">
          Try a broader service, symptom, or procedure term to bring knowledge
          articles back into view.
        </p>
      </Card>
    );
  }

  return (
    <section aria-labelledby="documentation-article-list-title">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
            Knowledge articles
          </p>
          <h2
            className="mt-1 font-display text-xl font-bold text-zinc-100"
            id="documentation-article-list-title"
          >
            {heading}
          </h2>
        </div>
        <span className="text-xs font-semibold uppercase text-zinc-500">
          {articles.length} {articles.length === 1 ? 'result' : 'results'}
        </span>
      </div>
      <Card className="divide-y divide-zinc-800">
        {articles.map((article) => (
          <button
            className="sd-focus-ring group flex w-full items-center gap-3 px-4 py-4 text-left transition-colors hover:bg-zinc-800/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-400"
            key={article.id}
            onClick={() => onSelect(article.id)}
            type="button"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm border border-zinc-700 bg-zinc-950 text-sky-400">
              <IconFileText aria-hidden="true" className="h-4 w-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-bold text-zinc-100">
                {article.title}
              </span>
              <span className="mt-1 block text-xs font-semibold uppercase tracking-wide text-zinc-500">
                {article.category}
              </span>
            </span>
            <IconChevronRight
              aria-hidden="true"
              className="h-5 w-5 shrink-0 text-zinc-600 transition-colors group-hover:text-sky-400"
            />
          </button>
        ))}
      </Card>
    </section>
  );
}
