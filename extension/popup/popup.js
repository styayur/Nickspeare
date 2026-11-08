import {
  DEFAULT_PREFERENCES,
  PREFERENCES_KEY,
  generateConstrained,
  loadPreferences,
  migratePreferences,
  toEngineOptions,
} from "../core/index.js";

const byId = (id) => document.getElementById(id);
const controls = {
  seed: byId("seed"),
  rule: byId("rule"),
  caseStyle: byId("caseStyle"),
  suffix: byId("suffix"),
  candidateCount: byId("candidateCount"),
  minLength: byId("minLength"),
  maxLength: byId("maxLength"),
  allowNumbers: byId("allowNumbers"),
  allowUnderscore: byId("allowUnderscore"),
  reservedWords: byId("reservedWords"),
  forbiddenPrefixes: byId("forbiddenPrefixes"),
  forbiddenSuffixes: byId("forbiddenSuffixes"),
};
const ui = {
  generate: byId("generate"),
  refresh: byId("refresh"),
  status: byId("status"),
  hint: byId("constraint-hint"),
  candidates: byId("candidates"),
  empty: byId("empty"),
  toast: byId("toast"),
};

let atlas;
let preferences = migratePreferences(DEFAULT_PREFERENCES);
let toastTimer;

function splitTerms(value) {
  return [...new Set(value.split(/[\s,]+/).map((term) => term.trim()).filter(Boolean))];
}

function readForm() {
  return migratePreferences({
    schemaVersion: 1,
    seed: Number(controls.seed.value),
    rule: controls.rule.value,
    caseStyle: controls.caseStyle.value,
    suffix: controls.suffix.value,
    candidateCount: Number(controls.candidateCount.value),
    minLength: Number(controls.minLength.value),
    maxLength: Number(controls.maxLength.value),
    allowNumbers: controls.allowNumbers.checked,
    allowUnderscore: controls.allowUnderscore.checked,
    reservedWords: splitTerms(controls.reservedWords.value),
    forbiddenPrefixes: splitTerms(controls.forbiddenPrefixes.value),
    forbiddenSuffixes: splitTerms(controls.forbiddenSuffixes.value),
  });
}

function writeForm(next) {
  const value = migratePreferences(next);
  controls.seed.value = value.seed;
  controls.rule.value = value.rule;
  controls.caseStyle.value = value.caseStyle;
  controls.suffix.value = value.suffix;
  controls.candidateCount.value = value.candidateCount;
  controls.minLength.value = value.minLength;
  controls.maxLength.value = value.maxLength;
  controls.allowNumbers.checked = value.allowNumbers;
  controls.allowUnderscore.checked = value.allowUnderscore;
  controls.reservedWords.value = value.reservedWords.join(", ");
  controls.forbiddenPrefixes.value = value.forbiddenPrefixes.join(", ");
  controls.forbiddenSuffixes.value = value.forbiddenSuffixes.join(", ");
  updateConstraintHint(value);
}

function updateConstraintHint(value) {
  const suffixHasDigits = value.suffix !== "none";
  const conflict = !value.allowNumbers && suffixHasDigits;
  ui.hint.hidden = !conflict;
  if (conflict) {
    ui.hint.textContent = "The selected suffix contains digits. Allow numbers or choose “No suffix”.";
  }
}

let saveTimer;
function queueSave() {
  preferences = readForm();
  updateConstraintHint(preferences);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    chrome.storage.local.set({ [PREFERENCES_KEY]: preferences }).catch(() => {
      showToast("Preferences could not be saved.");
    });
  }, 180);
}

function showToast(message) {
  clearTimeout(toastTimer);
  ui.toast.textContent = message;
  ui.toast.hidden = false;
  toastTimer = setTimeout(() => {
    ui.toast.hidden = true;
  }, 2200);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.append(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    return copied;
  }
}

function sourceText(source) {
  if (source.status === "attested") {
    const counts = source.counts?.total || 0;
    return `${counts} spoken occurrence${counts === 1 ? "" : "s"}`;
  }
  return source.status;
}

function candidateRow(candidate) {
  const item = document.createElement("li");
  item.className = "candidate";

  const head = document.createElement("div");
  head.className = "candidate-head";
  const name = document.createElement("h3");
  name.className = "candidate-name";
  name.textContent = candidate.variant;
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "copy";
  copy.textContent = "Copy";
  copy.setAttribute("aria-label", `Copy ${candidate.variant}`);
  copy.addEventListener("click", async () => {
    if (await copyText(candidate.variant)) showToast(`Copied ${candidate.variant}`);
    else showToast("Clipboard access was refused by the browser.");
  });
  head.append(name, copy);

  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Why this name?";
  details.append(summary);

  const why = document.createElement("p");
  why.className = "why";
  const formation = document.createElement("strong");
  formation.textContent = candidate.parts.join(" + ");
  why.append(formation, document.createTextNode(` → ${candidate.core}. Rule: ${candidate.kind.replaceAll("_", " ")}. `));
  for (const source of candidate.provenance.sources) {
    const line = document.createElement("span");
    line.className = "source-line";
    const category = source.editorial_categories.join(", ") || "not editorially categorised";
    line.textContent = `${source.word}: ${category}; ${sourceText(source)}.`;
    why.append(line);
  }
  const seedLine = document.createElement("span");
  seedLine.className = "source-line";
  seedLine.textContent = `Seed ${candidate.provenance.options.seed}; engine ${candidate.provenance.engine}.`;
  why.append(seedLine);
  details.append(why);

  item.append(head, details);
  return item;
}

function renderOutput(output) {
  ui.candidates.replaceChildren();
  ui.empty.hidden = output.results.length > 0;
  for (const candidate of output.results) ui.candidates.append(candidateRow(candidate));
  if (output.satisfied) {
    const firstSeed = output.results[0]?.provenance.options.seed;
    ui.status.textContent = `${output.results.length} names composed locally · seed ${firstSeed}`;
  } else if (output.results.length) {
    ui.status.textContent = `Only ${output.results.length} of ${output.policy.candidateCount} names fit these rules. Loosen a constraint to see more.`;
  } else {
    ui.status.textContent = "No candidate could satisfy these rules. The generator did not truncate a name.";
  }
}

async function generate() {
  ui.generate.disabled = true;
  ui.refresh.disabled = true;
  ui.status.textContent = "Turning the press…";
  try {
    preferences = readForm();
    await chrome.storage.local.set({ [PREFERENCES_KEY]: preferences });
    const output = generateConstrained(atlas, toEngineOptions(preferences), preferences);
    renderOutput(output);
  } catch (error) {
    ui.status.textContent = "The local engine could not compose a name. Try another seed.";
    ui.candidates.replaceChildren();
    ui.empty.hidden = false;
  } finally {
    ui.generate.disabled = false;
    ui.refresh.disabled = false;
  }
}

async function refresh() {
  preferences = readForm();
  const nextSeed = (preferences.seed + 1) >>> 0;
  controls.seed.value = nextSeed;
  await generate();
}

async function init() {
  try {
    const response = await fetch("../core/atlas.json");
    if (!response.ok) throw new Error(`Atlas load failed: ${response.status}`);
    atlas = await response.json();
    preferences = await loadPreferences(chrome.storage);
    writeForm(preferences);
    await generate();
  } catch (error) {
    ui.status.textContent = "The local atlas could not be loaded. Reload the extension.";
    ui.generate.disabled = true;
    ui.refresh.disabled = true;
  }
}

for (const element of [controls.rule, controls.caseStyle, controls.suffix, controls.candidateCount, controls.allowNumbers, controls.allowUnderscore]) {
  element.addEventListener("change", queueSave);
}
for (const element of [controls.seed, controls.minLength, controls.maxLength, controls.reservedWords, controls.forbiddenPrefixes, controls.forbiddenSuffixes]) {
  element.addEventListener("input", queueSave);
}
ui.generate.addEventListener("click", generate);
ui.refresh.addEventListener("click", refresh);
init();

