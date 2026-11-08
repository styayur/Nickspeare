import { execFileSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const output = path.join(root, "dist", "extension-test");
execFileSync(process.execPath, ["scripts/build-extension.mjs", "--out", output], {
  cwd: root,
  stdio: "inherit",
});
const manifestPath = path.join(output, "manifest.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
manifest.name = `${manifest.name} (test build)`;
manifest.host_permissions = ["http://127.0.0.1/*"];
await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`Patched loopback-only test permissions at ${output}\n`);
