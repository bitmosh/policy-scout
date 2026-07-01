## What changed?

Brief description of the changes in this PR.

## Safety impact?

Does this change affect:
- Policy decisions (DENY/ALLOW/SANDBOX_FIRST)?
- Risk scoring?
- Classification behavior?
- Redaction or privacy handling?
- Audit/report/sandbox/sweep behavior?

If yes, explain the impact and why it's safe.

## Tests run?

- [ ] `python -m pytest` passed
- [ ] `python -m policy_scout.cli.main doctor --json` passed
- [ ] `python -m policy_scout.cli.main eval run` passed
- [ ] Relevant manual testing completed

## Docs updated if behavior changed?

If this changes user-facing behavior, were docs updated?
- [ ] README.md
- [ ] CHANGELOG.md
- [ ] Relevant design docs

## Any redaction/privacy impact?

Does this change:
- Add new redaction patterns?
- Modify existing redaction logic?
- Change what gets logged/audited?
- Change report content?

If yes, explain.

## Any sandbox/audit/report/policy decision changes?

Does this change:
- Sandbox behavior or migration logic?
- Audit event structure or storage?
- Report generation or content?
- Policy engine or risk scoring?

If yes, explain the impact.
