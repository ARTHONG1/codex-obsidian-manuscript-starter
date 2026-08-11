# Remediation continuity record

## Counting rule

**Counted records** are structural counts or audit inventory counts, such as the number of audit findings or the number of test definitions. They do not claim that those items were executed.

**Executed records** are commands and tests actually run during remediation, with their observed result recorded beside them. Only executed records may be used as evidence that a check passed.

For example, a report may say that an audit counted 10 P1 findings while this remediation executed the focused tests for only the findings in the selected wave. Those are separate facts and must not be merged into one completion claim.

## This documentation pass

- Executed focused documentation contract: 5 tests, 5 passed.
- Executed full Python suite after all remediation waves: 203 tests, 202 passed, 0 failed, 1 skipped.
- Executed InstallerContract: 44 passed, 0 failed. Executed SecretScan: 3 passed, 0 failed.
- Executed Wave 5 exporter checks: locking, incomplete marker, binary readback/MIME, and empty-assets cases passed.
- The dependency-missing path was separately executed and returned deterministic `python_dependency_missing` JSON without a traceback.
