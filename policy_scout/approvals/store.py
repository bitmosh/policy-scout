"""Approval request persistence."""

import json
import os
import sys
from pathlib import Path
from typing import Optional, List
from .models import ApprovalRequest


class ApprovalStore:
    """Approval request store using JSONL persistence."""

    def __init__(self, path: Optional[Path] = None):
        """Initialize approval store with file path."""
        if path is None:
            # Default to ~/.local/share/policy-scout/approvals.jsonl
            path = Path.home() / ".local" / "share" / "policy-scout" / "approvals.jsonl"
        
        # Support environment variable override
        env_path = os.environ.get("POLICY_SCOUT_APPROVAL_PATH")
        if env_path:
            path = Path(env_path)
        
        self.path = path
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure the approval directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, approval: ApprovalRequest) -> bool:
        """Save an approval request to the store."""
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(approval.to_dict()) + "\n")
            return True
        except Exception as e:
            print(f"Warning: Failed to save approval request: {e}", file=sys.stderr)
            return False

    def get_by_id(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        if not self.path.exists():
            return None
        
        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        if data.get("approval_id") == approval_id:
                            return ApprovalRequest.from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to read approval request: {e}", file=sys.stderr)
        
        return None

    def list_pending(self) -> List[ApprovalRequest]:
        """List all pending approval requests."""
        if not self.path.exists():
            return []
        
        pending = []
        try:
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        if data.get("status") == "pending":
                            pending.append(ApprovalRequest.from_dict(data))
        except Exception as e:
            print(f"Warning: Failed to list approval requests: {e}", file=sys.stderr)
        
        return pending

    def update_status(self, approval_id: str, new_status: str) -> bool:
        """Update the status of an approval request."""
        if not self.path.exists():
            return False
        
        try:
            # Read all approvals
            approvals = []
            with open(self.path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        if data.get("approval_id") == approval_id:
                            data["status"] = new_status
                        approvals.append(data)
            
            # Write back
            with open(self.path, "w") as f:
                for approval in approvals:
                    f.write(json.dumps(approval) + "\n")
            
            return True
        except Exception as e:
            print(f"Warning: Failed to update approval status: {e}", file=sys.stderr)
            return False

    def clear(self):
        """Clear all approval requests."""
        if self.path.exists():
            self.path.unlink()
