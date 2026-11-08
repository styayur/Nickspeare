import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const extensionSource = path.join(root, "extension");
const defaultOut = path.join(root, "dist", "extension");
const args = process.argv.slice(2);
const outFlag = args.indexOf("--out");
const out = path.resolve(outFlag >= 0 ? args[outFlag + 1] : defaultOut);
const expectedRoot = path.join(root, "dist") + path.sep;
if (!out.startsWith(expectedRoot)) {
  throw new Error(`Refusing to remove output outside dist/: ${out}`);
}
await rm(out, { recursive: true, force: true });
await mkdir(path.dirname(out), { recursive: true });
await cp(extensionSource, out, { recursive: true });
await cp(path.join(root, "packages", "core"), path.join(out, "core"), { recursive: true });
await cp(path.join(root, "docs", "atlas.json"), path.join(out, "core", "atlas.json"));
await mkdir(path.join(out, "licenses"), { recursive: true });
await cp(path.join(root, "LICENSE"), path.join(out, "licenses", "LICENSE"));
await cp(path.join(root, "DATA_SOURCES.md"), path.join(out, "licenses", "DATA_SOURCES.md"));
await cp(path.join(root, "SECURITY.md"), path.join(out, "licenses", "SECURITY.md"));

const manifest = JSON.parse(await readFile(path.join(out, "manifest.json"), "utf8"));
if (manifest.manifest_version !== 3) throw new Error("Extension must use Manifest V3.");
if (!/^\d+\.\d+\.\d+$/.test(manifest.version)) throw new Error("Manifest version must be numeric.");
if (manifest.version !== "0.1.1" || manifest.version_name !== "0.1.0-alpha.2") {
  throw new Error("Unexpected extension version identity.");
}
const permissions = manifest.permissions || [];
if (permissions.some((permission) => !["activeTab", "scripting", "storage"].includes(permission))) {
  throw new Error(`Unexpected permission: ${permissions.join(", ")}`);
}
if (manifest.host_permissions || manifest.optional_host_permissions) {
  throw new Error("Production extension must not request host permissions.");
}
for (const relative of [
  manifest.action.default_popup,
  manifest.background.service_worker,
  ...Object.values(manifest.icons),
  "core/index.js",
  "core/atlas.json",
  "licenses/LICENSE",
  "licenses/DATA_SOURCES.md",
]) {
  await readFile(path.join(out, relative));
}

let commit = process.env.GITHUB_SHA || "";
let dirty = false;
if (!commit) {
  try {
    commit = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
    dirty = Boolean(execFileSync("git", ["status", "--porcelain"], { cwd: root, encoding: "utf8" }).trim());
  } catch {
    commit = "unknown";
  }
}
await writeFile(
  path.join(out, "BUILD_PROVENANCE.json"),
  `${JSON.stringify({
    project: "Nickspeare",
    component: "browser-extension",
    version: manifest.version_name,
    manifestVersion: manifest.version,
    source: "https://github.com/styayur/Nickspeare",
    commit: commit || "unknown",
    dirty,
    runtimeDependencies: 0,
    builtAt: new Date().toISOString(),
  }, null, 2)}\n`,
  "utf8",
);
process.stdout.write(`Built extension at ${out}\n`);
