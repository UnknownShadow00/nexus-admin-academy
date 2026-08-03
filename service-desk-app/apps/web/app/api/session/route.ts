import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import {
  hasNexusAdminAccess,
  verifyStudentSession,
} from '../../../lib/nexus-auth';

const STANDALONE_IDENTITY = {
  userId: 'you',
  name: 'Alex',
  email: '',
  isMentor: false,
  isAdmin: false,
} as const;

export async function GET(request: NextRequest) {
  if (process.env.NEXUS_INTEGRATION !== '1') {
    return NextResponse.json(STANDALONE_IDENTITY);
  }

  const session = verifyStudentSession(
    request.cookies.get('student_session')?.value,
  );
  if (!session) {
    return NextResponse.json(
      { error: 'Missing or invalid student session.' },
      { status: 401 },
    );
  }

  const isAdmin = await hasNexusAdminAccess(
    session,
    request.headers.get('cookie'),
  );

  return NextResponse.json({ ...session, isAdmin });
}
