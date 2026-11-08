# Microsoft Edge Add-ons publishing

This repository uses the [Microsoft Edge Add-ons Update REST API v1.1](https://learn.microsoft.com/en-us/microsoft-edge/extensions-chromium/publish/api/using-addons-api?tabs=v1-1) only for updates to a product that already exists in Partner Center.

## Preconditions

Before the automated path can run:

1. A maintainer completes the Microsoft Edge Add-ons program enrollment in Partner Center and accepts the Microsoft Edge App Developer Agreement.
2. An Nickspeare product exists in Partner Center and has a Product ID.
3. The first Nickspeare package and store listing have been submitted through Partner Center.
4. The Partner Center Publish API page has issued a Client ID and API key for this product.
5. The `edge-production` GitHub Environment exists and restricts deployment to trusted release tags.

The API cannot create a product or update store metadata such as descriptions and screenshots. Those changes remain Partner Center operations.

## GitHub configuration

Create the protected `edge-production` Environment and add:

| Kind | Name | Value |
| --- | --- | --- |
| Repository variable | `EDGE_PRODUCT_ID` | The Product ID GUID from Partner Center |
| Repository variable | `EDGE_CLIENT_ID` | The Publish API Client ID GUID |
| Environment secret | `EDGE_API_KEY` | The Publish API key |

Do not commit the API key. Prefer an Environment secret so the credential is unavailable to pull-request workflows.

The workflow is `.github/workflows/edge-publish.yml`. It runs after a successful `Release browser extension` workflow or by manual dispatch with an existing `extension-v*` tag.

## Release flow

1. The workflow checks out the immutable tag.
2. It downloads the release ZIP, `extension-acceptance.json`, and `SHA256SUMS`.
3. It verifies checksums, release readiness, commit, tag, ZIP hash, Chromium acceptance, Edge acceptance, manifest version, and the public privacy-policy URL.
4. It checks for prior `edge-store-acceptance.json` or `edge-publish-intent.json` assets. A release that already reached `SUBMITTED` is skipped.
5. It writes and uploads an intent asset **before** calling the store API. This prevents a rerun from blindly creating a duplicate submission if a prior run was interrupted.
6. It uploads the ZIP through the v1.1 draft-package endpoint and polls the upload operation.
7. It calls the publishing endpoint with the reviewer notes and polls the publishing operation.
8. It records operation IDs and the exact asset hash in `edge-store-acceptance.json`, then attaches that file and `edge-store-SHA256SUMS` to the existing GitHub Release.

The workflow does not create, delete, or replace the GitHub Release. It only adds new evidence assets and refuses to overwrite existing assets.

## HTTP contract

The client uses:

- API root: `https://api.addons.microsoftedge.microsoft.com`
- Upload: `POST /v1/products/{productID}/submissions/draft/package`
- Upload operation: `GET /v1/products/{productID}/submissions/draft/package/operations/{operationID}`
- Publish: `POST /v1/products/{productID}/submissions`
- Publish operation: `GET /v1/products/{productID}/submissions/operations/{operationID}`
- Headers: `Authorization: ApiKey ...` and `X-ClientID: ...`

Operation states are `InProgress`, `Succeeded`, and `Failed`. HTTP 408, 425, 429, and selected 5xx responses are retried with bounded backoff. Authentication and validation errors are not retried.

## Status semantics

`SUBMITTED` means Microsoft accepted the publishing operation. It does **not** mean review started, review passed, or the product is public.

Use these distinct states in evidence and reports:

- `SUBMITTED` - GitHub recorded a successful publish API operation.
- `IN_REVIEW` - Partner Center explicitly shows the submission in review.
- `REJECTED` - Partner Center explicitly reports rejection.
- `APPROVED` - Partner Center explicitly reports certification approval.
- `PUBLISHED` - the public Edge Add-ons listing URL is actually accessible.

The Update API reports operation progress, not a documented certification or public-listing endpoint. Review and publication status must be verified in Partner Center or the public store page.

## Failure recovery

- **Transient API error:** rerun the workflow. The existing intent asset makes the rerun fail closed, so first query Partner Center.
- **Intent exists, no acceptance asset:** determine in Partner Center whether a submission was created. Do not rerun blindly. Resolve the submission state, then remove or replace the stale intent only through reviewed maintainer action.
- **Submission rejected:** fix the actual package or listing issue, create a new immutable release version, and submit again. Do not mutate an old tag or reuse a rejected version silently.
- **Product metadata changes:** update the listing in Partner Center; the Update API only handles package updates.

## Security invariants

- No bypass actors.
- No forged check runs or bypass of portfolio R3/R4 approval.
- No `--admin` merge or force push.
- No use of Partner Center cookies, browser password stores, or exported session tokens.
- No claim of `PUBLISHED` without an accessible official store listing.
