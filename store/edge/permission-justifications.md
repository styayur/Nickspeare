# Permission justifications

## activeTab

Used only after the user invokes the extension. It allows the popup to request the active page when the user chooses **Use on page**, so the extension can present editable username-like fields without permanent site access.

## scripting

Used to inject `content/username-detector.js` on demand into the user-selected active page. The script classifies editable fields, excludes sensitive fields, and fills only the field chosen by the user. It is not registered as an always-on content script.

## storage

Used to save versioned local preferences under `nickspeare.preferences.v1`. These preferences include generation controls, seed, length limits, reserved words, and allowed character rules. No personal data, page contents, browsing history, cookies, credentials, or account data are stored.

## No host permissions

The production package requests no `host_permissions` or `optional_host_permissions`. Access to the active page is limited to the activeTab grant created by the user's extension action.

## Remote code and data disclosure

The production package loads no remote JavaScript, WebAssembly, stylesheets, or executable content. Generation uses bundled files and the bundled evidence atlas. The extension has no remote generation API and does not send registration-form data or page contents to a server.
