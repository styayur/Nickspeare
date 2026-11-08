import { normalizeUsernamePolicy } from "./username-policy.js";

export const PREFERENCES_SCHEMA = 1;
export const PREFERENCES_KEY = "nickspeare.preferences.v1";

export const DEFAULT_PREFERENCES = Object.freeze({
  schemaVersion: PREFERENCES_SCHEMA,
  rule: "rogue_to_king",
  caseStyle: "title",
  suffix: "agincourt",
  minLength: 4,
  maxLength: 24,
  candidateCount: 5,
  allowNumbers: true,
  allowUnderscore: true,
  reservedWords: [],
  forbiddenPrefixes: [],
  forbiddenSuffixes: [],
  seed: 1415,
  ambition: 65,
});

const clampInteger = (value, fallback, min, max) => {
  const parsed = Number(value);
  return Number.isInteger(parsed) ? Math.min(max, Math.max(min, parsed)) : fallback;
};

export function migratePreferences(input) {
  const source = input && typeof input === "object" ? input : {};
  const policy = normalizeUsernamePolicy({ ...DEFAULT_PREFERENCES, ...source });
  return {
    schemaVersion: PREFERENCES_SCHEMA,
    rule: policy.rule,
    caseStyle: policy.caseStyle,
    suffix: policy.suffix,
    minLength: policy.minLength,
    maxLength: policy.maxLength,
    candidateCount: policy.candidateCount,
    allowNumbers: policy.allowNumbers,
    allowUnderscore: policy.allowUnderscore,
    reservedWords: policy.reservedWords,
    forbiddenPrefixes: policy.forbiddenPrefixes,
    forbiddenSuffixes: policy.forbiddenSuffixes,
    seed: clampInteger(source.seed, DEFAULT_PREFERENCES.seed, 0, 0xffffffff),
    ambition: clampInteger(source.ambition, DEFAULT_PREFERENCES.ambition, 0, 100),
  };
}

export async function loadPreferences(storage) {
  const stored = await storage.local.get(PREFERENCES_KEY);
  return migratePreferences(stored?.[PREFERENCES_KEY]);
}

export async function savePreferences(storage, preferences) {
  const normalized = migratePreferences(preferences);
  await storage.local.set({ [PREFERENCES_KEY]: normalized });
  return normalized;
}

export function toEngineOptions(preferences) {
  const normalized = migratePreferences(preferences);
  return {
    seed: normalized.seed,
    rule: normalized.rule,
    style: normalized.caseStyle,
    suffix: normalized.suffix,
    ambition: normalized.ambition,
  };
}

export function fromEngineSeed(preferences, seed) {
  return migratePreferences({ ...preferences, seed });
}
