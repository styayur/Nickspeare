# Nickspeare — Shakespearean Username Generator

**A local composing room for names with a little rogue and a little royalty.**

Nickspeare is an offline-first browser extension that invents Shakespearean-style usernames from a small, source-linked evidence atlas built from *Henry IV, Part 1*, *Henry IV, Part 2*, and *Henry V*. It is designed for people who want a distinctive username, character name, handle, or writing prompt without depending on a remote generation service.

The extension opens as a compact composing room. Choose a seed, forge four to six candidates, inspect why each name was formed, copy a candidate, or explicitly choose a username field on the active page. Generation remains local, and the extension requests only `activeTab`, `scripting`, and `storage`.

## What you can do

- Generate four to six seeded names at a time and reproduce a result by keeping the same seed and controls.
- Apply length limits, title/lower/uppercase styling, digit and underscore rules, reserved words, forbidden prefixes, and forbidden suffixes.
- Inspect formation reasons and source-linked ingredients for each candidate.
- Copy a candidate to the clipboard.
- Choose a username-like field on the current page and insert one generated candidate after reviewing the field description.
- Keep local preferences between popup sessions.

## How generation works

The bundled atlas records words from spoken dialogue, source locations, speaker groups, and attestations. Nickspeare combines those ingredients using several composition strategies: rogue-to-king blending, character-level Markov coinage, quote splicing, and archaic coinage. A local scoring pass ranks the results. The interface explains the selected formation and labels historical dates as literary context rather than claims about a username's real-world availability.

The extension does not claim that a generated name is historically attested as a person's name. It does not query websites, registries, social networks, or account systems to check whether a username is available. It does not register accounts automatically.

## Safe field insertion

Page insertion is deliberately user-driven. Open the popup, generate or choose a candidate, select **Use on page**, and choose from the visible field descriptions. Empty fields are filled by default. A non-empty field requires an explicit replacement action. Email, password, one-time-code, payment-like, hidden, and other sensitive fields are excluded. The extension dispatches normal input and change events for controlled components, but it never submits a form.

No permanent host permissions are requested. The extension does not run an always-on content script, does not collect browsing history, and does not read cookies or account credentials.

## Privacy

All generation assets are bundled. The production extension does not use a remote API, analytics, telemetry, advertising, account system, or cloud synchronization. Preferences stay in `chrome.storage.local`; removing the extension clears its local storage. See the public privacy policy for the complete data-flow description.

## Compatibility and limitations

Nickspeare is a Manifest V3 extension for Chromium-based browsers and Microsoft Edge. The release is tested in Chromium and Microsoft Edge. Firefox, automatic in-page suggestion badges, iframe scanning, closed shadow-root scanning, remote username availability checks, and automatic form submission are outside the v0.1.0-alpha series.

The project is experimental. Generated names are creative outputs, not legal clearances or brand-availability advice. Use discretion before adopting a name for a commercial product or public identity.

## Licences and attribution

Extension code is licensed under AGPL-3.0-or-later. Folger-derived corpus evidence remains subject to CC BY-NC 3.0 attribution and noncommercial conditions; the application licence does not relicense the corpus. See the repository's DATA_SOURCES.md and the licences included in the extension package.

## Support

- Source and documentation: https://github.com/styayur/Nickspeare
- Issues: https://github.com/styayur/Nickspeare/issues
- Privacy policy: https://styayur.github.io/Nickspeare/privacy-policy.html
- Security reports: https://github.com/styayur/Nickspeare/security/advisories/new
