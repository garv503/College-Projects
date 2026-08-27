import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Alert from '../components/Alert';
import Icon from '../components/Icon';
import PasswordInput from '../components/PasswordInput';
import * as api from '../api';

/**
 * Signing up, in two steps.
 *
 * `details` collects the account; `code` confirms the address with the one-time
 * code emailed in between. The account does not exist until the code is
 * accepted, so leaving the page at the code step creates nothing.
 */
export default function Register() {
  const navigate = useNavigate();

  const [step, setStep] = useState('details');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [code, setCode] = useState('');
  const [sentTo, setSentTo] = useState('');
  const [emailed, setEmailed] = useState(true);
  const [notice, setNotice] = useState(null);

  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  const codeInput = useRef(null);

  // Move focus to the code box when it appears, so the next thing typed lands
  // where it should without a click.
  useEffect(() => {
    if (step === 'code') codeInput.current?.focus();
  }, [step]);

  // Counts the resend cooldown down to zero, matching the server's own limit.
  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const timer = setTimeout(() => setCooldown((n) => n - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  async function handleDetails(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      const result = await api.register(name, email, password);
      setSentTo(result.email);
      setEmailed(result.emailed);
      // No notice here - the heading already says a code was sent. The banner
      // is reserved for a resend, where it is the only confirmation.
      setNotice(null);
      setStep('code');
      setCooldown(60);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCode(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      await api.verifyOtp(sentTo, code);
      // The account exists now but you are not signed in; hand off to the login
      // page with a confirmation so the next step is obvious.
      navigate('/login', {
        replace: true,
        state: { notice: 'Account created. Please sign in.' },
      });
    } catch (err) {
      setError(err.message);
      setCode('');
      codeInput.current?.focus();
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setError(null);
    setNotice(null);
    setBusy(true);

    try {
      const result = await api.resendOtp(sentTo);
      setNotice(result.message);
      setEmailed(result.emailed);
      setCooldown(60);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  /* ------------------------------------------------------------ step two */

  if (step === 'code') {
    return (
      <main className="auth-shell">
        <div className="auth-card">
          <div className="auth-head">
            <div className="auth-icon">
              <Icon name="mail" />
            </div>
            <h1>Check your email</h1>
            <p>
              We sent a 6-digit code to <strong>{sentTo}</strong>.
            </p>
          </div>

          <div className="auth-body">
            <Alert kind="error">{error}</Alert>
            {notice && !error && <Alert kind="success">{notice}</Alert>}

            {!emailed && (
              <Alert kind="info">
                Email is not configured on this server, so the code was printed to
                the server console instead of being sent.
              </Alert>
            )}

            <form onSubmit={handleCode} noValidate>
              <div className="field">
                <label htmlFor="code">Verification code</label>
                <input
                  className="input otp-input"
                  type="text"
                  id="code"
                  name="code"
                  ref={codeInput}
                  value={code}
                  // Strip anything that is not a digit, so a pasted code with
                  // spaces or a stray dash still works.
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000000"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  required
                />
                <p className="field-hint">The code expires in 10 minutes.</p>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-block"
                disabled={busy || code.length < 6}
              >
                <Icon name="check" /> {busy ? 'Verifying...' : 'Verify and create account'}
              </button>
            </form>

            <div className="auth-actions">
              <button
                type="button"
                className="btn btn-ghost"
                onClick={handleResend}
                disabled={busy || cooldown > 0}
              >
                {cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setStep('details');
                  setCode('');
                  setError(null);
                  setNotice(null);
                }}
                disabled={busy}
              >
                Use a different email
              </button>
            </div>
          </div>

          <div className="auth-foot">
            Already registered? <Link to="/login">Sign in</Link>
          </div>
        </div>
      </main>
    );
  }

  /* ------------------------------------------------------------ step one */

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

          <form onSubmit={handleDetails} noValidate>
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
              <p className="field-hint">We will email you a code to confirm it.</p>
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
              <Icon name="user-plus" /> {busy ? 'Sending code...' : 'Continue'}
            </button>
          </form>
        </div>

        <div className="auth-foot">
          Already registered? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </main>
  );
}
