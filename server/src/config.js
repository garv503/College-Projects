import 'dotenv/config';

/**
 * Runtime configuration.
 *
 * Values are read from the environment, falling back to local development
 * defaults. Copy server/.env.example to server/.env to override them; that file
 * is gitignored so real credentials are never committed.
 */
export const config = {
  port: Number(process.env.PORT || 3000),

  db: {
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT || 3306),
    user: process.env.DB_USER || 'root',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'enotes',
  },

  session: {
    // Signs the session cookie. A fixed fallback keeps local development
    // frictionless; a real deployment must set SESSION_SECRET.
    secret: process.env.SESSION_SECRET || 'inkwell-development-secret-change-me',
    // One hour, matching the timeout the Java version used.
    maxAgeMs: 60 * 60 * 1000,
  },

  google: {
    // From Google Cloud Console -> Credentials -> OAuth 2.0 Client ID (Web).
    // Empty means Google sign-in is switched off and the button is hidden.
    clientId: process.env.GOOGLE_CLIENT_ID || '',
    get enabled() {
      return Boolean(this.clientId);
    },
  },

  mail: {
    host: process.env.MAIL_HOST || '',
    port: Number(process.env.MAIL_PORT || 587),
    user: process.env.MAIL_USER || '',
    password: process.env.MAIL_PASSWORD || '',
    from: process.env.MAIL_FROM || 'Inkwell <no-reply@inkwell.local>',
    // Without a host there is nothing to send through, so the mailer logs
    // messages to the console instead.
    get enabled() {
      return Boolean(this.host);
    },
  },

  // Used to build absolute links inside emails, which cannot be relative.
  appUrl: (process.env.APP_URL || `http://localhost:${Number(process.env.PORT || 3000)}`)
    .replace(/\/$/, ''),

  // How long the "set your password" link stays valid.
  setupTokenTtlMs: 24 * 60 * 60 * 1000,

  isProduction: process.env.NODE_ENV === 'production',
};

/** Warn loudly rather than silently shipping the development session secret. */
export function warnAboutInsecureDefaults(log = console.warn) {
  if (config.isProduction && !process.env.SESSION_SECRET) {
    log('[Inkwell] SESSION_SECRET is not set. Sessions can be forged. Set it before deploying.');
  }
}
