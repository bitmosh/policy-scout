# Contributing to Policy Scout

Policy Scout is an alpha-stage personal project. Contributions are welcome for
bug fixes, documentation improvements, and eval case additions.

## Reporting bugs

Open a GitHub issue using the bug report template. Include:

- The command or invocation that triggered the problem.
- The output you saw versus what you expected.
- Python version (`python --version`) and OS.
- Output of `policy-scout doctor --json` if relevant.

Do not include personal file paths, secret values, or credential material in
issue reports.

## Reporting security issues

Do not open a public issue for security-relevant findings. Use the GitHub
private Security Advisory path described in [SECURITY.md](SECURITY.md).

## Pull requests

- Keep PRs small and focused on a single concern.
- Add or update tests for changed behavior. Run `python -m pytest` before
  submitting.
- Update CHANGELOG.md and any affected documentation.
- The PR template describes the safety-impact checklist — fill it in honestly.

## Code of conduct

Be direct and constructive. Policy and safety semantics must not be weakened
without explicit justification.

## Author

Ryan Johnson ([@bitmosh](https://github.com/bitmosh))
