import crypto from 'node:crypto';
import { queryOne } from '../db.js';
import { publicView } from '../userView.js';

/**
 * Session, authorisation and CSRF guards.
 *
 * These are the security boundary. The React route guards only decide what to
 * render; every rule that actually matters is enforced here, on every request.
 */

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

/** Returns the session's CSRF token, creating one on first use. */
export function csrfToken(req) {
  if (!req.session.csrfToken) {
    req.session.csrfToken = crypto.randomBytes(32).toString('base64url');
  }
  return req.session.csrfToken;
}

/**
 * Rejects state-changing requests that do not carry the session's CSRF token.
 *
 * The token travels in a header rather than the body because the API speaks
 * JSON; an attacker's page can cause a request but cannot read the token, so it
 * cannot forge one.
 */
export function csrfProtection(exemptPaths = []) {
  const exempt = new Set(exemptPaths);

  return (req, res, next) => {
    if (SAFE_METHODS.has(req.method) || exempt.has(req.path)) {
      return next();
    }

    const expected = req.session?.csrfToken;
    const supplied = req.get('X-CSRF-Token');

    if (!expected || !supplied || !timingSafeEqual(expected, supplied)) {
      return res.status(403).json({
        error: 'Invalid or missing security token. Please reload the page and try again.',
      });
    }
    return next();
  };
}

/**
 * Re-reads the signed-in user from the database on every request.
 *
 * The session stores a snapshot taken at sign-in, so without this an account
 * deleted mid-session would stay usable, and an administrator who was demoted
 * would keep administrator access until their session expired. Re-reading makes
 * both take effect on the very next request.
 *
 * Costs one indexed primary-key lookup per API call, which is the right trade
 * for authorisation that is actually current.
 */
export async function refreshSession(req, res, next) {
  if (!req.session?.user) return next(); // Signed out; the guards handle it.

  try {
    const row = await queryOne(
      'SELECT id, full_name, email, role, created_at FROM user WHERE id = ?',
      [req.session.user.id],
    );

    if (!row) {
      // The account no longer exists; the session is meaningless.
      return req.session.destroy(() => {
        res.clearCookie('inkwell.sid');
        res.status(401).json({ error: 'Your account is no longer available. Please sign in again.' });
      });
    }

    req.session.user = publicView(row);
    return next();
  } catch (error) {
    return next(error);
  }
}

/** Requires a signed-in session. */
export function requireAuth(req, res, next) {
  if (!req.session?.user) {
    return res.status(401).json({ error: 'Please sign in to continue.' });
  }
  return next();
}

/**
 * Requires an administrator.
 *
 * The role is read from the session, which is set at sign-in from the database
 * and cannot be altered by the client.
 */
export function requireAdmin(req, res, next) {
  if (!req.session?.user) {
    return res.status(401).json({ error: 'Please sign in to continue.' });
  }
  if (req.session.user.role !== 'ADMIN') {
    // 403, not 404: the caller is known, they simply are not allowed.
    return res.status(403).json({ error: 'Administrator access is required.' });
  }
  return next();
}

/** Compares two strings without leaking how much of them matched via timing. */
function timingSafeEqual(a, b) {
  const bufferA = Buffer.from(a, 'utf8');
  const bufferB = Buffer.from(b, 'utf8');
  if (bufferA.length !== bufferB.length) return false;
  return crypto.timingSafeEqual(bufferA, bufferB);
}
