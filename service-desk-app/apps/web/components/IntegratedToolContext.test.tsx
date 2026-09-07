/** @vitest-environment jsdom */
import { TICKET_FIXTURES } from '@service-desk/shared';
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import {
  IntegratedToolContext,
  IntegratedToolLink,
  ToolBackLink,
} from './IntegratedToolContext';

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

describe('integrated tool navigation', () => {
  it('preserves standalone tool links', () => {
    const html = renderToStaticMarkup(
      <IntegratedToolLink href="/tools/documentation">
        Documentation
      </IntegratedToolLink>,
    );
    expect(html).toContain('href="/tools/documentation"');
    expect(renderToStaticMarkup(<ToolBackLink />)).toContain('Dashboard');
  });

  it('uses the existing workspace selection callback and preserves query hints', async () => {
    const onSelectTool = vi.fn();
    const host = document.createElement('div');
    document.body.append(host);
    const root = createRoot(host);
    try {
      await act(async () =>
        root.render(
          <IntegratedToolContext.Provider
            value={{
              ticket: TICKET_FIXTURES[0]!,
              returnDestination: '/learning-v2/modules/example',
              onSelectTool,
            }}
          >
            <IntegratedToolLink href="/tools/company-chat?contact=requester">
              Talk to requester
            </IntegratedToolLink>
            <ToolBackLink />
          </IntegratedToolContext.Provider>,
        ),
      );
      expect(host.querySelectorAll('button')).toHaveLength(1);
      expect(host.querySelector('a')).toBeNull();
      await act(async () => host.querySelector('button')!.click());
      expect(onSelectTool).toHaveBeenCalledTimes(1);
      expect(onSelectTool.mock.calls[0]?.[0]).toBe('company-chat');
      expect(onSelectTool.mock.calls[0]?.[1].get('contact')).toBe('requester');
    } finally {
      await act(async () => root.unmount());
      host.remove();
    }
  });
});
