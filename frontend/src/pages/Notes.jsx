import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Alert from '../components/Alert';
import Icon from '../components/Icon';
import NoteCard from '../components/NoteCard';
import * as api from '../api';

export default function Notes() {
  // The search term lives in the URL, so a search can be linked and survives a
  // refresh or a back-navigation.
  const [searchParams, setSearchParams] = useSearchParams();
  const search = searchParams.get('q') || '';

  const [term, setTerm] = useState(search);
  const [notes, setNotes] = useState([]);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setTerm(search);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setNotes(await api.listNotes(search));
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  function handleSearch(event) {
    event.preventDefault();
    const trimmed = term.trim();
    setSearchParams(trimmed ? { q: trimmed } : {});
  }

  async function handleTogglePin(note) {
    try {
      const updated = await api.togglePin(note.id);
      // Pinned notes sort to the top, so re-fetch rather than patching in place
      // and leaving the list in the wrong order.
      setNotes((current) =>
        [...current.map((n) => (n.id === updated.id ? updated : n))].sort(
          (a, b) => Number(b.pinned) - Number(a.pinned) || b.createdAt - a.createdAt,
        ),
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(note) {
    if (!window.confirm('Delete this note? This cannot be undone.')) return;

    try {
      await api.deleteNote(note.id);
      setNotes((current) => current.filter((n) => n.id !== note.id));
      setMessage('Note deleted.');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="page">
      <div className="container">
        <Alert kind="success">{message}</Alert>
        <Alert kind="error">{error}</Alert>

        <div className="page-head">
          <div>
            <h1>My notes</h1>
            <p className="sub">
              {search
                ? `${notes.length} result${notes.length === 1 ? '' : 's'} for “${search}”`
                : 'Everything you have saved, pinned notes first.'}
            </p>
          </div>
          <Link className="btn btn-primary" to="/notes/new">
            <Icon name="plus" /> New note
          </Link>
        </div>

        <div className="toolbar">
          <form className="search-form" onSubmit={handleSearch} role="search">
            <input
              className="input"
              type="search"
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              placeholder="Search your notes..."
              aria-label="Search notes"
            />
            <button type="submit" className="btn btn-outline">
              <Icon name="search" />
              <span className="visually-hidden">Search</span>
            </button>
          </form>

          {search && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSearchParams({})}>
              Clear search
            </button>
          )}
        </div>

        {loading ? (
          <p className="sub">Loading...</p>
        ) : notes.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">
              <Icon name={search ? 'search' : 'notes'} />
            </div>
            {search ? (
              <>
                <h3>No matches</h3>
                <p>Nothing matched &ldquo;{search}&rdquo;. Try a different word.</p>
                <button type="button" className="btn btn-outline" onClick={() => setSearchParams({})}>
                  Show all notes
                </button>
              </>
            ) : (
              <>
                <h3>Nothing here yet</h3>
                <p>Write your first note and it will appear right here.</p>
                <Link className="btn btn-primary" to="/notes/new">
                  <Icon name="plus" /> Write a note
                </Link>
              </>
            )}
          </div>
        ) : (
          <div className="notes-grid">
            {notes.map((note) => (
              <NoteCard
                key={note.id}
                note={note}
                onTogglePin={handleTogglePin}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
