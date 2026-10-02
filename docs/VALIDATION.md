# Validation

The public edition is a new standalone snapshot with no inherited Git history. Tests use synthetic data and local temporary workspaces. No live model APIs, company services, credentials or external writes were tested.

Run `python scripts/check.py` (or `test.bat` after offline installation). It checks syntax, core lifecycle and real Tk widgets. Consent responses in UI tests are synthetic; physical human interaction, accessibility, other DPI/screens and other operating systems require separate validation. Results are recorded in ignored `artifacts/check.json`.

**Measured clean-environment result:** 14/14 core and 6/6 real Tk UI tests passed, with 0 failures, errors or skips. Offline BAT installation passed using Python 3.10.4 x64. The native --temporary module launch, close and workspace cleanup passed; the app window was visually inspected after a footer-layout issue was corrected. See [validation.json](validation.json). Do not count `--core-only` as a complete UI test. This edition does not use clipboard export, so it neither fixes nor inherits a clipboard-test success claim from another application.
