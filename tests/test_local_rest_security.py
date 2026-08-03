from __future__ import annotations

import json
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    REPOSITORY_ROOT
    / "plugins"
    / "obsidian-manuscript-publisher"
    / "skills"
    / "obsidian-manuscript-publisher"
    / "scripts"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import save_via_obsidian_rest as rest


# A certificate-SHAPED placeholder, used only for the "certificate is required" checks.
# It is deliberately NOT parsable, so it must never be handed to ssl.create_default_context.
TEST_CERTIFICATE = """-----BEGIN CERTIFICATE-----
MIIBtest-only-certificate-value
-----END CERTIFICATE-----
"""


def build_self_signed_ca_pem() -> str | None:
    """Generate a throwaway self-signed CA certificate for CN=127.0.0.1.

    Returns the public PEM, or None when the platform cannot produce one. The private key is
    never exported, so nothing secret is created. This exists because certificate pinning cannot
    be verified with a fake value: ssl.create_default_context rejects unparsable cadata, which
    would force the test to mock the exact call under test.
    """
    script = r"""
Add-Type -AssemblyName System.Security
$rsa = [System.Security.Cryptography.RSA]::Create(2048)
try {
    $name = New-Object System.Security.Cryptography.X509Certificates.X500DistinguishedName("CN=127.0.0.1")
    $request = New-Object System.Security.Cryptography.X509Certificates.CertificateRequest(
        $name, $rsa,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1)
    $request.CertificateExtensions.Add(
        (New-Object System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($true, $false, 0, $true)))
    $cert = $request.CreateSelfSigned(
        [DateTimeOffset]::new([DateTime]::new(2020, 1, 1, 0, 0, 0, [DateTimeKind]::Utc)),
        [DateTimeOffset]::new([DateTime]::new(2050, 1, 1, 0, 0, 0, [DateTimeKind]::Utc)))
    $der = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
    $b64 = [Convert]::ToBase64String($der, [Base64FormattingOptions]::InsertLineBreaks)
    Write-Output "-----BEGIN CERTIFICATE-----"
    Write-Output $b64
    Write-Output "-----END CERTIFICATE-----"
}
finally { $rsa.Dispose() }
"""
    with tempfile.TemporaryDirectory() as scratch:
        script_path = Path(scratch) / "make-cert.ps1"
        script_path.write_text(script, encoding="utf-8")
        try:
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
    if completed.returncode != 0 or "BEGIN CERTIFICATE" not in completed.stdout:
        return None
    return completed.stdout.replace("\r\n", "\n")


class LocalRestSecurityTests(unittest.TestCase):
    def test_rejects_plain_http_even_on_loopback(self):
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            rest._local_base_url("http://127.0.0.1:27123")

    def test_rejects_redirects_before_authorization_can_leave_loopback(self):
        handler = rest._NoRedirectHandler()
        with self.assertRaises(urllib.error.HTTPError) as raised:
            handler.redirect_request(
                request=None,
                file_pointer=None,
                status=302,
                message="Found",
                headers={},
                new_url="https://example.invalid/collect",
            )
        self.assertEqual(raised.exception.code, 302)

    def test_connection_requires_the_local_public_certificate(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "data.json"
            config.write_text(
                json.dumps({"apiKey": "test-only", "port": 27124}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "certificate"):
                rest._connection(config)

    def test_connection_pins_only_the_local_certificate_without_mocking_ssl(self):
        """Run the real pinning path: no mock of ssl.create_default_context.

        Asserting verify_mode/check_hostname alone proves nothing, because both are stdlib
        defaults. The load-bearing property is that the trust store contains ONLY the plugin's own
        certificate, so the public CA roots cannot vouch for the endpoint.
        """
        pem = build_self_signed_ca_pem()
        if pem is None:
            raise unittest.SkipTest("cannot generate a self-signed certificate on this platform")

        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "data.json"
            config.write_text(
                json.dumps({"apiKey": "test-only", "port": 27124, "crypto": {"cert": pem}}),
                encoding="utf-8",
            )

            _, base_url, context = rest._connection(config)

        self.assertEqual(base_url, "https://127.0.0.1:27124")
        pinned = context.get_ca_certs()
        self.assertEqual(len(pinned), 1, "exactly the plugin certificate must be trusted")
        self.assertEqual(pinned[0]["subject"], ((("commonName", "127.0.0.1"),),))
        # The public trust store is materially larger, so this proves system roots were not loaded.
        self.assertLess(len(pinned), len(ssl.create_default_context().get_ca_certs()))
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_connection_rejects_a_malformed_certificate(self):
        """Covers the invalid-certificate branch, which the mocked test could never reach."""
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / "data.json"
            config.write_text(
                json.dumps(
                    {"apiKey": "test-only", "port": 27124, "crypto": {"cert": TEST_CERTIFICATE}}
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "certificate is invalid"):
                rest._connection(config)


if __name__ == "__main__":
    unittest.main()
