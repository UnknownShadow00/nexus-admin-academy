import { describe, expect, it } from 'vitest';

import {
  EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
  NEXUS_SERVICE_DESK_CONTRACT_HEADER,
  contractIsCompatible,
} from './service-desk-contract';

describe('Service Desk contract', () => {
  it('accepts only the exact semantic contract', () => {
    expect(NEXUS_SERVICE_DESK_CONTRACT_HEADER).toBe(
      'X-Nexus-Service-Desk-Contract',
    );
    expect(contractIsCompatible({ contract_version: EXPECTED_NEXUS_SERVICE_DESK_CONTRACT })).toBe(true);
    expect(contractIsCompatible({ contract_version: '1.0' })).toBe(false);
    expect(contractIsCompatible(null)).toBe(false);
  });
});
