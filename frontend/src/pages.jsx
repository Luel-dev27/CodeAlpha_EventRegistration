import React, { useEffect, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { api, pageData, query } from "./api.js";
import { useAuth } from "./auth.jsx";
import {
  dateTime,
  Empty,
  EventCard,
  Feedback,
  isClosed,
  Loading,
  Pagination,
  useRemote,
} from "./components.jsx";

export function Home() {
  const { data, loading, error } = useRemote(
    "events/?when=upcoming&page=1&page_size=3",
  );
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">MEET. LEARN. BELONG.</p>
          <h1>
            Good things happen
            <br />
            when we <em>show up.</em>
          </h1>
          <p className="hero-copy">
            A workshop, a conversation, a new connection. Discover what’s
            happening in your community and find your place.
          </p>
          <div className="hero-actions">
            <Link className="button" to="/events">
              Find your next event <span aria-hidden="true">↗</span>
            </Link>
            <Link className="text-link" to="/signup">
              Join the community
            </Link>
          </div>
        </div>
        <div className="hero-note" aria-label="How it works">
          <span className="note-symbol" aria-hidden="true">
            ✳
          </span>
          <p className="eyebrow">SOMETHING TO LOOK FORWARD TO</p>
          <h2>
            Your next
            <br />
            “glad I came”
            <br />
            starts here.
          </h2>
          <p>
            Find an event. Reserve a place.
            <br />
            We’ll keep the details together.
          </p>
          <span className="note-footer">CODEALPHA / COMMUNITY EVENTS</span>
        </div>
      </section>
      <section className="section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">MARK YOUR CALENDAR</p>
            <h2>Coming up next</h2>
          </div>
          <Link className="text-link" to="/events">
            View all events →
          </Link>
        </div>
        {loading ? (
          <Loading />
        ) : error ? (
          <Feedback error={error} />
        ) : pageData(data).results.length ? (
          <div className="event-grid">
            {pageData(data).results.map((event) => (
              <EventCard event={event} key={event.id} />
            ))}
          </div>
        ) : (
          <Empty title="The next gathering is on its way">
            Upcoming events will appear here when organizers publish them.
          </Empty>
        )}
      </section>
      <section className="how">
        <div>
          <span>01 / DISCOVER</span>
          <h3>Find your people.</h3>
          <p>Browse events by interest, location, and available places.</p>
        </div>
        <div>
          <span>02 / RESERVE</span>
          <h3>Make it a plan.</h3>
          <p>Sign in and reserve your place in a few moments.</p>
        </div>
        <div>
          <span>03 / MANAGE</span>
          <h3>Keep it together.</h3>
          <p>Your registrations and event details, all in one place.</p>
        </div>
      </section>
    </>
  );
}

export function Events() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState(params.get("search") || "");
  useEffect(
    () => setSearch(params.get("search") || ""),
    [params.get("search")],
  );
  const selected = params.get("when") || "";
  const available = params.get("available") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const request = `events/?${query({ search: params.get("search") || "", when: selected, available, page, page_size: 9 })}`;
  const { data, loading, error } = useRemote(request);
  function change(values) {
    setParams(
      query({
        search: params.get("search") || "",
        when: selected,
        available,
        page: 1,
        ...values,
      }),
    );
  }
  return (
    <section className="section directory">
      <p className="eyebrow">MAKE ROOM FOR SOMETHING GOOD</p>
      <h1 className="page-title">Explore events</h1>
      <p className="muted">Find a gathering that belongs on your calendar.</p>
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          change({ search });
        }}
      >
        <div className="search-field">
          <label htmlFor="search">Search events</label>
          <div className="search-row">
            <input
              id="search"
              type="search"
              maxLength={200}
              placeholder="Title or location"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <button>Search</button>
          </div>
        </div>
        <div>
          <label htmlFor="when">When</label>
          <select
            id="when"
            value={selected}
            onChange={(event) => change({ when: event.target.value })}
          >
            <option value="">All events</option>
            <option value="upcoming">Upcoming</option>
            <option value="past">Started / past</option>
          </select>
        </div>
        <div>
          <label htmlFor="available">Places</label>
          <select
            id="available"
            value={available}
            onChange={(event) => change({ available: event.target.value })}
          >
            <option value="">Any availability</option>
            <option value="true">Places available</option>
            <option value="false">Fully booked</option>
          </select>
        </div>
      </form>
      {loading ? (
        <Loading />
      ) : error ? (
        <Feedback error={error} />
      ) : (
        <>
          <p className="result-count">
            {pageData(data).count}{" "}
            {pageData(data).count === 1 ? "event" : "events"} found
          </p>
          {pageData(data).results.length ? (
            <div className="event-grid">
              {pageData(data).results.map((event) => (
                <EventCard event={event} key={event.id} />
              ))}
            </div>
          ) : (
            <Empty title="No matching events">
              Try another search or a different filter.
            </Empty>
          )}
          <Pagination
            data={pageData(data)}
            page={page}
            onPage={(value) => change({ page: value })}
          />
        </>
      )}
    </section>
  );
}

export function EventDetails() {
  const { id } = useParams();
  const { user } = useAuth();
  const [revision, setRevision] = useState(0);
  const {
    data: event,
    loading,
    error,
  } = useRemote(`events/${encodeURIComponent(id)}/`, revision);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [success, setSuccess] = useState("");
  async function register() {
    setBusy(true);
    setActionError("");
    setSuccess("");
    try {
      await api.request("registrations/", {
        method: "POST",
        body: { event_id: event.id },
      });
      setSuccess("You’re registered! Your place is reserved.");
    } catch (error) {
      setActionError(error.message);
    } finally {
      setBusy(false);
      setRevision((value) => value + 1);
    }
  }
  if (loading) return <Loading />;
  if (error)
    return (
      <section className="section">
        <Feedback error={error} />
        <Link to="/events">Back to events</Link>
      </section>
    );
  const closed = isClosed(event);
  const registered = event.registration_status === "registered";
  return (
    <section className="section">
      <Link className="text-link" to="/events">
        ← Back to events
      </Link>
      <div className="detail-layout">
        <article>
          <p className="eyebrow">A PLACE TO COME TOGETHER</p>
          <h1 className="page-title">{event.title}</h1>
          <p className="location">⌖ {event.location}</p>
          <div className="description-block">
            <h2>About this event</h2>
            <p>{event.description}</p>
          </div>
        </article>
        <aside className="reservation-panel">
          <p className="eyebrow">THE DETAILS</p>
          <dl>
            <dt>Starts</dt>
            <dd>{dateTime(event.start_time)}</dd>
            <dt>Ends</dt>
            <dd>{dateTime(event.end_time)}</dd>
            <dt>Location</dt>
            <dd>{event.location}</dd>
            <dt>Available places</dt>
            <dd>
              {event.available_capacity} of {event.capacity}
            </dd>
          </dl>
          {registered ? (
            <>
              <p className="tag tag-green">You’re registered</p>
              <Link className="button full" to="/registrations">
                Manage registration
              </Link>
            </>
          ) : closed ? (
            <p className="feedback">
              Registration is closed because this event has started.
            </p>
          ) : event.available_capacity === 0 ? (
            <p className="feedback">This event is fully booked.</p>
          ) : user ? (
            <button className="full" disabled={busy} onClick={register}>
              {busy
                ? "Reserving…"
                : event.registration_status === "cancelled"
                  ? "Register again"
                  : "Reserve my place"}
            </button>
          ) : (
            <Link
              className="button full"
              to="/login"
              state={{ from: `/events/${id}` }}
            >
              Sign in to register
            </Link>
          )}
          <Feedback error={actionError}>{success}</Feedback>
          <p className="small muted">
            Plans change. You can cancel your registration from your dashboard.
          </p>
        </aside>
      </div>
    </section>
  );
}

export function AuthPage({ signup = false }) {
  const { authenticate, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setError("");
    const form = new FormData(event.currentTarget);
    if (signup && form.get("password") !== form.get("confirm")) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await authenticate(signup ? "register" : "login", {
        username: form.get("username"),
        password: form.get("password"),
        ...(signup ? { email: form.get("email") } : {}),
      });
      const from = location.state?.from;
      navigate(
        typeof from === "string" &&
          from.startsWith("/") &&
          !from.startsWith("//")
          ? from
          : "/registrations",
        { replace: true },
      );
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }
  if (user)
    return (
      <section className="section">
        <h1>You’re signed in.</h1>
        <Link to="/registrations">View my registrations</Link>
      </section>
    );
  return (
    <section className="auth-layout">
      <div className="auth-intro">
        <p className="eyebrow">YOU’RE IN GOOD COMPANY</p>
        <h1>
          {signup
            ? "Your next connection starts here."
            : "Welcome back to what’s next."}
        </h1>
        <p>Find your events. Save your place. Be part of the conversation.</p>
        <span className="auth-art" aria-hidden="true">
          ✳
        </span>
      </div>
      <div className="auth-card">
        <h2>{signup ? "Create your account" : "Sign in"}</h2>
        <p className="muted">
          {signup
            ? "A few details, then you’re ready to explore."
            : "Your community is waiting."}
        </p>
        <form onSubmit={submit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            name="username"
            required
            maxLength={150}
            autoComplete="username"
          />
          {signup && (
            <>
              <label htmlFor="email">
                Email <span className="muted">(optional)</span>
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={254}
              />
            </>
          )}
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            required
            minLength={signup ? 8 : undefined}
            autoComplete={signup ? "new-password" : "current-password"}
            aria-describedby={signup ? "password-help" : undefined}
          />
          {signup && (
            <>
              <p className="small muted" id="password-help">
                Use at least 8 characters. Avoid common passwords, only numbers,
                and your personal details.
              </p>
              <label htmlFor="confirm">Confirm password</label>
              <input
                id="confirm"
                name="confirm"
                type="password"
                required
                autoComplete="new-password"
              />
            </>
          )}
          <Feedback error={error} />
          <button className="full" disabled={busy}>
            {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
          </button>
        </form>
        <p className="small">
          {signup ? "Already have an account?" : "New here?"}{" "}
          <Link to={signup ? "/login" : "/signup"} state={location.state}>
            {signup ? "Sign in" : "Create an account"}
          </Link>
        </p>
        <p className="session-note">
          For your privacy, your sign-in stays in this tab’s memory. Refreshing
          the page signs you out of the interface.
        </p>
      </div>
    </section>
  );
}

export function Dashboard() {
  const { user } = useAuth();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const { data, loading, error } = useRemote(
    `registrations/?${query({ status, page, page_size: 10 })}`,
    revision,
  );
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");
  async function act(registration, cancel) {
    if (
      cancel &&
      !window.confirm(
        `Cancel your registration for “${registration.event.title}”?`,
      )
    )
      return;
    setBusy(registration.id);
    setActionError("");
    setMessage("");
    try {
      await api.request(
        cancel ? `registrations/${registration.id}/cancel/` : "registrations/",
        {
          method: "POST",
          ...(cancel ? {} : { body: { event_id: registration.event.id } }),
        },
      );
      setMessage(
        cancel
          ? "Registration cancelled. Your place has been released."
          : "You’re registered again.",
      );
    } catch (error) {
      setActionError(error.message);
    } finally {
      setBusy(null);
      setRevision((value) => value + 1);
    }
  }
  return (
    <section className="section dashboard">
      <p className="eyebrow">YOUR PLANS, IN ONE PLACE</p>
      <h1 className="page-title">Hello, {user.username}.</h1>
      <p className="muted">Here’s what’s on your calendar.</p>
      <div className="section-heading">
        <h2>My registrations</h2>
        <div>
          <label htmlFor="status">Show registrations</label>
          <select
            id="status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All registrations</option>
            <option value="registered">Registered</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>
      <Feedback error={actionError}>{message}</Feedback>
      {loading ? (
        <Loading />
      ) : error ? (
        <Feedback error={error} />
      ) : pageData(data).results.length ? (
        <>
          <div className="registration-list">
            {pageData(data).results.map((registration) => (
              <article className="registration-row" key={registration.id}>
                <div>
                  <span
                    className={`tag ${registration.status === "registered" ? "tag-green" : ""}`}
                  >
                    {registration.status}
                  </span>
                  <h3>
                    <Link to={`/events/${registration.event.id}`}>
                      {registration.event.title}
                    </Link>
                  </h3>
                  <p>
                    {dateTime(registration.event.start_time)} ·{" "}
                    {registration.event.location}
                  </p>
                  {isClosed(registration.event) && (
                    <p className="small muted">This event has started.</p>
                  )}
                </div>
                <div className="row-actions">
                  <Link
                    className="text-link"
                    to={`/events/${registration.event.id}`}
                  >
                    Details ↗
                  </Link>
                  {registration.status === "registered" ? (
                    <button
                      className="secondary danger"
                      disabled={busy !== null}
                      onClick={() => act(registration, true)}
                    >
                      Cancel registration
                    </button>
                  ) : (
                    <button
                      className="secondary"
                      disabled={
                        busy !== null ||
                        isClosed(registration.event) ||
                        registration.event.available_capacity === 0
                      }
                      onClick={() => act(registration, false)}
                    >
                      Register again
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
          <Pagination data={pageData(data)} page={page} onPage={setPage} />
        </>
      ) : (
        <Empty
          title={
            status
              ? "No registrations in this category"
              : "Your calendar has room for something good"
          }
        >
          <Link to="/events">
            Explore events and reserve your first place →
          </Link>
        </Empty>
      )}
    </section>
  );
}
