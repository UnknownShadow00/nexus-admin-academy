'use client';

import { IconSearch } from '@tabler/icons-react';
import { useEffect, useRef, useState } from 'react';

interface SearchResult {
  id: number;
  title?: string;
  command?: string;
}

/** Uses the same authenticated Academy search endpoint and destinations as Phase 1. */
export function AcademySearch() {
  const input = useRef<HTMLInputElement>(null);
  const root = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState('idle');
  const [results, setResults] = useState<{
    lessons: SearchResult[];
    commands: SearchResult[];
  }>({ lessons: [], commands: [] });
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        input.current?.focus();
        setOpen(true);
      }
      if (event.key === 'Escape') setOpen(false);
    }
    function outside(event: PointerEvent) {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('keydown', key);
    document.addEventListener('pointerdown', outside);
    return () => {
      document.removeEventListener('keydown', key);
      document.removeEventListener('pointerdown', outside);
    };
  }, []);
  useEffect(() => {
    if (!query.trim()) {
      setStatus('idle');
      return;
    }
    const controller = new AbortController();
    setStatus('loading');
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `/api/search/global?q=${encodeURIComponent(query.trim())}`,
          {
            credentials: 'same-origin',
            cache: 'no-store',
            signal: controller.signal,
          },
        );
        if (!response.ok) throw Error('Search unavailable');
        const json = await response.json();
        const valid = (items: unknown): SearchResult[] =>
          Array.isArray(items)
            ? items.filter(
                (item) =>
                  Number.isInteger(item?.id) &&
                  (typeof item?.title === 'string' ||
                    typeof item?.command === 'string'),
              )
            : [];
        if (!controller.signal.aborted) {
          setResults({
            lessons: valid(json.data?.lessons),
            commands: valid(json.data?.commands),
          });
          setStatus('ready');
        }
      } catch {
        if (!controller.signal.aborted) setStatus('error');
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);
  return (
    <div className="sd-academy-search-wrap" ref={root}>
      <label className="sd-academy-search">
        <IconSearch size={20} aria-hidden="true" />
        <input
          ref={input}
          type="search"
          aria-label="Search lessons or commands"
          placeholder="Search lessons or commands…"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
        />
        <kbd>Ctrl K</kbd>
      </label>
      {open && query.trim() ? (
        <div
          className="sd-academy-search-results"
          role="region"
          aria-label="Search results"
        >
          {status === 'loading' ? (
            <p role="status">Searching…</p>
          ) : status === 'error' ? (
            <p role="alert">Search is unavailable. Try again shortly.</p>
          ) : (
            <>
              {results.lessons.map((result) => (
                <a href={`/lessons/${result.id}`} key={result.id}>
                  {result.title}
                </a>
              ))}
              {results.commands.map((result) => (
                <a href="/commands" key={result.id}>
                  {result.command}
                </a>
              ))}
              {!results.lessons.length && !results.commands.length ? (
                <p>No matches found.</p>
              ) : null}
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
