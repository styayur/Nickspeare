import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { compose, rankBlends } from "../docs/engine.js";
const atlas = JSON.parse(
  readFileSync(new URL("../docs/atlas.json", import.meta.url)),
);
const defaults = {
  seed: 1415,
  rule: "rogue_to_king",
  style: "title",
  suffix: "agincourt",
  ambition: 65,
};
test("all rules produce replayable structured records", () => {
  for (const rule of [
    "rogue_to_king",
    "markov_coin",
    "quote_splice",
    "archaic_coinage",
  ]) {
    const opts = { ...defaults, rule },
      a = compose(atlas, opts);
    assert.deepEqual(a, compose(atlas, opts));
    assert.equal(a.length, 4);
    assert.equal(new Set(a.map((n) => n.variant)).size, 4);
    for (const n of a) {
      assert.ok(n.variant.endsWith("1415"));
      assert.equal(n.provenance.trace.length, 4);
    }
  }
});
test("no suffix never leaks years", () => {
  for (let seed = 0; seed < 40; seed++)
    assert.ok(
      compose(atlas, { ...defaults, seed, suffix: "none" }).every((n) =>
        /^[A-Za-z]+$/.test(n.variant),
      ),
    );
});
test("numeric ornaments remain nonhistorical", () =>
  assert.equal(
    compose(atlas, { ...defaults, suffix: "number" })[0].provenance.date.kind,
    "number",
  ));
test("royal affinity changes weighted selection", () =>
  assert.notDeepEqual(
    compose(atlas, { ...defaults, ambition: 0 }),
    compose(atlas, { ...defaults, ambition: 100 }),
  ));
test("Markov records real conditional transitions", () => {
  for (const n of compose(atlas, { ...defaults, rule: "markov_coin" })) {
    assert.ok(n.core.startsWith(n.parts[0].replace(/[^a-z]/g, "").slice(0, 2)));
    assert.ok(
      n.provenance.transitions.every(
        (t) => t.probability > 0 && t.probability <= 1,
      ),
    );
  }
});
test("ranked blends keep alternatives and prefer highest score", () => {
  const rows = rankBlends("counterfeit", "majesty");
  assert.ok(rows.length > 1);
  assert.ok(rows.every((r) => r.score <= rows[0].score));
});
