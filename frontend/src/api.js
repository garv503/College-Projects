/**
 * Thin wrapper over fetch for the Inkwell API.
 *
 * Two things every call needs and none of the callers should have to remember:
 *
 *  - `credentials: 'same-origin'`, so the session cookie is sent. Without it
 *    every request looks signed-out.
 *  - the CSRF token header on writes. The server rejects any non-GET without it.
 */

const BASE = '/api';

let csrfToken = null;

/** Errors carrying the HTTP status, so callers can treat 401 as "signed out". */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = {};

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  if (method !== 'GET') {
    // A page reached directly by URL (the emailed setup link, for instance)
    // may write before anything has fetched a token. Fetch one rather than
    // letting the request fail the CSRF check. The session probe is a GET, so
    // this cannot recurse.
    if (!csrfToken) {
      await getSession();
    }
    headers['X-CSRF-Token'] = csrfToken;
  }

  const response = await fetch(BASE + path, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  // 204 and empty bodies are valid; don't blow up trying to parse them.
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new ApiError(data.error || 'Something went wrong.', response.status);
  }
  return data;
}

/**
 * Current user plus the CSRF token for this session.
 *
 * Returns `{ user: null }` when signed out rather than failing, so the app can
 * call it on load to decide what to render.
 */
export async function getSession() {
  const data = await request('/auth/session');
  csrfToken = data.csrfToken;
  return data;
}

export async function login(email, password) {
  const data = await request('/auth/login', {
    method: 'POST',
    body: { email, password },
  });
  // Signing in starts a new session, so the old token is dead - take the new one.
  csrfToken = data.csrfToken;
  return data.user;
}

/**
 * Step 1 of signing up: emails a confirmation code.
 *
 * No account exists until `verifyOtp` confirms that code.
 */
export async function register(name, email, password) {
  return request('/auth/register', {
    method: 'POST',
    body: { name, email, password },
  });
}

/** Step 2: confirms the code and creates the account. */
export async function verifyOtp(email, code) {
  return request('/auth/verify-otp', {
    method: 'POST',
    body: { email, code },
  });
}

/** Issues a fresh code for a signup waiting to be confirmed. */
export async function resendOtp(email) {
  return request('/auth/resend-otp', {
    method: 'POST',
    body: { email },
  });
}

export async function logout() {
  await request('/auth/logout', { method: 'POST' });
  // The session is gone; the token belonged to it.
  csrfToken = null;
}

export async function listNotes(search) {
  const query = search ? `?q=${encodeURIComponent(search)}` : '';
  const data = await request(`/notes${query}`);
  return data.notes;
}

export async function getNote(id) {
  const data = await request(`/notes/${id}`);
  return data.note;
}

export async function createNote(title, content) {
  return request('/notes', { method: 'POST', body: { title, content } });
}

export async function updateNote(id, title, content) {
  return request(`/notes/${id}`, { method: 'PUT', body: { title, content } });
}

export async function deleteNote(id) {
  return request(`/notes/${id}`, { method: 'DELETE' });
}

export async function togglePin(id) {
  const data = await request(`/notes/${id}/pin`, { method: 'POST' });
  return data.note;
}

export async function getStats() {
  return request('/stats');
}

/* --------------------------------------------------------------- admin only */
/* The server enforces the ADMIN role on all of these; hiding the UI is only a
   convenience, never the check that matters. */

export async function listUsers() {
  const data = await request('/admin/users');
  return data.users;
}

export async function getAdminStats() {
  return request('/admin/stats');
}

export async function setUserRole(id, role) {
  return request(`/admin/users/${id}/role`, { method: 'PATCH', body: { role } });
}

export async function deleteUser(id) {
  return request(`/admin/users/${id}`, { method: 'DELETE' });
}
