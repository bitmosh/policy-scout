# Commit and Bump Gate

This document describes the workflow for committing code to the Policy Scout repository and bumping the dev-log (blog) as a single reviewed release unit.

## Operating Principle

**blog.bumper is loosely coupled.** A bump failure should not block the code repo. The approval gate coordinates code push and dev-log bump as one reviewed release unit.

## Workflow

### 1. Work Locally

Make your changes to the codebase. Follow the existing project structure and conventions.

### 2. Run Validation

Before committing, run the full validation suite:

```bash
# Health diagnostics
python -m policy_scout.cli.main doctor --json

# Evaluation suite
python -m policy_scout.cli.main eval run

# Full test suite
python -m pytest
```

All three must pass before proceeding.

### 3. Commit Code

Commit your changes with a clear, descriptive commit message:

```bash
git add <files>
git commit -m "<descriptive message>"
```

### 4. Generate Bumper Dry-Run Preview

Generate a preview of the dev-log post that will be created:

```bash
bumper bump --dry
```

This will show the rendered post content without actually publishing it.

### 5. Review Together

Review the code commit and the rendered post together as one unit:

- The code commit shows what changed in the repository
- The bumper dry-run shows what will be published to the dev-log

Ensure both are accurate and consistent before proceeding.

### 6. Approve Once

When both the code and the post are correct, approve the release unit:

- If the code needs changes: amend the commit and re-dry-run
- If the post wording is wrong: fix the structured report/source and re-dry-run
- **Do not hand-edit generated MDX.** Fix the source data instead.

### 7. Push Code and Run Live Bump

Once approved:

```bash
# Push the code commit
git push

# Run the live bump to publish the dev-log post
bumper bump
```

The bumper will publish the post to the dev-log based on the commit that was just pushed.

## Important Notes

### Fixing Post Wording

If the dev-log post wording is incorrect:

1. Fix the structured report/source data (e.g., CHANGELOG.md, report generation logic)
2. Re-run `bumper bump --dry` to see the updated preview
3. Review again
4. If correct, push and run live bump

**Do not hand-edit the generated MDX.** The bumper generates posts from structured sources; editing the output directly creates a mismatch between code and documentation.

### Bump Failure Handling

If the bumper fails after the code is pushed:

- The code commit is still valid and merged
- The dev-log post is not published
- Fix the bumper issue (data format, configuration, etc.)
- Re-run `bumper bump` to publish the post

A bump failure does not block the code repo. The code and dev-log are loosely coupled.

### PR Template

When opening a pull request, use the PR template (`.github/pull_request_template.md`) to document:

- What changed
- Safety impact
- Tests run
- Docs updated
- Redaction/privacy impact
- Sandbox/audit/report/policy decision changes
- Whether a blog bump is needed

This ensures all safety and documentation considerations are reviewed before merge.

## Project Classifier

For Policy Scout, the `Project:` field in PASS COMPLETE messages should be:

```
Project: policy-scout
```

This ensures blog.bumper correctly routes the post to the Policy Scout project configuration in the registry (`~/.bumper/projects.toml`). The bumper registry is already configured with the correct project name, path, and remote for Policy Scout.
