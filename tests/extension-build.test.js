import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));

function filesUnder(directory) {
  return readdirSync(directory).flatMap((name) => {
    const full = path.join(directory, name);
    return statSync(full).isDirectory() ? filesUnder(full) : [full];
  });
}

test("extension build is standalone, versioned and permission-minimal", () => {
  execFileSync(process.execPath, ["scripts/build-extension.mjs"], { cwd: root, stdio: "pipe" });
  const output = path.join(root, "dist", "extension");
  const manifest = JSON.parse(readFileSync(path.join(output, "manifest.json"), "utf8"));
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.version, "0.1.0");
  assert.equal(manifest.version_name, "0.1.0-alpha.1");
  assert.deepEqual(manifest.permissions.sort(), ["activeTab", "scripting", "storage"]);
  assert.equal(manifest.host_permissions, undefined);
  assert.equal(manifest.optional_host_permissions, undefined);
  assert.match(manifest.content_security_policy.extension_pages, /script-src 'self'/);

  const names = filesUnder(output).map((file) => path.relative(output, file).replaceAll("\\", "/"));
  assert.ok(names.includes("core/engine.js"));
  assert.ok(names.includes("core/atlas.json"));
  assert.ok(names.includes("licenses/LICENSE"));
  assert.ok(names.includes("licenses/DATA_SOURCES.md"));
  assert.ok(names.includes("popup/popup.js"));
  assert.ok(!names.some((name) => /(^|\/)(node_modules|\.git|tests?|coverage)(\/|$)/.test(name)));
});

test("extension runtime contains no remote code or eval primitives", () => {
  const output = path.join(root, "dist", "extension");
  const javascript = filesUnder(output)
    .filter((file) => file.endsWith(".js"))
    .map((file) => readFileSync(file, "utf8"))
    .join("\n");
  assert.doesNotMatch(javascript, /\beval\s*\(/);
  assert.doesNotMatch(javascript, /\bnew\s+Function\b/);
  assert.doesNotMatch(javascript, /https?:\/\/[^\s"']+\.js\b/);
  const html = filesUnder(output)
    .filter((file) => file.endsWith(".html"))
    .map((file) => readFileSync(file, "utf8"))
    .join("\n");
  assert.doesNotMatch(html, /<script[^>]+src=["']https?:/i);
});
