import Icon from './Icon';

/** Icon per kind. Anything unrecognised falls back to `success`, as before. */
const ICONS = { error: 'alert', info: 'bolt', success: 'check' };

/** Banner for flash messages, matching the ones the JSP version showed. */
export default function Alert({ kind = 'error', children }) {
  if (!children) return null;

  const variant = ICONS[kind] ? kind : 'success';

  return (
    <div
      className={`alert alert-${variant}`}
      role={variant === 'error' ? 'alert' : 'status'}
    >
      <Icon name={ICONS[variant]} />
      <span>{children}</span>
    </div>
  );
}
