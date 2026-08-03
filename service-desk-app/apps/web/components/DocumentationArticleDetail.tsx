import type { DocumentationArticle } from '@service-desk/shared';
import { Badge, Card } from '@service-desk/ui';
import { IconFileText } from '@tabler/icons-react';

export function DocumentationArticleDetail({
  article,
}: {
  article: DocumentationArticle;
}) {
  return (
    <article aria-labelledby="documentation-article-title">
      <Card>
        <header className="border-b border-zinc-800 px-5 py-5 sm:px-7 sm:py-6">
          <div className="flex items-start gap-4">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-sm border border-sky-400/30 bg-sky-400/10 text-sky-400">
              <IconFileText aria-hidden="true" className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <Badge variant="sky">{article.category}</Badge>
              <h2
                className="mt-3 font-display text-2xl font-bold leading-tight text-zinc-100"
                id="documentation-article-title"
              >
                {article.title}
              </h2>
            </div>
          </div>
        </header>
        <div className="space-y-4 px-5 py-6 text-sm leading-7 text-zinc-300 sm:px-7">
          {article.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
        <footer className="border-t border-zinc-800 px-5 py-4 text-xs text-zinc-500 sm:px-7">
          Practice reference · Verify current tool state before applying a
          change.
        </footer>
      </Card>
    </article>
  );
}
