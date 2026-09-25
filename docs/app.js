import { compose } from "./engine.js";
const $ = (id) => document.getElementById(id);
const escape = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let atlas,
  results = [],
  selected = 0,
  step = -1,
  lastKey = "";
const params = new URLSearchParams(location.search);
for (const id of ["rule", "style", "suffix", "seed", "ambition"])
  if (params.has(id)) {
    const element = $(id),
      value = params.get(id);
    if (element.tagName === "SELECT") {
      if ([...element.options].some((o) => o.value === value))
        element.value = value;
    } else if (
      /^\d+$/.test(value) &&
      Number(value) >= Number(element.min) &&
      Number(value) <= Number(element.max)
    )
      element.value = value;
  }
function affinity() {
  const enabled = $("rule").value === "rogue_to_king";
  $("ambition").disabled = !enabled;
  $("affinity-value").textContent = enabled
    ? $("ambition").value + "%"
    : "not used by this rule";
}
$("ambition").addEventListener("input", affinity);
$("rule").addEventListener("change", affinity);
affinity();
function options() {
  return {
    seed: Number($("seed").value),
    rule: $("rule").value,
    style: $("style").value,
    suffix: $("suffix").value,
    ambition: Number($("ambition").value),
  };
}
function render(index) {
  selected = index;
  step = -1;
  const n = results[index],
    p = n.provenance;
  $("result").hidden = false;
  $("result-name").textContent = n.variant;
  $("result-kind").textContent = n.kind.replaceAll("_", " ");
  $("result-description").textContent = n.parts.join(" + ") + " → " + n.core;
  $("journey-title").textContent =
    n.kind === "rogue_to_king"
      ? "From Eastcheap to Agincourt"
      : "The making of a name";
  $("advance").textContent =
    n.kind === "rogue_to_king" ? "Follow the coronation" : "Follow the process";
  $("journey").innerHTML = p.trace
    .map(
      (s, i) =>
        `<li><span class="step">${i + 1} / ${escape(s.stage)}</span><strong>${escape(s.value)}</strong><small>${escape(s.detail)}</small></li>`,
    )
    .join("");
  $("evidence").innerHTML =
    (p.quote
      ? `<p>Quote seed: “${escape(p.quote.text)}” — ${escape(p.quote.speaker)}, <cite>${escape(p.quote.play)}</cite>. This curated attribution is separate from the three-play word index below.</p>`
      : "") +
    p.sources
      .map(
        (s) =>
          `<article class="evidence-word"><div class="evidence-head"><b>${escape(s.word)}</b><span class="faction">${escape(s.affiliation || "unverified")} / ${escape(s.status)}</span></div><small>Editorial category: ${escape(s.editorial_categories.join(", ") || "none")}. ${s.log_odds === null ? "No indexed attestation in these three plays." : `Royal log odds: ${s.log_odds.toFixed(3)} · ${s.counts.total} spoken occurrences`}</small><ul>${s.occurrences
            .slice(0, 2)
            .map(
              (e) =>
                `<li><a href="${escape(e.url)}" target="_blank" rel="noopener">${escape(e.play)}</a> — ${escape(e.speakers.join(" / ") || "unattributed")}<br><small>line ${escape(e.line || "unlabelled")} / ${escape(e.speech_id)} / ${escape(e.word_id)}</small></li>`,
            )
            .join("")}</ul></article>`,
      )
      .join("");
  const rows = [
    ["engine", p.engine],
    ["seed", p.options.seed],
    ["impression", index + 1],
    [
      "royal affinity",
      n.kind === "rogue_to_king" ? p.options.ambition + "%" : "not applicable",
    ],
    ["date class", p.date.kind],
    ["source corpus", "1H4 / 2H4 / H5"],
    [
      "Markov",
      n.kind === "markov_coin"
        ? `order 3; ${p.transitions.length} transitions${p.fallback ? "; seed fallback" : ""}`
        : "not used",
    ],
  ];
  $("record").innerHTML = rows
    .map(([k, v]) => `<dt>${escape(k)}</dt><dd>${escape(v)}</dd>`)
    .join("");
  $("candidates").innerHTML = p.candidates.length
    ? `<table><thead><tr><th scope="col">Candidate</th><th scope="col">Score</th></tr></thead><tbody>${p.candidates.map((c) => `<tr><td>${escape(c.text)}<br>${escape(c.method)}</td><td>${c.score.toFixed(3)}</td></tr>`).join("")}</tbody></table>`
    : p.transitions.length
      ? `<p>${p.transitions.map((t) => `${escape(t.context)} → ${escape(t.next)} (${t.probability.toFixed(2)})`).join("<br>")}</p>`
      : "<p>This rule does not rank blend candidates.</p>";
  $("date-note").textContent = p.date.explanation;
  $("alternatives").innerHTML = results
    .map(
      (r, i) =>
        `<button data-index="${i}" aria-pressed="${i === index}">${escape(r.variant)}</button>`,
    )
    .join("");
}
function run(advanceSeed = false) {
  let opts = options(),
    key = JSON.stringify(opts);
  if (advanceSeed && key === lastKey) {
    $("seed").value = String((opts.seed + 1) >>> 0);
    opts = options();
    key = JSON.stringify(opts);
  }
  results = compose(atlas, opts);
  lastKey = key;
  render(0);
  $("status").textContent =
    `${results.length} impressions composed. Seed ${opts.seed}; replayable in this browser engine.`;
}
$("compose-form").addEventListener("submit", (e) => {
  e.preventDefault();
  try {
    run(true);
  } catch (error) {
    $("status").textContent = error.message;
  }
});
$("alternatives").addEventListener("click", (e) => {
  const button = e.target.closest("button");
  if (button) render(Number(button.dataset.index));
});
$("advance").addEventListener("click", () => {
  step = (step + 1) % 4;
  [...$("journey").children].forEach((li, i) => {
    li.classList.toggle("active", i === step);
    if (i === step) li.setAttribute("aria-current", "step");
    else li.removeAttribute("aria-current");
  });
  const entry = results[selected].provenance.trace[step];
  $("status").textContent =
    `Step ${step + 1}: ${entry.stage} — ${entry.value}. ${entry.detail}`;
  $("advance").textContent = step === 3 ? "Begin again" : "Next step";
});
async function copy(text, label) {
  try {
    await navigator.clipboard.writeText(text);
    $("status").textContent = label;
  } catch {
    $("status").textContent =
      "Clipboard unavailable. Use Export provenance to save the name and replay settings.";
  }
}
$("copy").addEventListener("click", () =>
  copy(results[selected].variant, "Name copied."),
);
$("share").addEventListener("click", () => {
  const url = new URL(location.href);
  url.search = new URLSearchParams({
    ...results[selected].provenance.options,
    impression: selected,
  }).toString();
  copy(url.href, "Replay link copied.");
});
$("download").addEventListener("click", () => {
  const n = results[selected],
    blob = new Blob([JSON.stringify(n, null, 2) + "\n"], {
      type: "application/json",
    }),
    url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = n.variant + "-provenance.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $("status").textContent =
    "Provenance exported with source hashes and replay settings.";
});
try {
  const response = await fetch("./atlas.json");
  if (!response.ok)
    throw Error(
      `Source atlas could not load (${response.status}). Reload to retry.`,
    );
  atlas = await response.json();
  $("corpus-status").textContent =
    `3 plays / ${Object.keys(atlas.words).length} indexed words`;
  $("go").disabled = false;
  run();
  const impression = Number(params.get("impression"));
  if (
    Number.isInteger(impression) &&
    impression >= 0 &&
    impression < results.length
  )
    render(impression);
} catch (error) {
  $("status").textContent = error.message;
  $("corpus-status").textContent = "Source atlas unavailable";
}
