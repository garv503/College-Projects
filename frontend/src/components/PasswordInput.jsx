import { useRef, useState } from 'react';
import Icon from './Icon';

/** Password field with the show/hide control inside it. */
export default function PasswordInput({ id, value, onChange, placeholder, autoComplete, minLength, required }) {
  const [revealed, setRevealed] = useState(false);
  const inputRef = useRef(null);

  function toggle() {
    setRevealed((wasRevealed) => !wasRevealed);

    // Clicking the button takes focus off the field; put the caret back at the
    // end so typing can continue uninterrupted.
    const input = inputRef.current;
    if (input) {
      const caret = input.value.length;
      input.focus();
      try {
        input.setSelectionRange(caret, caret);
      } catch {
        /* Some browsers reject setSelectionRange on certain input types. */
      }
    }
  }

  return (
    <div className="password-wrap">
      <input
        ref={inputRef}
        className="input"
        type={revealed ? 'text' : 'password'}
        id={id}
        name={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        minLength={minLength}
        required={required}
      />
      <button
        type="button"
        className="password-toggle"
        onClick={toggle}
        aria-pressed={revealed}
        aria-label={revealed ? 'Hide password' : 'Show password'}
        title={revealed ? 'Hide password' : 'Show password'}
      >
        <Icon name={revealed ? 'eye-off' : 'eye'} />
      </button>
    </div>
  );
}
