// Shared evidence, independent browser RNG. No external runtime dependencies.
export function random(seed) {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}
const norm = (w) => w.toLowerCase().replace(/[^a-z]/g, "");
const pick = (a, rng) => a[Math.floor(rng() * a.length)];
function weighted(items, weight, rng) {
  const weights = items.map(weight),
    total = weights.reduce((a, b) => a + b, 0);
  let cursor = rng() * total;
  for (let i = 0; i < items.length; i++) {
    cursor -= weights[i];
    if (cursor < 0) return items[i];
  }
  return items.at(-1);
}
export function rankBlends(a, b) {
  let overlap = a + b;
  for (let n = Math.min(a.length, b.length); n > 1; n--)
    if (a.slice(-n) === b.slice(0, n)) {
      overlap = a + b.slice(n);
      break;
    }
  const options = [
    [overlap, "longest overlap"],
    [a + b, "concatenation"],
  ];
  const vowels = [...a.matchAll(/[aeiouy]+/g)];
  if (vowels.length > 1)
    options.push([
      a.slice(0, vowels.at(-1).index) + b,
      "final vowel-group cut",
    ]);
  const seen = new Set();
  return options
    .filter(([text]) => {
      if (seen.has(text)) return false;
      seen.add(text);
      return true;
    })
    .map(([text, method]) => {
      const retention = Math.min(1, text.length / (a.length + b.length));
      const clusters = (text.match(/[^aeiouy]+/g) || []).reduce(
        (s, c) => s + Math.max(0, c.length - 3),
        0,
      );
      return {
        text,
        method,
        retention,
        cluster_penalty: clusters,
        score: Number(
          (
            2 * retention -
            0.35 * clusters -
            (0.3 * Math.abs(text.length - 12)) / 12
          ).toFixed(4),
        ),
      };
    })
    .sort(
      (a, b) =>
        b.score - a.score || (a.text < b.text ? -1 : a.text > b.text ? 1 : 0),
    );
}
export function trainMarkov(words, order = 3) {
  const chain = new Map();
  for (const raw of words) {
    const word = "^".repeat(order) + norm(raw) + "$";
    for (let i = 0; i < word.length - order; i++) {
      const key = word.slice(i, i + order);
      if (!chain.has(key)) chain.set(key, []);
      chain.get(key).push(word[i + order]);
    }
  }
  return chain;
}
function markov(chain, seed, rng) {
  const prefix = norm(seed).slice(0, 2);
  for (let attempt = 0; attempt < 80; attempt++) {
    let text = prefix,
      key = ("^^^" + prefix).slice(-3),
      transitions = [];
    for (let i = 0; i < 16; i++) {
      const choices = chain.get(key);
      if (!choices) break;
      const next = pick(choices, rng);
      transitions.push({
        context: key,
        next,
        probability: choices.filter((c) => c === next).length / choices.length,
      });
      if (next === "$") {
        if (text.length >= 4 && text.length <= 14)
          return { text, transitions, fallback: false };
        break;
      }
      text += next;
      key = (key + next).slice(-3);
    }
  }
  return { text: norm(seed), transitions: [], fallback: true };
}
function source(word, atlas) {
  return {
    word,
    status: atlas.words[norm(word)]
      ? "attested"
      : "unverified seed or generated form",
    editorial_categories: ["tavern", "kings", "archaic"].filter((k) =>
      atlas.lexicon[k].includes(word),
    ),
    ...(atlas.words[norm(word)] || {
      occurrences: [],
      counts: {},
      log_odds: null,
      affiliation: "unverified",
    }),
  };
}
const STOP = new Set(
  "the a an of to and or in on is be are was were not that this with for from my our your his her i you we he she it they o all such by as if but so would could should has have did never".split(
    " ",
  ),
);
export function compose(atlas, options) {
  const { seed, rule, style, suffix, ambition } = options,
    rng = random(seed);
  const all = [
    ...new Set(
      ["tavern", "kings", "archaic", "titles", "characters", "places"].flatMap(
        (k) => atlas.lexicon[k],
      ),
    ),
  ];
  const chain = trainMarkov(all),
    results = [],
    seen = new Set();
  for (let attempt = 0; results.length < 4 && attempt < 160; attempt++) {
    let core,
      parts,
      candidates = [],
      quote = null,
      transitions = [],
      fallback = false;
    if (rule === "rogue_to_king") {
      const a = pick(atlas.lexicon.tavern, rng);
      const b = weighted(
        atlas.lexicon.kings,
        (w) => {
          const odds = atlas.words[norm(w)]?.log_odds || 0;
          return Math.exp(
            Math.max(-3, Math.min(3, odds)) * (ambition / 50 - 1),
          );
        },
        rng,
      );
      parts = [a, b];
      candidates = rankBlends(norm(a), norm(b));
      core = candidates[0].text;
    } else if (rule === "markov_coin") {
      const word = pick(all, rng),
        sampled = markov(chain, word, rng);
      parts = [word];
      core = sampled.text;
      transitions = sampled.transitions;
      fallback = sampled.fallback;
    } else if (rule === "quote_splice") {
      quote = pick(atlas.quotes, rng);
      const words = [
        ...new Set(
          (quote.text.toLowerCase().match(/[a-z]+/g) || []).filter(
            (w) => w.length >= 4 && !STOP.has(w),
          ),
        ),
      ];
      for (let i = words.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [words[i], words[j]] = [words[j], words[i]];
      }
      parts = words.slice(0, 3);
      core = parts[0];
      for (const next of parts.slice(1)) {
        candidates = rankBlends(core, next);
        core = candidates[0].text;
      }
    } else if (rule === "archaic_coinage") {
      const word = pick(atlas.lexicon.archaic, rng),
        affix = pick(atlas.lexicon.affixes, rng).replace(/^-/, "");
      parts = [word];
      core = norm(word).slice(0, Math.max(2, word.length - 1)) + affix;
    } else throw Error("Unknown composition rule");
    const date =
      suffix === "none"
        ? { value: "", kind: "none", explanation: "No date appended." }
        : suffix === "number"
          ? {
              value: String(10 + Math.floor(rng() * 90)),
              kind: "number",
              explanation: "Random numeric ornament; no historical claim.",
            }
          : atlas.years[suffix];
    if (!date) throw Error("Unknown date option");
    const variant =
      (style === "upper"
        ? core.toUpperCase()
        : style === "lower"
          ? core
          : core[0].toUpperCase() + core.slice(1)) + date.value;
    if (seen.has(variant)) continue;
    seen.add(variant);
    const trace =
      rule === "rogue_to_king"
        ? [
            {
              stage: "Eastcheap",
              value: parts[0],
              detail: "Select the tavern ingredient",
            },
            {
              stage: "Royal encounter",
              value: parts[1],
              detail: "Weighted by speaker-group affinity",
            },
            { stage: "Fusion", value: core, detail: candidates[0].method },
            {
              stage: "Inscription",
              value: variant,
              detail:
                date.kind === "historical"
                  ? "Append a historical allusion"
                  : date.explanation,
            },
          ]
        : [
            {
              stage: "Ingredients",
              value: parts.join(" + "),
              detail: quote
                ? quote.play
                : rule === "markov_coin"
                  ? "Lexicon prefix seed"
                  : "Archaic seed",
            },
            {
              stage: "Transformation",
              value: core,
              detail: rule.replaceAll("_", " "),
            },
            { stage: "Date", value: date.value || "—", detail: date.kind },
            { stage: "Inscription", value: variant, detail: "A new coinage" },
          ];
    results.push({
      variant,
      core,
      kind: rule,
      parts,
      suffix: date.value,
      provenance: {
        schema_version: 1,
        engine: "browser-1.1",
        options: { ...options },
        ordinal: results.length,
        sources: parts.map((w) => source(w, atlas)),
        quote,
        date,
        trace,
        candidates,
        transitions,
        fallback,
        corpus: atlas.sources.map((s) => ({ file: s.file, sha256: s.sha256 })),
        interpretation:
          "Word attestation is not attestation of the invented name. Speaker cohorts are editorial.",
      },
    });
  }
  if (!results.length) throw Error("No composition found. Try another seed.");
  return results;
}
