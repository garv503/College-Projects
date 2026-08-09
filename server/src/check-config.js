/**
 * Configuration doctor: `npm run check` from the project root.
 *
 * Reports what is configured, what is missing, and what looks wrong - notably
 * the two easy mistakes when setting up Google sign-in, which are pasting an
 * API key or the client *secret* instead of the client ID.
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

/* --------------------------------------------------------- google sign-in */

console.log('\nGoogle sign-in  (optional)');

const id = config.google.clientId.trim();

if (!id) {
  off('GOOGLE_CLIENT_ID', 'not set - the button shows as a disabled placeholder');
  console.log('           Create one: Google Cloud Console -> APIs & Services');
  console.log('           -> Credentials -> Create credentials -> OAuth client ID');
  console.log('           -> Web application, with this authorised JS origin:');
  console.log(`             ${config.appUrl}`);
} else if (id.startsWith('AIza')) {
  // An API key, not an OAuth client id - the most common mix-up.
  bad('GOOGLE_CLIENT_ID', 'this looks like an API KEY (starts "AIza"), not an OAuth client ID');
  problems += 1;
} else if (id.startsWith('GOCSPX-')) {
  // The client secret sits right next to the id in the Console.
  bad('GOOGLE_CLIENT_ID', 'this looks like the client SECRET (starts "GOCSPX-"). Use the client ID');
  problems += 1;
} else if (!id.endsWith('.apps.googleusercontent.com')) {
  bad('GOOGLE_CLIENT_ID', 'should end in ".apps.googleusercontent.com"');
  problems += 1;
} else {
  ok('GOOGLE_CLIENT_ID', `${id.slice(0, 12)}...${id.slice(-28)}`);
  console.log(`           Make sure ${config.appUrl} is an authorised JavaScript origin.`);
}

/* -------------------------------------------------------------------- mail */

console.log('\nOutgoing email  (optional)');

if (!config.mail.enabled) {
  off('MAIL_HOST', 'not set - setup emails print to this console instead of sending');
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
  ? 'No problems found. Optional features marked OFF simply are not enabled.\n'
  : `${problems} problem(s) to fix - see [ FIX ] above.\n`);

await pool.end();
process.exit(problems === 0 ? 0 : 1);
