# Browser extension v0.1.0-alpha.2

Nickspeare for Chromium and Microsoft Edge is a Manifest V3 popup that composes usernames from the bundled evidence atlas. It is an independent pre-release from the Python package and the GitHub Pages app.

## Install

Download `nickspeare-extension-chromium-v0.1.0-alpha.2.zip` from the GitHub pre-release, extract it, open `chrome://extensions` or `edge://extensions`, enable Developer mode, and load the extracted folder as an unpacked extension. `manifest.json` must be at the folder root.

To build locally:

```sh
npm ci
npm run build:extension
```

Load `dist/extension`. The production directory is assembled from `extension/` plus the shared JavaScript core in `packages/core/` and `docs/atlas.json`.

## Permissions and privacy

The release manifest requests only:

| Permission | Use |
|---|---|
| `storage` | Save versioned local preferences such as rule, length and default case. |
| `activeTab` | Temporarily access the active page after the user clicks the extension. |
| `scripting` | Inject the on-demand field bridge into that active page. |

There are no permanent or optional host permissions in v0.1. The extension does not declare content scripts that run automatically. Page access is requested by an explicit **Use on page** action after opening the popup. The full public policy is at [Nickspeare Browser Extension Privacy Policy](https://styayur.github.io/Nickspeare/privacy-policy.html).

Generated names, selected candidates and page field descriptors remain in memory. Preferences are the only persisted data. The extension has no account, telemetry, analytics, advertising, remote generation API or cloud sync. It does not read or transmit passwords, OTPs, payment data, cookies, tokens, account data or browsing history.

## Generation

The popup imports the shared browser engine and applies an independent username policy:

- four existing composition rules;
- minimum and maximum length;
- title, lower or upper case;
- digit and underscore policy;
- reserved words, forbidden prefixes and forbidden suffixes;
- seed replay and duplicate removal.

Invalid candidates are rejected and regenerated. Names are never truncated merely to satisfy a constraint. Username availability is not checked against any website or remote service.

## Field bridge

The content script is injected only on demand into Chrome's isolated world. It scores editable text inputs using `autocomplete`, names, IDs, labels, accessibility text, form context, registration/login wording and visibility. Email, password, OTP, telephone, number, hidden and payment-like fields are excluded.

The user must choose a field in the popup. Non-empty fields display an explicit **Replace existing text** action; the message bridge also refuses writes unless `replaceExisting` is true. The bridge validates its own message sender and field ID, uses a native value setter, and dispatches bubbling `input` and `change` events without submitting the form. This preserves React controlled-input behavior in the acceptance fixture.

Fields inside iframes, closed shadow roots and browser-internal pages are not accessed. Those cases produce a visible, non-destructive explanation. In-page suggestion badges and persistent per-site authorization are deferred beyond v0.1.

## Verification

```sh
python -m pip install playwright
python -m playwright install chromium
npm ci
npm run test:extension
```

The test harness creates two builds:

- `dist/extension` — the production permission set;
- `dist/extension-test` — identical runtime plus `http://127.0.0.1/*` host access used only to drive local form fixtures.

The real-browser suite loads both builds, checks popup generation, clipboard, offline operation, local preference migration, field classification, sensitive-field exclusion, non-empty protection, explicit replacement, React state synchronization, no auto-submit, permission denial and restricted pages. On Windows the same suite can run against actual Edge with `--browser msedge`.

Release checks also run:

```sh
npm run test:coverage
npm run audit:extension
npm run package:extension
```

`artifacts/extension-acceptance.json` records the exact commit, test counts, core coverage, browser compatibility, security audit, licence gate, quality score and release readiness. The score is project-generated acceptance evidence, not third-party certification.

GitHub Actions are referenced by reviewed full commit SHAs. React fixtures, Python development tools and the CodeForge CLI are pinned; the production extension still has zero runtime npm dependencies. The tag release workflow waits for exact-commit build, browser, Python, CodeQL and CodeForge check evidence before it publishes the pre-release.

## Known limitations

- Chromium and Edge only; Firefox is not a v0.1 target.
- No iframe, closed shadow-root or cross-origin subframe scanning.
- No automatic field suggestions, keyboard interception or form submission.
- No availability check against account services.
- Google Chrome branded builds cannot be automated through the removed command-line unpacking flag; the same Manifest V3 runtime is verified in Chromium, and Chrome users load the ZIP through Developer mode.

## Licences

Extension code is AGPL-3.0-or-later. Folger-derived evidence remains subject to CC BY-NC 3.0 attribution and noncommercial restrictions. The ZIP includes `licenses/LICENSE` and `licenses/DATA_SOURCES.md`; the application licence does not relicense the corpus derivatives.

## 中文摘要

扩展仅使用 `activeTab`、`scripting` 和 `storage`，普通生成与复制完全本地运行。页面访问由用户点击扩展后按需触发；不访问 iframe，不读取或填写密码、邮箱、OTP、支付字段，不自动提交表单，也不检查用户名是否被网站占用。正式发布目标是 Chromium 与 Edge；Firefox、页内自动建议和商店提交不在 v0.1 范围内。代码采用 AGPL-3.0-or-later，Folger 衍生语料仍受 CC BY-NC 3.0 的非商业与署名条件约束。
