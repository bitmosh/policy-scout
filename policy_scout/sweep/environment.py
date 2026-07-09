# SPDX-License-Identifier: Apache-2.0
"""Environment variable name checks for quick system sweep."""

import os
from typing import List
from .models import Finding


def check_environment_variables(sweep_id: str) -> List[Finding]:
    """Check for sensitive environment variable names.

    Args:
        sweep_id: Sweep result ID.

    Returns:
        List of findings.
    """
    findings = []
    
    # Sensitive environment variable names to check
    sensitive_names = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GITHUB_TOKEN",
        "NPM_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "API_KEY",
        "TOKEN",
        "SECRET",
        "PASSWORD",
    ]
    
    # Check which sensitive names are present
    present_names = []
    for name in sensitive_names:
        if name in os.environ:
            present_names.append(name)
    
    if present_names:
        # Group by category
        api_keys = [n for n in present_names if "API_KEY" in n or "TOKEN" in n]
        aws_keys = [n for n in present_names if "AWS" in n]
        generic_secrets = [n for n in present_names if n in ["SECRET", "PASSWORD"]]
        
        if api_keys:
            findings.append(Finding(
                finding_id=f"find_env_api_keys_{sweep_id}",
                sweep_id=sweep_id,
                severity="medium",
                confidence="high",
                category="credential_exposure_signal",
                title="Sensitive API key environment variable names present",
                location="process environment",
                evidence_ref=f"variables: {', '.join(api_keys)}",
                why_it_matters="Sensitive environment variable names are present in current process environment.",
                recommended_action="Review if these environment variables are expected and properly secured.",
            ))
        
        if aws_keys:
            findings.append(Finding(
                finding_id=f"find_env_aws_{sweep_id}",
                sweep_id=sweep_id,
                severity="medium",
                confidence="high",
                category="credential_exposure_signal",
                title="AWS credential environment variable names present",
                location="process environment",
                evidence_ref=f"variables: {', '.join(aws_keys)}",
                why_it_matters="AWS credential environment variable names are present in current process environment.",
                recommended_action="Review if these environment variables are expected and properly secured.",
            ))
        
        if generic_secrets:
            findings.append(Finding(
                finding_id=f"find_env_secrets_{sweep_id}",
                sweep_id=sweep_id,
                severity="low",
                confidence="high",
                category="credential_exposure_signal",
                title="Generic secret environment variable names present",
                location="process environment",
                evidence_ref=f"variables: {', '.join(generic_secrets)}",
                why_it_matters="Generic secret environment variable names are present in current process environment.",
                recommended_action="Review if these environment variables are expected.",
            ))
    
    return findings
