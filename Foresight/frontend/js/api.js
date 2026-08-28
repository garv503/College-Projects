/* =====================================================================
   API client
   =====================================================================
   One place that knows how to talk to the backend. Pages call
   `api.get(...)` and never touch fetch, headers or tokens themselves.

   localStorage holds exactly one thing: the signed token. Identity comes
   from `GET /api/auth/me`, which the server answers based on the token's
   signature, so editing anything client-side either changes nothing or
   invalidates the signature.

   Storing `role` here instead would be the mistake to avoid - anyone can
   open the console and set it. The browser is never the authority on who
   the user is.
   ===================================================================== */

const API_BASE = (() => {
  // Served by Flask on the same origin in development and in Docker, so
  // relative URLs work. The override is for the case where the pages are
  // hosted separately (GitHub Pages, Netlify) from the API.
  const override = document.querySelector('meta[name="api-base"]')?.content;
  return (override || "").replace(/\/$/, "");
})();

const TOKEN_KEY = "fs.token";

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set token(value) {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
  get isSignedIn() {
    return Boolean(localStorage.getItem(TOKEN_KEY));
  },
};

/** An error carrying the HTTP status and the server's error code. */
export class ApiError extends Error {
  constructor(message, status, code, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;

  // FormData sets its own multipart Content-Type with a boundary string.
  // Setting it manually omits the boundary and the upload fails to parse.
  const isFormData = body instanceof FormData;
  if (body && !isFormData) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: isFormData ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    // fetch only rejects on a network-level failure, so this is
    // genuinely "the server is unreachable" rather than an HTTP error.
    throw new ApiError(
      "Cannot reach the server. Is the API running on port 5000?",
      0,
      "network_error"
    );
  }

  // An expired or invalid token means the session is over. Handled here
  // rather than in every caller, so no page has to remember to check.
  if (response.status === 401) {
    auth.clear();
    if (!location.pathname.endsWith("index.html") && location.pathname !== "/") {
      location.replace("index.html?expired=1");
    }
    const payload = await safeJson(response);
    throw new ApiError(
      payload?.error?.message || "Your session has expired",
      401,
      "unauthorized"
    );
  }

  if (raw) {
    if (!response.ok) throw await toError(response);
    return response;
  }

  const payload = await safeJson(response);

  if (!response.ok) {
    const err = payload?.error || {};
    throw new ApiError(
      err.message || `Request failed (${response.status})`,
      response.status,
      err.code || "error",
      err.details
    );
  }

  return payload;
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function toError(response) {
  const payload = await safeJson(response);
  const err = payload?.error || {};
  return new ApiError(
    err.message || `Request failed (${response.status})`,
    response.status,
    err.code || "error",
    err.details
  );
}

/** Build a query string, dropping empty values so `?q=` never appears. */
function qs(params = {}) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, value);
    }
  }
  const str = search.toString();
  return str ? `?${str}` : "";
}

export const api = {
  get: (path, params) => request(path + qs(params)),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  delete: (path) => request(path, { method: "DELETE" }),

  /** Fetch a file and hand the browser a download. */
  async download(path, params) {
    const response = await request(path + qs(params), { raw: true });
    const blob = await response.blob();

    // Prefer the filename the server chose in Content-Disposition.
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : "download.csv";

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Releasing the object URL avoids leaking the blob for the lifetime
    // of the page.
    URL.revokeObjectURL(url);
    return filename;
  },

  upload(path, file) {
    const form = new FormData();
    form.append("file", file);
    return request(path, { method: "POST", body: form });
  },
};

/* --- Session helpers -------------------------------------------------- */

export async function signIn(username, password) {
  const result = await api.post("/api/auth/login", { username, password });
  auth.token = result.token;
  return result.user;
}

export function signOut() {
  auth.clear();
  location.href = "index.html";
}

/**
 * Confirm the session with the server and return the user.
 *
 * Called on every protected page load. Redirects to the login page if
 * the token is missing or rejected - which is the only gate that
 * matters, since the API independently enforces the same rules.
 */
export async function requireSession({ role } = {}) {
  if (!auth.isSignedIn) {
    location.replace("index.html");
    throw new ApiError("Not signed in", 401, "unauthorized");
  }

  const user = await api.get("/api/auth/me");

  if (role && !role.includes(user.role)) {
    // Send them to the page their role can actually use, rather than
    // showing an empty screen full of failed requests.
    location.replace(user.role === "student" ? "dashboard.html" : "admin.html");
    throw new ApiError("Wrong role for this page", 403, "forbidden");
  }

  return user;
}
