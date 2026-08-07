'use client';

import {
  DOCUMENTATION_ARTICLE_FIXTURES,
  DOCUMENTATION_CATEGORY_FIXTURES,
} from '@service-desk/shared';
import { Badge, Button, Input, PanelFrame } from '@service-desk/ui';
import {
  IconArrowLeft,
  IconBooks,
  IconChevronLeft,
  IconSearch,
} from '@tabler/icons-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { DocumentationArticleDetail } from './DocumentationArticleDetail';
import { DocumentationArticleList } from './DocumentationArticleList';
import { DocumentationCategoryGrid } from './DocumentationCategoryGrid';

export function DocumentationTool() {
  const searchParams = useSearchParams();
  const categoryParam = searchParams.get('category');
  const articleParam = searchParams.get('article');
  const [query, setQuery] = useState('');
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(
    null,
  );
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    if (
      articleParam &&
      DOCUMENTATION_ARTICLE_FIXTURES.some(
        (article) => article.id === articleParam,
      )
    ) {
      setQuery('');
      setSelectedCategoryId(null);
      setSelectedArticleId(articleParam);
      return;
    }
    if (
      categoryParam &&
      DOCUMENTATION_CATEGORY_FIXTURES.some(
        (category) => category.id === categoryParam,
      )
    ) {
      setSelectedArticleId(null);
      setSelectedCategoryId(categoryParam);
    }
  }, [articleParam, categoryParam]);

  const normalizedQuery = query.trim().toLowerCase();
  const searchResults = useMemo(
    () =>
      normalizedQuery
        ? DOCUMENTATION_ARTICLE_FIXTURES.filter((article) =>
            [article.title, article.category, ...article.body]
              .join(' ')
              .toLowerCase()
              .includes(normalizedQuery),
          )
        : [],
    [normalizedQuery],
  );
  const selectedCategory =
    DOCUMENTATION_CATEGORY_FIXTURES.find(
      (category) => category.id === selectedCategoryId,
    ) ?? null;
  const selectedArticle =
    DOCUMENTATION_ARTICLE_FIXTURES.find(
      (article) => article.id === selectedArticleId,
    ) ?? null;
  const articleCategory = selectedArticle
    ? (DOCUMENTATION_CATEGORY_FIXTURES.find(
        (category) => category.name === selectedArticle.category,
      ) ?? null)
    : null;

  function showAllCategories() {
    setQuery('');
    setSelectedArticleId(null);
    setSelectedCategoryId(null);
  }

  function showArticleCategory() {
    setQuery('');
    setSelectedArticleId(null);
    setSelectedCategoryId(articleCategory?.id ?? null);
  }

  return (
    <PanelFrame
      aria-labelledby="documentation-title"
      className="mx-auto w-full max-w-7xl p-0"
      variant="contained"
    >
      <header className="border-b border-zinc-700 px-4 py-4 sm:px-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Link
            className="sd-back-button sd-focus-ring inline-flex min-h-10 items-center gap-2 self-start rounded-sm px-2 text-sm font-extrabold uppercase text-sky-400 hover:bg-zinc-800 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            href="/"
          >
            <IconArrowLeft aria-hidden="true" className="h-4 w-4" />
            Dashboard
          </Link>
          <Badge variant="sky">
            {DOCUMENTATION_ARTICLE_FIXTURES.length} articles
          </Badge>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
            <IconBooks aria-hidden="true" className="h-6 w-6" />
          </span>
          <div>
            <p className="font-label text-xs font-extrabold uppercase tracking-widest text-sky-400">
              Service desk reference
            </p>
            <h1
              className="font-display text-2xl font-bold text-zinc-100"
              id="documentation-title"
            >
              Documentation
            </h1>
          </div>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-zinc-400">
          Find concise procedures, service notes, and escalation guidance for
          the practice environment.
        </p>
        <label className="relative mt-4 block max-w-2xl">
          <span className="sr-only">
            Search article titles, bodies, and categories
          </span>
          <IconSearch
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500"
          />
          <Input
            className="pl-9"
            onChange={(event) => {
              setQuery(event.target.value);
              setSelectedArticleId(null);
            }}
            placeholder="Search procedures, services, or symptoms"
            type="search"
            value={query}
          />
        </label>
      </header>

      <div className="p-4 sm:p-5">
        {selectedArticle ? (
          <>
            <nav
              aria-label="Documentation breadcrumb"
              className="mb-4 flex flex-wrap items-center gap-1 text-xs font-semibold uppercase text-zinc-500"
            >
              <button
                className="sd-focus-ring rounded-sm px-2 py-1 text-sky-400 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                onClick={showAllCategories}
                type="button"
              >
                All categories
              </button>
              <span aria-hidden="true">/</span>
              <button
                className="sd-focus-ring rounded-sm px-2 py-1 text-sky-400 hover:text-sky-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                onClick={showArticleCategory}
                type="button"
              >
                {selectedArticle.category}
              </button>
              <span aria-hidden="true">/</span>
              <span className="max-w-full truncate px-2 text-zinc-400">
                {selectedArticle.title}
              </span>
            </nav>
            <Button
              className="mb-4 px-3"
              onClick={showArticleCategory}
              variant="ghost"
            >
              <IconChevronLeft aria-hidden="true" className="h-4 w-4" />
              Back to category
            </Button>
            <DocumentationArticleDetail article={selectedArticle} />
          </>
        ) : normalizedQuery ? (
          <DocumentationArticleList
            articles={searchResults}
            heading={`Results for “${query.trim()}”`}
            onSelect={setSelectedArticleId}
          />
        ) : selectedCategory ? (
          <>
            <Button
              className="mb-4 px-3"
              onClick={showAllCategories}
              variant="ghost"
            >
              <IconChevronLeft aria-hidden="true" className="h-4 w-4" />
              All categories
            </Button>
            <DocumentationArticleList
              articles={selectedCategory.articles}
              heading={selectedCategory.name}
              onSelect={setSelectedArticleId}
            />
          </>
        ) : (
          <DocumentationCategoryGrid
            categories={DOCUMENTATION_CATEGORY_FIXTURES}
            onSelect={setSelectedCategoryId}
          />
        )}
      </div>
    </PanelFrame>
  );
}
