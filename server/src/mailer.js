import nodemailer from 'nodemailer';
import { config } from './config.js';

/**
 * Outgoing email.
 *
 * When SMTP is configured, mail is sent for real. When it is not - which is the
 * default for local development - the message is printed to the console
 * instead, including any link it contains, so the flow can be exercised
 * end to end without a mail account. It deliberately never throws: failing to
 * send a setup email must not fail the signup that triggered it.
 */

let transporter = null;

if (config.mail.enabled) {
  transporter = nodemailer.createTransport({
    host: config.mail.host,
    port: config.mail.port,
    // 465 is implicit TLS; other ports upgrade with STARTTLS.
    secure: config.mail.port === 465,
    auth: { user: config.mail.user, pass: config.mail.password },
  });
}

/**
 * Sends an email, or logs it when SMTP is not configured.
 *
 * @returns {Promise<{delivered: boolean, previewText?: string}>}
 */
export async function sendMail({ to, subject, text, html }) {
  if (!transporter) {
    console.log(
      '\n──────────── Inkwell: email not sent (SMTP not configured) ────────────\n'
      + `To:      ${to}\n`
      + `Subject: ${subject}\n\n`
      + `${text}\n`
      + '───────────────────────────────────────────────────────────────────────\n'
      + 'Set MAIL_HOST / MAIL_USER / MAIL_PASSWORD in server/.env to send for real.\n',
    );
    return { delivered: false };
  }

  try {
    await transporter.sendMail({ from: config.mail.from, to, subject, text, html });
    return { delivered: true };
  } catch (error) {
    // Logged, not thrown: the caller's operation already succeeded.
    console.error('[Inkwell] could not send email to', to, '-', error.message);
    return { delivered: false };
  }
}

/** The "finish setting up your account" email sent after a Google signup. */
export function accountSetupEmail({ name, link }) {
  const subject = 'Finish setting up your Inkwell account';

  const text = [
    `Hi ${name},`,
    '',
    'Your Inkwell account was created using Google sign-in.',
    '',
    'You can keep signing in with Google. If you would also like to sign in',
    'with an email and password, set a password here:',
    '',
    link,
    '',
    'This link can only be used once and expires in 24 hours.',
    '',
    'If you did not create this account, you can ignore this email.',
    '',
    '— Inkwell',
  ].join('\n');

  const html = `
    <div style="font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;
                background:#141b2b;color:#e9eefa;padding:32px;border-radius:14px">
      <h1 style="margin:0 0 4px;font-size:20px">Welcome to Inkwell, ${escapeHtml(name)}</h1>
      <p style="color:#9aa8c2;margin:0 0 24px">Your account was created using Google sign-in.</p>
      <p style="margin:0 0 20px">
        You can keep signing in with Google. If you would also like to sign in with an
        email and password, set one now:
      </p>
      <p style="margin:0 0 24px">
        <a href="${escapeHtml(link)}"
           style="display:inline-block;padding:12px 22px;border-radius:10px;
                  background:linear-gradient(135deg,#4fd1e8,#2f6fe0);color:#fff;
                  text-decoration:none;font-weight:600">Set a password</a>
      </p>
      <p style="color:#6b7994;font-size:13px;margin:0">
        This link can only be used once and expires in 24 hours.
        If you did not create this account, you can ignore this email.
      </p>
    </div>`;

  return { subject, text, html };
}

/** Escapes text interpolated into the HTML email body. */
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
