import nodemailer from 'nodemailer';
import { config } from './config.js';

/**
 * Outgoing email.
 *
 * When SMTP is configured, mail is sent for real. When it is not - the default
 * locally - the message is printed to the server console instead, code and all,
 * so registration can be completed end to end without a mail account.
 *
 * Sending deliberately never throws. A signup must not fail because the mail
 * server did; the caller decides what to tell the user.
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

/** True when a real message would be sent rather than printed to the console. */
export const mailEnabled = () => Boolean(transporter);

/**
 * Sends an email, or logs it when SMTP is not configured.
 *
 * @returns {Promise<{delivered: boolean}>}
 */
export async function sendMail({ to, subject, text, html }) {
  if (!transporter) {
    console.log(
      '\n──────────── Inkwell: email not sent (SMTP not configured) ────────────\n'
      + `To:      ${to}\n`
      + `Subject: ${subject}\n\n`
      + `${text}\n`
      + '───────────────────────────────────────────────────────────────────────\n'
      + 'Set MAIL_HOST / MAIL_USER / MAIL_PASSWORD to send this for real.\n',
    );
    return { delivered: false };
  }

  try {
    await transporter.sendMail({ from: config.mail.from, to, subject, text, html });
    return { delivered: true };
  } catch (error) {
    // Logged, not thrown: the caller's operation is still valid.
    console.error('[Inkwell] could not send email to', to, '-', error.message);
    return { delivered: false };
  }
}

/** The "confirm your email address" message sent during registration. */
export function verificationEmail({ name, code, minutes }) {
  const subject = `${code} is your Inkwell verification code`;

  const text = [
    `Hi ${name},`,
    '',
    'Use this code to finish creating your Inkwell account:',
    '',
    `    ${code}`,
    '',
    `The code expires in ${minutes} minutes and can only be used once.`,
    '',
    'If you did not try to create an account, you can ignore this email.',
    '',
    '— Inkwell',
  ].join('\n');

  const html = `
    <div style="font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;
                background:#141b2b;color:#e9eefa;padding:32px;border-radius:14px">
      <h1 style="margin:0 0 4px;font-size:20px">Confirm your email, ${escapeHtml(name)}</h1>
      <p style="color:#9aa8c2;margin:0 0 24px">
        Enter this code to finish creating your Inkwell account.
      </p>
      <p style="margin:0 0 24px;font-size:34px;font-weight:700;letter-spacing:0.22em;
                text-align:center;padding:18px;border-radius:12px;background:#0d1320;
                border:1px solid #24304a;color:#4fd1e8">${escapeHtml(code)}</p>
      <p style="color:#6b7994;font-size:13px;margin:0">
        The code expires in ${minutes} minutes and can only be used once.
        If you did not try to create an account, you can ignore this email.
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
