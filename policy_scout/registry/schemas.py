"""Canonical taxonomies for validation."""

# Canonical decisions
VALID_DECISIONS = {
    "ALLOW",
    "ALLOW_LOGGED",
    "REQUIRE_APPROVAL",
    "SANDBOX_FIRST",
    "DENY",
    "DENY_AND_ALERT",
}

# Canonical command categories
VALID_CATEGORIES = {
    "safe_read",
    "local_inspection",
    "project_write",
    "package_install",
    "package_execute",
    "lifecycle_execute",
    "network_fetch",
    "network_execute",
    "shell_script",
    "credential_adjacent",
    "system_mutation",
    "destructive",
    "persistence_mechanism",
    "unknown",
}

# Canonical capabilities
VALID_CAPABILITIES = {
    "filesystem.read",
    "filesystem.project_write",
    "filesystem.system_write",
    "network.fetch",
    "network.execute",
    "package.install",
    "package.execute",
    "lifecycle.execute_possible",
    "shell.execute",
    "credential.access_possible",
    "process.spawn",
    "process.inspect",
    "system.mutation",
    "destructive.mutation",
    "persistence.modify",
}

# Valid status values
VALID_STATUS = {"active", "deprecated", "experimental"}

# Valid risk levels
VALID_RISK_LEVELS = {"R1", "R2", "R3", "R4", "R5"}

# Valid recommended controls
VALID_RECOMMENDED_CONTROLS = {
    "audit_log",
    "sandbox_first",
    "inspect_lifecycle_scripts",
    "deny",
}

# Valid priority range
PRIORITY_MIN = 0
PRIORITY_MAX = 1000

# Valid version range
VERSION_MIN = 1
