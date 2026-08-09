import Icon from './Icon';

/** Success/error banner, matching the flash messages the JSP version showed. */
export default function Alert({ kind = 'error', children }) {
  if (!children) return null;

  const isError = kind === 'error';

  return (
    <div className={`alert alert-${isError ? 'error' : 'success'}`} role={isError ? 'alert' : 'status'}>
      <Icon name={isError ? 'alert' : 'check'} />
      <span>{children}</span>
    </div>
  );
}
