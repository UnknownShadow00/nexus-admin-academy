import jwt, { type Algorithm, type JwtPayload } from 'jsonwebtoken';

const SUPPORTED_ALGORITHMS = new Set<Algorithm>(['HS256', 'HS384', 'HS512']);

export interface NexusIdentity {
  email: string;
  isAdmin: boolean;
  isMentor: boolean;
  name: string;
  userId: string;
}

export type VerifiedStudentSession = Omit<NexusIdentity, 'isAdmin'>;

function getJwtAlgorithm(): Algorithm | null {
  const algorithm = process.env.JWT_ALGORITHM as Algorithm | undefined;
  return algorithm && SUPPORTED_ALGORITHMS.has(algorithm) ? algorithm : null;
}

function isStudentPayload(
  payload: string | JwtPayload,
): payload is JwtPayload & {
  email: string;
  is_mentor: boolean;
  name: string;
  sub: string;
} {
  return (
    typeof payload !== 'string' &&
    typeof payload.sub === 'string' &&
    /^\d+$/.test(payload.sub) &&
    typeof payload.name === 'string' &&
    typeof payload.email === 'string' &&
    typeof payload.is_mentor === 'boolean' &&
    typeof payload.exp === 'number'
  );
}

export function verifyStudentSession(
  token: string | undefined,
): VerifiedStudentSession | null {
  const secret = process.env.JWT_SECRET_KEY;
  const algorithm = getJwtAlgorithm();

  if (!token || !secret || !algorithm) {
    return null;
  }

  try {
    const payload = jwt.verify(token, secret, {
      algorithms: [algorithm],
    });

    if (!isStudentPayload(payload)) {
      return null;
    }

    return {
      email: payload.email,
      isMentor: payload.is_mentor,
      name: payload.name,
      userId: payload.sub,
    };
  } catch {
    return null;
  }
}

export async function hasNexusAdminAccess(
  session: VerifiedStudentSession,
  cookieHeader: string | null,
): Promise<boolean> {
  if (session.isMentor) {
    return true;
  }

  const adminCheckBaseUrl = process.env.NEXUS_ADMIN_CHECK_URL;
  if (!adminCheckBaseUrl) {
    return false;
  }

  try {
    const response = await fetch(
      `${adminCheckBaseUrl.replace(/\/+$/, '')}/api/service-desk/admin-check`,
      {
        cache: 'no-store',
        headers: { cookie: cookieHeader ?? '' },
      },
    );

    if (!response.ok) {
      return false;
    }

    const result: unknown = await response.json();
    return (
      typeof result === 'object' &&
      result !== null &&
      'is_admin' in result &&
      result.is_admin === true
    );
  } catch {
    return false;
  }
}
