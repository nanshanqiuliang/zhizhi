"""Deterministic mock/replay harness for calculus machine review v2."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker
from pypdf import PdfReader

from scripts.calculus_dataset_validation import JsonObject

DATASET_DIR = Path("evals/calculus-v1")
POLICY_PATH = DATASET_DIR / "review-policy.v2.json"
POLICY_SCHEMA_PATH = DATASET_DIR / "schema/review-policy.schema.json"
SCHEMA_PATH = DATASET_DIR / "schema/machine-review.schema.json"
HARNESS_VERSION = "calculus-ai-review-harness.v2.mock.1"
FIXTURE_TIME = "2026-08-13T13:00:00Z"

Scenario = Literal["accept", "dispute", "abstain", "timeout", "budget_exceeded"]


class MachineReviewValidationError(ValueError):
    """Raised when a v2 machine review violates a deterministic invariant."""

    code = "review_provenance_invalid"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _sha256(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = _canonical_json(value)
    return hashlib.sha256(payload).hexdigest()


def _artifact_sha256(artifact: JsonObject) -> str:
    payload = {key: value for key, value in artifact.items() if key != "artifact_sha256"}
    return _sha256(payload)


def _load_object(path: Path) -> JsonObject:
    try:
        value: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MachineReviewValidationError(f"{path}: cannot parse JSON: {error}") from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise MachineReviewValidationError(f"{path}: expected an object with string keys")
    return value


def load_review_policy(root: Path) -> JsonObject:
    """Load the non-network calculus v2 review policy."""

    policy = _load_object(root / POLICY_PATH)
    schema = _load_object(root / POLICY_SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(policy), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise MachineReviewValidationError(f"review-policy.v2.json:{location}: {first.message}")
    waivable = set(cast(list[str], policy["waivable_risk_codes"]))
    hard = set(cast(list[str], policy["hard_invariants"]))
    if waivable & hard:
        raise MachineReviewValidationError(
            f"review policy cannot make hard invariants waivable: {sorted(waivable & hard)}"
        )
    return policy


def policy_sha256(policy: JsonObject) -> str:
    """Return a content address for a review policy."""

    return _sha256(policy)


def review_dataset_sha256(dataset: JsonObject) -> str:
    """Hash all reviewable data while excluding mutable approval metadata."""

    subject = {key: value for key, value in dataset.items() if key not in {"status", "review"}}
    return _sha256(subject)


def _input_manifest(dataset: JsonObject, policy: JsonObject) -> JsonObject:
    return {
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": review_dataset_sha256(dataset),
        "policy_sha256": policy_sha256(policy),
    }


def _stable_uuid(label: str) -> str:
    digest = bytearray(hashlib.sha256(label.encode("utf-8")).digest()[:16])
    digest[6] = (digest[6] & 0x0F) | 0x70
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(UUID(bytes=bytes(digest)))


def _versioned_hash(version: str) -> JsonObject:
    return {"version": version, "sha256": _sha256(version)}


def _provenance(
    role_id: str,
    policy: JsonObject,
    *,
    provider: str,
    model_id: str,
) -> JsonObject:
    role_policy = cast(JsonObject, cast(JsonObject, policy["roles"])[role_id])
    prompt_version = cast(str, role_policy["prompt_version"])
    context_version = cast(str, role_policy["context_version"])
    return {
        "actor_type": "ai_agent",
        "role_id": role_id,
        "agent_run_id": _stable_uuid(f"{role_id}:run"),
        "lineage_id": _stable_uuid("calculus-v1:review-lineage"),
        "session_id": _stable_uuid(f"{role_id}:session"),
        "provider": provider,
        "model_id": model_id,
        "model_revision": "fixture-2026-08-13",
        "prompt": {
            "version": prompt_version,
            "sha256": _sha256({"version": prompt_version, "text": role_policy["prompt_text"]}),
        },
        "context": {
            "version": context_version,
            "sha256": _sha256({"version": context_version, "scope": role_policy["context_scope"]}),
        },
        "tool_policy": _versioned_hash(
            f"{policy['policy_id']}:{role_id}:"
            f"{','.join(cast(list[str], role_policy['allowed_tools']))}"
        ),
        "harness": _versioned_hash(HARNESS_VERSION),
    }


def _dataset_items(dataset: JsonObject) -> list[tuple[str, JsonObject]]:
    result: list[tuple[str, JsonObject]] = []
    for item_kind, key in (
        ("concept", "concepts"),
        ("relation", "relations"),
        ("anchor", "anchors"),
    ):
        items = cast(list[JsonObject], dataset[key])
        result.extend((item_kind, item) for item in items)
    return result


def _claim_id(item_kind: str, item_id: str) -> str:
    return f"claim-{item_kind}-{item_id}"


def _evidence_id(role_id: str, item_kind: str, item_id: str) -> str:
    role_token = {"ai_subject_reviewer": "subject", "ai_qa_auditor": "qa"}[role_id]
    return f"evidence-{role_token}-{item_kind}-{item_id}"


def _item_pages(dataset: JsonObject, item_kind: str, item: JsonObject) -> list[int]:
    anchors = {
        cast(str, anchor["id"]): anchor for anchor in cast(list[JsonObject], dataset["anchors"])
    }
    if item_kind == "anchor":
        selected = [item]
    elif item_kind == "concept":
        selected = [anchors[anchor_id] for anchor_id in cast(list[str], item["anchor_ids"])]
    else:
        selected = [
            anchors[anchor_id] for anchor_id in cast(list[str], item["evidence_anchor_ids"])
        ]
    return sorted({cast(int, cast(JsonObject, anchor["selector"])["page"]) for anchor in selected})


def _evidence_payload(
    dataset: JsonObject,
    item_kind: str,
    item: JsonObject,
    page_hashes: dict[int, str],
) -> JsonObject:
    source = cast(JsonObject, dataset["source"])
    pages = _item_pages(dataset, item_kind, item)
    locator = "pages:" + ",".join(str(page) for page in pages)
    return {
        "source_id": source["resource_id"],
        "source_kind": "first_party_artifact",
        "locator": locator,
        "content_sha256": _sha256([page_hashes[page] for page in pages]),
        "position": "support",
        "claim_support_summary": (
            "Frozen PDF page text was replayed for this claim; mock mode does not establish "
            "semantic correctness."
        ),
        "retrieved_at": FIXTURE_TIME,
        "untrusted_instructions_detected": False,
        "instructions_ignored": True,
    }


@lru_cache(maxsize=4)
def _pdf_page_hashes(pdf_path_text: str, expected_sha256: str) -> dict[int, str]:
    pdf_path = Path(pdf_path_text)
    try:
        pdf_bytes = pdf_path.read_bytes()
        if _sha256(pdf_bytes) != expected_sha256:
            raise MachineReviewValidationError(
                "first-party replay PDF hash mismatch", code="review_evidence_invalid"
            )
        reader = PdfReader(pdf_path, strict=True)
        return {
            page_number: _sha256(page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        }
    except (OSError, ValueError) as error:
        raise MachineReviewValidationError(
            f"cannot build first-party page replay index: {error}",
            code="review_evidence_invalid",
        ) from error


@dataclass
class ReplaySearchProvider:
    """Read-only content-addressed search fixture with deduplicated call recording."""

    records: dict[str, JsonObject]
    calls: list[str] = field(default_factory=list)
    _seen_calls: set[str] = field(default_factory=set)

    @classmethod
    def from_dataset(cls, root: Path, dataset: JsonObject) -> ReplaySearchProvider:
        source = cast(JsonObject, dataset["source"])
        pdf_path = root / DATASET_DIR / cast(str, source["local_path"])
        page_hashes = _pdf_page_hashes(str(pdf_path.resolve()), cast(str, source["sha256"]))
        records: dict[str, JsonObject] = {}
        for item_kind, item in _dataset_items(dataset):
            records[_claim_id(item_kind, cast(str, item["id"]))] = _evidence_payload(
                dataset, item_kind, item, page_hashes
            )
        return cls(records=records)

    def search(self, role_id: str, claim_id: str) -> tuple[JsonObject, JsonObject]:
        """Return a frozen result and one immutable trace item."""

        call_id = f"call-{role_id.removeprefix('ai_').replace('_', '-')}-{claim_id}"
        if call_id not in self._seen_calls:
            self._seen_calls.add(call_id)
            self.calls.append(call_id)
        try:
            result = deepcopy(self.records[claim_id])
        except KeyError as error:
            raise MachineReviewValidationError(
                f"replay search has no record for {claim_id}", code="review_evidence_invalid"
            ) from error
        trace = {
            "call_id": call_id,
            "tool_id": "replay_search",
            "query_sha256": _sha256(claim_id),
            "result_sha256": _sha256(result),
            "status": "succeeded",
        }
        return result, trace

    def verify(self, evidence: JsonObject) -> bool:
        claim_id = evidence.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in self.records:
            return False
        record = self.records[claim_id]
        return all(evidence.get(key) == value for key, value in record.items())


def _build_evidence(
    role_id: str,
    dataset: JsonObject,
    provider: ReplaySearchProvider,
) -> tuple[list[JsonObject], list[JsonObject]]:
    evidence: list[JsonObject] = []
    traces: list[JsonObject] = []
    for item_kind, item in _dataset_items(dataset):
        item_id = cast(str, item["id"])
        claim_id = _claim_id(item_kind, item_id)
        record, trace = provider.search(role_id, claim_id)
        record.update(
            {
                "evidence_id": _evidence_id(role_id, item_kind, item_id),
                "claim_id": claim_id,
            }
        )
        evidence.append(record)
        traces.append(trace)
    return evidence, traces


def _build_findings(
    dataset: JsonObject,
    *,
    scenario: Scenario,
) -> list[JsonObject]:
    findings: list[JsonObject] = []
    for index, (item_kind, item) in enumerate(_dataset_items(dataset)):
        item_id = cast(str, item["id"])
        decision = "accept"
        confidence = 0.99
        rationale = "Frozen first-party fixture supports the reviewed claim."
        uncertainty: str | None = None
        if scenario == "dispute" and index == 0:
            decision = "dispute"
            confidence = 0.9
            rationale = "The seeded claim requires independent adjudication."
            uncertainty = "A deterministic dispute fixture was injected."
        elif scenario == "abstain" and index == 0:
            decision = "abstain"
            confidence = 0.0
            rationale = "The mock reviewer abstained because evidence was declared insufficient."
            uncertainty = "Evidence sufficiency could not be established."
        findings.append(
            {
                "claim_id": _claim_id(item_kind, item_id),
                "item_kind": item_kind,
                "item_id": item_id,
                "decision": decision,
                "evidence_ids": [_evidence_id("ai_subject_reviewer", item_kind, item_id)],
                "counterevidence_ids": [],
                "confidence": confidence,
                "rationale": rationale,
                "uncertainty": uncertainty,
            }
        )
    return findings


def build_mock_machine_review(
    dataset: JsonObject,
    policy: JsonObject,
    provider: ReplaySearchProvider,
    *,
    scenario: Scenario = "accept",
    same_model: bool = True,
) -> JsonObject:
    """Build a deterministic no-network subject/adjudication/QA artifact bundle."""

    manifest = _input_manifest(dataset, policy)
    subject_evidence, subject_trace = _build_evidence("ai_subject_reviewer", dataset, provider)
    subject: JsonObject = {
        "schema_version": "ai-subject-review.v2",
        "provenance": _provenance(
            "ai_subject_reviewer",
            policy,
            provider="mock_provider_a",
            model_id="mock_model_a",
        ),
        "input_manifest": deepcopy(manifest),
        "findings": _build_findings(dataset, scenario=scenario),
        "evidence_ledger": subject_evidence,
        "tool_trace": subject_trace,
    }
    subject["artifact_sha256"] = _artifact_sha256(subject)

    adjudication: JsonObject | None = None
    if scenario == "dispute":
        disputed = next(
            finding
            for finding in cast(list[JsonObject], subject["findings"])
            if finding["decision"] == "dispute"
        )
        adjudication_evidence, adjudication_trace = provider.search(
            "ai_dispute_adjudicator", cast(str, disputed["claim_id"])
        )
        adjudication_evidence.update(
            {
                "evidence_id": f"evidence-adjudication-{disputed['claim_id']}",
                "claim_id": disputed["claim_id"],
            }
        )
        adjudication = {
            "schema_version": "ai-dispute-resolution.v2",
            "provenance": _provenance(
                "ai_dispute_adjudicator",
                policy,
                provider="mock_provider_b",
                model_id="mock_model_b",
            ),
            "input_manifest": deepcopy(manifest),
            "subject_artifact_sha256": subject["artifact_sha256"],
            "resolutions": [
                {
                    "claim_id": disputed["claim_id"],
                    "decision": "reject_proposed",
                    "rationale": "Independent deterministic replay rejects the seeded dispute.",
                    "evidence_ids": [adjudication_evidence["evidence_id"]],
                    "counterevidence_ids": [],
                    "confidence": 0.99,
                    "uncertainty": (
                        "Mock replay cannot establish product-eligible subject evidence."
                    ),
                }
            ],
            "evidence_ledger": [adjudication_evidence],
            "tool_trace": [adjudication_trace],
        }
        adjudication["artifact_sha256"] = _artifact_sha256(adjudication)

    qa_provider = "mock_provider_a" if same_model else "mock_provider_b"
    qa_model = "mock_model_a" if same_model else "mock_model_b"
    qa_evidence, qa_trace = _build_evidence("ai_qa_auditor", dataset, provider)
    failure: JsonObject | None = None
    qa_decision = "pass"
    machine_state = "inconclusive"
    if scenario == "timeout":
        failure = {
            "code": "provider_timeout",
            "retryable": True,
            "detail": "The replayed provider exceeded its role deadline.",
        }
        qa_decision = "inconclusive"
        machine_state = "inconclusive"
    elif scenario == "budget_exceeded":
        failure = {
            "code": "budget_exceeded",
            "retryable": False,
            "detail": "The configured mock tool budget was exhausted.",
        }
        qa_decision = "inconclusive"
        machine_state = "inconclusive"
    elif scenario == "abstain":
        failure = {
            "code": "review_inconclusive",
            "retryable": True,
            "detail": "At least one subject finding abstained.",
        }
        qa_decision = "inconclusive"
        machine_state = "inconclusive"
    elif scenario in {"accept", "dispute"}:
        failure = {
            "code": "review_inconclusive",
            "retryable": False,
            "detail": (
                "Deterministic mock replay validates contracts but does not establish subject "
                "evidence for a product-eligible machine review."
            ),
        }
        qa_decision = "inconclusive"

    qa: JsonObject = {
        "schema_version": "ai-qa-report.v2",
        "provenance": _provenance("ai_qa_auditor", policy, provider=qa_provider, model_id=qa_model),
        "input_manifest": deepcopy(manifest),
        "subject_artifact_sha256": subject["artifact_sha256"],
        "adjudication_artifact_sha256": (
            adjudication["artifact_sha256"] if adjudication is not None else None
        ),
        "decision": qa_decision,
        "mechanical_checks": {
            "dataset_binding": True,
            "coverage_30_40_50": True,
            "artifact_binding": True,
            "tool_policy": True,
            "evidence_replay": True,
        },
        "evidence_ledger": qa_evidence,
        "tool_trace": qa_trace,
    }
    qa["artifact_sha256"] = _artifact_sha256(qa)

    shared_provider = (
        cast(JsonObject, subject["provenance"])["provider"]
        == cast(JsonObject, qa["provenance"])["provider"]
    )
    shared_model = (
        cast(JsonObject, subject["provenance"])["model_id"]
        == cast(JsonObject, qa["provenance"])["model_id"]
    )
    return {
        "schema_version": "calculus-machine-review.v2",
        "review_id": "calculus-v1-machine-review-mock",
        "machine_state": machine_state,
        "assurance": {
            "execution_mode": "deterministic_mock_replay",
            "evidence_basis": "first_party_page_replay",
            "subject_evidence_established": False,
            "product_eligible": False,
        },
        "input_manifest": manifest,
        "correlation": {
            "classification": (
                "correlated_review" if shared_provider or shared_model else "independent_review"
            ),
            "shared_provider": shared_provider,
            "shared_model": shared_model,
        },
        "subject_artifact": subject,
        "adjudication_artifact": adjudication,
        "qa_artifact": qa,
        "failure": failure,
        "owner_risk_acceptance": None,
    }


def _validate_schema(root: Path, review: JsonObject) -> None:
    schema = _load_object(root / SCHEMA_PATH)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(review), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise MachineReviewValidationError(f"machine-review.json:{location}: {first.message}")


def _assert_provenance(role: str, artifact: JsonObject, policy: JsonObject) -> JsonObject:
    provenance = cast(JsonObject, artifact["provenance"])
    if provenance.get("role_id") != role:
        raise MachineReviewValidationError(f"{role}: provenance role mismatch")
    role_policy = cast(JsonObject, cast(JsonObject, policy["roles"])[role])
    for provenance_field, policy_field in (
        ("prompt", "prompt_version"),
        ("context", "context_version"),
    ):
        value = cast(JsonObject, provenance[provenance_field])
        expected_version = role_policy[policy_field]
        hash_payload: JsonObject
        if provenance_field == "prompt":
            hash_payload = {
                "version": expected_version,
                "text": role_policy["prompt_text"],
            }
        else:
            hash_payload = {
                "version": expected_version,
                "scope": role_policy["context_scope"],
            }
        if value.get("version") != expected_version or value.get("sha256") != _sha256(hash_payload):
            raise MachineReviewValidationError(f"{role}: {provenance_field} version/hash mismatch")
    for provenance_field in ("tool_policy", "harness"):
        value = cast(JsonObject, provenance[provenance_field])
        if value.get("sha256") != _sha256(value.get("version")):
            raise MachineReviewValidationError(f"{role}: {provenance_field} sha256 mismatch")
    if cast(JsonObject, provenance["harness"])["version"] != HARNESS_VERSION:
        raise MachineReviewValidationError(f"{role}: harness version mismatch")
    return provenance


def _validate_tool_trace(role: str, artifact: JsonObject, policy: JsonObject) -> None:
    allowed = set(
        cast(
            list[str],
            cast(JsonObject, cast(JsonObject, policy["roles"])[role])["allowed_tools"],
        )
    )
    trace = cast(list[JsonObject], artifact["tool_trace"])
    limit = cast(int, policy["max_tool_calls_per_role"])
    if len(trace) > limit:
        raise MachineReviewValidationError(
            f"{role}: tool budget exceeded", code="review_tool_denied"
        )
    call_ids: set[str] = set()
    for call in trace:
        if call["tool_id"] not in allowed:
            raise MachineReviewValidationError(
                f"{role}: tool not allowed: {call['tool_id']}", code="review_tool_denied"
            )
        if call["call_id"] in call_ids:
            raise MachineReviewValidationError(
                f"{role}: duplicate tool call: {call['call_id']}", code="review_tool_denied"
            )
        call_ids.add(cast(str, call["call_id"]))


def _validate_evidence(
    role: str,
    artifact: JsonObject,
    provider: ReplaySearchProvider,
) -> None:
    evidence_ids: set[str] = set()
    for evidence in cast(list[JsonObject], artifact["evidence_ledger"]):
        evidence_id = cast(str, evidence["evidence_id"])
        if evidence_id in evidence_ids:
            raise MachineReviewValidationError(
                f"{role}: duplicate evidence id: {evidence_id}", code="review_evidence_invalid"
            )
        evidence_ids.add(evidence_id)
        if evidence["untrusted_instructions_detected"] and not evidence["instructions_ignored"]:
            raise MachineReviewValidationError(
                f"{role}: untrusted source instructions influenced the review",
                code="prompt_injection_suspected",
            )
        if not provider.verify(evidence):
            raise MachineReviewValidationError(
                f"{role}: replay evidence mismatch: {evidence_id}",
                code="review_evidence_invalid",
            )


def _validate_findings(
    subject: JsonObject,
    dataset: JsonObject,
    policy: JsonObject,
) -> None:
    expected = {(item_kind, cast(str, item["id"])) for item_kind, item in _dataset_items(dataset)}
    findings = cast(list[JsonObject], subject["findings"])
    actual = {(cast(str, item["item_kind"]), cast(str, item["item_id"])) for item in findings}
    if actual != expected or len(findings) != len(expected):
        raise MachineReviewValidationError("subject finding coverage mismatch")
    evidence_by_id = {
        cast(str, item["evidence_id"]): item
        for item in cast(list[JsonObject], subject["evidence_ledger"])
    }
    threshold = cast(float, policy["minimum_accept_confidence"])
    for finding in findings:
        if finding["decision"] == "accept":
            if not finding["evidence_ids"]:
                raise MachineReviewValidationError(
                    f"accept requires evidence: {finding['claim_id']}",
                    code="review_evidence_invalid",
                )
            if cast(float, finding["confidence"]) < threshold:
                raise MachineReviewValidationError(
                    f"accept confidence below policy threshold: {finding['claim_id']}",
                    code="review_evidence_invalid",
                )
        referenced = set(cast(list[str], finding["evidence_ids"])) | set(
            cast(list[str], finding["counterevidence_ids"])
        )
        if not referenced.issubset(evidence_by_id):
            raise MachineReviewValidationError(
                f"finding references unknown evidence: {finding['claim_id']}",
                code="review_evidence_invalid",
            )
        for evidence_id in cast(list[str], finding["evidence_ids"]):
            evidence = evidence_by_id[evidence_id]
            if evidence["claim_id"] != finding["claim_id"]:
                raise MachineReviewValidationError(
                    f"evidence claim binding mismatch: {finding['claim_id']}/{evidence_id}",
                    code="review_evidence_invalid",
                )
            if evidence["position"] != "support":
                raise MachineReviewValidationError(
                    f"support evidence has incorrect position: {finding['claim_id']}/{evidence_id}",
                    code="review_evidence_invalid",
                )
        for evidence_id in cast(list[str], finding["counterevidence_ids"]):
            evidence = evidence_by_id[evidence_id]
            if evidence["claim_id"] != finding["claim_id"]:
                raise MachineReviewValidationError(
                    f"counterevidence claim binding mismatch: {finding['claim_id']}/{evidence_id}",
                    code="review_evidence_invalid",
                )
            if evidence["position"] != "counterevidence":
                raise MachineReviewValidationError(
                    f"counterevidence has incorrect position: {finding['claim_id']}/{evidence_id}",
                    code="review_evidence_invalid",
                )


def _validate_artifact_hash(label: str, artifact: JsonObject) -> None:
    actual = _artifact_sha256(artifact)
    if artifact.get("artifact_sha256") != actual:
        raise MachineReviewValidationError(f"{label} artifact sha256 mismatch")


def _validate_owner_acceptance(
    review: JsonObject,
    policy: JsonObject,
    manifest: JsonObject,
) -> None:
    acceptance = review.get("owner_risk_acceptance")
    if acceptance is None:
        if review["machine_state"] == "accepted_with_owner_risk":
            raise MachineReviewValidationError("owner risk state requires an acceptance artifact")
        return
    acceptance = cast(JsonObject, acceptance)
    hard = set(cast(list[str], policy["hard_invariants"]))
    risks = set(cast(list[str], acceptance["risk_codes"]))
    if risks & hard:
        raise MachineReviewValidationError(
            f"owner risk acceptance cannot waive hard invariant: {sorted(risks & hard)}"
        )
    waivable = set(cast(list[str], policy["waivable_risk_codes"]))
    if not risks.issubset(waivable):
        raise MachineReviewValidationError(
            f"owner risk acceptance contains non-waivable risk: {sorted(risks - waivable)}"
        )
    if acceptance["content_sha256"] != manifest["dataset_sha256"]:
        raise MachineReviewValidationError("owner risk acceptance content hash mismatch")
    if acceptance["policy_sha256"] != manifest["policy_sha256"]:
        raise MachineReviewValidationError("owner risk acceptance policy hash mismatch")
    accepted_at = datetime.fromisoformat(cast(str, acceptance["accepted_at"]))
    expires_at = datetime.fromisoformat(cast(str, acceptance["expires_at"]))
    if expires_at <= accepted_at:
        raise MachineReviewValidationError("owner risk acceptance must expire after acceptance")
    if review["machine_state"] != "accepted_with_owner_risk":
        raise MachineReviewValidationError(
            "owner risk acceptance requires accepted_with_owner_risk state"
        )


def validate_machine_review(
    root: Path,
    review: JsonObject,
    dataset: JsonObject,
    policy: JsonObject,
    provider: ReplaySearchProvider,
) -> None:
    """Validate schema, provenance, isolation, evidence, tools, state, and hashes."""

    _validate_schema(root, review)
    expected_manifest = _input_manifest(dataset, policy)
    manifest = cast(JsonObject, review["input_manifest"])
    if manifest.get("dataset_sha256") != expected_manifest["dataset_sha256"]:
        raise MachineReviewValidationError(
            "review dataset input drifted", code="review_input_drifted"
        )
    if manifest != expected_manifest:
        raise MachineReviewValidationError("review input manifest mismatch")

    subject = cast(JsonObject, review["subject_artifact"])
    qa = cast(JsonObject, review["qa_artifact"])
    for label, artifact in (("subject", subject), ("QA", qa)):
        if artifact["input_manifest"] != manifest:
            raise MachineReviewValidationError(f"{label} input manifest mismatch")
    raw_subject_provenance = cast(JsonObject, subject["provenance"])
    raw_qa_provenance = cast(JsonObject, qa["provenance"])
    if raw_subject_provenance.get("prompt") == raw_qa_provenance.get("prompt"):
        raise MachineReviewValidationError("subject and QA require distinct prompt")
    if raw_subject_provenance.get("context") == raw_qa_provenance.get("context"):
        raise MachineReviewValidationError("subject and QA require distinct context")
    subject_provenance = _assert_provenance("ai_subject_reviewer", subject, policy)
    qa_provenance = _assert_provenance("ai_qa_auditor", qa, policy)

    if subject_provenance["agent_run_id"] == qa_provenance["agent_run_id"]:
        raise MachineReviewValidationError("subject and QA require distinct agent_run_id")
    if subject_provenance["session_id"] == qa_provenance["session_id"]:
        raise MachineReviewValidationError("subject and QA cannot use a shared mutable session")
    if subject_provenance["prompt"] == qa_provenance["prompt"]:
        raise MachineReviewValidationError("subject and QA require distinct prompt")
    if subject_provenance["context"] == qa_provenance["context"]:
        raise MachineReviewValidationError("subject and QA require distinct context")

    shared_provider = subject_provenance["provider"] == qa_provenance["provider"]
    shared_model = subject_provenance["model_id"] == qa_provenance["model_id"]
    expected_classification = (
        "correlated_review" if shared_provider or shared_model else "independent_review"
    )
    correlation = cast(JsonObject, review["correlation"])
    if correlation != {
        "classification": expected_classification,
        "shared_provider": shared_provider,
        "shared_model": shared_model,
    }:
        raise MachineReviewValidationError("correlation classification mismatch")
    if review["machine_state"] == "machine_verified" and expected_classification != (
        "independent_review"
    ):
        raise MachineReviewValidationError(
            "machine_verified requires independent provider/model review"
        )
    assurance = cast(JsonObject, review["assurance"])
    if assurance["product_eligible"] and not assurance["subject_evidence_established"]:
        raise MachineReviewValidationError(
            "product eligibility requires established subject evidence"
        )
    if review["machine_state"] in {"machine_reviewed", "machine_verified"} and not (
        assurance["subject_evidence_established"] and assurance["product_eligible"]
    ):
        raise MachineReviewValidationError(
            "machine review states require established subject evidence and product eligibility"
        )
    if (
        review["machine_state"] == "accepted_with_owner_risk"
        and not assurance["subject_evidence_established"]
    ):
        raise MachineReviewValidationError(
            "owner risk acceptance cannot replace missing subject evidence"
        )
    if assurance["execution_mode"] == "deterministic_mock_replay":
        if assurance != {
            "execution_mode": "deterministic_mock_replay",
            "evidence_basis": "first_party_page_replay",
            "subject_evidence_established": False,
            "product_eligible": False,
        }:
            raise MachineReviewValidationError("mock-only assurance metadata is invalid")
        if review["machine_state"] != "inconclusive":
            raise MachineReviewValidationError(
                "mock-only subject evidence cannot produce a product-eligible machine state"
            )

    _validate_tool_trace("ai_subject_reviewer", subject, policy)
    _validate_tool_trace("ai_qa_auditor", qa, policy)
    _validate_evidence("ai_subject_reviewer", subject, provider)
    _validate_evidence("ai_qa_auditor", qa, provider)
    _validate_findings(subject, dataset, policy)
    _validate_artifact_hash("subject", subject)
    if qa["subject_artifact_sha256"] != subject["artifact_sha256"]:
        raise MachineReviewValidationError("QA subject artifact binding mismatch")

    disputes = [
        finding
        for finding in cast(list[JsonObject], subject["findings"])
        if finding["decision"] == "dispute"
    ]
    adjudication_value = review["adjudication_artifact"]
    if disputes:
        if not isinstance(adjudication_value, dict):
            raise MachineReviewValidationError("dispute requires adjudication artifact")
        adjudication = cast(JsonObject, adjudication_value)
        if adjudication["input_manifest"] != manifest:
            raise MachineReviewValidationError("adjudication input manifest mismatch")
        adjudication_provenance = _assert_provenance("ai_dispute_adjudicator", adjudication, policy)
        if adjudication_provenance["agent_run_id"] in {
            subject_provenance["agent_run_id"],
            qa_provenance["agent_run_id"],
        }:
            raise MachineReviewValidationError("adjudication requires a distinct agent run")
        if adjudication["subject_artifact_sha256"] != subject["artifact_sha256"]:
            raise MachineReviewValidationError("adjudication subject artifact binding mismatch")
        _validate_tool_trace("ai_dispute_adjudicator", adjudication, policy)
        _validate_evidence("ai_dispute_adjudicator", adjudication, provider)
        adjudication_evidence = {
            evidence["evidence_id"]: evidence
            for evidence in cast(list[JsonObject], adjudication["evidence_ledger"])
        }
        for resolution in cast(list[JsonObject], adjudication["resolutions"]):
            evidence_ids = set(cast(list[str], resolution["evidence_ids"]))
            counterevidence_ids = set(cast(list[str], resolution["counterevidence_ids"]))
            if not (evidence_ids | counterevidence_ids).issubset(adjudication_evidence):
                raise MachineReviewValidationError(
                    f"adjudication references unknown evidence: {resolution['claim_id']}"
                )
            for evidence_id in evidence_ids | counterevidence_ids:
                if adjudication_evidence[evidence_id]["claim_id"] != resolution["claim_id"]:
                    raise MachineReviewValidationError(
                        f"adjudication evidence claim binding mismatch: {resolution['claim_id']}"
                    )
            for evidence_id in evidence_ids:
                if adjudication_evidence[evidence_id]["position"] != "support":
                    raise MachineReviewValidationError(
                        f"adjudication support evidence has incorrect position: {evidence_id}"
                    )
            for evidence_id in counterevidence_ids:
                if adjudication_evidence[evidence_id]["position"] != "counterevidence":
                    raise MachineReviewValidationError(
                        f"adjudication counterevidence has incorrect position: {evidence_id}"
                    )
        resolved = {
            resolution["claim_id"]
            for resolution in cast(list[JsonObject], adjudication["resolutions"])
            if resolution["decision"] != "inconclusive"
        }
        expected_disputes = {finding["claim_id"] for finding in disputes}
        if resolved != expected_disputes:
            raise MachineReviewValidationError("unresolved dispute remains after adjudication")
        _validate_artifact_hash("adjudication", adjudication)
        if qa["adjudication_artifact_sha256"] != adjudication["artifact_sha256"]:
            raise MachineReviewValidationError("QA adjudication artifact binding mismatch")
    elif adjudication_value is not None or qa["adjudication_artifact_sha256"] is not None:
        raise MachineReviewValidationError("adjudication artifact exists without a dispute")

    _validate_artifact_hash("QA", qa)
    failure = review["failure"]
    subject_decisions = {
        finding["decision"] for finding in cast(list[JsonObject], subject["findings"])
    }
    if review["machine_state"] == "inconclusive":
        if failure is None or qa["decision"] != "inconclusive":
            raise MachineReviewValidationError(
                "inconclusive state requires a failure and inconclusive QA"
            )
    elif failure is not None:
        raise MachineReviewValidationError("passing machine state cannot retain a failure")
    elif subject_decisions - {"accept", "dispute"}:
        raise MachineReviewValidationError("non-final subject decision cannot pass machine review")
    elif qa["decision"] != "pass":
        raise MachineReviewValidationError("passing machine state requires QA pass")

    _validate_owner_acceptance(review, policy, manifest)
