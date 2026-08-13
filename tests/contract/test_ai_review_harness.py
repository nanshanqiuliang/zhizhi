from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.ai_review_harness import (
    MachineReviewValidationError,
    ReplaySearchProvider,
    build_mock_machine_review,
    load_review_policy,
    policy_sha256,
    validate_machine_review,
)
from scripts.calculus_dataset_validation import load_and_validate_dataset

ROOT = Path(__file__).resolve().parents[2]


def _artifact_hash(artifact: dict[str, object]) -> str:
    payload = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _fixture() -> tuple[dict[str, object], dict[str, object], ReplaySearchProvider]:
    dataset = load_and_validate_dataset(ROOT)
    policy = load_review_policy(ROOT)
    provider = ReplaySearchProvider.from_dataset(ROOT, dataset)
    return dataset, policy, provider


def _review(
    *, scenario: str = "accept", same_model: bool = True
) -> tuple[dict[str, object], dict[str, object], ReplaySearchProvider]:
    dataset, policy, provider = _fixture()
    review = build_mock_machine_review(
        dataset,
        policy,
        provider,
        scenario=scenario,
        same_model=same_model,
    )
    return review, dataset, provider


def test_accept_replay_is_mock_only_inconclusive_with_explicit_correlation() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)

    validate_machine_review(ROOT, review, dataset, policy, provider)

    assert review["machine_state"] == "inconclusive"
    assert review["assurance"] == {
        "execution_mode": "deterministic_mock_replay",
        "evidence_basis": "first_party_page_replay",
        "subject_evidence_established": False,
        "product_eligible": False,
    }
    assert review["failure"]["code"] == "review_inconclusive"
    assert review["correlation"]["classification"] == "correlated_review"
    assert (
        review["subject_artifact"]["artifact_sha256"]
        == review["qa_artifact"]["subject_artifact_sha256"]
    )


def test_review_policy_has_versioned_role_prompts_and_disjoint_risk_classes() -> None:
    policy = load_review_policy(ROOT)

    assert policy["schema_version"] == "ai-review-policy.v2"
    assert len(policy_sha256(policy)) == 64
    prompts = {role["prompt_version"] for role in policy["roles"].values()}
    contexts = {role["context_version"] for role in policy["roles"].values()}
    assert len(prompts) == len(contexts) == 3
    assert set(policy["waivable_risk_codes"]).isdisjoint(policy["hard_invariants"])


def test_replay_is_deterministic_and_does_not_duplicate_tool_calls() -> None:
    first, _, first_provider = _review()
    second, _, second_provider = _review()

    assert first == second
    assert len(first_provider.calls) == len(set(first_provider.calls)) == 240
    assert first_provider.calls == second_provider.calls


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (("subject_artifact", "provenance", "agent_run_id"), "agent_run_id"),
        (("subject_artifact", "provenance", "prompt", "sha256"), "sha256"),
        (("subject_artifact", "provenance", "context", "sha256"), "sha256"),
        (("subject_artifact", "provenance", "tool_policy", "sha256"), "sha256"),
        (("subject_artifact", "provenance", "harness", "sha256"), "sha256"),
        (("subject_artifact", "input_manifest", "dataset_sha256"), "dataset_sha256"),
    ],
)
def test_required_provenance_fields_fail_closed(path: tuple[str, ...], message: str) -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    cursor = changed
    for part in path[:-1]:
        cursor = cursor[part]
    del cursor[path[-1]]

    with pytest.raises(MachineReviewValidationError, match=message):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("agent_run_id", "distinct agent_run_id"),
        ("session_id", "shared mutable session"),
        ("context", "distinct context"),
        ("prompt", "distinct prompt"),
    ],
)
def test_subject_and_qa_run_isolation_is_non_waivable(field: str, message: str) -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    subject_value = changed["subject_artifact"]["provenance"][field]
    changed["qa_artifact"]["provenance"][field] = deepcopy(subject_value)

    with pytest.raises(MachineReviewValidationError, match=message):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_same_model_cannot_be_mislabeled_as_independent() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    review["correlation"]["classification"] = "independent_review"

    with pytest.raises(MachineReviewValidationError, match="correlation classification mismatch"):
        validate_machine_review(ROOT, review, dataset, policy, provider)


def test_cross_provider_mock_is_independent_but_never_machine_verified() -> None:
    review, dataset, provider = _review(same_model=False)
    policy = load_review_policy(ROOT)

    validate_machine_review(ROOT, review, dataset, policy, provider)

    assert review["correlation"]["classification"] == "independent_review"
    assert review["machine_state"] == "inconclusive"
    assert review["assurance"]["product_eligible"] is False


def test_controlled_live_cannot_be_product_eligible_without_subject_evidence() -> None:
    review, dataset, provider = _review(same_model=False)
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    changed["assurance"] = {
        "execution_mode": "controlled_live",
        "evidence_basis": "controlled_sources",
        "subject_evidence_established": False,
        "product_eligible": True,
    }
    changed["machine_state"] = "machine_verified"
    changed["failure"] = None
    qa = changed["qa_artifact"]
    qa["decision"] = "pass"
    qa["artifact_sha256"] = _artifact_hash(qa)

    with pytest.raises(MachineReviewValidationError, match="subject evidence|product eligibility"):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_accept_requires_evidence_and_minimum_confidence() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    changed["subject_artifact"]["findings"][0]["evidence_ids"] = []
    changed["subject_artifact"]["findings"][0]["confidence"] = 0.5

    with pytest.raises(MachineReviewValidationError, match="accept requires evidence"):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_finding_evidence_must_bind_the_same_claim_and_support_position() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    changed["subject_artifact"]["findings"][0]["evidence_ids"] = [
        changed["subject_artifact"]["evidence_ledger"][1]["evidence_id"]
    ]

    with pytest.raises(MachineReviewValidationError, match="evidence claim binding mismatch"):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_contract_allows_multiple_independent_evidence_items_for_one_claim() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    subject = changed["subject_artifact"]
    duplicate = deepcopy(subject["evidence_ledger"][0])
    duplicate["evidence_id"] += "-second"
    subject["evidence_ledger"].append(duplicate)
    subject["findings"][0]["evidence_ids"].append(duplicate["evidence_id"])
    subject["artifact_sha256"] = _artifact_hash(subject)
    qa = changed["qa_artifact"]
    qa["subject_artifact_sha256"] = subject["artifact_sha256"]
    qa["artifact_sha256"] = _artifact_hash(qa)

    validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_prompt_injection_that_changes_instructions_fails_closed() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    evidence = changed["subject_artifact"]["evidence_ledger"][0]
    evidence["untrusted_instructions_detected"] = True
    evidence["instructions_ignored"] = False

    with pytest.raises(MachineReviewValidationError) as captured:
        validate_machine_review(ROOT, changed, dataset, policy, provider)

    assert captured.value.code == "prompt_injection_suspected"


def test_tool_call_outside_role_allowlist_fails_closed() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    changed["subject_artifact"]["tool_trace"][0]["tool_id"] = "write_database"

    with pytest.raises(MachineReviewValidationError) as captured:
        validate_machine_review(ROOT, changed, dataset, policy, provider)

    assert captured.value.code == "review_tool_denied"


def test_dataset_input_drift_fails_closed() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed_dataset = deepcopy(dataset)
    changed_dataset["concepts"][0]["definition_zh"] += "漂移"

    with pytest.raises(MachineReviewValidationError) as captured:
        validate_machine_review(ROOT, review, changed_dataset, policy, provider)

    assert captured.value.code == "review_input_drifted"


def test_false_replay_citation_fails_closed() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    changed["subject_artifact"]["evidence_ledger"][0]["content_sha256"] = "0" * 64

    with pytest.raises(MachineReviewValidationError) as captured:
        validate_machine_review(ROOT, changed, dataset, policy, provider)

    assert captured.value.code == "review_evidence_invalid"


@pytest.mark.parametrize("scenario", ["timeout", "budget_exceeded", "abstain"])
def test_recoverable_failures_are_inconclusive_and_never_verified(scenario: str) -> None:
    review, dataset, provider = _review(scenario=scenario)
    policy = load_review_policy(ROOT)

    validate_machine_review(ROOT, review, dataset, policy, provider)

    assert review["machine_state"] == "inconclusive"
    assert review["failure"]["code"] in {
        "provider_timeout",
        "budget_exceeded",
        "review_inconclusive",
    }


def test_dispute_requires_frozen_independent_adjudication_before_qa() -> None:
    review, dataset, provider = _review(scenario="dispute")
    policy = load_review_policy(ROOT)

    validate_machine_review(ROOT, review, dataset, policy, provider)

    adjudication = review["adjudication_artifact"]
    assert adjudication is not None
    assert review["qa_artifact"]["adjudication_artifact_sha256"] == adjudication["artifact_sha256"]
    assert (
        adjudication["provenance"]["agent_run_id"]
        != review["subject_artifact"]["provenance"]["agent_run_id"]
    )
    assert adjudication["evidence_ledger"]
    assert adjudication["tool_trace"]
    assert adjudication["resolutions"][0]["evidence_ids"]
    assert adjudication["resolutions"][0]["confidence"] >= 0.8


def test_adjudication_counterevidence_requires_counterevidence_position() -> None:
    review, dataset, provider = _review(scenario="dispute")
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    adjudication = changed["adjudication_artifact"]
    evidence_id = adjudication["resolutions"][0]["evidence_ids"][0]
    adjudication["resolutions"][0]["counterevidence_ids"] = [evidence_id]
    adjudication["artifact_sha256"] = _artifact_hash(adjudication)
    qa = changed["qa_artifact"]
    qa["adjudication_artifact_sha256"] = adjudication["artifact_sha256"]
    qa["artifact_sha256"] = _artifact_hash(qa)

    with pytest.raises(MachineReviewValidationError, match="counterevidence.*position"):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_unresolved_dispute_cannot_produce_machine_verified() -> None:
    review, dataset, provider = _review(scenario="dispute")
    policy = load_review_policy(ROOT)
    changed = deepcopy(review)
    changed["adjudication_artifact"] = None
    changed["qa_artifact"]["adjudication_artifact_sha256"] = None

    with pytest.raises(MachineReviewValidationError, match="dispute requires adjudication"):
        validate_machine_review(ROOT, changed, dataset, policy, provider)


def test_qa_must_bind_exact_frozen_subject_artifact() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    review["qa_artifact"]["subject_artifact_sha256"] = "f" * 64

    with pytest.raises(MachineReviewValidationError, match="QA subject artifact binding"):
        validate_machine_review(ROOT, review, dataset, policy, provider)


def test_owner_risk_acceptance_cannot_make_mock_only_review_product_eligible() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    review["owner_risk_acceptance"] = {
        "owner_id": "workspace_owner",
        "risk_codes": ["review_correlated_agents"],
        "scope": "calculus-v1 mock review only",
        "content_sha256": review["input_manifest"]["dataset_sha256"],
        "policy_sha256": review["input_manifest"]["policy_sha256"],
        "accepted_at": "2026-08-13T14:00:00Z",
        "expires_at": "2026-08-20T14:00:00Z",
    }
    review["machine_state"] = "accepted_with_owner_risk"
    with pytest.raises(MachineReviewValidationError, match="mock-only|subject evidence"):
        validate_machine_review(ROOT, review, dataset, policy, provider)


def test_coverage_must_match_all_30_40_50_dataset_items() -> None:
    review, dataset, provider = _review()
    policy = load_review_policy(ROOT)
    review["subject_artifact"]["findings"].pop()

    with pytest.raises(MachineReviewValidationError, match="finding coverage mismatch|too short"):
        validate_machine_review(ROOT, review, dataset, policy, provider)
