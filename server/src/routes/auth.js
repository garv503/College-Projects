import crypto from 'node:crypto';
import { Router } from 'express';
import { config } from '../config.js';
import { execute, queryOne } from '../db.js';
import { mailEnabled, sendMail, verificationEmail } from '../mailer.js';
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
 */
router.get('/session', (req, res) => {
  res.json({
    user: req.session.user ? { ...req.session.user } : null,
    csrfToken: csrfToken(req),
  });
});

/* ------------------------------------------------- registration with an OTP */

/**
 * A cryptographically random numeric code.
 *
 * `randomInt` is used rather than `Math.random`, which is predictable enough to
 * guess from a couple of observed codes.
 */
function generateOtp() {
  const max = 10 ** config.otp.length;
  return String(crypto.randomInt(0, max)).padStart(config.otp.length, '0');
}

/** Sends the code, and reports whether it went by email or to the console. */
async function deliverOtp({ name, email, code }) {
  const minutes = Math.round(config.otp.ttlMs / 60000);
  const { subject, text, html } = verificationEmail({ name, code, minutes });
  await sendMail({ to: email, subject, text, html });
  return mailEnabled();
}

/**
 * Step 1 of 2: validates the details and emails a confirmation code.
 *
 * No account is created here. The signup waits in `pending_registration` until
 * the code is confirmed, so an address nobody can receive mail at never becomes
 * a usable account.
 */
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

    const address = email.toLowerCase();

    const taken = await queryOne('SELECT id FROM user WHERE email = ?', [address]);
    if (taken) {
      return res.status(409).json({ error: 'An account with that email already exists.' });
    }

    const code = generateOtp();
    const expires = new Date(Date.now() + config.otp.ttlMs);

    // Starting over replaces any earlier pending attempt for this address,
    // which also resets the attempt counter - the person proving they own the
    // address is not the one who should be locked out by someone else's typing.
    await execute(
      `INSERT INTO pending_registration
         (full_name, email, password, otp_code, otp_expires, attempts, last_sent_at)
       VALUES (?, ?, ?, ?, ?, 0, NOW())
       ON DUPLICATE KEY UPDATE
         full_name = VALUES(full_name), password = VALUES(password),
         otp_code = VALUES(otp_code), otp_expires = VALUES(otp_expires),
         attempts = 0, last_sent_at = NOW()`,
      [name, address, password, code, expires],
    );

    const emailed = await deliverOtp({ name, email: address, code });

    return res.status(200).json({
      message: `We sent a ${config.otp.length}-digit code to ${address}.`,
      email: address,
      emailed,
      expiresInMinutes: Math.round(config.otp.ttlMs / 60000),
    });
  } catch (error) {
    return next(error);
  }
});

/**
 * Step 2 of 2: confirms the code and creates the account.
 *
 * The name, email and password all come from the stored pending row rather than
 * from this request, so the code confirms exactly the signup it was issued for -
 * a valid code cannot be replayed to create a different account.
 */
router.post('/verify-otp', async (req, res, next) => {
  try {
    const email = trimmed(req.body?.email);
    const code = trimmed(req.body?.code);

    if (!email || !code) {
      return res.status(400).json({ error: 'Enter the code we emailed you.' });
    }

    const address = email.toLowerCase();
    const pending = await queryOne(
      'SELECT * FROM pending_registration WHERE email = ?',
      [address],
    );

    if (!pending) {
      return res.status(404).json({
        error: 'That signup has expired. Please register again.',
      });
    }

    if (new Date(pending.otp_expires).getTime() < Date.now()) {
      await execute('DELETE FROM pending_registration WHERE id = ?', [pending.id]);
      return res.status(400).json({ error: 'That code has expired. Please register again.' });
    }

    if (pending.attempts >= config.otp.maxAttempts) {
      await execute('DELETE FROM pending_registration WHERE id = ?', [pending.id]);
      return res.status(429).json({
        error: 'Too many incorrect codes. Please register again to get a new one.',
      });
    }

    // Compared with a timing-safe equality so the response time cannot be used
    // to discover the code digit by digit.
    if (!timingSafeEqual(code, pending.otp_code)) {
      await execute('UPDATE pending_registration SET attempts = attempts + 1 WHERE id = ?',
        [pending.id]);
      const left = config.otp.maxAttempts - (pending.attempts + 1);
      return res.status(400).json({
        error: left > 0
          ? `That code is not right. ${left} attempt${left === 1 ? '' : 's'} left.`
          : 'That code is not right. Please register again to get a new one.',
      });
    }

    // The first account to exist becomes the administrator, so a fresh install
    // is administrable without seeding anything by hand.
    const existing = await queryOne('SELECT COUNT(*) AS total FROM user');
    const role = Number(existing.total) === 0 ? 'ADMIN' : 'USER';

    try {
      await execute(
        'INSERT INTO user (full_name, email, password, role) VALUES (?, ?, ?, ?)',
        [pending.full_name, pending.email, pending.password, role],
      );
    } catch (error) {
      // Someone completed a signup for this address in the meantime.
      if (error.code === 'ER_DUP_ENTRY') {
        await execute('DELETE FROM pending_registration WHERE id = ?', [pending.id]);
        return res.status(409).json({ error: 'An account with that email already exists.' });
      }
      throw error;
    }

    // Consumed: the code cannot be used a second time.
    await execute('DELETE FROM pending_registration WHERE id = ?', [pending.id]);

    return res.status(201).json({ message: 'Account created. Please sign in.' });
  } catch (error) {
    return next(error);
  }
});

/** Issues a fresh code for a signup already waiting to be confirmed. */
router.post('/resend-otp', async (req, res, next) => {
  try {
    const email = trimmed(req.body?.email);
    if (!email) return res.status(400).json({ error: 'Please register again.' });

    const address = email.toLowerCase();
    const pending = await queryOne(
      'SELECT * FROM pending_registration WHERE email = ?',
      [address],
    );

    if (!pending) {
      return res.status(404).json({ error: 'That signup has expired. Please register again.' });
    }

    const since = Date.now() - new Date(pending.last_sent_at).getTime();
    if (since < config.otp.resendCooldownMs) {
      const wait = Math.ceil((config.otp.resendCooldownMs - since) / 1000);
      return res.status(429).json({ error: `Please wait ${wait}s before asking for another code.` });
    }

    const code = generateOtp();
    const expires = new Date(Date.now() + config.otp.ttlMs);

    await execute(
      'UPDATE pending_registration SET otp_code = ?, otp_expires = ?, attempts = 0, '
      + 'last_sent_at = NOW() WHERE id = ?',
      [code, expires, pending.id],
    );

    const emailed = await deliverOtp({ name: pending.full_name, email: address, code });

    return res.json({ message: `We sent a new code to ${address}.`, emailed });
  } catch (error) {
    return next(error);
  }
});

/** Length-independent constant-time string comparison. */
function timingSafeEqual(a, b) {
  const left = Buffer.from(String(a));
  const right = Buffer.from(String(b));
  if (left.length !== right.length) return false;
  return crypto.timingSafeEqual(left, right);
}

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

    // One message for every failure - unknown email or wrong password - so the
    // response cannot be used to discover which emails are registered.
    if (!user || user.password !== password) {
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

router.post('/logout', (req, res, next) => {
  req.session.destroy((error) => {
    if (error) return next(error);
    res.clearCookie('inkwell.sid');
    return res.json({ message: 'You have been signed out.' });
  });
});

export default router;
