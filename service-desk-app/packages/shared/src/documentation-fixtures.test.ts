import { describe, expect, it } from 'vitest';

import {
  DOCUMENTATION_ARTICLE_FIXTURES,
  DOCUMENTATION_CATEGORY_FIXTURES,
} from './documentation-fixtures';

describe('documentation fixtures', () => {
  it('contains the required ten-category, 38-article structure', () => {
    expect(
      DOCUMENTATION_CATEGORY_FIXTURES.map((category) => [
        category.name,
        category.articles.length,
      ]),
    ).toEqual([
      ['Environment Overview', 1],
      ['Email & Mail Server', 4],
      ['Password & Security', 4],
      ['Network & Connectivity', 5],
      ['Server Documentation', 4],
      ['Standard Procedures / SOPs', 4],
      ['Software & Licensing', 3],
      ['Hardware & Assets', 5],
      ['Contacts & Escalation', 4],
      ['Credentials & Access', 4],
    ]);
    expect(DOCUMENTATION_ARTICLE_FIXTURES).toHaveLength(38);
  });

  it('gives every article a unique id and two to four useful paragraphs', () => {
    const ids = DOCUMENTATION_ARTICLE_FIXTURES.map((article) => article.id);

    expect(new Set(ids).size).toBe(ids.length);
    for (const article of DOCUMENTATION_ARTICLE_FIXTURES) {
      expect(article.body.length).toBeGreaterThanOrEqual(2);
      expect(article.body.length).toBeLessThanOrEqual(4);
      expect(article.body.every((paragraph) => paragraph.length > 40)).toBe(
        true,
      );
    }
  });
});
