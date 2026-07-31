import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { AGENT_ONBOARDING_PROMPT, INSTALL_COMMAND } from "../src/app.js";
import worker from "../worker/index.js";

const testDirectory = dirname(fileURLToPath(import.meta.url));
const siteDirectory = resolve(testDirectory, "..");
const repositoryDirectory = resolve(siteDirectory, "..");

test("homepage exposes every official distribution and agent resource", async () => {
  const html = await readFile(resolve(siteDirectory, "src/index.html"), "utf8");

  for (const expected of [
    "https://perfectplaylist.dev",
    "https://pypi.org/project/perfect-playlist/",
    "https://github.com/devin-thomas/perfect-playlist",
    "/SKILL.md",
    INSTALL_COMMAND,
    "data-copy=\"onboarding\"",
  ]) {
    assert.match(html, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("agent onboarding prompt identifies the product and preserves safety boundaries", () => {
  for (const expected of [
    "https://perfectplaylist.dev",
    "https://pypi.org/project/perfect-playlist/",
    "https://github.com/devin-thomas/perfect-playlist",
    "https://perfectplaylist.dev/SKILL.md",
    INSTALL_COMMAND,
    "Preserve order and duplicates",
    "Never substitute, reorder, silently skip, overwrite",
  ]) {
    assert.ok(AGENT_ONBOARDING_PROMPT.includes(expected), `missing ${expected}`);
  }
});

test("build publishes the repository's canonical skill without drift", async () => {
  const [canonicalSkill, publishedSkill] = await Promise.all([
    readFile(resolve(repositoryDirectory, "SKILL.md"), "utf8"),
    readFile(resolve(siteDirectory, "dist/SKILL.md"), "utf8"),
  ]);

  assert.equal(publishedSkill, canonicalSkill);
});

test("worker adds browser security headers to static responses", async () => {
  const env = {
    ASSETS: {
      fetch: async () => new Response("ok", { headers: { "Content-Type": "text/plain" } }),
    },
  };
  const response = await worker.fetch(new Request("https://perfectplaylist.dev/"), env);

  assert.equal(response.headers.get("X-Content-Type-Options"), "nosniff");
  assert.equal(response.headers.get("Cross-Origin-Opener-Policy"), "same-origin");
  const policy = response.headers.get("Content-Security-Policy");
  assert.match(policy, /frame-ancestors 'none'/);
  assert.match(policy, /script-src 'self' https:\/\/static\.cloudflareinsights\.com/);
  assert.match(policy, /connect-src 'self' https:\/\/cloudflareinsights\.com/);
});
