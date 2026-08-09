import { useCallback, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Alert from '../components/Alert';
import GoogleButton from '../components/GoogleButton';
import Icon from '../components/Icon';
import PasswordInput from '../components/PasswordInput';
import { useAuth } from '../auth';

export default function Login() {
  const { signIn, signInWithGoogle, google } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  // Set by RequireAuth when it turned someone away, so they land back where
  // they were trying to go instead of always on the dashboard.
  const redirectTo = location.state?.from || '/dashboard';
  const notice = location.state?.notice;

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      await signIn(email, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const handleGoogle = useCallback(
    async (credential) => {
      setError(null);
      try {
        await signInWithGoogle(credential);
        navigate(redirectTo, { replace: true });
      } catch (err) {
        setError(err.message);
      }
    },
    [signInWithGoogle, navigate, redirectTo],
  );

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <div className="auth-head">
          <div className="auth-icon">
            <Icon name="user" />
          </div>
          <h1>Welcome back</h1>
          <p>Sign in to reach your notes.</p>
        </div>

        <div className="auth-body">
          {notice && <Alert kind="success">{notice}</Alert>}
          <Alert kind="error">{error}</Alert>

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input
                className="input"
                type="email"
                id="email"
                name="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
                autoFocus
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
              <PasswordInput
                id="password"
                value={password}
                onChange={setPassword}
                placeholder="Your password"
                autoComplete="current-password"
                required
              />
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
              <Icon name="user" /> {busy ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <GoogleButton
            clientId={google.clientId}
            onCredential={handleGoogle}
            onError={setError}
          />
        </div>

        <div className="auth-foot">
          New here? <Link to="/register">Create an account</Link>
        </div>
      </div>
    </main>
  );
}
