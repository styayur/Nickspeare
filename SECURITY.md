# Security Policy

## Supported version

Security fixes target the current `main` branch and the latest release.

## Report privately

Do not report exploitable issues in a public issue. Use GitHub private vulnerability reporting:

https://github.com/styayur/Nickspeare/security/advisories/new

Include the affected version, Python/browser environment, reproduction command, impact, and any proof-of-concept details needed to verify the report. Sanitize local paths and private data.

## Scope

Relevant issues include unsafe handling of custom corpus paths, XML/JSON parsing, browser URL/state handling, package-data substitution, dependency compromise, and accidental disclosure of source files or local paths.

Nickspeare has no runtime service, account system, analytics, or generation API. Corpus rights are separate from the AGPL application license; see [DATA_SOURCES.md](DATA_SOURCES.md).
