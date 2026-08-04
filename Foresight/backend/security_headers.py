"""HTTP security headers.

Headers the browser enforces on our behalf. They cost nothing to send and
they close whole classes of attack that application code cannot.

The important one is the Content-Security-Policy. Because every page in
this project loads its JavaScript from a file - there is not a single
inline `<script>` block left in frontend/ - the policy can omit
`'unsafe-inline'` from `script-src` entirely. That is what turns CSP from
decoration into a real control: even if a stored-XSS payload reached the
DOM, the browser would refuse to execute it, because the script is
neither from an allowed host nor carrying the request's nonce.

The one page that genuinely needs an inline script (the Swagger UI
bootstrap) is given a per-request nonce instead of weakening the policy
for the whole application.
"""

from __future__ import annotations

import secrets

from flask import g, request

# Hosts we deliberately load code from. Everything else is refused.
#   cdn.jsdelivr.net - Chart.js, pinned to an exact version
#   unpkg.com        - Swagger UI, only on /api/docs
SCRIPT_HOSTS = ("https://cdn.jsdelivr.net", "https://unpkg.com")
STYLE_HOSTS = ("https://unpkg.com",)


def _content_security_policy(nonce: str) -> str:
    """Build the policy for this request."""
    directives = {
        # Nothing is allowed unless a more specific directive permits it.
        "default-src": ["'self'"],
        "script-src": ["'self'", f"'nonce-{nonce}'", *SCRIPT_HOSTS],
        # `'unsafe-inline'` is unavoidable for styles: the markup uses a
        # handful of `style="..."` attributes and Swagger UI injects its
        # own. An injected stylesheet is a far smaller problem than
        # injected script, which is why the same exception is not made
        # above.
        "style-src": ["'self'", "'unsafe-inline'", *STYLE_HOSTS],
        # data: covers the inline SVG chevron on <select> and the favicon.
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'", "data:"],
        # The front end only ever calls its own API. This is what stops
        # injected script from exfiltrating data to another host.
        "connect-src": ["'self'"],
        # No Flash, Java, or <object> of any kind.
        "object-src": ["'none'"],
        # Stops an injected <base> tag redirecting every relative URL.
        "base-uri": ["'self'"],
        # Forms can only submit back to us.
        "form-action": ["'self'"],
        # Clickjacking: the modern replacement for X-Frame-Options.
        "frame-ancestors": ["'none'"],
    }
    return "; ".join(f"{key} {' '.join(values)}" for key, values in directives.items())


def init_app(app) -> None:
    """Attach the nonce generator and the response headers."""

    @app.before_request
    def _assign_nonce():
        # A fresh, unguessable value per request. Reusing one across
        # requests would let an attacker who learned it embed a script
        # that passes the policy.
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.after_request
    def _set_headers(response):
        nonce = g.get("csp_nonce", "")
        response.headers.setdefault(
            "Content-Security-Policy", _content_security_policy(nonce)
        )

        # Stops the browser second-guessing a declared Content-Type. Without
        # it, a text/plain response containing markup can be sniffed as HTML
        # and executed.
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # frame-ancestors above supersedes this, but it is still honoured by
        # older browsers that ignore CSP.
        response.headers.setdefault("X-Frame-Options", "DENY")

        # Send the full URL only to ourselves. Roll-number-bearing URLs
        # should not leak to a third party in a Referer header.
        response.headers.setdefault("Referrer-Policy", "same-origin")

        # Switch off device APIs the app never uses, so injected script
        # cannot reach for them either.
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), interest-cohort=()",
        )

        # API responses carry marks, and sometimes credentials. Keeping
        # them out of the browser's disk cache means closing the laptop
        # lid is enough - the next person cannot page back to them.
        if request.path.startswith("/api/"):
            response.headers.setdefault(
                "Cache-Control", "no-store, no-cache, must-revalidate"
            )
            response.headers.setdefault("Pragma", "no-cache")

        # Only meaningful over TLS, and actively harmful to set on a plain
        # http deployment - a browser that caches it will refuse to load
        # the site over http afterwards.
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        # Note on the `Server` header: it is NOT set here, because it
        # cannot be. gunicorn writes its own after Flask has finished and
        # overrides whatever the application set - neither popping nor
        # assigning the header from this handler has any effect, which is
        # worth stating so nobody adds that line back believing it works.
        #
        # It sends the bare product name (`gunicorn`) with no version, so
        # nothing exploitable leaks. Removing the name entirely is a job
        # for a reverse proxy in front of the app:
        #     nginx:  proxy_hide_header Server;  server_tokens off;

        return response
