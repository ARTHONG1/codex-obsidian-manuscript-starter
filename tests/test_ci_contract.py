import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "windows-ci.yml"
ACTION_LOCK = ROOT / "ci" / "action-lock.json"
RESOLVER = ROOT / "ci" / "resolve-action-lock.ps1"


def read_workflow():
    return WORKFLOW.read_text(encoding="utf-8")


def read_lock():
    return json.loads(ACTION_LOCK.read_text(encoding="utf-8"))


class CiContractTests(unittest.TestCase):
    def test_action_lock_records_reviewed_official_actions(self):
        lock = read_lock()
        expected = {
            "actions/checkout",
            "actions/setup-python",
            "actions/upload-artifact",
            "gitleaks/gitleaks-action",
        }
        self.assertEqual(set(lock), expected)
        for repository, entry in lock.items():
            self.assertEqual(entry["repository"], repository)
            self.assertRegex(entry["reviewed_ref"], r"[A-Za-z0-9._-]+")
            self.assertRegex(entry["sha"], r"[0-9a-f]{40}")

    def test_workflow_uses_only_locked_immutable_action_refs(self):
        workflow = read_workflow()
        lock = read_lock()
        uses_values = re.findall(r"(?m)^\s*uses:\s*([^\s#]+)", workflow)
        self.assertTrue(uses_values)
        self.assertTrue(all(
        re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}", value)
        for value in uses_values
        ))
        self.assertTrue(all(
        any(value == f"{repository}@{entry['sha']}" for repository, entry in lock.items())
        for value in uses_values
        ))

    def test_workflow_covers_required_windows_jobs_and_installer_matrix(self):
        workflow = read_workflow()
        for job in ("contracts:", "installer:", "python:", "pester:", "package:"):
            self.assertRegex(workflow, rf"(?m)^\s*{re.escape(job)}")
        for scenario in (
        "python311_selected",
        "python313_selected",
        "python_absent",
        "python312_ready",
        "restart_resume",
        "venv_reuse",
        ):
            self.assertIn(scenario, workflow)
        self.assertIn("windows-latest", workflow)

    def test_workflow_delegates_installer_matrix_to_scenario_runner(self):
        workflow = read_workflow()
        self.assertIn("ci\\run-installer-scenario.ps1", workflow)
        self.assertNotIn("install-windows.ps1 -RuntimeRoot", workflow)
        self.assertIn("-Scenario $env:INSTALLER_SCENARIO", workflow)

    def test_contracts_job_sets_up_python_and_installs_dev_requirements(self):
        workflow = read_workflow()
        contracts = workflow.split("  installer:", 1)[0]
        self.assertIn("actions/setup-python@", contracts)
        self.assertIn('python-version: "3.12"', contracts)
        self.assertIn("requirements-dev", contracts)
        self.assertIn('(Get-Command python).Source', contracts)
        self.assertNotIn("C:\\hostedtoolcache\\windows\\Python\\3.12.0\\x64\\python.exe", contracts)

    def test_workflow_invokes_required_contracts_and_release_checks(self):
        workflow = read_workflow()
        required_fragments = (
        "run-python-tests.ps1",
        "run-pester-tests.ps1",
        "TestRunnerContract.Tests.ps1",
        "InstallerContract.Tests.ps1",
        "PythonRuntimeContract.Tests.ps1",
        "SecretScan.Tests.ps1",
        "test_dependency_contract.py",
        "test_documentation_contract.py",
        "verify_skill_sync.py",
        "build-release.ps1",
        "verify-release.ps1",
        "gitleaks",
        "upload-artifact",
        )
        for fragment in required_fragments:
            self.assertIn(fragment, workflow)

    def test_workflow_runs_owned_aggregate_evidence_before_packaging(self):
        workflow = read_workflow()
        self.assertRegex(workflow, r"(?m)^\s*aggregate:")
        self.assertIn("run-all-tests.ps1", workflow)
        self.assertIn("needs: [contracts, installer, python, pester, aggregate]", workflow)
        self.assertIn("test-evidence.json", workflow)

    def test_skill_manifest_generator_excludes_generated_python_bytecode(self):
        generator = ROOT / "ci" / "generate-codex-skills-manifest.py"
        text = generator.read_text(encoding="utf-8")
        self.assertIn("__pycache__", text)
        self.assertIn(".pyc", text)

    def test_workflow_keeps_ci_state_in_temporary_roots(self):
        workflow = read_workflow()
        self.assertTrue("New-TemporaryFile" in workflow or "New-Item -ItemType Directory" in workflow)
        self.assertTrue("TestDrive" in workflow or "$env:TEMP" in workflow or "[IO.Path]::GetTempPath()" in workflow)
        forbidden = (
        "C:\\Users\\user",
        "C:\\Users\\runneradmin\\Desktop",
        "C:\\Users\\runneradmin\\Documents",
        ".codex\\skills",
        )
        for path in forbidden:
            self.assertNotIn(path.lower(), workflow.lower())

    def test_resolver_uses_github_api_refs_without_executing_response_content(self):
        resolver = RESOLVER.read_text(encoding="utf-8")
        self.assertIn("https://api.github.com/repos/", resolver)
        self.assertIn("git/ref/tags/", resolver)
        self.assertIn("gh api", resolver)
        self.assertTrue("git/ref/tags/$Ref^{}" in resolver or "deref" in resolver.lower())
        self.assertIn("ConvertFrom-Json", resolver)
        self.assertNotIn("Invoke-Expression", resolver)
        self.assertNotIn("Start-Process", resolver)
        self.assertRegex(resolver, r"\b40\b")

    def test_resolver_injected_api_uses_exact_tag_ref_url_and_dereferences_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            harness = Path(temp_dir) / "resolver-harness.ps1"
            output = Path(temp_dir) / "action-lock.json"
            seen_urls = Path(temp_dir) / "seen-urls.txt"
            harness.write_text(
                f"""
$global:SeenUrls = @()
function Invoke-MockGitHubApi {{
    param([string]$Url)
    $global:SeenUrls += $Url
    switch ($Url) {{
        "https://api.github.com/repos/actions/checkout/git/ref/tags/v4.2.2" {{
            return '{{"object":{{"type":"tag","sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"message":"$(Write-Output hacked)"}}'
        }}
        "https://api.github.com/repos/actions/checkout/git/tags/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" {{
            return '{{"object":{{"type":"commit","sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}},"message":"$(Write-Output hacked)"}}'
        }}
        default {{ throw "Unexpected URL: $Url" }}
    }}
}}
$mockApi = ${{function:Invoke-MockGitHubApi}}
& "{RESOLVER}" -OutputPath "{output}" -Allowlist @{{ "actions/checkout" = "v4.2.2" }} -ApiInvoker $mockApi
"$($global:SeenUrls -join [Environment]::NewLine)" | Set-Content -LiteralPath "{seen_urls}"
""",
                encoding="utf-8",
            )
            completed = subprocess.run(
                ["pwsh", "-NoProfile", "-File", str(harness)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["actions/checkout"]["sha"],
                "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            )
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["actions/checkout"]["reviewed_ref"],
                "v4.2.2",
            )
            self.assertEqual(
                seen_urls.read_text(encoding="utf-8").splitlines(),
                [
                    "https://api.github.com/repos/actions/checkout/git/ref/tags/v4.2.2",
                    "https://api.github.com/repos/actions/checkout/git/tags/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                ],
            )

    def test_dependency_lock_copies_record_the_same_gitleaks_identity(self):
        paths = (
        ROOT / "dependencies.lock.json",
        ROOT / "bootstrap" / "dependencies.lock.json",
        ROOT / "plugins" / "obsidian-manuscript-publisher" / "bootstrap" / "dependencies.lock.json",
        )
        locks = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        identities = [lock["ciTools"]["gitleaks"] for lock in locks]
        self.assertEqual(identities[0], identities[1])
        self.assertEqual(identities[1], identities[2])
        self.assertEqual(identities[0]["repository"], "gitleaks/gitleaks-action")
        self.assertRegex(identities[0]["sha"], r"[0-9a-f]{40}")


if __name__ == "__main__":
    unittest.main()
