export const EXPECTED_NEXUS_SERVICE_DESK_CONTRACT = '2.0' as const;
export const NEXUS_SERVICE_DESK_CONTRACT_HEADER =
  'X-Nexus-Service-Desk-Contract' as const;

export function contractIsCompatible(value: unknown): boolean {
  return (
    typeof value === 'object' &&
    value !== null &&
    'contract_version' in value &&
    value.contract_version === EXPECTED_NEXUS_SERVICE_DESK_CONTRACT
  );
}
