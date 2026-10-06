import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  captureV2LaunchContextForTicket,
  launchContextAppliesToCurrentTicket,
  workspaceHref,
} from './workspace-navigation';

const launch =
  'returnTo=%2Flearning-v2%2Fmodules%2Fip&v2ModuleKey=module.ip&v2AssessmentKey=assess.ip&tool=directory&ticket=INC2504';

afterEach(() => vi.unstubAllGlobals());

describe('Service Desk workspace navigation', () => {
  it('keeps launch context tied to the original ticket across queue and ticket switches', () => {
    const queue = workspaceHref('/', launch, 'INC2504');
    const other = workspaceHref(
      '/tickets/INC2501',
      new URL(queue, 'http://local').search,
    );
    const original = workspaceHref(
      '/tickets/INC2504',
      new URL(other, 'http://local').search,
      'INC2501',
    );
    const otherUrl = new URL(other, 'http://local');
    const originalUrl = new URL(original, 'http://local');

    expect(otherUrl.searchParams.get('v2LaunchTicket')).toBe('INC2504');
    expect(otherUrl.searchParams.get('v2ModuleKey')).toBe('module.ip');
    expect(otherUrl.searchParams.get('tool')).toBeNull();
    expect(otherUrl.searchParams.get('ticket')).toBeNull();
    expect(
      launchContextAppliesToCurrentTicket(otherUrl.pathname, otherUrl.search),
    ).toBe(false);
    expect(
      launchContextAppliesToCurrentTicket(
        originalUrl.pathname,
        originalUrl.search,
      ),
    ).toBe(true);
    expect(
      launchContextAppliesToCurrentTicket(
        `/service-desk${originalUrl.pathname}`,
        originalUrl.search,
      ),
    ).toBe(true);
    expect(originalUrl.searchParams.get('returnTo')).toBe(
      '/learning-v2/modules/ip',
    );
  });

  it('leaves ordinary ticket routes clean', () => {
    expect(workspaceHref('/tickets/INC2501', '')).toBe('/tickets/INC2501');
  });

  it('captures V2 context only for the action ticket before a switch', () => {
    const location = {
      pathname: '/service-desk/tickets/INC2504',
      search: `?${launch}&v2LaunchTicket=INC2504`,
    };
    vi.stubGlobal('window', { location });

    expect(captureV2LaunchContextForTicket('INC2504')).toEqual({
      moduleKey: 'module.ip',
      assessmentKey: 'assess.ip',
    });
    expect(captureV2LaunchContextForTicket('INC2501')).toBeNull();

    location.pathname = '/service-desk/tickets/INC2501';
    expect(captureV2LaunchContextForTicket('INC2504')).toBeNull();
    expect(captureV2LaunchContextForTicket('INC2501')).toBeNull();
  });
});
