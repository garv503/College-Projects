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
    // Marks the session cookie HTTPS-only. Defaults to on in production, but
    // has to be separately switchable: the Docker image runs with
    // NODE_ENV=production while still being reached over plain HTTP on
    // localhost, and a Secure cookie is silently dropped over HTTP - sign-in
    // then appears to succeed but every following request is anonymous.
    // Set COOKIE_SECURE=true once TLS terminates in front of the app.
    secureCookie: process.env.COOKIE_SECURE
      ? process.env.COOKIE_SECURE === 'true'
      : process.env.NODE_ENV === 'production',
  },

  // One-time code emailed to confirm an address during registration.
  otp: {
    length: 6,
    ttlMs: 10 * 60 * 1000,
    // Wrong guesses allowed before the code is burned and a new one is needed.
    // Without a cap, a 6-digit code is only a million tries from being brute
    // forced by anyone who knows the email address.
    maxAttempts: 5,
    // How long before a pending signup can ask for a fresh code, so the resend
    // button cannot be used to send someone mail repeatedly.
    resendCooldownMs: 60 * 1000,
  },

  mail: {
    host: process.env.MAIL_HOST || '',
    port: Number(process.env.MAIL_PORT || 587),
    user: process.env.MAIL_USER || '',
    password: process.env.MAIL_PASSWORD || '',
    from: process.env.MAIL_FROM || 'Inkwell <no-reply@inkwell.local>',
    // Without a host there is nothing to send through, so the mailer prints the
    // message - code included - to the server console instead.
    get enabled() {
      return Boolean(this.host);
    },
  },

  // The absolute base URL this instance is reached at.
  appUrl: (process.env.APP_URL || `http://localhost:${Number(process.env.PORT || 3000)}`)
    .replace(/\/$/, ''),

  isProduction: process.env.NODE_ENV === 'production',
};

/** Warn loudly rather than silently shipping the development session secret. */
export function warnAboutInsecureDefaults(log = console.warn) {
  if (config.isProduction && !process.env.SESSION_SECRET) {
    log('[Inkwell] SESSION_SECRET is not set. Sessions can be forged. Set it before deploying.');
  }
}
