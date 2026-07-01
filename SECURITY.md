# Security Policy

## Scope

Policy Scout is an alpha-stage local CLI tool. The security boundaries it enforces and the known limitations of those boundaries are documented in [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md). Read that document before relying on this tool for a sensitive workflow.

## Reporting a vulnerability

If you find a security issue — bypass path, redaction failure, approval escalation, injection vector — please open a **private** GitHub Security Advisory rather than a public issue:

> GitHub repo → **Security** tab → **Report a vulnerability**

Include a description of the issue, the affected code path, and steps to reproduce if possible. There is no formal SLA for this project, but reports will be reviewed and acknowledged promptly.

Do not open a public issue for security-relevant findings before coordinating disclosure.

## Known limitations

Policy Scout explicitly does not provide:

- kernel-grade or container-grade process isolation
- coverage of every shell grammar edge case
- guaranteed detection of all secret forms or malicious packages
- governance of actions that bypass its CLI, hook, MCP, or integration boundary

These are design boundaries, not bugs. See [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) for the full out-of-scope list.
