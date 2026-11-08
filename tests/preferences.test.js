import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_PREFERENCES,
  PREFERENCES_KEY,
  fromEngineSeed,
  loadPreferences,
  migratePreferences,
  savePreferences,
  toEngineOptions,
} from "../packages/core/preferences.js";

function memoryStorage(initial = {}) {
  const state = { ...initial };
  return {
    state,
    local: {
      async get(key) {
        return { [key]: state[key] };
      },
      async set(values) {
        Object.assign(state, values);
      },
    },
  };
}

test("preferences migrate malformed and legacy data without throwing", () => {
  const migrated = migratePreferences({
    rule: "quote_splice",
    minLength: 12,
    maxLength: 8,
    candidateCount: 99,
    seed: -9,
    ambition: "80",
    unexpected: "discard",
  });
  assert.equal(migrated.schemaVersion, 1);
  assert.equal(migrated.rule, "quote_splice");
  assert.equal(migrated.minLength, 8);
  assert.equal(migrated.maxLength, 12);
  assert.equal(migrated.candidateCount, 6);
  assert.equal(migrated.seed, 0);
  assert.equal(migrated.ambition, 80);
  assert.equal("unexpected" in migrated, false);
});

test("load, save and seed updates use only the versioned local key", async () => {
  const storage = memoryStorage({
    [PREFERENCES_KEY]: { rule: "archaic_coinage", suffix: "none", schemaVersion: 0 },
    "nickspeare.user": "must not be read",
  });
  const loaded = await loadPreferences(storage);
  assert.equal(loaded.rule, "archaic_coinage");
  assert.equal(loaded.suffix, "none");
  const saved = await savePreferences(storage, fromEngineSeed(loaded, 42));
  assert.equal(saved.seed, 42);
  assert.equal(storage.state[PREFERENCES_KEY].seed, 42);
  assert.deepEqual(Object.keys(storage.state).sort(), [PREFERENCES_KEY, "nickspeare.user"].sort());
});

test("engine options preserve page-compatible option names", () => {
  assert.deepEqual(toEngineOptions({ ...DEFAULT_PREFERENCES, caseStyle: "upper", seed: 7 }), {
    seed: 7,
    rule: "rogue_to_king",
    style: "upper",
    suffix: "agincourt",
    ambition: 65,
  });
});

