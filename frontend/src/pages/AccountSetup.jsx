import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import Alert from '../components/Alert';
import Icon from '../components/Icon';
import PasswordInput from '../components/PasswordInput';
import * as api from '../api';

/**
 * Target of the "set a password" link in the account-setup email.
 *
 * The token is validated before the form is shown, so an expired or already-used
 * link says so immediately instead of after the user has typed a password.
 */
export default function AccountSetup() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [account, setAccount] = useState(null);
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('That link is invalid or has expired.');
      setChecking(false);
      return undefined;
    }

    let cancelled = false;

    api
      .checkSetupToken(token)
      .then((data) => {
        if (!cancelled) setAccount(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      await api.setupPassword(token, password);
      setDone(true);
      // Give the confirmation a moment to register before moving on.
      setTimeout(() => navigate('/login', {
        replace: true,
        state: { notice: 'Password set. You can now sign in with your email address.' },
      }), 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <div className="auth-head">
          <div className="auth-icon">
            <Icon name={done ? 'check' : 'lock'} />
          </div>
          <h1>{done ? 'All set' : 'Set your password'}</h1>
          <p>
            {done
              ? 'Taking you to the sign-in page...'
              : account
                ? `Add a password to ${account.email} so you can sign in without Google.`
                : 'Finish setting up your account.'}
          </p>
        </div>

        <div className="auth-body">
          <Alert kind="error">{error}</Alert>

          {checking ? (
            <p className="sub">Checking your link...</p>
          ) : account && !done ? (
            <form onSubmit={handleSubmit} noValidate>
              <div className="field">
                <label htmlFor="password">New password</label>
                <PasswordInput
                  id="password"
                  value={password}
                  onChange={setPassword}
                  placeholder="At least 8 characters"
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
                <p className="field-hint">Use 8 characters or more.</p>
              </div>

              <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
                <Icon name="check" /> {busy ? 'Saving...' : 'Set password'}
              </button>
            </form>
          ) : !done ? (
            <p className="sub">
              Ask for a new link by signing in with Google again, or{' '}
              <Link to="/register">create an account</Link>.
            </p>
          ) : null}
        </div>

        <div className="auth-foot">
          <Link to="/login">Back to sign in</Link>
        </div>
      </div>
    </main>
  );
}
