import crypto from 'node:crypto';
import { Router } from 'express';
import { OAuth2Client } from 'google-auth-library';
import { config } from '../config.js';
import { execute, queryOne } from '../db.js';
import { accountSetupEmail, sendMail } from '../mailer.js';
import { csrfToken } from '../middleware/security.js';
import { publicView } from '../userView.js';

/**
 * Account endpoints.
 *
 * Passwords are compared as plain text because they are stored that way, by
 * explicit project choice - see the Security section of the README.
 */
const router = Router();

const MIN_PASSWORD_LENGTH = 8;
const MAX_NAME_LENGTH = 100;
const MAX_EMAIL_LENGTH = 190;

function looksLikeEmail(value) {
  if (typeof value !== 'string') return false;
  const at = value.indexOf('@');
  const dot = value.lastIndexOf('.');
  return at > 0 && dot > at + 1 && dot < value.length - 1 && !value.includes(' ');
}

const trimmed = (value) => (typeof value === 'string' && value.trim() ? value.trim() : null);

/**
 * Current user and CSRF token.
 *
 * Always 200, even signed out: the front end calls this on load to decide what
 * to render, and "nobody is signed in" is a normal answer.
 *
 * Also reports whether Google sign-in is configured, so the client can show the
 * button only when pressing it would actually work.
 */
router.get('/session', (req, res) => {
  res.json({
    user: req.session.user ? { ...req.session.user } : null,
    csrfToken: csrfToken(req),
    googleEnabled: config.google.enabled,
    googleClientId: config.google.clientId || null,
  });
});

router.post('/register', async (req, res, next) => {
  try {
    const name = trimmed(req.body?.name);
    const email = trimmed(req.body?.email);
    const password = typeof req.body?.password === 'string' ? req.body.password : null;

    if (!name) return res.status(400).json({ error: 'Please enter your full name.' });
    if (name.length > MAX_NAME_LENGTH) {
      return res.status(400).json({ error: `Name must be ${MAX_NAME_LENGTH} characters or fewer.` });
    }
    if (!looksLikeEmail(email)) {
      return res.status(400).json({ error: 'Please enter a valid email address.' });
    }
    if (email.length > MAX_EMAIL_LENGTH) {
      return res.status(400).json({ error: `Email must be ${MAX_EMAIL_LENGTH} characters or fewer.` });
    }
    if (!password || password.length < MIN_PASSWORD_LENGTH) {
      return res.status(400).json({ error: `Password must be at least ${MIN_PASSWORD_LENGTH} characters.` });
    }

    // The very first account to exist becomes the administrator, so a fresh
    // install is administrable without seeding anything by hand.
    const existing = await queryOne('SELECT COUNT(*) AS total FROM user');
    const role = Number(existing.total) === 0 ? 'ADMIN' : 'USER';

    await execute(
      'INSERT INTO user (full_name, email, password, role) VALUES (?, ?, ?, ?)',
      [name, email.toLowerCase(), password, role],
    );

    return res.status(201).json({ message: 'Account created. Please sign in.' });
  } catch (error) {
    // The unique index on email is what enforces this; catching the violation
    // avoids a check-then-insert race between two simultaneous signups.
    if (error.code === 'ER_DUP_ENTRY') {
      return res.status(409).json({ error: 'An account with that email already exists.' });
    }
    return next(error);
  }
});

router.post('/login', async (req, res, next) => {
  try {
    const email = trimmed(req.body?.email);
    const password = typeof req.body?.password === 'string' ? req.body.password : null;

    if (!email || !password) {
      return res.status(400).json({ error: 'Please enter both your email and password.' });
    }

    const user = await queryOne(
      'SELECT id, full_name, email, password, role, created_at FROM user WHERE email = ?',
      [email.toLowerCase()],
    );

    // One message for every failure - unknown email, wrong password, or a
    // Google account with no password yet - so the response cannot be used to
    // discover which emails are registered or how they signed up.
    // The explicit null check matters: a Google account stores NULL here, and
    // it must never be treated as "matches whatever was supplied".
    if (!user || user.password === null || user.password !== password) {
      return res.status(401).json({ error: 'Invalid email or password.' });
    }

    const view = publicView(user);

    // Issue a fresh session id on sign-in, so a session id planted beforehand
    // cannot be reused afterwards (session fixation).
    return req.session.regenerate((regenerateError) => {
      if (regenerateError) return next(regenerateError);

      req.session.user = view;
      return res.json({ user: view, csrfToken: csrfToken(req) });
    });
  } catch (error) {
    return next(error);
  }
});

/* --------------------------------------------------------- Google sign-in */

const googleClient = config.google.enabled ? new OAuth2Client(config.google.clientId) : null;

/**
 * Signs in (or registers) with a Google ID token.
 *
 * The client obtains the token from Google Identity Services and posts it here.
 * It is verified server-side against Google's public keys and checked to be
 * issued for this application - an unverified token is just an untrusted string
 * and must never be believed.
 *
 * A first-time Google user gets an account and a "set your password" email, so
 * the account also works without Google later.
 */
router.post('/google', async (req, res, next) => {
  if (!googleClient) {
    return res.status(503).json({
      error: 'Google sign-in is not configured on this server.',
    });
  }

  const credential = typeof req.body?.credential === 'string' ? req.body.credential : null;
  if (!credential) {
    return res.status(400).json({ error: 'Missing Google credential.' });
  }

  let payload;
  try {
    const ticket = await googleClient.verifyIdToken({
      idToken: credential,
      audience: config.google.clientId,
    });
    payload = ticket.getPayload();
  } catch {
    return res.status(401).json({ error: 'That Google sign-in could not be verified.' });
  }

  // Google sets this false when the address itself is unconfirmed; trusting it
  // would let someone claim an address they do not own.
  if (!payload?.email || payload.email_verified === false) {
    return res.status(401).json({ error: 'Your Google account has no verified email address.' });
  }

  const email = payload.email.toLowerCase();
  const googleId = payload.sub;
  const name = (payload.name || email.split('@')[0]).slice(0, 100);

  try {
    let user = await queryOne(
      'SELECT id, full_name, email, password, role, google_id, created_at FROM user '
      + 'WHERE google_id = ? OR email = ?',
      [googleId, email],
    );

    let isNewAccount = false;

    if (!user) {
      // First account on a fresh install becomes the administrator, matching
      // the rule used for email/password registration.
      const existing = await queryOne('SELECT COUNT(*) AS total FROM user');
      const role = Number(existing.total) === 0 ? 'ADMIN' : 'USER';

      const result = await execute(
        'INSERT INTO user (full_name, email, password, role, google_id, email_verified) '
        + 'VALUES (?, ?, NULL, ?, ?, TRUE)',
        [name, email, role, googleId],
      );

      isNewAccount = true;
      user = await queryOne(
        'SELECT id, full_name, email, password, role, google_id, created_at FROM user WHERE id = ?',
        [result.insertId],
      );
    } else if (!user.google_id) {
      // The address already had a password account; link Google to it rather
      // than creating a second account for the same person.
      await execute('UPDATE user SET google_id = ?, email_verified = TRUE WHERE id = ?',
        [googleId, user.id]);
      user.google_id = googleId;
    }

    if (isNewAccount) {
      // Fire-and-forget: a mail problem must not fail the sign-in.
      void sendAccountSetupEmail(user).catch((error) => {
        console.error('[Inkwell] setup email failed:', error.message);
      });
    }

    const view = publicView(user);

    return req.session.regenerate((regenerateError) => {
      if (regenerateError) return next(regenerateError);

      req.session.user = view;
      return res.json({ user: view, csrfToken: csrfToken(req), isNewAccount });
    });
  } catch (error) {
    return next(error);
  }
});

/* ------------------------------------------------- account setup by email */

/**
 * Issues a single-use token and emails the "set a password" link.
 *
 * Storing only a hash would be better practice, but this project stores
 * passwords in plain text by explicit choice, so hashing the token here would
 * be security theatre next to that. The token is still long, random,
 * single-use and short-lived.
 */
async function sendAccountSetupEmail(user) {
  const token = crypto.randomBytes(32).toString('hex');
  const expires = new Date(Date.now() + config.setupTokenTtlMs);

  await execute('UPDATE user SET setup_token = ?, setup_token_expires = ? WHERE id = ?',
    [token, expires, user.id]);

  const link = `${config.appUrl}/account-setup?token=${token}`;
  const { subject, text, html } = accountSetupEmail({ name: user.full_name, link });

  return sendMail({ to: user.email, subject, text, html });
}

/** Checks a setup token so the page can show a useful message before asking for input. */
router.get('/setup-token/:token', async (req, res, next) => {
  try {
    const user = await findBySetupToken(req.params.token);
    if (!user) {
      return res.status(404).json({ error: 'That link is invalid or has expired.' });
    }
    return res.json({ email: user.email, name: user.full_name });
  } catch (error) {
    return next(error);
  }
});

/** Consumes a setup token and sets the account's password. */
router.post('/setup-password', async (req, res, next) => {
  try {
    const token = typeof req.body?.token === 'string' ? req.body.token : null;
    const password = typeof req.body?.password === 'string' ? req.body.password : null;

    if (!token) return res.status(400).json({ error: 'That link is invalid or has expired.' });
    if (!password || password.length < MIN_PASSWORD_LENGTH) {
      return res.status(400).json({
        error: `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`,
      });
    }

    const user = await findBySetupToken(token);
    if (!user) {
      return res.status(404).json({ error: 'That link is invalid or has expired.' });
    }

    // Clearing the token in the same statement makes the link single-use.
    await execute(
      'UPDATE user SET password = ?, setup_token = NULL, setup_token_expires = NULL WHERE id = ?',
      [password, user.id],
    );

    return res.json({ message: 'Password set. You can now sign in with your email address.' });
  } catch (error) {
    return next(error);
  }
});

/** Looks up an unexpired setup token. */
async function findBySetupToken(token) {
  if (!token || token.length !== 64) return null;
  return queryOne(
    'SELECT id, full_name, email FROM user '
    + 'WHERE setup_token = ? AND setup_token_expires > NOW()',
    [token],
  );
}

router.post('/logout', (req, res, next) => {
  req.session.destroy((error) => {
    if (error) return next(error);
    res.clearCookie('inkwell.sid');
    return res.json({ message: 'You have been signed out.' });
  });
});

export default router;
