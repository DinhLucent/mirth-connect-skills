from pathlib import Path
import shutil

from mirth_agent_tools.config import Settings
from mirth_agent_tools.redaction import redact_phi
from mirth_agent_tools import tools


def test_dry_run_skips_write_api_calls() -> None:
    scratch = _scratch_dir("dry-run")
    settings = Settings(
        base_url="https://localhost:8443",
        username="admin",
        password="admin",
        full_access=True,
        dry_run=True,
        backup_dir=scratch / "backups",
        log_dir=scratch / "logs",
    )

    result = tools.deploy_channel("abc", settings=settings)

    assert result["ok"] is True
    assert result["data"] == {"dry_run": True, "skipped": "mirth.deploy_channel"}
    assert (scratch / "logs" / "audit.jsonl").exists()


def test_approval_gate_blocks_write_without_token() -> None:
    scratch = _scratch_dir("approval")
    settings = Settings(
        base_url="https://localhost:8443",
        username="admin",
        password="admin",
        full_access=True,
        require_approval=True,
        approval_token="secret",
        backup_dir=scratch / "backups",
        log_dir=scratch / "logs",
    )

    result = tools.deploy_channel("abc", settings=settings)

    assert result["ok"] is False
    assert result["needs_user_input"] is True
    assert "approval token" in result["user_question"].lower()


def _scratch_dir(name: str) -> Path:
    path = Path(__file__).parent / ".tmp" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_plan_operation_is_local_and_structured() -> None:
    result = tools.plan_operation("delete_channel", channel_id="abc")

    assert result["ok"] is True
    assert result["data"]["operation"] == "delete_channel"
    assert result["data"]["destructive"] is True
    assert "backup_channel" in result["data"]["prechecks"]


def test_redact_phi_masks_common_hl7_fields() -> None:
    text = "PID|1||12345||Doe^Jane||19700101||||123 Main St||555-123-4567|||123-45-6789"

    redacted = redact_phi(text)

    assert "Doe^Jane" not in redacted
    assert "19700101" not in redacted
    assert "555-123-4567" not in redacted
    assert "123-45-6789" not in redacted


def test_redact_phi_masks_hl7_name_inside_wrapped_content() -> None:
    text = "<content>PID|1||12345||Doe^Jane||19700101||||123 Main St||555-123-4567</content>"

    redacted = redact_phi(text)

    assert "Doe^Jane" not in redacted
    assert "[REDACTED_NAME]" in redacted
