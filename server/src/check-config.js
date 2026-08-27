/**
 * Configuration doctor: `npm run check` from the project root.
 *
 * Reports what is configured, what is missing, and what looks wrong - notably
 * a session cookie marked HTTPS-only while the app is served over plain HTTP,
 * which breaks sign-in without producing any error.
 *
 * Read-only. It never changes configuration or data.
 */
import { config } from './config.js';
import { pool, queryOne } from './db.js';

const ok = (label, detail = '') => console.log(`  [ OK ]   ${label}${detail ? ` - ${detail}` : ''}`);
const off = (label, detail = '') => console.log(`  [ OFF ]  ${label}${detail ? ` - ${detail}` : ''}`);
const bad = (label, detail = '') => console.log(`  [ FIX ]  ${label}${detail ? ` - ${detail}` : ''}`);

let problems = 0;

console.log('\nInkwell configuration check\n' + '='.repeat(60));

/* ------------------------------------------------------------------ core */

console.log('\nCore');

if (config.session.secret.startsWith('local-development')
    || config.session.secret.includes('change-me')) {
  off('SESSION_SECRET', 'still the development default (fine locally)');
} else {
  ok('SESSION_SECRET', 'set');
}

ok('APP_URL', config.appUrl);
ok('PORT', String(config.port));

// A Secure cookie served over plain HTTP is dropped by the browser, so sign-in
// looks like it worked and every later request is anonymous. Silent otherwise.
if (config.session.secureCookie && config.appUrl.startsWith('http://')) {
  bad('COOKIE_SECURE', `cookie is HTTPS-only but APP_URL is ${config.appUrl} - nobody can stay signed in`);
  problems += 1;
} else if (config.session.secureCookie) {
  ok('COOKIE_SECURE', 'session cookie is HTTPS-only');
} else {
  off('COOKIE_SECURE', 'session cookie works over plain HTTP (set true behind HTTPS)');
}

/* -------------------------------------------------------------- database */

console.log('\nDatabase');

try {
  await queryOne('SELECT 1');
  ok('connection', `${config.db.user}@${config.db.host}:${config.db.port}/${config.db.database}`);

  const admins = await queryOne("SELECT COUNT(*) AS n FROM user WHERE role = 'ADMIN'");
  const users = await queryOne('SELECT COUNT(*) AS n FROM user');

  if (Number(admins.n) === 0) {
    bad('administrator', 'no ADMIN account exists - restart promotes the oldest account');
    problems += 1;
  } else {
    ok('administrator', `${admins.n} admin of ${users.n} account(s)`);
  }
} catch (error) {
  bad('connection', error.message);
  problems += 1;
}

/* -------------------------------------------------------------------- mail */

console.log('\nOutgoing email  (registration codes)');

if (!config.mail.enabled) {
  off('MAIL_HOST', 'not set - verification codes print to the server console');
} else {
  ok('MAIL_HOST', `${config.mail.host}:${config.mail.port}`);
  if (!config.mail.user || !config.mail.password) {
    bad('MAIL_USER / MAIL_PASSWORD', 'host is set but credentials are missing');
    problems += 1;
  } else {
    ok('credentials', config.mail.user);
  }
  if (config.mail.host.includes('gmail') && config.mail.password.length !== 16) {
    console.log('           Gmail needs a 16-character App Password, not the account password.');
  }
}

/* ------------------------------------------------------------------ verdict */

console.log('\n' + '='.repeat(60));
console.log(problems === 0
  ? 'No problems found. Anything marked OFF simply is not enabled.\n'
  : `${problems} problem(s) to fix - see [ FIX ] above.\n`);

await pool.end();
process.exit(problems === 0 ? 0 : 1);
