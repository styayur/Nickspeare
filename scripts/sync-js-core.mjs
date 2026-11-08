import { copyFile } from "node:fs/promises";
await copyFile(
  new URL("../packages/core/engine.js", import.meta.url),
  new URL("../docs/engine.js", import.meta.url),
);
process.stdout.write("Synced packages/core/engine.js -> docs/engine.js\n");

