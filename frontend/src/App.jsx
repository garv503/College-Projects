import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import { ICON_SPRITE } from './components/Icon';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Notes from './pages/Notes';
import NoteEditor from './pages/NoteEditor';
import Admin from './pages/Admin';
import NotFound from './pages/NotFound';
import { useAuth } from './auth';

/**
 * Gate for signed-in routes.
 *
 * This is a convenience, not the security boundary - the API enforces access on
 * every call, so hiding a route here only saves the user a pointless request.
 */
function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Wait for the session probe. Redirecting during it would bounce a signed-in
  // user to the login page every time they refreshed.
  if (loading) {
    return (
      <main className="page">
        <div className="container">
          <p className="sub">Loading...</p>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search, notice: null }}
      />
    );
  }

  return children;
}

/**
 * Gate for the admin console.
 *
 * Again only a convenience: /api/admin/* is behind requireAdmin on the server,
 * so a non-admin who reached this route anyway would get 403s and see nothing.
 */
function RequireAdmin({ children }) {
  const { user, loading } = useAuth();

  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'ADMIN') return <Navigate to="/dashboard" replace />;

  return children;
}

/** Keeps signed-in users off the sign-in and registration pages. */
function RedirectIfSignedIn({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  return (
    <>
      {ICON_SPRITE}
      <Navbar />

      <Routes>
        <Route path="/" element={<Landing />} />

        <Route
          path="/login"
          element={
            <RedirectIfSignedIn>
              <Login />
            </RedirectIfSignedIn>
          }
        />
        <Route
          path="/register"
          element={
            <RedirectIfSignedIn>
              <Register />
            </RedirectIfSignedIn>
          }
        />

        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/notes"
          element={
            <RequireAuth>
              <Notes />
            </RequireAuth>
          }
        />
        <Route
          path="/notes/new"
          element={
            <RequireAuth>
              <NoteEditor mode="create" />
            </RequireAuth>
          }
        />
        <Route
          path="/notes/:id/edit"
          element={
            <RequireAuth>
              <NoteEditor mode="edit" />
            </RequireAuth>
          }
        />

        <Route
          path="/admin"
          element={
            <RequireAdmin>
              <Admin />
            </RequireAdmin>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
