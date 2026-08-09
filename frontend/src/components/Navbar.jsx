import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import Icon from './Icon';
import { useAuth } from '../auth';

export default function Navbar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleSignOut() {
    await signOut();
    navigate('/login');
  }

  // Collapse the mobile menu whenever a destination is chosen, otherwise it
  // stays open covering the page it just navigated to.
  const close = () => setMenuOpen(false);

  const navLinkClass = ({ isActive }) => `nav-link${isActive ? ' is-active' : ''}`;

  return (
    <header className="site-header">
      <div className="container">
        <nav className="nav" aria-label="Main">
          <Link className="brand" to={user ? '/dashboard' : '/'} onClick={close}>
            <span className="brand-mark">
              <Icon name="book" />
            </span>
            Inkwell
          </Link>

          <button
            type="button"
            className="nav-toggle-label"
            aria-expanded={menuOpen}
            aria-label="Toggle navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Icon name="menu" style={{ width: 22, height: 22 }} />
          </button>

          {user && (
            <ul className={`nav-links${menuOpen ? ' is-open' : ''}`}>
              <li>
                <NavLink className={navLinkClass} to="/dashboard" onClick={close}>
                  <Icon name="home" /> Dashboard
                </NavLink>
              </li>
              <li>
                <NavLink className={navLinkClass} to="/notes/new" onClick={close}>
                  <Icon name="plus" /> New note
                </NavLink>
              </li>
              <li>
                <NavLink className={navLinkClass} to="/notes" end onClick={close}>
                  <Icon name="notes" /> My notes
                </NavLink>
              </li>
              {/* Shown to administrators only. The route and the API are both
                  guarded regardless of whether this link is rendered. */}
              {user.role === 'ADMIN' && (
                <li>
                  <NavLink className={navLinkClass} to="/admin" onClick={close}>
                    <Icon name="shield" /> Admin
                  </NavLink>
                </li>
              )}
            </ul>
          )}

          <div className={`nav-actions${menuOpen ? ' is-open' : ''}`}>
            {user ? (
              <>
                <span className="user-chip" title={user.email}>
                  <span className="avatar">{user.initial}</span>
                  <span className="name">{user.name}</span>
                </span>
                <button type="button" className="btn btn-outline btn-sm" onClick={handleSignOut}>
                  <Icon name="logout" /> Sign out
                </button>
              </>
            ) : (
              <>
                <Link className="btn btn-outline btn-sm" to="/login" onClick={close}>
                  <Icon name="user" /> Sign in
                </Link>
                <Link className="btn btn-primary btn-sm" to="/register" onClick={close}>
                  <Icon name="user-plus" /> Get started
                </Link>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}
