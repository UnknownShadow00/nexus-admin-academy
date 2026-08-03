import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { hasNexusAdminAccess, verifyStudentSession } from './lib/nexus-auth';

function loginRedirect(request: NextRequest) {
  return NextResponse.redirect(
    new URL('/login?next=/service-desk', request.nextUrl.origin),
    307,
  );
}

function appRootRedirect(request: NextRequest) {
  return NextResponse.redirect(
    new URL(request.nextUrl.basePath || '/', request.nextUrl.origin),
    307,
  );
}

export async function middleware(request: NextRequest) {
  if (process.env.NEXUS_INTEGRATION !== '1') {
    return NextResponse.next();
  }

  const session = verifyStudentSession(
    request.cookies.get('student_session')?.value,
  );
  if (!session) {
    return loginRedirect(request);
  }

  // NextURL strips the configured basePath; the fallback keeps this safe if URL
  // normalization is disabled in a future Next.js configuration.
  const appPathname =
    request.nextUrl.basePath &&
    request.nextUrl.pathname.startsWith(request.nextUrl.basePath)
      ? request.nextUrl.pathname.slice(request.nextUrl.basePath.length) || '/'
      : request.nextUrl.pathname;

  if (
    appPathname.startsWith('/admin') &&
    !(await hasNexusAdminAccess(session, request.headers.get('cookie')))
  ) {
    return appRootRedirect(request);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // The capture-group pattern below requires a "/" after basePath, so it
    // never matches the bare basePath root (e.g. exactly "/service-desk");
    // this explicit "/" entry closes that gap.
    '/',
    '/((?!api/health|_next/static|_next/image|favicon\\.ico(?:$|/)).*)',
  ],
  runtime: 'nodejs',
};
