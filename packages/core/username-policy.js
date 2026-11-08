import { compose } from "./engine.js";

export const USERNAME_POLICY_SCHEMA = 1;
export const USERNAME_POLICY_LIMITS = Object.freeze({
  minLength: 1,
  maxLength: 64,
  candidateCountMin: 1,
  candidateCountMax: 6,
});
export const CASE_STYLES = Object.freeze(["title", "lower", "upper"]);
export const COMPOSITION_RULES = Object.freeze([
  "rogue_to_king",
  "markov_coin",
  "quote_splice",
  "archaic_coinage",
]);
export const SUFFIX_OPTIONS = Object.freeze(["agincourt", "coronation", "none", "number"]);

const count = (value, fallback, min, max) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, Math.trunc(parsed)));
};

const stringList = (value) => {
  if (Array.isArray(value)) {
    return [...new Set(value.map(String).map((item) => item.trim()).filter(Boolean))];
  }
  if (typeof value === "string") {
    return [...new Set(value.split(/[\s,]+/).map((item) => item.trim()).filter(Boolean))];
  }
  return [];
};

export function normalizeUsernamePolicy(input = {}) {
  const source = input && typeof input === "object" ? input : {};
  const rawMin = count(
    source.minLength,
    USERNAME_POLICY_LIMITS.minLength,
    USERNAME_POLICY_LIMITS.minLength,
    USERNAME_POLICY_LIMITS.maxLength,
  );
  const rawMax = count(
    source.maxLength,
    24,
    USERNAME_POLICY_LIMITS.minLength,
    USERNAME_POLICY_LIMITS.maxLength,
  );
  return {
    schemaVersion: USERNAME_POLICY_SCHEMA,
    minLength: Math.min(rawMin, rawMax),
    maxLength: Math.max(rawMin, rawMax),
    candidateCount: count(
      source.candidateCount,
      5,
      USERNAME_POLICY_LIMITS.candidateCountMin,
      USERNAME_POLICY_LIMITS.candidateCountMax,
    ),
    caseStyle: CASE_STYLES.includes(source.caseStyle)
      ? source.caseStyle
      : "title",
    allowNumbers: source.allowNumbers !== false,
    allowUnderscore: source.allowUnderscore !== false,
    rule: COMPOSITION_RULES.includes(source.rule)
      ? source.rule
      : "rogue_to_king",
    suffix: SUFFIX_OPTIONS.includes(source.suffix) ? source.suffix : "agincourt",
    reservedWords: stringList(source.reservedWords),
    forbiddenPrefixes: stringList(source.forbiddenPrefixes),
    forbiddenSuffixes: stringList(source.forbiddenSuffixes),
  };
}

export function validateUsername(value, inputPolicy = {}) {
  const policy = normalizeUsernamePolicy(inputPolicy);
  const username = String(value ?? "");
  const reasons = [];
  if (!username) return { valid: false, reasons: ["Username is empty."] };
  if (username.length < policy.minLength) reasons.push(`Shorter than ${policy.minLength} characters.`);
  if (username.length > policy.maxLength) reasons.push(`Longer than ${policy.maxLength} characters.`);
  if (!/[A-Za-z]/.test(username)) reasons.push("Must contain at least one letter.");

  const allowed = policy.allowUnderscore ? /^[A-Za-z0-9_]+$/ : /^[A-Za-z0-9]+$/;
  if (!allowed.test(username)) {
    reasons.push(policy.allowUnderscore ? "Contains characters outside letters, numbers and underscores." : "Contains characters outside letters and numbers.");
  }
  if (!policy.allowNumbers && /\d/.test(username)) reasons.push("Numbers are not allowed.");
  if (!policy.allowUnderscore && username.includes("_")) reasons.push("Underscores are not allowed.");
  if (username.startsWith("_") || username.endsWith("_") || username.includes("__")) {
    reasons.push("Underscores may not lead, trail or repeat.");
  }

  if (policy.caseStyle === "lower" && username !== username.toLowerCase()) reasons.push("Must use lowercase letters.");
  if (policy.caseStyle === "upper" && username !== username.toUpperCase()) reasons.push("Must use uppercase letters.");
  if (policy.caseStyle === "title") {
    const expected = username ? username[0].toUpperCase() + username.slice(1).toLowerCase() : "";
    if (username !== expected) reasons.push("Must use title case.");
  }

  const folded = username.toLowerCase();
  if (policy.reservedWords.some((word) => word.toLowerCase() === folded)) reasons.push("Username is reserved.");
  if (policy.forbiddenPrefixes.some((prefix) => folded.startsWith(prefix.toLowerCase()))) reasons.push("Username uses a forbidden prefix.");
  if (policy.forbiddenSuffixes.some((suffix) => folded.endsWith(suffix.toLowerCase()))) reasons.push("Username uses a forbidden suffix.");
  return { valid: reasons.length === 0, reasons };
}

export function generateConstrained(atlas, options, inputPolicy = {}, maxSeedAttempts = 256) {
  const policy = normalizeUsernamePolicy(inputPolicy);
  const results = [];
  const rejected = [];
  const seen = new Set();
  let seed = Number(options.seed) >>> 0;
  let attempts = 0;
  while (results.length < policy.candidateCount && attempts < maxSeedAttempts) {
    let batch;
    try {
      batch = compose(atlas, { ...options, seed });
    } catch (error) {
      rejected.push({ value: null, reasons: [String(error?.message || error)] });
      seed = (seed + 1) >>> 0;
      attempts += 1;
      continue;
    }
    for (const candidate of batch) {
      const key = candidate.variant.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const verdict = validateUsername(candidate.variant, policy);
      if (verdict.valid) results.push(candidate);
      else if (rejected.length < 20) rejected.push({ value: candidate.variant, reasons: verdict.reasons });
      if (results.length === policy.candidateCount) break;
    }
    seed = (seed + 1) >>> 0;
    attempts += 1;
  }
  return {
    results,
    attempts,
    policy,
    rejected,
    satisfied: results.length === policy.candidateCount,
  };
}
