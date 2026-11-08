# Nickspeare Browser Extension Privacy Policy

**Effective date:** 8 November 2026  
**Public URL:** https://styayur.github.io/Nickspeare/privacy-policy.html

## Scope

This policy applies to the Manifest V3 Nickspeare browser extension for Chromium and Microsoft Edge. It does not describe the separate Python package or the GitHub Pages composing room except where they share source data.

## Local processing

Nickspeare generates invented Shakespearean-style usernames from a bundled evidence atlas. Generation happens locally in the extension. After the user explicitly invokes the popup and chooses **Use on page**, the extension can classify editable fields on the active page and can insert a selected generated name into a field the user explicitly chooses.

## Data handled locally

- **Preferences:** generation rule, letter case, suffix, candidate count, length limits, reserved words, forbidden prefixes or suffixes, and seed are stored in `chrome.storage.local` under `nickspeare.preferences.v1`.
- **Temporary field descriptors:** limited metadata such as field type, labels, accessible names, autocomplete hints, visibility, form context and whether a field is empty is read only for the requested page-field chooser and kept in memory.
- **Generated names:** candidates remain in the popup until replaced or closed; no remote or cloud history is created.

## Data not collected

The extension does not collect, store or transmit passwords, one-time codes, payment-card data, cookies, authentication tokens, browsing history, account credentials, personal contact details or registration-form contents. Email, password, OTP, payment-like, hidden and similarly sensitive fields are excluded from insertion.

## Network and remote code

The production extension does not contact a Nickspeare server or a third-party generation service. It does not load remotely hosted JavaScript, WebAssembly, stylesheets or executable code. All runtime assets are bundled. The extension works offline after installation.

## Permissions

- `activeTab`: temporary access to the active page after the user invokes the extension.
- `scripting`: injects the on-demand field bridge after the user selects page insertion.
- `storage`: saves local versioned preferences.

There are no permanent or optional host permissions. No always-on content script is declared.

## Retention and deletion

Preferences remain in the browser profile until the extension is removed or the profile is deleted. To clear them, open `edge://extensions` or `chrome://extensions`, remove Nickspeare, and reinstall if desired. Generated names and temporary field descriptors are not retained after the popup closes.

## Sharing and sale

Nickspeare does not sell, rent, share or transmit personal data. There is no analytics, telemetry, advertising, account system, cloud sync or developer-operated backend.

## Children

The extension is a general-purpose writing aid and is not directed at children. It does not knowingly collect personal information from anyone.

## Licensing and source evidence

Extension code is AGPL-3.0-or-later. Folger-derived corpus evidence retains CC BY-NC 3.0 attribution and noncommercial conditions. Free distribution does not relicense the corpus or grant unrestricted commercial rights. See [DATA_SOURCES.md](https://github.com/styayur/Nickspeare/blob/main/DATA_SOURCES.md).

## Contact

- Public questions and non-sensitive bug reports: https://github.com/styayur/Nickspeare/issues
- Security or privacy reports: https://github.com/styayur/Nickspeare/security/advisories/new

## Changes

Material changes will be published on the public page and in the repository before the corresponding extension release.
