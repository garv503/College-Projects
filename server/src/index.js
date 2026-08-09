import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import session from 'express-session';
import MySQLStoreFactory from 'express-mysql-session';

import { config, warnAboutInsecureDefaults } from './config.js';
import { pool } from './db.js';
import { initialiseSchema } from './schema.js';
import { csrfProtection, refreshSession, requireAdmin, requireAuth } from './middleware/security.js';
import authRoutes from './routes/auth.js';
import notesRoutes from './routes/notes.js';
import statsRoutes from './routes/stats.js';
import adminRoutes from './routes/admin.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const clientDir = path.resolve(here, '../../frontend/dist');

const app = express();

// Behind a proxy this lets secure cookies work; harmless when running direct.
app.set('trust proxy', 1);
app.disable('x-powered-by');

app.use(express.json({ limit: '256kb' }));

/* ------------------------------------------------------------------ session */

const MySQLStore = MySQLStoreFactory(session);

// Sessions live in MySQL rather than in memory, so a server restart does not
// sign everyone out and the default in-memory store's leak warning does not
// apply.
const sessionStore = new MySQLStore({ createDatabaseTable: true, clearExpired: true }, pool);

app.use(
  session({
    name: 'inkwell.sid',
    secret: config.session.secret,
    store: sessionStore,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true, // Script cannot read it.
      sameSite: 'lax', // Not sent on cross-site POSTs; CSRF tokens back this up.
      secure: config.isProduction, // HTTPS-only once deployed.
      maxAge: config.session.maxAgeMs,
    },
  }),
);

/* ---------------------------------------------------------------------- api */

// Login and register are exempt: they are the requests that establish a
// session, so there is no token to present yet.
app.use('/api', csrfProtection(['/auth/login', '/auth/register']));

// Re-reads the user from the database, so a deletion or a role change takes
// effect on the next request rather than when the session expires.
app.use('/api', refreshSession);

app.use('/api/auth', authRoutes);
app.use('/api/notes', requireAuth, notesRoutes);
app.use('/api/stats', requireAuth, statsRoutes);
app.use('/api/admin', requireAdmin, adminRoutes);

// Anything else under /api is a real 404, not the SPA shell.
app.use('/api', (req, res) => {
  res.status(404).json({ error: 'Unknown endpoint.' });
});

/* ------------------------------------------------------- static react build */

app.use(express.static(clientDir, { index: false }));

// Client-side routes such as /notes have no file behind them; serve the shell
// and let the router decide. Only GETs, and only outside /api.
app.get('*', (req, res, next) => {
  res.sendFile(path.join(clientDir, 'index.html'), (error) => {
    if (error) {
      next(
        new Error(
          'The React build is missing. Run "npm run build" in the frontend directory '
          + '(or "npm run build" at the project root).',
        ),
      );
    }
  });
});

/* ------------------------------------------------------------- error handler */

// Four arguments: Express only treats this as an error handler with all of them.
// eslint-disable-next-line no-unused-vars
app.use((error, req, res, next) => {
  console.error('[Inkwell]', error);
  // Never return the message or stack to the client - it can leak internals.
  res.status(500).json({ error: 'Something went wrong. Please try again.' });
});

/* -------------------------------------------------------------------- start */

async function start() {
  warnAboutInsecureDefaults();

  try {
    await initialiseSchema();
  } catch (error) {
    // Deliberately not fatal: the server should still start and report a clear
    // error per request rather than refusing to boot.
    console.error('[Inkwell schema] could not verify schema -', error.message);
  }

  app.listen(config.port, () => {
    console.log(`Inkwell is running at http://localhost:${config.port}/`);
  });
}

async function shutdown(signal) {
  console.log(`\n[Inkwell] ${signal} received, shutting down.`);
  try {
    await new Promise((resolve) => sessionStore.close(resolve));
    await pool.end();
  } finally {
    process.exit(0);
  }
}

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

start();
