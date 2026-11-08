# Nickspeare Browser Extension v0.1.0-alpha.1

**Pre-release.** A lightweight, offline-first Manifest V3 username composer for Chromium and Microsoft Edge.

## Highlights

- Generate 4–6 seeded Shakespearean usernames locally in a compact popup.
- Apply length, case, digit, underscore, reserved-word and prefix/suffix constraints.
- Copy any candidate or explicitly choose a username field on the active page.
- Classify registration usernames, login usernames, display nicknames and other text fields.
- Protect non-empty fields, exclude password/email/OTP/payment-like inputs, dispatch native input events for controlled components and never submit a form.
- Reuse the existing source-linked browser engine and evidence atlas, with formation reasons available in each candidate’s details.
- Store only versioned preferences in `chrome.storage.local`; there is no account, analytics, telemetry or remote generation API.

## Install

1. Download and extract `nickspeare-extension-chromium-v0.1.0-alpha.1.zip`.
2. Open `chrome://extensions` in Chrome/Chromium or `edge://extensions` in Edge.
3. Enable **Developer mode** and choose **Load unpacked**.
4. Select the extracted folder containing `manifest.json` at its root.

The extension works without a page username field for generation and copying. Page insertion is available only after user interaction and a field selection. Firefox and store distribution are not part of this pre-release.

## Browser acceptance

- Chromium {{CHROMIUM_VERSION}}: **PASS** (real MV3 load, popup, offline generation, clipboard, field bridge and React controlled input).
- Microsoft Edge {{EDGE_VERSION}}: **PASS** (same acceptance suite).
- Google Chrome branded build: **NOT_RUN** for automated CLI loading because branded Chrome blocks the unpacked-extension command-line flag; developers and users can still load the ZIP through Developer mode.
- Firefox: **NOT_APPLICABLE** for v0.1.0-alpha.1.

## Permissions and privacy

| Permission | Purpose |
|---|---|
| `activeTab` | Temporary access to the active page only after the toolbar action is used. |
| `scripting` | Inject the on-demand field bridge when the user chooses **Use on page**. |
| `storage` | Save local generation preferences. |

There are no permanent or optional host permissions. The extension does not collect page content, account information, cookies, tokens, passwords or browsing history, and it does not send form data to any server. Fields inside iframes and closed shadow roots are not accessed. Username availability is not checked.

## Known limitations

- Chromium and Edge only; Firefox retention remains future work.
- No automatic in-page suggestion badges or persistent per-site permission grants.
- No iframe, closed shadow-root or cross-origin subframe scanning.
- No remote availability check and no form submission.
- Alpha software: preferences are local and the generated-name policy remains heuristic.

## Privacy and data rights

The extension processes generation locally. Preferences stay in `chrome.storage.local`; page field metadata is read only after user action and is not sent to a server. Read the full [Privacy Policy](https://styayur.github.io/Nickspeare/privacy-policy.html).

## Licences and data rights

Extension code is **AGPL-3.0-or-later**. Folger-derived evidence remains subject to **CC BY-NC 3.0** attribution and noncommercial conditions; the code licence does not relicense the corpus derivatives. The ZIP includes `licenses/LICENSE`, `licenses/DATA_SOURCES.md` and `licenses/SECURITY.md`. This pre-release is not offered as an unrestricted commercial dataset or naming service.

## Verification

- Acceptance status: **{{ACCEPTANCE_STATUS}}**
- Project-generated quality score: **{{QUALITY_SCORE}} / 100** (not third-party certification)
- Source commit: `{{COMMIT}}`
- ZIP SHA-256: `{{ZIP_SHA256}}`
- Asset integrity: `SHA256SUMS`
- Machine-readable evidence: `extension-acceptance.json`

## Roadmap

Next work includes a reviewed corpus extension, clearer evidence views, optional user-authorized in-page suggestions and Firefox compatibility research.

## 中文摘要

Nickspeare 浏览器扩展 v0.1.0-alpha.1 是面向 Chromium 与 Microsoft Edge 的离线优先预发布版本。它可在本地生成带来源解释的用户名，支持长度、大小写、数字、下划线和保留词等规则，并可在用户明确选择字段后填入当前页面。扩展不会填写密码、邮箱、OTP 或支付类字段，不会覆盖非空文本（除非用户明确点击替换），也不会自动提交表单。

正式构建只申请 `activeTab`、`scripting` 和 `storage`，没有永久站点权限，不收集页面内容、账户信息或浏览历史，也不连接远程生成服务。Chrome/Chromium 与 Edge 已通过真实浏览器验收；Firefox、iframe、closed shadow root、页内自动建议和商店提交不在本版本范围内。代码采用 AGPL-3.0-or-later；Folger 衍生语料仍受 CC BY-NC 3.0 的署名与非商业限制约束。
