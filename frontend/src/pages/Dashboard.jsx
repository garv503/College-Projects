import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Alert from '../components/Alert';
import Icon from '../components/Icon';
import NoteCard, { formatDate } from '../components/NoteCard';
import * as api from '../api';
import { useAuth } from '../auth';

export default function Dashboard() {
  const { user } = useAuth();

  const [stats, setStats] = useState({ totalNotes: 0, pinnedNotes: 0 });
  const [notes, setNotes] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    Promise.all([api.getStats(), api.listNotes()])
      .then(([loadedStats, loadedNotes]) => {
        if (cancelled) return;
        setStats(loadedStats);
        setNotes(loadedNotes);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="page">
      <div className="container">
        <Alert kind="error">{error}</Alert>

        <div className="page-head">
          <div>
            <h1>Hello, {user?.name}</h1>
            <p className="sub">Here is what you have saved so far.</p>
          </div>
          <Link className="btn btn-primary" to="/notes/new">
            <Icon name="plus" /> New note
          </Link>
        </div>

        <div className="stat-grid">
          <div className="stat">
            <div className="stat-label">
              <Icon name="notes" /> Total notes
            </div>
            <div className="stat-value">{stats.totalNotes}</div>
          </div>

          <div className="stat">
            <div className="stat-label">
              <Icon name="pin" /> Pinned
            </div>
            <div className="stat-value">{stats.pinnedNotes}</div>
          </div>

          <div className="stat">
            <div className="stat-label">
              <Icon name="clock" /> Member since
            </div>
            <div className="stat-value" style={{ fontSize: '1.25rem' }}>
              {user?.createdAt ? formatDate(user.createdAt) : '—'}
            </div>
          </div>
        </div>

        {loading ? (
          <p className="sub">Loading your notes...</p>
        ) : notes.length === 0 ? (
          <div className="empty">
            <div className="empty-icon">
              <Icon name="notes" />
            </div>
            <h3>No notes yet</h3>
            <p>Your notes will show up here once you write your first one.</p>
            <Link className="btn btn-primary" to="/notes/new">
              <Icon name="plus" /> Write your first note
            </Link>
          </div>
        ) : (
          <>
            <div className="page-head">
              <h2>Recent notes</h2>
              <Link to="/notes">View all {stats.totalNotes} &rarr;</Link>
            </div>

            <div className="notes-grid">
              {/* A preview only; the full list lives on /notes. */}
              {notes.slice(0, 6).map((note) => (
                <NoteCard key={note.id} note={note} withTime={false} />
              ))}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
