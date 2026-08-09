import { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Alert from '../components/Alert';
import GoogleButton from '../components/GoogleButton';
import Icon from '../components/Icon';
import PasswordInput from '../components/PasswordInput';
import * as api from '../api';
import { useAuth } from '../auth';

export default function Register() {
  const navigate = useNavigate();
  const { signInWithGoogle, google } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      await api.register(name, email, password);
      // Registration does not sign you in; hand off to the login page with a
      // confirmation so the next step is obvious.
      navigate('/login', {
        replace: true,
        state: { notice: 'Account created. Please sign in.' },
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  // Google signups are created and signed in server-side in one step, so this
  // goes straight to the dashboard; the setup email follows separately.
  const handleGoogle = useCallback(
    async (credential) => {
      setError(null);
      try {
        await signInWithGoogle(credential);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        setError(err.message);
      }
    },
    [signInWithGoogle, navigate],
  );

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <div className="auth-head">
          <div className="auth-icon">
            <Icon name="user-plus" />
          </div>
          <h1>Create your account</h1>
          <p>Start keeping your notes in one place.</p>
        </div>

        <div className="auth-body">
          <Alert kind="error">{error}</Alert>

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="name">Full name</label>
              <input
                className="input"
                type="text"
                id="name"
                name="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Your name"
                autoComplete="name"
                maxLength={100}
                required
                autoFocus
              />
            </div>

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
                maxLength={190}
                required
              />
            </div>

            <div className="field">
              <label htmlFor="password">Password</label>
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
              <Icon name="user-plus" /> {busy ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <GoogleButton
            clientId={google.clientId}
            onCredential={handleGoogle}
            onError={setError}
          />
        </div>

        <div className="auth-foot">
          Already registered? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </main>
  );
}
