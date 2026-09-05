import { afterEach, describe, expect, it, vi } from 'vitest';

import { EXPECTED_NEXUS_SERVICE_DESK_CONTRACT } from '../../../lib/service-desk-contract';
import { GET } from './route';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe('Service Desk health metadata', () => {
  it('publishes its canonical non-sensitive contract version', async () => {
    delete process.env.NEXUS_ADMIN_CHECK_URL;
    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.contract_version).toBe(EXPECTED_NEXUS_SERVICE_DESK_CONTRACT);
    expect(body).not.toHaveProperty('jwt');
    expect(body).not.toHaveProperty('environment');
  });

  it('reports compatible backend metadata', async () => {
    vi.stubEnv('NEXUS_ADMIN_CHECK_URL', 'http://candidate-backend');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        Response.json({
          contract_version: EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
        }),
      ),
    );

    const response = await GET();
    const body = await response.json();
    expect(response.status).toBe(200);
    expect(body.contract).toEqual({
      expected: EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
      actual: EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
      compatible: true,
    });
  });

  it.each([
    ['missing contract field', {}],
    ['wrong contract', { contract_version: '1.0' }],
  ])('fails health on %s', async (_name, backendBody) => {
    vi.stubEnv('NEXUS_ADMIN_CHECK_URL', 'http://candidate-backend');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(Response.json(backendBody)),
    );

    const response = await GET();
    const body = await response.json();
    expect(response.status).toBe(503);
    expect(body.status).toBe('contract_mismatch');
    expect(body.contract_version).toBe(EXPECTED_NEXUS_SERVICE_DESK_CONTRACT);
  });
});
