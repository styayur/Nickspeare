import { copyFile } from "node:fs/promises";
await copyFile(
  new URL("../packages/core/engine.js", import.meta.url),
  new URL("../docs/engine.js", import.meta.url),
);
console.log("Synced packages/core/engine.js -> docs/engine.js");
