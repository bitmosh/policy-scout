# Contributing to Policy Scout

Policy Scout is an alpha-stage personal project. Contributions are welcome for
bug fixes, documentation improvements, and eval case additions.

## License

By submitting a pull request, you agree that your contribution will be
licensed under the [Apache License, Version 2.0][apache-2.0] — the same
license as this project.

You do not lose the rights to your contribution by submitting it; the
Apache-2.0 license grants the project (and downstream users) the same
rights as everyone else has to use, modify, and distribute your work.

## Developer Certificate of Origin (DCO)

All commits must be signed off, attesting to the [Developer Certificate of
Origin][dco]:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use `git commit -s` (or `git commit --signoff`) to add this line
automatically. This is a lightweight alternative to a full Contributor
License Agreement and serves the same provenance function.

If you forget to sign off, `git commit --amend --signoff` (or, for many
commits, `git rebase --signoff HEAD~N`) can fix it before pushing.

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
- Sign off your commits (`git commit -s`).
- The PR template describes the safety-impact checklist — fill it in honestly.

## Code of conduct

Be direct and constructive. Policy and safety semantics must not be weakened
without explicit justification.

## Author

Ryan Johnson ([@bitmosh](https://github.com/bitmosh))

[apache-2.0]: https://www.apache.org/licenses/LICENSE-2.0
[dco]: https://developercertificate.org/
