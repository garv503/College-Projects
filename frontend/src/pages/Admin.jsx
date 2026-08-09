import { useCallback, useEffect, useState } from 'react';
import Alert from '../components/Alert';
import Icon from '../components/Icon';
import { formatDate } from '../components/NoteCard';
import * as api from '../api';
import { useAuth } from '../auth';

/**
 * Administrator console: everyone's accounts, their roles, and site totals.
 *
 * Controls the server would refuse are disabled here too - an admin cannot
 * change their own role or delete their own account, which is what guarantees
 * at least one administrator always remains.
 */
export default function Admin() {
  const { user } = useAuth();

  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    try {
      const [loadedUsers, loadedStats] = await Promise.all([api.listUsers(), api.getAdminStats()]);
      setUsers(loadedUsers);
      setStats(loadedStats);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function changeRole(target) {
    const nextRole = target.role === 'ADMIN' ? 'USER' : 'ADMIN';
    const verb = nextRole === 'ADMIN' ? 'Promote' : 'Demote';

    if (!window.confirm(`${verb} ${target.name} to ${nextRole}?`)) return;

    setBusyId(target.id);
    setMessage(null);
    try {
      const result = await api.setUserRole(target.id, nextRole);
      setMessage(result.message);
      setError(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  async function removeUser(target) {
    const warning = target.noteCount > 0
      ? `Delete ${target.name}? Their ${target.noteCount} note(s) will be deleted too. This cannot be undone.`
      : `Delete ${target.name}? This cannot be undone.`;

    if (!window.confirm(warning)) return;

    setBusyId(target.id);
    setMessage(null);
    try {
      const result = await api.deleteUser(target.id);
      setMessage(result.message);
      setError(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="page">
      <div className="container">
        <Alert kind="success">{message}</Alert>
        <Alert kind="error">{error}</Alert>

        <div className="page-head">
          <div>
            <h1>
              <Icon name="shield" style={{ width: 26, height: 26, marginRight: 8 }} />
              Admin console
            </h1>
            <p className="sub">Signed in as {user?.name} (administrator).</p>
          </div>
        </div>

        {stats && (
          <div className="stat-grid">
            <div className="stat">
              <div className="stat-label">
                <Icon name="users" /> Users
              </div>
              <div className="stat-value">{stats.totalUsers}</div>
            </div>
            <div className="stat">
              <div className="stat-label">
                <Icon name="shield" /> Administrators
              </div>
              <div className="stat-value">{stats.totalAdmins}</div>
            </div>
            <div className="stat">
              <div className="stat-label">
                <Icon name="notes" /> Notes (all users)
              </div>
              <div className="stat-value">{stats.totalNotes}</div>
            </div>
            <div className="stat">
              <div className="stat-label">
                <Icon name="pin" /> Pinned
              </div>
              <div className="stat-value">{stats.pinnedNotes}</div>
            </div>
          </div>
        )}

        <div className="page-head">
          <h2>All accounts</h2>
        </div>

        {loading ? (
          <p className="sub">Loading accounts...</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th className="num">Notes</th>
                  <th>Joined</th>
                  <th className="actions-col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <div className="cell-user">
                        <span className="avatar">{row.name.charAt(0).toUpperCase()}</span>
                        <div>
                          <div className="cell-name">
                            {row.name}
                            {row.isSelf && <span className="tag" style={{ marginLeft: 8 }}>you</span>}
                          </div>
                          <div className="cell-sub">{row.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className={`tag${row.role === 'ADMIN' ? ' tag-pinned' : ''}`}>
                        {row.role === 'ADMIN' && <Icon name="shield" style={{ width: 12, height: 12 }} />}
                        {row.role}
                      </span>
                    </td>
                    <td className="num">{row.noteCount}</td>
                    <td className="cell-sub">{formatDate(row.createdAt)}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          disabled={row.isSelf || busyId === row.id}
                          onClick={() => changeRole(row)}
                          title={
                            row.isSelf
                              ? 'You cannot change your own role'
                              : row.role === 'ADMIN'
                                ? 'Demote to USER'
                                : 'Promote to ADMIN'
                          }
                        >
                          <Icon name={row.role === 'ADMIN' ? 'arrow-down' : 'arrow-up'} />
                          {row.role === 'ADMIN' ? 'Demote' : 'Promote'}
                        </button>

                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          disabled={row.isSelf || busyId === row.id}
                          onClick={() => removeUser(row)}
                          title={row.isSelf ? 'You cannot delete your own account' : 'Delete this user'}
                        >
                          <Icon name="trash" /> Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  );
}
