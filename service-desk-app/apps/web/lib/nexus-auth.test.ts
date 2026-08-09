import jwt from 'jsonwebtoken';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { hasNexusAdminAccess, verifyStudentSession } from './nexus-auth';

const SECRET = 'test-secret-shared-with-nexus';

function sign(
  payload: Record<string, unknown>,
  opts: jwt.SignOptions = {},
) {
  return jwt.sign(payload, SECRET, {
    algorithm: 'HS256',
    expiresIn: '1h',
    ...opts,
  });
}

describe('verifyStudentSession', () => {
  beforeEach(() => {
    process.env.JWT_SECRET_KEY = SECRET;
    process.env.JWT_ALGORITHM = 'HS256';
  });

  it('accepts a valid student token', () => {
    const token = sign({
      sub: '42',
      name: 'Jamie Student',
      email: 'jamie@example.com',
      is_mentor: false,
    });

    expect(verifyStudentSession(token)).toEqual({
      email: 'jamie@example.com',
      isMentor: false,
      name: 'Jamie Student',
      userId: '42',
    });
  });

  it('accepts a valid mentor/admin token and maps is_mentor to isMentor', () => {
    const token = sign({
      sub: '7',
      name: 'Morgan Mentor',
      email: 'morgan@example.com',
      is_mentor: true,
    });

    expect(verifyStudentSession(token)).toEqual({
      email: 'morgan@example.com',
      isMentor: true,
      name: 'Morgan Mentor',
      userId: '7',
    });
  });

  it('rejects an expired token', () => {
    const token = sign(
      {
        sub: '5',
        name: 'Expired User',
        email: 'exp@example.com',
        is_mentor: false,
      },
      { expiresIn: -10 },
    );

    expect(verifyStudentSession(token)).toBeNull();
  });

  it('rejects a token forged with the wrong secret', () => {
    const token = jwt.sign(
      { sub: '99', name: 'Eve', email: 'eve@example.com', is_mentor: false },
      'wrong-secret',
      { algorithm: 'HS256', expiresIn: '1h' },
    );

    expect(verifyStudentSession(token)).toBeNull();
  });

  it('rejects a token signed with a different algorithm than configured', () => {
    const token = jwt.sign(
      {
        sub: '11',
        name: 'AlgSwitch',
        email: 'x@example.com',
        is_mentor: false,
      },
      SECRET,
      { algorithm: 'HS384', expiresIn: '1h' },
    );

    expect(verifyStudentSession(token)).toBeNull();
  });

  it('rejects a malformed token missing a required field', () => {
    const token = sign({ sub: '10', name: 'NoEmail', is_mentor: false });

    expect(verifyStudentSession(token)).toBeNull();
  });

  it('rejects a missing/undefined token', () => {
    expect(verifyStudentSession(undefined)).toBeNull();
  });

  it('rejects an empty token (e.g. cookie cleared on logout)', () => {
    expect(verifyStudentSession('')).toBeNull();
  });
});

describe('hasNexusAdminAccess', () => {
  const nonMentorSession = {
    email: 'jamie@example.com',
    isMentor: false,
    name: 'Jamie',
    userId: '42',
  };
  const mentorSession = { ...nonMentorSession, isMentor: true };

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.NEXUS_ADMIN_CHECK_URL;
  });

  it('short-circuits to true for a mentor session without calling the admin-check URL', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);

    await expect(hasNexusAdminAccess(mentorSession, null)).resolves.toBe(
      true,
    );
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('fails closed for a non-mentor when no admin-check URL is configured', async () => {
    await expect(
      hasNexusAdminAccess(nonMentorSession, null),
    ).resolves.toBe(false);
  });

  it('returns true when the backend reports is_admin: true', async () => {
    process.env.NEXUS_ADMIN_CHECK_URL = 'http://nexus-backend:8000';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ is_admin: true }), { status: 200 }),
      ),
    );

    await expect(
      hasNexusAdminAccess(nonMentorSession, 'admin_session=real'),
    ).resolves.toBe(true);
  });

  it('accepts a verified Nexus admin cookie without a student session', async () => {
    process.env.NEXUS_ADMIN_CHECK_URL = 'http://nexus-backend:8000';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ is_admin: true }), { status: 200 }),
      ),
    );

    await expect(
      hasNexusAdminAccess(null, 'admin_session=real'),
    ).resolves.toBe(true);
  });

  it('returns false when the backend reports is_admin: false', async () => {
    process.env.NEXUS_ADMIN_CHECK_URL = 'http://nexus-backend:8000';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ is_admin: false }), { status: 200 }),
      ),
    );

    await expect(hasNexusAdminAccess(nonMentorSession, null)).resolves.toBe(
      false,
    );
  });

  it('fails closed when the admin-check backend is unreachable', async () => {
    process.env.NEXUS_ADMIN_CHECK_URL = 'http://nexus-backend:8000';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('network down')),
    );

    await expect(hasNexusAdminAccess(nonMentorSession, null)).resolves.toBe(
      false,
    );
  });

  it('fails closed when the admin-check backend returns a non-2xx status', async () => {
    process.env.NEXUS_ADMIN_CHECK_URL = 'http://nexus-backend:8000';
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('error', { status: 500 })),
    );

    await expect(hasNexusAdminAccess(nonMentorSession, null)).resolves.toBe(
      false,
    );
  });
});
