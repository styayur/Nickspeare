import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { compose, generateConstrained, normalizeUsernamePolicy, validateUsername } from "../packages/core/index.js";
import { compose as facadeCompose } from "../docs/engine.js";

const atlas = JSON.parse(readFileSync(new URL("../docs/atlas.json", import.meta.url)));
const base = {
  seed: 1415,
  rule: "rogue_to_king",
  style: "title",
  suffix: "none",
  ambition: 65,
};

test("shared core generates the same replayable records as the Pages facade", () => {
  assert.deepEqual(compose(atlas, base), facadeCompose(atlas, base));
});

test("policy validation rejects length, characters, case and reserved words", () => {
  assert.equal(validateUsername("Sack", { minLength: 5, maxLength: 12 }).valid, false);
  assert.equal(validateUsername("Sack!", { minLength: 4, maxLength: 12 }).valid, false);
  assert.equal(validateUsername("sack", { caseStyle: "title" }).valid, false);
  assert.equal(validateUsername("Sack", { reservedWords: ["sack"] }).valid, false);
  assert.equal(validateUsername("Sack_1415", { allowUnderscore: false }).valid, false);
  assert.equal(validateUsername("Sack1415", { allowNumbers: false }).valid, false);
});

test("policy normalization clamps and migrates malformed values", () => {
  const policy = normalizeUsernamePolicy({
    minLength: -4,
    maxLength: 999,
    candidateCount: 20,
    rule: "unknown",
    caseStyle: "mixed",
    allowNumbers: "false",
    reservedWords: "king, crown,  king",
  });
  assert.equal(policy.minLength, 1);
  assert.equal(policy.maxLength, 64);
  assert.equal(policy.candidateCount, 6);
  assert.equal(policy.rule, "rogue_to_king");
  assert.equal(policy.caseStyle, "title");
  assert.equal(policy.allowNumbers, true);
  assert.deepEqual(policy.reservedWords, ["king", "crown"]);
});

test("constrained generation regenerates rather than truncating candidates", () => {
  const output = generateConstrained(
    atlas,
    base,
    {
      minLength: 8,
      maxLength: 14,
      candidateCount: 4,
      caseStyle: "title",
      allowNumbers: false,
      allowUnderscore: false,
    },
  );
  assert.equal(output.satisfied, true, JSON.stringify(output.rejected));
  assert.equal(output.results.length, 4);
  assert.equal(new Set(output.results.map((row) => row.variant.toLowerCase())).size, 4);
  for (const row of output.results) {
    assert.ok(row.variant.length >= 8 && row.variant.length <= 14, row.variant);
    assert.match(row.variant, /^[A-Z][a-z]+$/);
    assert.equal(validateUsername(row.variant, output.policy).valid, true);
  }
});

test("impossible policies report an honest satisfied=false result", () => {
  const output = generateConstrained(
    atlas,
    { ...base, suffix: "number" },
    { minLength: 4, maxLength: 10, allowNumbers: false, candidateCount: 2 },
    4,
  );
  assert.equal(output.results.length, 0);
  assert.equal(output.satisfied, false);
  assert.ok(output.rejected.length > 0);
});
