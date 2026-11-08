# Reviewer notes — Nickspeare v0.1.0-alpha.2

## Test environment

- No account, login, license key, or payment is required.
- Public review fixture: https://styayur.github.io/Nickspeare/fixtures/edge-review.html
- Privacy policy: https://styayur.github.io/Nickspeare/privacy-policy.html
- Source: https://github.com/styayur/Nickspeare

## Install

1. Extract `nickspeare-extension-chromium-v0.1.0-alpha.2.zip`.
2. Open `edge://extensions`.
3. Enable **Developer mode**.
4. Choose **Load unpacked** and select the extracted folder containing `manifest.json`.
5. Open the Nickspeare toolbar popup.

## Basic generation test

1. Enter a seed such as `1415`.
2. Select **Forge names**.
3. Confirm that four to six candidates appear.
4. Expand a candidate's details and confirm that a formation explanation and source-linked evidence appear.
5. Copy a candidate and paste it into a text editor to verify clipboard behavior.
6. Disable network access or go offline and repeat generation; the popup should continue to work.

## Advanced controls

1. Open **Advanced controls**.
2. Change the rule, case, suffix, candidate count, minimum/maximum length, reserved words, or forbidden affixes.
3. Select **Forge names**.
4. Confirm that invalid candidates are regenerated rather than truncated.

## Controlled page insertion test

1. Open the public review fixture in a normal HTTP or HTTPS tab.
2. Open the Nickspeare popup and choose a generated candidate.
3. Select **Use on page**.
4. Choose the registration username field.
5. Confirm the selected empty field receives the candidate.
6. Choose the login username field, which contains existing text, and confirm that replacement requires an explicit action.
7. Confirm that the email and password fields are excluded from the field chooser.
8. Confirm that no form is submitted.
9. Choose the display-name field and confirm that the visible value changes without a remote request.

## Permissions and privacy checks

- The production manifest should contain only `activeTab`, `scripting`, and `storage`.
- No host permissions or optional host permissions should be present.
- Generation should use bundled assets and should not issue network requests.
- Preferences should persist after closing and reopening the popup.
- Removing the extension should remove its local storage.

## Expected limitations

- No remote username-availability check.
- No automatic form submission.
- No iframe or closed shadow-root scanning.
- No Firefox support in this series.

