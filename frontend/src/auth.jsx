import React, { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, setToken } from "./api.js";

const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const reset = () => {
      setUser(null);
      setNotice("Your session is no longer valid. Please sign in again.");
    };
    window.addEventListener("auth:invalid", reset);
    return () => window.removeEventListener("auth:invalid", reset);
  }, []);
  async function authenticate(mode, body) {
    const result = await api.request(`auth/${mode}/`, {
      method: "POST",
      body,
      authenticated: false,
    });
    setToken(result.token);
    setUser(result.user);
    setNotice("");
  }
  async function logout() {
    try {
      await api.request("auth/logout/", { method: "POST" });
      setToken(null);
      setUser(null);
      setNotice("You have been signed out.");
    } catch (error) {
      setNotice(
        error.status === 401
          ? "Your session has ended."
          : "Could not revoke your token. Please reconnect and try signing out again.",
      );
    }
  }
  return (
    <AuthContext.Provider value={{ user, notice, authenticate, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
export function RequireAuth({ children }) {
  const { user } = useAuth();
  const location = useLocation();
  return user ? (
    children
  ) : (
    <Navigate to="/login" replace state={{ from: location.pathname }} />
  );
}
