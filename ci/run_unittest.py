import argparse
import json
import sys
import unittest
from pathlib import Path


def build_suite(root: Path, test_names: list[str]) -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    if test_names:
        suite = unittest.TestSuite()
        for name in test_names:
            suite.addTests(loader.loadTestsFromName(name))
        return suite
    return loader.discover(str(root / "tests"), pattern="test*.py")


class JsonTestResult(unittest.TextTestResult):
    def summary(self) -> dict[str, object]:
        tests_run = self.testsRun
        failures = len(self.failures)
        errors = len(self.errors)
        skipped = len(self.skipped)
        return {
            "testsRun": tests_run,
            "failures": failures,
            "errors": errors,
            "skipped": skipped,
            "successful": failures == 0 and errors == 0,
        }


class JsonTestRunner(unittest.TextTestRunner):
    resultclass = JsonTestResult


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--test-name", action="append", default=[])
    args = parser.parse_args()

    root = args.root.resolve()
    sys.path.insert(0, str(root))
    suite = build_suite(root, args.test_name)
    result = JsonTestRunner(stream=sys.stderr, verbosity=1).run(suite)
    print(json.dumps(result.summary(), sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
