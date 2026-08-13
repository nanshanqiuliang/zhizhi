from pathlib import Path

from scripts.repository_validation import find_suspected_secrets


def test_placeholder_secret_references_are_allowed(tmp_path: Path) -> None:
    config = tmp_path / "providers.yaml"
    config.write_text(
        "secret_ref: env://DEEPSEEK_API_KEY\n"
        "secret_ref: keychain://knowledge-tree-agent/deepseek-api-key\n",
        encoding="utf-8",
    )

    assert find_suspected_secrets([config]) == []


def test_private_key_and_api_token_are_rejected(tmp_path: Path) -> None:
    private_key = tmp_path / "private.pem"
    marker = "-----BEGIN " + "PRIVATE KEY-----"
    private_key.write_text(f"{marker}\nnot-real\n", encoding="utf-8")
    token = tmp_path / "leak.txt"
    token.write_text(f"token = {'sk-' + 'a' * 32}\n", encoding="utf-8")

    findings = find_suspected_secrets([private_key, token])

    assert {finding.rule for finding in findings} == {"private_key", "api_token"}
    assert all(finding.line == 1 for finding in findings)
