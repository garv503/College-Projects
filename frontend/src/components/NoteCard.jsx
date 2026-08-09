import { Link } from 'react-router-dom';
import Icon from './Icon';

/** Formats an epoch-millis timestamp in the reader's own locale and timezone. */
export function formatDate(millis, withTime = false) {
  if (!millis) return '';
  const options = { day: 'numeric', month: 'short', year: 'numeric' };
  if (withTime) {
    options.hour = '2-digit';
    options.minute = '2-digit';
  }
  return new Date(millis).toLocaleString(undefined, options);
}

/**
 * A single note.
 *
 * React escapes interpolated text, so a note whose body contains markup is
 * displayed rather than executed.
 */
export default function NoteCard({ note, onTogglePin, onDelete, showActions = true, withTime = true }) {
  return (
    <article className={`note${note.pinned ? ' is-pinned' : ''}`}>
      <div className="note-body">
        <h3 className="note-title">
          {note.pinned && (
            <span className="note-pin-marker" title="Pinned">
              <Icon name="pin" />
            </span>
          )}
          {note.title}
        </h3>
        <p className="note-content">{note.content}</p>
      </div>

      <div className="note-meta">
        <span className="tag">
          <Icon name="clock" style={{ width: 12, height: 12 }} />
          {formatDate(note.createdAt, withTime)}
        </span>
        {note.pinned && <span className="tag tag-pinned">pinned</span>}
        {note.edited && <span className="tag">edited</span>}
      </div>

      {showActions && (
        <div className="note-actions">
          {onTogglePin && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => onTogglePin(note)}
              title={note.pinned ? 'Unpin this note' : 'Pin this note'}
            >
              <Icon name="pin" /> {note.pinned ? 'Unpin' : 'Pin'}
            </button>
          )}

          <Link className="btn btn-ghost btn-sm" to={`/notes/${note.id}/edit`}>
            <Icon name="edit" /> Edit
          </Link>

          {onDelete && (
            <button
              type="button"
              className="btn btn-danger btn-sm spacer"
              onClick={() => onDelete(note)}
              title="Delete this note"
            >
              <Icon name="trash" /> Delete
            </button>
          )}
        </div>
      )}
    </article>
  );
}
