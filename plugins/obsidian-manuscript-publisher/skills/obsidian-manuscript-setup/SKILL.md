---
name: obsidian-manuscript-setup
description: Use when a beginner has Codex but has not yet installed or connected Obsidian for the Obsidian Manuscript Publisher workflow.
---

# Obsidian Manuscript Setup

Set up the Windows 10/11 Obsidian Manuscript Publisher environment for a user who already has Codex. This skill owns first-time installation, connection testing, and recovery guidance. It does not publish conversations or manuscripts.

## Safety Gate

Before any write or installation action, state these three facts and request confirmation in one short question:

1. The setup creates a new empty Vault by default and refuses to overwrite a non-empty folder.
2. It installs the pinned `obsidian-local-rest-api` community plugin from the release hashes bundled with this plugin. The API listens only on `https://127.0.0.1`; never enable its non-encrypted HTTP server or expose it to a network.
3. The plugin generates an API key inside the user's Vault. Never print, copy into a command, log, Git repository, or manuscript, and never send it to an external service.

Proceed only after the user explicitly approves this Local REST community-plugin installation.

## First-time Setup

1. Locate this plugin's own `bootstrap\\install-windows.ps1`. Do not download or execute an unpinned script from a URL.
2. Run it with `-InstallObsidian -EnableCommunityPlugin -LaunchObsidian` and, only if the user chose an existing empty folder, `-AllowExistingEmptyVault`. Pass a user-selected `-VaultPath` only after repeating the exact path for confirmation.
3. If Obsidian installation reports a restart requirement, ask the user to reopen Codex and resume at the same step. Do not create a Vault before the installer has both the explicit community-plugin consent and a usable Obsidian installation path.
4. When Obsidian opens, run this plugin's `bootstrap\\doctor.ps1`. It must pass a create-read-delete test of a temporary `_system` note through the local REST API. The doctor result must be `ready` before using `obsidian-manuscript-publisher`.

## Recovery Rules

- If the doctor cannot connect, keep Obsidian open, verify that the Local REST API plugin remains enabled, and rerun the doctor. Do not fall back to direct Vault filesystem writes.
- If the target Vault is not empty or the Local REST plugin folder already exists, stop. Explain that setup intentionally refuses overwrites and ask the user to choose a new empty folder or preserve their existing configuration.
- If a checksum fails, stop without enabling the plugin. Never bypass the mismatch or substitute an unpinned download.
- To disconnect the starter without deleting notes, use `bootstrap\\uninstall.ps1 -RemoveRuntimeConfig`. It intentionally leaves the Vault and Obsidian plugin untouched.

## Completion Response

Report only the Vault path, the installed plugin version, the doctor status, and the next prompt the user can use: `이 프로젝트를 원고 프로젝트로 등록해줘`.
