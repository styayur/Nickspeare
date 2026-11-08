import { DEFAULT_PREFERENCES, PREFERENCES_KEY } from "../core/preferences.js";

chrome.runtime.onInstalled.addListener(async () => {
  const stored = await chrome.storage.local.get(PREFERENCES_KEY);
  if (!stored[PREFERENCES_KEY]) {
    await chrome.storage.local.set({ [PREFERENCES_KEY]: DEFAULT_PREFERENCES });
  }
});
