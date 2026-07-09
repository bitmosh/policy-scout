# SPDX-License-Identifier: Apache-2.0
"""eval command handler."""

import json
import sys

from ...evals.loader import load_eval_cases, validate_eval_cases
from ...evals.runner import run_eval_suite
from ...evals.report import generate_eval_report, generate_eval_json


def handle_eval_run_command(
    json_output: bool = False,
    filter_tag: str = None,
    file_path: str = None,
):
    """Handle eval run command."""
    try:
        # Load eval cases
        cases = load_eval_cases(path=file_path)

        # Validate eval cases
        validation_errors = validate_eval_cases(cases)
        if validation_errors:
            print("Eval case validation errors:", file=sys.stderr)
            for error in validation_errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)

        # Run eval suite
        results, summary = run_eval_suite(cases, filter_tag=filter_tag)

        # Output results
        if json_output:
            print(json.dumps(generate_eval_json(results, summary), indent=2))
        else:
            print(generate_eval_report(results, summary))

        # Set exit code based on pass/fail
        if summary.failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Eval run failed: {e}", file=sys.stderr)
        sys.exit(1)
