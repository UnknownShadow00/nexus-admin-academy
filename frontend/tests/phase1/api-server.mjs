import http from 'node:http';
import * as fixture from './fixtures.mjs';

// Bind loopback only. This process has no production URLs, DB, env files, or secrets.
const server = http.createServer(async (request, response) => {
  const path = new URL(request.url, 'http://127.0.0.1:5820').pathname;
  const origin = request.headers.origin;
  if (origin && /^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(origin)) {
    response.setHeader('Access-Control-Allow-Origin', origin);
    response.setHeader('Access-Control-Allow-Credentials', 'true');
    response.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Nexus-Warmup');
    response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  }
  if (request.method === 'OPTIONS') { response.writeHead(204); response.end(); return; }
  const send = (data, status = 200) => { response.writeHead(status, { 'Content-Type': 'application/json' }); response.end(JSON.stringify(data)); };
  const ok = (data) => send({ success: true, data });
  const cookie = request.headers.cookie || '';
  let tokenStudent;
  try { tokenStudent = JSON.parse(Buffer.from((request.headers.authorization || '').split('.')[1], 'base64').toString()); } catch { /* no fixture token */ }
  const legacy = tokenStudent?.sub === '900002' || (!tokenStudent && cookie.includes('phase1-cohort=legacy'));
  const signedIn = Boolean(tokenStudent) || /phase1-cohort=(legacy|v2)/.test(cookie);
  if (path === '/health') return send({ status: 'ok', fixture: true });
  if (path === '/auth/login' && request.method === 'POST') {
    let body = ''; for await (const chunk of request) body += chunk;
    const credentials = JSON.parse(body);
    const legacyLogin = credentials.username === 'phase1-legacy';
    if (!['phase1-v2', 'phase1-legacy'].includes(credentials.username) || credentials.password !== 'fixture-only-password') return send({ detail: 'Unknown fixture account' }, 401);
    const student = fixture.student(legacyLogin);
    // Unsigned token exists only in this fixture process; cannot authenticate to Nexus.
    const payload = Buffer.from(JSON.stringify({ sub: String(student.student_id), name: student.name, exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64');
    response.setHeader('Set-Cookie', `phase1-cohort=${legacyLogin ? 'legacy' : 'v2'}; Path=/; SameSite=Lax`);
    return send({ ...student, access_token: `fixture.${payload}.fixture` });
  }
  if (path === '/auth/logout') { response.setHeader('Set-Cookie', 'phase1-cohort=; Path=/; Max-Age=0'); return ok({}); }
  if (path === '/auth/me') return signedIn ? ok(fixture.student(legacy)) : send({ detail: 'Fixture sign-in required' }, 401);
  if (path === '/api/admin/session/status') return ok({ authenticated: false });
  if (path === '/api/service-desk/contract') return send({ contract_version: '2.0', fixture: true });
  if (path === '/service-desk/api/health') return send({ status: 'ok', contract_version: '2.0', contract: { actual: '2.0', compatible: true }, fixture: true });
  if (!signedIn) return send({ detail: 'Fixture sign-in required' }, 401);
  if (path === '/api/v2/curriculum/access') return ok({ master_enabled: true, student_enabled: !legacy, mode: 'pilot' });
  if (path.startsWith('/api/v2/') && legacy) return send({ detail: 'Not enrolled in fixture cohort' }, 403);
  if (path === '/api/v2/curriculum') return ok(fixture.learning);
  if (path === `/api/v2/curriculum/modules/${fixture.module.key}`) return ok(fixture.moduleDetail);
  if (path === `/api/v2/curriculum/modules/${fixture.module.key}/lessons/${fixture.lesson.key}`) return ok(fixture.lessonDetail);
  if (/^\/api\/students\/90000[12]\/stats$/.test(path)) return send({ success: true, ...fixture.stats });
  if (/^\/api\/students\/90000[12]\/check-in$/.test(path)) return ok({});
  if (path === '/api/training') return ok(fixture.training);
  if (path === '/api/training/progress') return ok(fixture.trainingProgress);
  if (path === '/api/service-desk/progress-summary') return ok({ tickets_completed: 0, passed_first_try: 0, needed_revision: 0, skills: [], recent_activity: [] });
  if (path === '/api/search/global') return ok({ lessons: [{ id: 900001, title: 'Welcome to Nexus' }], commands: [] });
  if (path === '/api/lessons/900001') return ok({ id: 900001, title: 'Welcome to Nexus', summary: 'This is disposable fixture content.', completed: false, resources: [], related_activities: [] });
  return send({ detail: 'Endpoint is outside Phase 1 fixture coverage' }, 404);
});
server.listen(5820, '127.0.0.1', () => console.log('Phase 1 disposable API fixtures on loopback:5820'));
