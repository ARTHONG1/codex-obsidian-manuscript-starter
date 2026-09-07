# Security policy

## Supported release

Security fixes are tracked against the latest tagged release.

## Reporting

Do not post API keys, certificates, Vault contents, or private paths in a
public issue. Use a private GitHub security report when available, or contact
the repository maintainer through the project profile before disclosing
sensitive details.

The installer is designed for loopback HTTPS communication with Obsidian's
Local REST API. It does not request or store remote service credentials.
