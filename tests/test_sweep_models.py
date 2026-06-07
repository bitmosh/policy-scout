"""Tests for sweep models."""

from policy_scout.sweep.models import Finding, SweepResult


def test_finding_id_starts_with_find():
    """Test finding IDs start with 'find_'."""
    finding = Finding()
    assert finding.finding_id.startswith("find_")


def test_finding_severity_defaults():
    """Test finding severity defaults to 'info'."""
    finding = Finding()
    assert finding.severity == "info"


def test_finding_confidence_defaults():
    """Test finding confidence defaults to 'moderate'."""
    finding = Finding()
    assert finding.confidence == "moderate"


def test_finding_to_dict():
    """Test finding conversion to dictionary."""
    finding = Finding(
        sweep_id="sweep_123",
        severity="high",
        confidence="moderate",
        category="suspicious_lifecycle_script",
        title="Test finding",
        location="package.json",
        evidence_ref="test",
        why_it_matters="Test",
        recommended_action="Review",
    )
    data = finding.to_dict()

    assert data["finding_id"] == finding.finding_id
    assert data["sweep_id"] == "sweep_123"
    assert data["severity"] == "high"
    assert data["confidence"] == "moderate"
    assert data["category"] == "suspicious_lifecycle_script"
    assert data["title"] == "Test finding"
    assert data["location"] == "package.json"
    assert data["evidence_ref"] == "test"
    assert data["why_it_matters"] == "Test"
    assert data["recommended_action"] == "Review"
    assert data["schema_version"] == 1


def test_finding_from_dict():
    """Test finding creation from dictionary."""
    data = {
        "finding_id": "find_123",
        "sweep_id": "sweep_123",
        "severity": "high",
        "confidence": "moderate",
        "category": "suspicious_lifecycle_script",
        "title": "Test finding",
        "location": "package.json",
        "evidence_ref": "test",
        "why_it_matters": "Test",
        "recommended_action": "Review",
        "schema_version": 1,
    }

    finding = Finding.from_dict(data)

    assert finding.finding_id == "find_123"
    assert finding.sweep_id == "sweep_123"
    assert finding.severity == "high"
    assert finding.confidence == "moderate"
    assert finding.category == "suspicious_lifecycle_script"
    assert finding.title == "Test finding"
    assert finding.location == "package.json"
    assert finding.evidence_ref == "test"
    assert finding.why_it_matters == "Test"
    assert finding.recommended_action == "Review"


def test_sweep_result_id_starts_with_sweep():
    """Test sweep result IDs start with 'sweep_'."""
    result = SweepResult()
    assert result.sweep_id.startswith("sweep_")


def test_sweep_result_defaults():
    """Test sweep result defaults."""
    result = SweepResult()

    assert result.sweep_type == "project"
    assert result.project_root == ""
    assert result.findings_count == {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    assert result.findings == []
    assert result.could_not_verify == []
    assert result.schema_version == 1


def test_sweep_result_to_dict():
    """Test sweep result conversion to dictionary."""
    finding = Finding(
        sweep_id="sweep_123",
        severity="high",
        confidence="moderate",
        category="suspicious_lifecycle_script",
        title="Test finding",
        location="package.json",
    )

    result = SweepResult(
        sweep_id="sweep_123",
        sweep_type="project",
        project_root="/test/project",
        findings=[finding],
        could_not_verify=["test"],
    )

    data = result.to_dict()

    assert data["sweep_id"] == "sweep_123"
    assert data["sweep_type"] == "project"
    assert data["project_root"] == "/test/project"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["title"] == "Test finding"
    assert data["could_not_verify"] == ["test"]
    assert data["schema_version"] == 1


def test_sweep_result_from_dict():
    """Test sweep result creation from dictionary."""
    data = {
        "sweep_id": "sweep_123",
        "sweep_type": "project",
        "started_at": "2024-01-01T00:00:00Z",
        "completed_at": "2024-01-01T00:00:10Z",
        "project_root": "/test/project",
        "findings_count": {
            "critical": 0,
            "high": 1,
            "medium": 0,
            "low": 0,
            "info": 0,
        },
        "findings": [
            {
                "finding_id": "find_123",
                "sweep_id": "sweep_123",
                "severity": "high",
                "confidence": "moderate",
                "category": "suspicious_lifecycle_script",
                "title": "Test finding",
                "location": "package.json",
                "evidence_ref": "test",
                "why_it_matters": "Test",
                "recommended_action": "Review",
                "schema_version": 1,
            }
        ],
        "could_not_verify": ["test"],
        "schema_version": 1,
    }

    result = SweepResult.from_dict(data)

    assert result.sweep_id == "sweep_123"
    assert result.sweep_type == "project"
    assert result.project_root == "/test/project"
    assert len(result.findings) == 1
    assert result.findings[0].title == "Test finding"
    assert result.could_not_verify == ["test"]


def test_sweep_result_add_finding():
    """Test adding a finding to sweep result."""
    result = SweepResult()

    finding1 = Finding(
        severity="high",
        confidence="moderate",
        category="suspicious_lifecycle_script",
        title="Test finding 1",
        location="package.json",
    )

    finding2 = Finding(
        severity="medium",
        confidence="moderate",
        category="suspicious_lifecycle_script",
        title="Test finding 2",
        location="package.json",
    )

    result.add_finding(finding1)
    result.add_finding(finding2)

    assert len(result.findings) == 2
    assert result.findings_count["high"] == 1
    assert result.findings_count["medium"] == 1
    assert result.findings[0].sweep_id == result.sweep_id
    assert result.findings[1].sweep_id == result.sweep_id
