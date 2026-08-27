import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as api from './api';

/**
 * Holds the signed-in user for the whole app.
 *
 * The session lives in an HttpOnly cookie that script cannot read, so on load
 * the app has to ask the server who it is. `loading` covers that first round
 * trip - routes must wait for it rather than assuming "no user yet" means
 * "signed out", which would bounce a signed-in user to the login page on every
 * refresh.
 */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    api
      .getSession()
      .then((data) => {
        if (cancelled) return;
        setUser(data.user);
      })
      .catch(() => {
        // A failed probe just means "not signed in" as far as the UI cares.
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email, password) => {
    const signedIn = await api.login(email, password);
    setUser(signedIn);
    return signedIn;
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      // Clear locally even if the call failed, so the UI cannot get stuck
      // showing a session the user has asked to end.
      setUser(null);
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, signIn, signOut, setUser }),
    [user, loading, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider');
  }
  return context;
}
