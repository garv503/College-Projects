import { useEffect, useRef, useState } from 'react';

const SCRIPT_ID = 'google-identity-services';
const SCRIPT_SRC = 'https://accounts.google.com/gsi/client';

/** Loads Google Identity Services once, shared by every mount of this button. */
function loadGoogleScript() {
  if (window.google?.accounts?.id) return Promise.resolve();

  const existing = document.getElementById(SCRIPT_ID);
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', resolve);
      existing.addEventListener('error', reject);
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.id = SCRIPT_ID;
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error('Could not load Google sign-in.'));
    document.head.appendChild(script);
  });
}

/**
 * "Continue with Google" button.
 *
 * Google hands back an ID token, which is passed straight to the server - the
 * browser is not trusted to say who the user is; the token is verified
 * server-side against Google's keys.
 *
 * When no client id is configured the real button cannot work, so a disabled
 * placeholder is shown that says why. Showing a live-looking button that fails
 * on click would be worse, and rendering nothing at all makes a configuration
 * gap look like a missing feature.
 *
 * This is the one place the app talks to a third-party origin. Everything else
 * is self-hosted.
 */
export default function GoogleButton({ clientId, onCredential, onError }) {
  const container = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!clientId) return undefined;

    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !container.current) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => {
            if (response?.credential) {
              onCredential(response.credential);
            } else {
              onError?.('Google sign-in did not return a credential.');
            }
          },
        });

        window.google.accounts.id.renderButton(container.current, {
          theme: 'filled_black',
          size: 'large',
          shape: 'pill',
          width: 320,
          text: 'continue_with',
        });
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [clientId, onCredential, onError]);

  return (
    <div className="google-signin">
      <div className="divider"><span>or</span></div>

      {!clientId ? (
        <div className="google-placeholder">
          <button type="button" className="btn btn-outline btn-block" disabled>
            <GoogleMark /> Continue with Google
          </button>
          <p className="field-hint" style={{ textAlign: 'center' }}>
            Not configured yet — set <code>GOOGLE_CLIENT_ID</code> in{' '}
            <code>server/.env</code> to switch this on.
          </p>
        </div>
      ) : failed ? (
        <p className="field-hint" style={{ textAlign: 'center' }}>
          Google sign-in could not be loaded. Check your connection and reload.
        </p>
      ) : (
        <div ref={container} className="google-button-slot" />
      )}
    </div>
  );
}

/** Google's mark, inlined so the placeholder needs no third-party request. */
function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A9 9 0 0 0 9 18z" />
      <path fill="#FBBC05" d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.94H.96a9 9 0 0 0 0 8.12l3.01-2.34z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58z" />
    </svg>
  );
}
