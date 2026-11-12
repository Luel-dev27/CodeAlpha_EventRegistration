import { test } from "node:test";
import assert from "node:assert/strict";
import { createApi, pageData, query } from "../src/api.js";

const response = (body, status = 200) =>
  new Response(JSON.stringify(body), { status });
test("client sends JSON and authentication only to the configured API", async () => {
  const calls = [];
  const api = createApi({
    origin: "http://localhost:5173",
    getToken: () => "test-token",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return response({ id: 1 });
    },
  });
  await api.request("registrations/", {
    method: "POST",
    body: { event_id: 1 },
  });
  assert.equal(calls[0].url, "http://localhost:5173/api/registrations/");
  assert.equal(calls[0].options.headers.Authorization, "Token test-token");
  assert.equal(calls[0].options.credentials, "omit");
  assert.deepEqual(JSON.parse(calls[0].options.body), { event_id: 1 });
  await api.request("auth/login/", {
    method: "POST",
    authenticated: false,
    body: { username: "test", password: "test-only" },
  });
  assert.equal(calls[1].options.headers.Authorization, undefined);
  for (const path of [
    "https://evil.example/api/",
    "//evil.example/",
    "../outside",
    "/admin/",
  ])
    await assert.rejects(() => api.request(path), /configured API/);
  assert.equal(calls.length, 2);
});
test("invalid tokens invalidate memory auth and field errors remain useful", async () => {
  let invalidated = false;
  const api = createApi({
    getToken: () => "test-token",
    onUnauthorized: () => {
      invalidated = true;
    },
    fetchImpl: async () => response({ detail: "Invalid token." }, 401),
  });
  await assert.rejects(
    () => api.request("registrations/"),
    (error) => error.status === 401 && error.message === "Invalid token.",
  );
  assert.equal(invalidated, true);
  const validation = createApi({
    fetchImpl: async () =>
      response({ password: ["Too common.", "Too short."] }, 400),
  });
  await assert.rejects(
    () => validation.request("auth/register/"),
    /Too common.*Too short/,
  );
});
test("network, server, rate-limit, and malformed responses are handled", async () => {
  const offline = createApi({
    fetchImpl: async () => {
      throw new TypeError("network");
    },
  });
  await assert.rejects(() => offline.request("events/"), /Unable to reach/);
  for (const status of [409, 429, 500]) {
    const api = createApi({
      fetchImpl: async () => response({ detail: "Safe message" }, status),
    });
    await assert.rejects(
      () => api.request("events/"),
      (error) => error.status === status && error.message === "Safe message",
    );
  }
  const broken = createApi({
    fetchImpl: async () =>
      new Response("<html>bad gateway</html>", { status: 502 }),
  });
  await assert.rejects(() => broken.request("events/"), /unexpected response/);
});
test("query parameters and legacy/paginated results normalize", () => {
  assert.equal(
    query({ search: "a & b", page: 2, when: "" }),
    "search=a+%26+b&page=2",
  );
  assert.equal(pageData([{ id: 1 }]).count, 1);
  const page = { results: [], count: 0, next: null, previous: null };
  assert.equal(pageData(page), page);
});

test("a late 401 from an old request does not invalidate a newer login", async () => {
  let token = "old-token";
  let finish;
  let invalidated = false;
  const api = createApi({
    getToken: () => token,
    onUnauthorized: () => {
      invalidated = true;
    },
    fetchImpl: () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  });
  const pending = api.request("registrations/");
  token = "new-token";
  finish(response({ detail: "Invalid token." }, 401));
  await assert.rejects(
    () => pending,
    (error) => error.status === 401,
  );
  assert.equal(invalidated, false);
});
