# SPDX-License-Identifier: Apache-2.0
"""Eval report generation (human and JSON)."""

from typing import List
from .models import EvalResult, EvalSummary


def generate_eval_report(
    results: List[EvalResult],
    summary: EvalSummary,
) -> str:
    """Generate human-readable eval report.

    Args:
        results: List of EvalResult objects.
        summary: EvalSummary object.

    Returns:
        Markdown-formatted report string.
    """
    lines = []
    lines.append("# Policy Scout Eval Report")
    lines.append("")
    lines.append(f"Total Cases: {summary.total_cases}")
    lines.append(f"Passed: {summary.passed}")
    lines.append(f"Failed: {summary.failed}")
    lines.append(f"Pass Rate: {summary.pass_rate:.1%}")
    lines.append(f"Execution Time: {summary.execution_time_ms}ms")
    lines.append("")

    if summary.failed_case_ids:
        lines.append("## Failed Cases")
        lines.append("")
        for case_id in summary.failed_case_ids:
            result = next(r for r in results if r.case_id == case_id)
            lines.append(f"### {case_id}")
            lines.append(f"Command: `{result.command}`")
            lines.append(f"Expected Decision: {result.expected_decision}")
            lines.append(f"Actual Decision: {result.actual_decision}")
            if result.failure_reasons:
                lines.append("Failure Reasons:")
                for reason in result.failure_reasons:
                    lines.append(f"  - {reason}")
            lines.append("")

    if summary.passed > 0:
        lines.append("## Passed Cases")
        lines.append("")
        for result in results:
            if result.passed:
                lines.append(f"- {result.case_id}: `{result.command}`")
        lines.append("")

    return "\n".join(lines)


def generate_eval_json(
    results: List[EvalResult],
    summary: EvalSummary,
) -> dict:
    """Generate JSON eval report.

    Args:
        results: List of EvalResult objects.
        summary: EvalSummary object.

    Returns:
        JSON-serializable dict.
    """
    return {
        "summary": summary.to_dict(),
        "results": [r.to_dict() for r in results],
    }
