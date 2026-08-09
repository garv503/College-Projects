/**
 * Inline SVG icons, carried over from the JSP sprite.
 *
 * Kept as data rather than separate files so a single <symbol> set renders once
 * per page and every icon inherits `currentColor` from its surroundings.
 */

export const ICON_SPRITE = (
  <svg xmlns="http://www.w3.org/2000/svg" style={{ display: 'none' }} aria-hidden="true" focusable="false">
    <symbol id="i-book" viewBox="0 0 24 24">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </symbol>
    <symbol id="i-home" viewBox="0 0 24 24">
      <path d="M3 9.5 12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" />
    </symbol>
    <symbol id="i-plus" viewBox="0 0 24 24">
      <path d="M12 5v14M5 12h14" />
    </symbol>
    <symbol id="i-notes" viewBox="0 0 24 24">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M8 13h8M8 17h5" />
    </symbol>
    <symbol id="i-user" viewBox="0 0 24 24">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </symbol>
    <symbol id="i-user-plus" viewBox="0 0 24 24">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M19 8v6M22 11h-6" />
    </symbol>
    <symbol id="i-logout" viewBox="0 0 24 24">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="m16 17 5-5-5-5M21 12H9" />
    </symbol>
    <symbol id="i-edit" viewBox="0 0 24 24">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4z" />
    </symbol>
    <symbol id="i-trash" viewBox="0 0 24 24">
      <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M10 11v6M14 11v6" />
    </symbol>
    <symbol id="i-pin" viewBox="0 0 24 24">
      <path d="M12 17v5" />
      <path d="M9 4h6l-1 6 3 3v1H7v-1l3-3z" />
    </symbol>
    <symbol id="i-search" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </symbol>
    <symbol id="i-check" viewBox="0 0 24 24">
      <path d="M20 6 9 17l-5-5" />
    </symbol>
    <symbol id="i-alert" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v5M12 16h.01" />
    </symbol>
    <symbol id="i-clock" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </symbol>
    <symbol id="i-lock" viewBox="0 0 24 24">
      <rect x="4" y="10" width="16" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
    </symbol>
    <symbol id="i-bolt" viewBox="0 0 24 24">
      <path d="M13 2 4 14h7l-1 8 9-12h-7z" />
    </symbol>
    <symbol id="i-menu" viewBox="0 0 24 24">
      <path d="M3 6h18M3 12h18M3 18h18" />
    </symbol>
    <symbol id="i-arrow-left" viewBox="0 0 24 24">
      <path d="M19 12H5M12 19l-7-7 7-7" />
    </symbol>
    <symbol id="i-eye" viewBox="0 0 24 24">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </symbol>
    <symbol id="i-eye-off" viewBox="0 0 24 24">
      <path d="M10.6 6.2A9.9 9.9 0 0 1 12 5c6.4 0 10 7 10 7a18 18 0 0 1-3 4M6.2 6.4A18.4 18.4 0 0 0 2 12s3.6 7 10 7a9.8 9.8 0 0 0 4.5-1.1" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2M3 3l18 18" />
    </symbol>
  </svg>
);

export default function Icon({ name, className = 'icon', style }) {
  return (
    <svg className={className} style={style}>
      <use href={`#i-${name}`} />
    </svg>
  );
}
