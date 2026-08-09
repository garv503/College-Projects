import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import { useAuth } from '../auth';

export default function NotFound() {
  const { user } = useAuth();

  return (
    <main className="page">
      <div className="container">
        <div className="empty">
          <div className="empty-icon" style={{ color: 'var(--danger)', background: 'var(--danger-bg)' }}>
            <Icon name="alert" />
          </div>
          <h3>Page not found</h3>
          <p>That page does not exist. It may have moved, or the link may be wrong.</p>

          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            {user ? (
              <>
                <Link className="btn btn-primary" to="/dashboard">
                  Back to dashboard
                </Link>
                <Link className="btn btn-outline" to="/notes">
                  My notes
                </Link>
              </>
            ) : (
              <Link className="btn btn-primary" to="/">
                Back to home
              </Link>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
