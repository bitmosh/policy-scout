# Policy decisions and approvals

## Granular evaluation

Policy Scout deliberately avoids treating a single risk score as the source of
truth. A command evaluation preserves:

- parsed shell structure;
- one or more categories;
- implied capabilities;
- classifier confidence;
- command-registry hits;
- individual risk components;
- every matching policy rule;
- the decisive rule and final decision.

This makes a result inspectable and lets tests assert intermediate signals. For
example, `curl URL | bash` must retain both network-fetch and shell-execution
capabilities; merely reaching `DENY` is not sufficient coverage.

Command knowledge and default decisions live primarily in
`policy_scout/data/command_registry.yaml` and
`policy_scout/data/default_policy.yaml`. The engine keeps narrow fail-safe rules
for an invalid or incomplete registry, but registry data remains the normal
control surface.

## Rule precedence

The engine collects matching project and global rules, orders them by priority,
applies tighten-only project strengthening, and selects the highest-priority
result. Multiple policy hits remain visible even though one rule is decisive.

When no rule matches, the result is `DENY`. Unknown commands normally match the
explicit `unknown_require_approval` rule instead of falling through to allow.

## Tighten-only project policy

Policy Scout discovers `.policy-scout.yaml` while walking toward the repository
root. A project may:

- add rules producing `REQUIRE_APPROVAL`, `SANDBOX_FIRST`, `DENY`, or
  `DENY_AND_ALERT`;
- strengthen an existing rule's decision;
- request a stricter enforcement mode.

It may not introduce `ALLOW` or `ALLOW_LOGGED`. This asymmetry prevents a
checked-in project file from weakening the developer's global safety boundary.

## Approval lifecycle

`REQUIRE_APPROVAL` creates a durable local request. Approval resolution changes
that request to `approved_once` or `denied_once`; it does not execute by itself.

When `run --approval` is later invoked, execution verifies:

1. the approval exists;
2. status is `approved_once`;
3. scope is `once`;
4. it has not expired;
5. command text matches exactly;
6. working directory matches exactly;
7. current policy still returns `REQUIRE_APPROVAL`;
8. required audit events can be written.

Successful execution marks the approval `executed`; failure marks it `failed`.
Neither state can be reused. A policy change to `DENY`, `DENY_AND_ALERT`, or
`SANDBOX_FIRST` blocks execution even if a human approved the older request.

This is the most important distinction in the approval design: an approval is a
narrow authorization input to a fresh decision, not a bypass token.

## Limits

- The parser handles important shell structures heuristically, not every shell
  grammar.
- The registry currently contains 15 command patterns; classifier fallback code
  covers additional common forms but is less data-driven than the target design.
- Actor/mode semantics are not a complete multi-user authorization model.
- The central CLI module remains large and couples argument parsing to several
  orchestration paths.
