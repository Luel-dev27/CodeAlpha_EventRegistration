export class ApiError extends Error {
  constructor(message, status, fields = {}) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}

function describe(body) {
  if (!body || typeof body !== "object")
    return "The request could not be completed.";
  return Object.entries(body)
    .map(([field, value]) => {
      const text = Array.isArray(value)
        ? value.join(" ")
        : typeof value === "object"
          ? JSON.stringify(value)
          : String(value);
      return field === "detail" || field === "non_field_errors"
        ? text
        : `${field.replaceAll("_", " ")}: ${text}`;
    })
    .join(" ");
}

export function createApi({
  baseUrl = "/api/",
  origin = globalThis.location?.origin || "http://localhost",
  fetchImpl = globalThis.fetch,
  getToken = () => null,
  onUnauthorized = () => {},
} = {}) {
  const base = new URL(baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`, origin);
  if (
    !["http:", "https:"].includes(base.protocol) ||
    base.username ||
    base.password ||
    base.search ||
    base.hash
  )
    throw new Error("Invalid API base URL");
  async function request(
    path,
    { method = "GET", body, signal, authenticated = true } = {},
  ) {
    const url = new URL(path, base);
    // Never follow caller-controlled absolute URLs with an authorization header.
    if (
      url.origin !== base.origin ||
      !url.pathname.startsWith(base.pathname) ||
      path.startsWith("/") ||
      path.includes("..")
    )
      throw new Error("API path must stay within the configured API");
    const token = authenticated ? getToken() : null;
    let response;
    try {
      response = await fetchImpl(url.href, {
        method,
        signal,
        credentials: "omit",
        redirect: "error",
        headers: {
          Accept: "application/json",
          ...(body === undefined ? {} : { "Content-Type": "application/json" }),
          ...(token ? { Authorization: `Token ${token}` } : {}),
        },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
    } catch (error) {
      if (error.name === "AbortError") throw error;
      throw new ApiError(
        "Unable to reach the server. Check your connection and try again.",
        0,
      );
    }
    let data;
    try {
      data = await response.json();
    } catch {
      throw new ApiError(
        "The server returned an unexpected response.",
        response.status,
      );
    }
    if (!response.ok) {
      if (response.status === 401 && token && getToken() === token)
        onUnauthorized();
      throw new ApiError(describe(data), response.status, data);
    }
    return data;
  }
  return { request };
}

let token = null;
export const setToken = (value) => {
  token = value;
};
export const api = createApi({
  baseUrl: import.meta.env?.VITE_API_BASE_URL || "/api/",
  getToken: () => token,
  onUnauthorized: () => {
    token = null;
    globalThis.dispatchEvent?.(new Event("auth:invalid"));
  },
});
export const query = (params) =>
  new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  ).toString();
export const pageData = (data) =>
  Array.isArray(data)
    ? { results: data, count: data.length, next: null, previous: null }
    : data;
