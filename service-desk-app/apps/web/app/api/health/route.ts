import {
  EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
  contractIsCompatible,
} from '../../../lib/service-desk-contract';

export async function GET() {
  const backend = process.env.NEXUS_ADMIN_CHECK_URL;
  let actual: unknown = null;
  if (backend) {
    try {
      const response = await fetch(`${backend}/api/service-desk/contract`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3000),
      });
      actual = response.ok ? await response.json() : null;
    } catch {
      actual = null;
    }
  }
  const compatible = backend ? contractIsCompatible(actual) : null;
  return Response.json(
    {
      status: compatible === false ? 'contract_mismatch' : 'ok',
      timestamp: new Date().toISOString(),
      contract: {
        expected: EXPECTED_NEXUS_SERVICE_DESK_CONTRACT,
        actual:
          typeof actual === 'object' && actual !== null && 'contract_version' in actual
            ? actual.contract_version
            : null,
        compatible,
      },
    },
    { status: compatible === false ? 503 : 200 },
  );
}
