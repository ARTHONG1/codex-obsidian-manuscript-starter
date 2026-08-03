#!/usr/bin/env python3
"""Save and verify a Markdown card through the local Obsidian REST plugin."""

from __future__ import annotations

import argparse
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath


TEXT_CONTENT_TYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".json": "text/plain; charset=utf-8",
    ".csv": "text/plain; charset=utf-8",
}


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects so the Bearer token never leaves the loopback origin."""

    def redirect_request(self, request, file_pointer, status, message, headers, new_url):
        raise urllib.error.HTTPError(new_url, status, "Local REST redirects are forbidden", headers, file_pointer)


def _relative_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("vault_relative_path must stay inside the vault")
    return path.as_posix()


def _local_base_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("Obsidian REST endpoint has an invalid port") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != "127.0.0.1"
        or parsed.username
        or parsed.password
        or port is None
        or not 1 <= port <= 65535
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Obsidian REST endpoint must be an HTTPS 127.0.0.1 origin")
    return f"https://127.0.0.1:{port}"


def _content_type(vault_relative_path: str) -> str:
    """Use the plugin's text parser only for known text artifacts."""
    return TEXT_CONTENT_TYPES.get(PurePosixPath(vault_relative_path).suffix.lower(), "application/octet-stream")


def _request(url: str, token: str, method: str, body: bytes | None = None, content_type: str | None = None, context=None) -> bytes:
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = content_type or "application/octet-stream"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    handlers: list[object] = [_NoRedirectHandler()]
    if context is not None:
        handlers.insert(0, urllib.request.HTTPSHandler(context=context))
    opener = urllib.request.build_opener(*handlers)
    with opener.open(request, timeout=10) as response:
        return response.read()


def _connection(config_path: Path, base_url: str | None = None) -> tuple[str, str, object | None]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    token = config.get("apiKey")
    if not token:
        raise ValueError("Obsidian Local REST API key is unavailable")
    certificate = config.get("crypto", {}).get("cert") if isinstance(config.get("crypto"), dict) else None
    if not certificate or not str(certificate).strip():
        raise ValueError("Obsidian Local REST public certificate is unavailable")
    url_base = _local_base_url(base_url or f"https://127.0.0.1:{config.get('port', 27124)}")
    try:
        context = ssl.create_default_context(cadata=str(certificate))
    except ssl.SSLError as error:
        raise ValueError("Obsidian Local REST public certificate is invalid") from error
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return token, url_base, context


def _vault_endpoint(url_base: str, vault_relative_path: str, *, directory: bool = False) -> str:
    relative_path = _relative_path(vault_relative_path)
    endpoint = f"{url_base}/vault/{urllib.parse.quote(relative_path, safe='/')}"
    return endpoint + "/" if directory else endpoint


def read_vault_file(config_path: Path, vault_relative_path: str, base_url: str | None = None) -> bytes | None:
    token, url_base, context = _connection(config_path, base_url)
    endpoint = _vault_endpoint(url_base, vault_relative_path)
    try:
        return _request(endpoint, token, "GET", context=context)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def list_vault_directory(config_path: Path, vault_relative_directory: str, base_url: str | None = None) -> list[str] | None:
    token, url_base, context = _connection(config_path, base_url)
    endpoint = _vault_endpoint(url_base, vault_relative_directory, directory=True)
    try:
        payload = _request(endpoint, token, "GET", context=context)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise
    parsed = json.loads(payload.decode("utf-8"))
    files = parsed.get("files")
    if not isinstance(files, list) or any(not isinstance(item, str) for item in files):
        raise RuntimeError("Obsidian directory listing has an invalid response")
    return files


def delete_and_verify(config_path: Path, vault_relative_path: str, base_url: str | None = None) -> str:
    token, url_base, context = _connection(config_path, base_url)
    relative_path = _relative_path(vault_relative_path)
    endpoint = _vault_endpoint(url_base, relative_path)
    try:
        _request(endpoint, token, "DELETE", context=context)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    if read_vault_file(config_path, relative_path, base_url) is not None:
        raise RuntimeError("deleted vault path is still readable")
    return relative_path


def save_and_verify(config_path: Path, vault_relative_path: str, content: bytes, base_url: str | None = None) -> str:
    token, url_base, context = _connection(config_path, base_url)
    relative_path = _relative_path(vault_relative_path)
    endpoint = _vault_endpoint(url_base, relative_path)
    _request(endpoint, token, "PUT", content, _content_type(relative_path), context)
    if _request(endpoint, token, "GET", context=context) != content:
        raise RuntimeError("Obsidian did not return the content that was saved")
    return relative_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--vault-relative-path", required=True)
    parser.add_argument("--content-file", required=True)
    parser.add_argument("--base-url")
    arguments = parser.parse_args()
    content_path = Path(arguments.content_file)
    if not content_path.is_file():
        parser.error("--content-file must be an existing file")
    relative_path = save_and_verify(
        Path(arguments.config),
        arguments.vault_relative_path,
        content_path.read_bytes(),
        arguments.base_url,
    )
    print(json.dumps({"status": "saved", "vault_relative_path": relative_path}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
