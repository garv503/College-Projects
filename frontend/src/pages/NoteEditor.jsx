import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Alert from '../components/Alert';
import Icon from '../components/Icon';
import * as api from '../api';

/**
 * Create and edit share this page: the two forms were identical apart from
 * their heading and which call they made on submit.
 */
export default function NoteEditor({ mode }) {
  const isEdit = mode === 'edit';
  const { id } = useParams();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(isEdit);

  useEffect(() => {
    if (!isEdit) return undefined;

    let cancelled = false;

    api
      .getNote(id)
      .then((note) => {
        if (cancelled) return;
        setTitle(note.title);
        setContent(note.content);
      })
      .catch((err) => {
        if (cancelled) return;
        // A note that is missing, or belongs to someone else, comes back as 404;
        // there is nothing to edit, so return to the list.
        if (err.status === 404) {
          navigate('/notes', { replace: true });
          return;
        }
        setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id, isEdit, navigate]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);

    try {
      if (isEdit) {
        await api.updateNote(id, title, content);
      } else {
        await api.createNote(title, content);
      }
      navigate('/notes');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <div className="container" style={{ maxWidth: 800 }}>
        <Alert kind="error">{error}</Alert>

        <div className="page-head">
          <div>
            <h1>{isEdit ? 'Edit note' : 'New note'}</h1>
            <p className="sub">
              {isEdit ? 'Changes are saved to this note only.' : 'Give it a title and write whatever you need.'}
            </p>
          </div>
          <Link className="btn btn-ghost btn-sm" to="/notes">
            <Icon name="arrow-left" /> Back to notes
          </Link>
        </div>

        <div className="card">
          <div className="card-body">
            {loading ? (
              <p className="sub">Loading note...</p>
            ) : (
              <form onSubmit={handleSubmit} noValidate>
                <div className="field">
                  <label htmlFor="title">Title</label>
                  <input
                    className="input"
                    type="text"
                    id="title"
                    name="title"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="What is this note about?"
                    maxLength={200}
                    required
                    autoFocus
                  />
                </div>

                <div className="field">
                  <label htmlFor="content">Content</label>
                  <textarea
                    className="textarea"
                    id="content"
                    name="content"
                    value={content}
                    onChange={(event) => setContent(event.target.value)}
                    placeholder="Start writing..."
                    maxLength={20000}
                    required
                  />
                  <p className="field-hint">Line breaks are preserved.</p>
                </div>

                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <button type="submit" className="btn btn-primary" disabled={busy}>
                    <Icon name="check" /> {busy ? 'Saving...' : isEdit ? 'Save changes' : 'Save note'}
                  </button>
                  <Link className="btn btn-outline" to="/notes">
                    Cancel
                  </Link>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
