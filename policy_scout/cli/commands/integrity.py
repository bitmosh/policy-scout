"""integrity command handler."""

import json
import sys


def handle_integrity_command(args):
    """Handle integrity subcommands."""
    from ...integrity.registry_manifest import (
        verify_registry_integrity,
        generate_manifest,
        write_manifest,
    )

    if args.integrity_subcommand == "check":
        result = verify_registry_integrity()

        if args.json:
            out = {
                "passed": result.passed,
                "files_checked": result.files_checked,
                "reason": result.reason,
                "errors": result.errors,
            }
            print(json.dumps(out, indent=2))
        else:
            status_sym = "✓" if result.passed else "✗"
            print(f"Registry integrity: {status_sym}")
            print(f"  {result.reason}")
            if result.errors and (getattr(args, "verbose", False) or not result.passed):
                for err in result.errors:
                    print(f"  - {err}")

        if not result.passed:
            sys.exit(1)

    elif args.integrity_subcommand == "update-manifest":
        version = getattr(args, "version", "dev")
        manifest = generate_manifest(version=version)
        write_manifest(manifest)
        files = manifest["files"]
        print(f"Manifest updated: {len(files)} file(s) hashed.")
        for name in files:
            print(f"  {name}")

    else:
        print("Error: No integrity subcommand provided", file=sys.stderr)
        sys.exit(1)
