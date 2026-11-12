// Uses an existing Firefox + geckodriver; all Django data is in memory.
import { test } from "node:test";
import { randomBytes } from "node:crypto";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdirSync, writeFileSync } from "node:fs";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "../frontend/node_modules/vite/dist/node/index.js";
import { createApi } from "../frontend/src/api.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function until(check, label, timeout = 20000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const value = await check();
    if (value) return value;
    await pause(100);
  }
  throw new Error(`Timed out: ${label}`);
}

test(
  "React/Django integration and real Firefox attendee journey",
  { timeout: 120000 },
  async (t) => {
    let backend, vite, driver, session, driverOrigin;
    t.after(async () => {
      if (session)
        await fetch(`${driverOrigin}/session/${session}`, {
          method: "DELETE",
        }).catch(() => {});
      if (driver && driver.exitCode === null) driver.kill("SIGTERM");
      if (vite) await vite.close();
      if (backend && backend.exitCode === null) {
        backend.kill("SIGTERM");
        await once(backend, "exit");
      }
    });
    backend = spawn(
      path.join(root, "backend/.venv/bin/python"),
      ["-B", "scripts/test_server.py"],
      { cwd: root, stdio: ["ignore", "pipe", "pipe"] },
    );
    let output = "",
      backendError = "";
    backend.stdout.on("data", (value) => {
      output += value;
    });
    backend.stderr.on("data", (value) => {
      backendError += value;
    });
    const target = await until(() => {
      if (backend.exitCode !== null)
        throw new Error(`Test server exited: ${backendError}`);
      return output.match(/TEST_SERVER=(http:\/\/[^\s]+)/)?.[1];
    }, "Django fixture server");
    vite = await createServer({
      configFile: false,
      root: path.join(root, "frontend"),
      server: { host: "127.0.0.1", port: 0, proxy: { "/api": target } },
    });
    await vite.listen();
    const origin = `http://127.0.0.1:${vite.httpServer.address().port}`;
    let token = null;
    const client = createApi({ origin, getToken: () => token });
    await t.test("actual frontend client through Vite to Django", async () => {
      const events = await client.request("events/?page=1&when=upcoming");
      assert.equal(events.count, 2);
      await assert.rejects(
        () => client.request("registrations/"),
        (error) => error.status === 401,
      );
    });
    const reserve = net.createServer();
    reserve.listen(0, "127.0.0.1");
    await once(reserve, "listening");
    const port = reserve.address().port;
    await new Promise((resolve) => reserve.close(resolve));
    driverOrigin = `http://127.0.0.1:${port}`;
    driver = spawn(
      process.env.GECKODRIVER_PATH || "geckodriver",
      ["--host", "127.0.0.1", "--port", String(port), "--log", "error"],
      { stdio: ["ignore", "pipe", "pipe"] },
    );
    let driverError;
    driver.on("error", (error) => {
      driverError = error;
    });
    await until(async () => {
      if (driverError) throw driverError;
      try {
        return (await fetch(`${driverOrigin}/status`)).ok;
      } catch {
        return false;
      }
    }, "geckodriver");
    async function command(suffix, method = "GET", body) {
      const res = await fetch(`${driverOrigin}${suffix}`, {
        method,
        headers: { "Content-Type": "application/json" },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      const { value } = await res.json();
      if (!res.ok)
        throw new Error(`WebDriver: ${value?.message || res.status}`);
      return value;
    }
    const created = await command("/session", "POST", {
      capabilities: {
        alwaysMatch: {
          browserName: "firefox",
          "moz:firefoxOptions": { args: ["-headless"] },
        },
      },
    });
    session = created.sessionId;
    const route = (s) => `/session/${session}${s}`;
    const execute = (script, args = []) =>
      command(route("/execute/sync"), "POST", { script, args });
    const find = async (selector) =>
      (
        await command(route("/element"), "POST", {
          using: "css selector",
          value: selector,
        })
      )["element-6066-11e4-a52e-4f735466cecf"];
    const click = async (selector) =>
      command(route(`/element/${await find(selector)}/click`), "POST", {});
    const type = async (selector, text) =>
      command(route(`/element/${await find(selector)}/value`), "POST", {
        text,
      });
    const navigate = async (url) =>
      command(route("/url"), "POST", { url: new URL(url, origin).href });
    const contains = (text) =>
      execute("return document.body.textContent.includes(arguments[0])", [
        text,
      ]);
    const waitText = (text) => until(() => contains(text), text);
    const username = `attendee_${Date.now()}`;
    const password = `${randomBytes(18).toString("base64url")}!aZ7`;
    await t.test("protected route and signup validation", async () => {
      await navigate("/registrations");
      await waitText("Your community is waiting.");
      assert.ok((await command(route("/url"))).endsWith("/login"));
      await navigate("/signup");
      await until(
        () => execute('return !!document.querySelector("#confirm")'),
        "signup form",
      );
      await type("#username", username);
      await type("#password", "password");
      await type("#confirm", "different");
      await click(".auth-card button");
      await waitText("Passwords do not match.");
      await command(
        route(`/element/${await find("#confirm")}/clear`),
        "POST",
        {},
      );
      await type("#confirm", "password");
      await click(".auth-card button");
      await waitText("too common");
    });
    await t.test(
      "signup, search, event details, and registration",
      async () => {
        await command(
          route(`/element/${await find("#password")}/clear`),
          "POST",
          {},
        );
        await type("#password", password);
        await command(
          route(`/element/${await find("#confirm")}/clear`),
          "POST",
          {},
        );
        await type("#confirm", password);
        await click(".auth-card button");
        await waitText(`Hello, ${username}.`);
        await waitText("Your calendar has room");
        await click('nav a[href="/events"]');
        await waitText("3 events found");
        await type("#search", "Community workshop");
        await click(".filters button");
        await waitText("1 event found");
        await click(".event-card h3 a");
        await waitText("About this event");
        await click(".reservation-panel button");
        await waitText("Your place is reserved.");
        await waitText("You’re registered");
        await click('.reservation-panel a[href="/registrations"]');
        await waitText("Community workshop");
        await until(
          () => execute('return !!document.querySelector(".registration-row")'),
          "dashboard record",
        );
      },
    );
    await t.test(
      "cancel confirmation, cancellation, and reactivation",
      async () => {
        await click(".registration-row button");
        await command(route("/alert/dismiss"), "POST", {});
        assert.equal(await contains("Registration cancelled."), false);
        await click(".registration-row button");
        await command(route("/alert/accept"), "POST", {});
        await waitText("Registration cancelled.");
        await waitText("Register again");
        await click(".registration-row button");
        await waitText("You’re registered again.");
        await until(
          () =>
            execute(
              'return document.querySelector(".registration-row .tag")?.textContent === "registered"',
            ),
          "reactivated status",
        );
      },
    );
    await t.test("logout and login forms", async () => {
      await click("nav button");
      await waitText("Your community is waiting.");
      await type("#username", username);
      await type("#password", "incorrect");
      await click(".auth-card button");
      await waitText("Invalid username or password.");
      await command(
        route(`/element/${await find("#password")}/clear`),
        "POST",
        {},
      );
      await type("#password", password);
      await click(".auth-card button");
      await waitText(`Hello, ${username}.`);
    });
    await t.test(
      "full event and backend conflict through real API client",
      async () => {
        const other = await client.request("auth/register/", {
          method: "POST",
          authenticated: false,
          body: { username: `other_${Date.now()}`, password },
        });
        token = other.token;
        const events = await client.request("events/?search=Community");
        await assert.rejects(
          () =>
            client.request("registrations/", {
              method: "POST",
              body: { event_id: events[0].id },
            }),
          (error) => error.status === 409 && error.message.includes("full"),
        );
        await click("nav button");
        await waitText("Your community is waiting.");
        await type("#username", other.user.username);
        await type("#password", password);
        await click(".auth-card button");
        await waitText(`Hello, ${other.user.username}.`);
        await click('nav a[href="/events"]');
        await waitText("3 events found");
        await click('.event-card h3 a[href="/events/1"]');
        await waitText("fully booked");
      },
    );
    await t.test(
      "memory-only authentication and expired/invalid token handling",
      async () => {
        assert.equal(
          await execute("return localStorage.length + sessionStorage.length"),
          0,
        );
        // Revoke this account token externally; the next protected request must clear UI auth.
        await client.request("auth/logout/", { method: "POST" });
        await click('nav a[href="/registrations"]');
        await waitText("Your session is no longer valid.");
        await waitText("Your community is waiting.");
        await navigate("/registrations");
        await waitText("Your community is waiting.");
      },
    );
    await t.test("desktop/mobile layout and keyboard access", async () => {
      await navigate("/");
      await waitText("Coming up next");
      await command(route("/window/rect"), "POST", {
        width: 1280,
        height: 960,
      });
      const artifacts = path.join(root, ".test-artifacts");
      mkdirSync(artifacts, { recursive: true });
      writeFileSync(
        path.join(artifacts, "desktop.png"),
        Buffer.from(await command(route("/screenshot")), "base64"),
      );
      await command(route("/window/rect"), "POST", { width: 500, height: 850 });
      assert.equal(
        await execute(
          "return document.documentElement.scrollWidth <= window.innerWidth",
        ),
        true,
      );
      await click(".menu-toggle");
      await until(
        () =>
          execute(
            'return document.querySelector(".menu-toggle").getAttribute("aria-expanded")==="true"',
          ),
        "mobile menu",
      );
      assert.equal(
        await execute(
          'return document.querySelector(".skip-link").getAttribute("href")',
        ),
        "#main",
      );
      writeFileSync(
        path.join(artifacts, "mobile.png"),
        Buffer.from(await command(route("/screenshot")), "base64"),
      );
    });
  },
);
