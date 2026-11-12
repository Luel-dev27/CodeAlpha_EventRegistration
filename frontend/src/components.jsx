import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "./api.js";
import { useAuth } from "./auth.jsx";

export function useRemote(path, revision = 0) {
  const { user } = useAuth();
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  useEffect(() => {
    const controller = new AbortController();
    setState({ data: null, loading: true, error: "" });
    api
      .request(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted)
          setState({ data, loading: false, error: "" });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({ data: null, loading: false, error: error.message });
      });
    return () => controller.abort();
  }, [path, revision, user?.id]);
  return state;
}

export const dateTime = (value) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
export const isClosed = (event) => new Date(event.start_time) <= new Date();
export function Feedback({ error, children }) {
  return error ? (
    <p className="feedback error" role="alert">
      {error}
    </p>
  ) : children ? (
    <p className="feedback success" role="status">
      {children}
    </p>
  ) : null;
}
export function Loading() {
  return (
    <p className="loading" role="status">
      Loading…
    </p>
  );
}
export function Empty({ title = "Nothing here yet", children }) {
  return (
    <div className="empty">
      <span aria-hidden="true">◇</span>
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  );
}
export function EventCard({ event }) {
  const date = new Date(event.start_time);
  const state = isClosed(event)
    ? "Registration closed"
    : event.available_capacity === 0
      ? "Fully booked"
      : `${event.available_capacity} places available`;
  return (
    <article className="event-card">
      <div className="card-top">
        <div className="date-stamp">
          <span>{date.toLocaleDateString(undefined, { month: "short" })}</span>
          <strong>{date.getDate()}</strong>
        </div>
        <span
          className={`tag ${event.registration_status === "registered" ? "tag-green" : ""}`}
        >
          {event.registration_status === "registered"
            ? "You’re registered"
            : state}
        </span>
      </div>
      <div className="card-body">
        <p className="location">⌖ {event.location}</p>
        <h3>
          <Link to={`/events/${event.id}`}>{event.title}</Link>
        </h3>
        <p className="summary">{event.description}</p>
        <p className="event-time">{dateTime(event.start_time)}</p>
      </div>
      <Link className="card-link" to={`/events/${event.id}`}>
        Explore event <span aria-hidden="true">↗</span>
      </Link>
    </article>
  );
}
export function Pagination({ data, page, onPage }) {
  if (!data || (!data.next && !data.previous)) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        className="secondary"
        disabled={!data.previous}
        onClick={() => onPage(page - 1)}
      >
        Previous
      </button>
      <span>Page {page}</span>
      <button
        className="secondary"
        disabled={!data.next}
        onClick={() => onPage(page + 1)}
      >
        Next
      </button>
    </nav>
  );
}
