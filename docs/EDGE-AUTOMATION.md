# Microsoft Edge Add-ons publishing — CANCELLED

Cancelled on 2026-11-09 at the owner’s request. The GitHub Actions workflow
`edge-publish.yml` was disabled and its definition removed. Neither successful
extension releases nor manual dispatch can invoke store submission. The
`edge-production` Environment was removed after confirming it contained no
Secrets or Variables; repository-level Edge credentials were also absent.

The CLI in `scripts/edge_publish.py` exits with code 2 before reading credentials
or contacting Microsoft. Its historical evidence helpers remain for audit
compatibility; the production network transport always refuses requests.

Browser extension development, Manifest V3, Chromium/Edge compatibility testing,
package creation and GitHub Release distribution continue. Existing tags,
Releases, ZIPs, hashes and acceptance evidence must be preserved.

Historical design is available in PR #33 and Git history. Do not reinstate its
setup instructions or triggers as part of ordinary CI or extension releases.

The only observed publishing run, 42497318254, failed during release-evidence
download; upload and submission steps were skipped. This is not proof of any
Partner Center status. Cancellation does not withdraw a previously submitted
application and makes no claim about Microsoft approval, rejection or publication.
