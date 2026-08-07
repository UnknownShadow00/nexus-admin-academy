import jwt from 'jsonwebtoken';
import { NextRequest } from 'next/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { config, middleware } from './middleware';

const SECRET = 'test-secret-shared-with-nexus';
const NEXT_CONFIG = { basePath: '/service-desk', i18n: null, trailingSlash: false };

function sign(payload: Record<string, unknown>, opts: jwt.SignOptions = {}) {
  return jwt.sign(payload, SECRET, {
    algorithm: 'HS256',
    expiresIn: '1h',
    ...opts,
  });
}

function requestFor(pathname: string, cookie?: string) {
  return new NextRequest(`http://localhost:3000${pathname}`, {
    headers: cookie ? { cookie } : undefined,
    nextConfig: NEXT_CONFIG,
  });
}

describe('middleware config', () => {
  it('matcher includes an explicit "/" entry so the bare basePath root is gated', () => {
    // Regression guard: the capture-group pattern below requires a "/" after
    // basePath, so without this explicit "/" entry, Next.js never invokes
    // middleware() for the exact basePath root (e.g. "/service-desk" with no
    // trailing path) even though every sub-route is correctly gated.
    expect(config.matcher).toContain('/');
  });
});

describe('middleware', () => {
  beforeEach(() => {
    process.env.NEXUS_INTEGRATION = '1';
    process.env.JWT_SECRET_KEY = SECRET;
    process.env.JWT_ALGORITHM = 'HS256';
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete process.env.NEXUS_INTEGRATION;
    delete process.env.NEXUS_ADMIN_CHECK_URL;
  });

  it('passes every request through when Nexus integration is disabled', async () => {
    delete process.env.NEXUS_INTEGRATION;
    const response = await middleware(requestFor('/service-desk'));
    expect(response.status).toBe(200);
    expect(response.headers.get('location')).toBeNull();
  });

  it('redirects to /login?next=/service-desk on the bare basePath root with no cookie', async () => {
    const response = await middleware(requestFor('/service-desk'));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'http://localhost:3000/login?next=/service-desk',
    );
  });

  it('redirects to login for a sub-route with no cookie (unauthorized redirect behavior)', async () => {
    const response = await middleware(requestFor('/service-desk/tickets/INC2401'));
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'http://localhost:3000/login?next=/service-desk',
    );
  });

  it('redirects to login for an expired session', async () => {
    const token = sign(
      { sub: '5', name: 'Expired', email: 'exp@example.com', is_mentor: false },
      { expiresIn: -60 },
    );
    const response = await middleware(
      requestFor('/service-desk', `student_session=${token}`),
    );
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'http://localhost:3000/login?next=/service-desk',
    );
  });

  it('allows a valid student session through on the bare basePath root', async () => {
    const token = sign({
      sub: '42',
      name: 'Jamie',
      email: 'jamie@example.com',
      is_mentor: false,
    });
    const response = await middleware(
      requestFor('/service-desk', `student_session=${token}`),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get('location')).toBeNull();
    expect(response.headers.get('x-middleware-rewrite')).toBeNull();
  });

  it('redirects a non-admin student away from /admin', async () => {
    const token = sign({
      sub: '42',
      name: 'Jamie',
      email: 'jamie@example.com',
      is_mentor: false,
    });
    const response = await middleware(
      requestFor('/service-desk/admin', `student_session=${token}`),
    );
    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('http://localhost:3000/service-desk');
  });

  it('allows a mentor session into /admin', async () => {
    const token = sign({
      sub: '7',
      name: 'Morgan',
      email: 'morgan@example.com',
      is_mentor: true,
    });
    const response = await middleware(
      requestFor('/service-desk/admin', `student_session=${token}`),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get('location')).toBeNull();
    expect(response.headers.get('x-middleware-rewrite')).toBeNull();
  });

  it('passes an authenticated base-path API request to Next routing', async () => {
    const token = sign({
      sub: '42',
      name: 'Jamie',
      email: 'jamie@example.com',
      is_mentor: false,
    });
    const response = await middleware(
      requestFor(
        '/service-desk/api/session',
        `student_session=${token}`,
      ),
    );
    expect(response.headers.get('x-middleware-rewrite')).toBeNull();
  });
});
