import React, { useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { RequireAuth, useAuth } from "./auth.jsx";
import { Feedback } from "./components.jsx";
import { AuthPage, Dashboard, EventDetails, Events, Home } from "./pages.jsx";

export default function App() {
  const { user, logout, notice } = useAuth();
  const [menu, setMenu] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="container nav-wrap">
          <Link className="brand" to="/" onClick={() => setMenu(false)}>
            <span className="brand-mark" aria-hidden="true">
              g.
            </span>
            gather<span className="brand-caption">by CodeAlpha</span>
          </Link>
          <button
            className="menu-toggle secondary"
            aria-expanded={menu}
            aria-controls="main-nav"
            onClick={() => setMenu(!menu)}
          >
            Menu
          </button>
          <nav
            id="main-nav"
            className={menu ? "nav-open" : ""}
            aria-label="Main navigation"
          >
            <NavLink to="/" end onClick={() => setMenu(false)}>
              Home
            </NavLink>
            <NavLink to="/events" onClick={() => setMenu(false)}>
              Events
            </NavLink>
            {user ? (
              <>
                <NavLink to="/registrations" onClick={() => setMenu(false)}>
                  My registrations
                </NavLink>
                <button
                  className="secondary"
                  disabled={loggingOut}
                  onClick={async () => {
                    setLoggingOut(true);
                    await logout();
                    setLoggingOut(false);
                    setMenu(false);
                  }}
                >
                  {loggingOut ? "Signing out…" : "Log out"}
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" onClick={() => setMenu(false)}>
                  Sign in
                </NavLink>
                <Link
                  className="button small-button"
                  to="/signup"
                  onClick={() => setMenu(false)}
                >
                  Get started ↗
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main id="main" className="container">
        {notice && <Feedback>{notice}</Feedback>}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/events" element={<Events />} />
          <Route path="/events/:id" element={<EventDetails />} />
          <Route path="/signup" element={<AuthPage key="signup" signup />} />
          <Route path="/login" element={<AuthPage key="login" />} />
          <Route
            path="/registrations"
            element={
              <RequireAuth>
                <Dashboard />
              </RequireAuth>
            }
          />
          <Route
            path="*"
            element={
              <section className="section">
                <h1>Page not found</h1>
                <Link to="/events">Explore events →</Link>
              </section>
            }
          />
        </Routes>
      </main>
      <footer className="container footer">
        <div>
          <strong>gather / CodeAlpha</strong>
          <p>Make time for your community.</p>
        </div>
        <span>Event Registration System · Internship portfolio</span>
      </footer>
    </>
  );
}
