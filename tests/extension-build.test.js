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
  assert.equal(manifest.version, "0.1.1");
  assert.equal(manifest.version_name, "0.1.0-alpha.2");
  assert.equal(manifest.default_locale, "en");
  assert.equal(manifest.name, "__MSG_extensionName__");
  assert.equal(manifest.description, "__MSG_extensionDescription__");
  assert.deepEqual(manifest.permissions.sort(), ["activeTab", "scripting", "storage"]);
  assert.equal(manifest.host_permissions, undefined);
  assert.equal(manifest.optional_host_permissions, undefined);
  assert.match(manifest.content_security_policy.extension_pages, /script-src 'self'/);

  const names = filesUnder(output).map((file) => path.relative(output, file).replaceAll("\\", "/"));
  assert.ok(names.includes("core/engine.js"));
  assert.ok(names.includes("core/atlas.json"));
  assert.ok(names.includes("licenses/LICENSE"));
  assert.ok(names.includes("licenses/DATA_SOURCES.md"));
  assert.ok(names.includes("SOURCE.md"));
  assert.ok(names.includes("_locales/en/messages.json"));
  assert.ok(names.includes("_locales/zh_CN/messages.json"));
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

test("test-only extension grants loopback access without contaminating production", () => {
  execFileSync(process.execPath, ["scripts/extension-loopback-build.mjs"], { cwd: root, stdio: "pipe" });
  const production = JSON.parse(readFileSync(path.join(root, "dist", "extension", "manifest.json"), "utf8"));
  const testBuild = JSON.parse(readFileSync(path.join(root, "dist", "extension-test", "manifest.json"), "utf8"));
  assert.equal(production.host_permissions, undefined);
  assert.deepEqual(testBuild.host_permissions, ["http://127.0.0.1/*"]);
  assert.match(testBuild.name, /test build/);
  assert.ok(filesUnder(path.join(root, "dist", "extension-test")).some((file) => file.endsWith("username-detector.js")));
});

test("page bridge avoids destructive DOM and code-evaluation APIs", () => {
  const content = readFileSync(path.join(root, "extension", "content", "username-detector.js"), "utf8");
  assert.doesNotMatch(content, /\.innerHTML\s*=/);
  assert.doesNotMatch(content, /\beval\s*\(/);
  assert.doesNotMatch(content, /\bnew\s+Function\b/);
  assert.doesNotMatch(content, /fetch\s*\(/);
  assert.match(content, /sender\.id !== chrome\.runtime\.id/);
  assert.match(content, /FIELD_NOT_EMPTY/);
  assert.match(content, /SENSITIVE_HINTS/);
});
