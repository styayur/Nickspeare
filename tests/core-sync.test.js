import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("Pages engine is a byte-identical mirror of the shared core", () => {
  const core = readFileSync(new URL("../packages/core/engine.js", import.meta.url));
  const pages = readFileSync(new URL("../docs/engine.js", import.meta.url));
  assert.deepEqual(pages, core);
});
