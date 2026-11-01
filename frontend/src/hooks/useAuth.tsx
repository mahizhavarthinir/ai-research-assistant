"use client";

import { useState, useEffect, useCallback, createContext, useContext } from "react";
import type { UserProfile } from "@/types";
import { authApi, getToken, clearToken } from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const profile = await authApi.getProfile();
      setUser(profile);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const token = getToken();
    if (!token) {
      Promise.resolve().then(() => {
        if (isMounted) setLoading(false);
      });
      return;
    }

    authApi
      .getProfile()
      .then((profile) => {
        if (isMounted) {
          setUser(profile);
          setLoading(false);
        }
      })
      .catch(() => {
        clearToken();
        if (isMounted) {
          setUser(null);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (email: string, password: string) => {
    await authApi.login({ email, password });
    await fetchUser();
  };

  const register = async (email: string, username: string, password: string, fullName?: string) => {
    await authApi.register({ email, username, password, full_name: fullName });
    await fetchUser();
  };

  const logout = async () => {
    await authApi.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
