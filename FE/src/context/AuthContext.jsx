import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);       // { id, name, email, role, departmentId }
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);  // true until initial token check done

  // Called by Login page on success
  const login = useCallback((userData, jwt) => {
    localStorage.setItem('token', jwt);
    setToken(jwt);
    setUser(userData); // set immediately so navigation can proceed
    // enrich with full profile (adds departmentName, avatarSignedUrl, etc.)
    import('../api/apiHelpers').then(({ getRequest }) => {
      getRequest({ url: '/users/me' })
        .then((data) => { if (data?.id) setUser(data); })
        .catch(() => {}); // keep userData as fallback
    });
  }, []);

  const updateUser = useCallback((updates) => {
    setUser((prev) => prev ? { ...prev, ...updates } : prev);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  }, []);

  // On mount: if token exists, fetch /users/me to rehydrate user state
  useEffect(() => {
    if (!token) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(false);
      return;
    }

    import('../api/apiHelpers').then(({ getRequest }) => {
      getRequest({ url: '/users/me' })
        .then((data) => {
          if (data?.id) {
            setUser(data);
          } else {
            // Token is stale/invalid
            localStorage.removeItem('token');
            setToken(null);
          }
        })
        .catch(() => {
          localStorage.removeItem('token');
          setToken(null);
        })
        .finally(() => setLoading(false));
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}