import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace

import pytest

import pada3dacb.evaluation.concepts.report as report_module
from pada3dacb.evaluation.concepts.report import (
    ConceptEvaluationPlan,
    CooperativeReaderPolicy,
    CooperativeReadResult,
    PublicationBlocked,
    PublicationPathBudget,
    PublicationProbeResult,
    build_artifact_index,
    build_completion_manifest,
    commit_output,
    create_validated_publication_sibling,
    derive_publication_names,
    generate_concept_report,
    prepare_publication_transaction,
    probe_publication_operations,
    publish_validated_publication,
    read_cooperative_publication,
    recover_validated_publication,
    serialize_canonical_publication_identity,
    verify_completed_output,
)
from pada3dacb.evaluation.schemas import CheckpointPolicy, Direction, MethodId
from scripts import evaluate_concepts


@pytest.fixture
def plan():
    return ConceptEvaluationPlan(
        "evaluation-identity", "synthetic_test_only", (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,), (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        ("evaluation_manifest.json",),
    )


@pytest.fixture
def final(tmp_path):
    path = tmp_path / "canonical-output"
    path.write_bytes(b"old-final")
    return path


def _measured_budget(final, plan):
    return probe_publication_operations(
        final, plan, "reports/concepts/evaluation_manifest.json"
    ).budget


def prepare(final, plan, manifest_hash, budget=None, **kwargs):
    return prepare_publication_transaction(
        final, plan, "reports/concepts/evaluation_manifest.json", attempt=1,
        owner_token="owner", expected_manifest_hash=manifest_hash,
        budget=budget or _measured_budget(final, plan), **kwargs,
    )


def test_identity_and_grammar_are_canonical_and_collision_deterministic(tmp_path, plan):
    identity = serialize_canonical_publication_identity(
        plan, "reports/concepts/evaluation_manifest.json"
    )
    assert b"display_alias" not in identity
    assert b"C:\\foreign\\absolute" not in identity
    budget = _measured_budget(tmp_path / "canonical-output", plan)
    first = derive_publication_names(
        tmp_path / "canonical-output", plan,
        "reports/concepts/evaluation_manifest.json", attempt=35,
        existing_names=(), budget=budget,
    )
    second = derive_publication_names(
        tmp_path / "canonical-output", plan,
        "reports/concepts/evaluation_manifest.json", attempt=35,
        existing_names={first.sibling_path.name, first.journal_path.name}, budget=budget,
    )
    assert re.fullmatch(r"p3dco\.concept-output\.[a-z2-7]+\.z(?:\.c1)?\.tmp", first.sibling_path.name)
    assert second.collision_token == "1"
    assert second.sibling_path.name != first.sibling_path.name
    assert (tmp_path / "canonical-output").name == "canonical-output"
def test_budget_rejection_happens_before_any_mutation(tmp_path, plan, final):
    before = final.read_bytes()
    budget = PublicationPathBudget(
        verified_path_units=len(str(tmp_path).encode("utf-16-le")) // 2 + 1 + len(final.name),
        verified_component_units=12,
    )
    with pytest.raises(ValueError, match="budget"):
        prepare(final, plan, "a" * 64, budget=budget)
    assert final.read_bytes() == before
    assert tuple(tmp_path.iterdir()) == (final,)


@pytest.mark.parametrize("provider", [lambda size: b"x" * (size - 1), lambda size: None])
def test_short_or_unavailable_cs_prng_fails_before_mutation(tmp_path, plan, final, provider):
    with pytest.raises(ValueError, match="CSPRNG"):
        prepare(final, plan, "b" * 64, capability_provider=provider)
    assert final.read_bytes() == b"old-final"
    assert tuple(tmp_path.iterdir()) == (final,)


def test_exclusive_durable_prepared_journal_binds_transaction(tmp_path, plan, final):
    result = prepare(
        final, plan, "c" * 64,
        capability_provider=lambda size: bytes(range(size)),
    )
    payload = json.loads(result.journal_path.read_text())
    assert payload["state"] == "prepared"
    assert payload["capability_hex"] == bytes(range(32)).hex()
    assert payload["canonical_relative_path"] == "reports/concepts/evaluation_manifest.json"
    assert payload["sibling_name"] == result.sibling_path.name
    assert payload["owner_token"] == "owner"
    assert result.final_path.read_bytes() == b"old-final"
    with pytest.raises(FileExistsError):
        os.open(result.journal_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    if os.name != "nt":
        assert os.stat(result.journal_path).st_mode & 0o777 == 0o600


@pytest.fixture
def complete_candidate():
    plan = ConceptEvaluationPlan(
        "evaluation-identity", "synthetic_test_only", (MethodId.MMD,),
        (Direction.ADNI_TO_OASIS,), (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        ("artifact_index.json", "evaluation_manifest.json", "payload.txt"),
    )
    ordinary = {"payload.txt": b"candidate\n"}
    artifacts = {
        **ordinary,
        "artifact_index.json": build_artifact_index(ordinary),
    }
    artifacts["evaluation_manifest.json"] = build_completion_manifest(
        plan, ordinary, {}, {}, 1, 1, "percentile_95_linear",
        {"authorized_exports": False, "concept_normalizer": False,
         "atlas_hash": False, "protocol_approval": False},
        "1970-01-01T00:00:00Z", "1970-01-01T00:00:00Z",
    )
    return plan, artifacts


def prepare_complete(final, plan, artifacts):
    import hashlib

    return prepare(
        final, plan, hashlib.sha256(artifacts["evaluation_manifest.json"]).hexdigest(),
        capability_provider=lambda size: bytes(range(size)),
    )


def test_constructs_and_validates_sibling_before_any_rename(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    assert validated.sibling_path.is_dir()
    assert json.loads(validated.journal_path.read_text())["state"] == "validated"
    assert verify_completed_output(
        validated.sibling_path, expected_identity=plan.evaluation_identity
    )["evaluation_identity"] == plan.evaluation_identity
    assert final.read_bytes() == b"old-final"


def test_invalid_candidate_tree_is_rejected_before_state_promotion(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)

    def writer(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        if path.name == "payload.txt":
            (path.parent / "foreign.txt").write_bytes(b"foreign")

    with pytest.raises(ValueError, match="output"):
        create_validated_publication_sibling(prepared, plan, artifacts, writer=writer)
    assert json.loads(prepared.journal_path.read_text())["state"] == "aborted"
    assert (prepared.sibling_path / "foreign.txt").read_bytes() == b"foreign"
    assert final.read_bytes() == b"old-final"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("canonical_identity_sha256", "0" * 64),
        ("capability_hex", "00" * 32),
        ("attempt_token", "2"),
    ],
)
def test_exact_journal_identity_capability_and_token_mismatch_rejected(
    tmp_path, final, complete_candidate, field, value
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    journal = json.loads(prepared.journal_path.read_text())
    journal[field] = value
    prepared.journal_path.write_text(json.dumps(journal), encoding="utf-8")

    with pytest.raises(ValueError, match="journal"):
        create_validated_publication_sibling(prepared, plan, artifacts)
    assert not prepared.sibling_path.exists()
    assert final.read_bytes() == b"old-final"


def test_collision_ordinal_preserves_foreign_entry_and_final(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    first = derive_publication_names(
        final, plan, "reports/concepts/evaluation_manifest.json", attempt=1,
        existing_names=(), budget=_measured_budget(tmp_path / "canonical-output", plan),
    )
    (tmp_path / first.sibling_path.name).write_bytes(b"foreign")
    prepared = prepare_complete(final, plan, artifacts)

    assert prepared.sibling_path.name.endswith(".c1.tmp")
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    assert (tmp_path / first.sibling_path.name).read_bytes() == b"foreign"
    assert validated.sibling_path.is_dir()
    assert final.read_bytes() == b"old-final"


@pytest.mark.parametrize("failure", ["missing", "hash", "type"])
def test_missing_type_and_hash_divergence_stay_prepared(
    tmp_path, final, complete_candidate, failure
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)

    def writer(path, payload):
        if failure == "missing" and path.name == "payload.txt":
            return
        if failure == "type" and path.name == "payload.txt":
            path.mkdir(parents=True)
            return
        if failure == "hash" and path.name == "payload.txt":
            payload = b"tampered\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    with pytest.raises(ValueError, match="validation|output"):
        create_validated_publication_sibling(prepared, plan, artifacts, writer=writer)
    assert json.loads(prepared.journal_path.read_text())["state"] == "aborted"
    assert final.read_bytes() == b"old-final"


def test_volume_and_mode_binding_divergence_is_rejected_before_sibling(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    journal = json.loads(prepared.journal_path.read_text())
    journal["same_volume_file_identifiers"]["parent_device"] += 1
    journal["type_mode"]["final_mode"] += 1
    prepared.journal_path.write_text(json.dumps(journal), encoding="utf-8")

    with pytest.raises(ValueError, match="journal"):
        create_validated_publication_sibling(prepared, plan, artifacts)
    assert not prepared.sibling_path.exists()
    assert final.read_bytes() == b"old-final"


def _write_tree(root, artifacts):
    if root.is_file():
        root.unlink()
    root.mkdir()
    for relative_path, payload in artifacts.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def test_publisher_overwrites_only_an_exact_valid_final_and_cleans_authenticated_backup(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    result = publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0
    )

    assert result == final
    assert verify_completed_output(final, expected_identity=plan.evaluation_identity)
    assert (final / "payload.txt").read_bytes() == b"candidate\n"
    journal = json.loads(validated.journal_path.read_text())
    assert journal["state"] == "published"
    assert journal["backup_capability_hex"] == validated.capability.hex()
    assert journal["backup_file_identifiers"] == journal["backup_source_final_file_identifiers"]
    assert not validated.sibling_path.exists()
    assert not validated.names.backup_path.exists()



def test_second_publisher_preserves_first_result_when_both_prepared_against_absence(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    final.unlink()
    first = create_validated_publication_sibling(
        prepare_complete(final, plan, artifacts), plan, artifacts
    )
    second = create_validated_publication_sibling(
        prepare_complete(final, plan, artifacts), plan, artifacts
    )

    assert publish_validated_publication(
        first, plan, absent_window_timeout_seconds=1.0
    ) == final
    first_bytes = {
        path.relative_to(final): path.read_bytes()
        for path in final.rglob("*")
        if path.is_file()
    }

    with pytest.raises(PublicationBlocked, match="presence|authenticated|validation"):
        publish_validated_publication(
            second, plan, absent_window_timeout_seconds=1.0
        )

    assert final.is_dir()
    assert {
        path.relative_to(final): path.read_bytes()
        for path in final.rglob("*")
        if path.is_file()
    } == first_bytes
    assert second.sibling_path.is_dir()
    assert not second.names.backup_path.exists()


def test_explicit_overwrite_accepts_a_different_valid_evaluation_identity(
    tmp_path, complete_candidate
):
    old_plan, old_artifacts = complete_candidate
    output = tmp_path / "canonical-output"
    assert commit_output(output, old_plan, old_artifacts) == output

    new_plan = ConceptEvaluationPlan(
        "replacement-identity",
        old_plan.analysis_mode,
        old_plan.methods,
        old_plan.directions,
        old_plan.checkpoint_policies,
        old_plan.intended_relative_paths,
    )
    ordinary = {"payload.txt": b"replacement\n"}
    new_artifacts = {
        **ordinary,
        "artifact_index.json": build_artifact_index(ordinary),
    }
    new_artifacts["evaluation_manifest.json"] = build_completion_manifest(
        new_plan,
        ordinary,
        {},
        {},
        1,
        1,
        "percentile_95_linear",
        {
            "authorized_exports": False,
            "concept_normalizer": False,
            "atlas_hash": False,
            "protocol_approval": False,
        },
        "1970-01-01T00:00:00Z",
        "1970-01-01T00:00:00Z",
    )

    assert commit_output(
        output,
        new_plan,
        new_artifacts,
        overwrite=True,
        absent_window_timeout_seconds=1.0,
    ) == output
    assert verify_completed_output(
        output, expected_identity=new_plan.evaluation_identity
    )["evaluation_identity"] == new_plan.evaluation_identity
    assert (output / "payload.txt").read_bytes() == b"replacement\n"


def test_publishing_state_is_durable_before_sibling_promotion(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    observed = {}
    original_replace = os.replace

    def observe_promotion(source, destination):
        if Path(source) == validated.sibling_path and Path(destination) == final:
            observed["state"] = json.loads(
                validated.journal_path.read_text(encoding="utf-8")
            )["state"]
        original_replace(source, destination)

    assert publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0,
        replace=observe_promotion,
    ) == final
    assert observed == {"state": "publishing"}


def test_final_absent_persists_durable_publishing_before_sibling_promotion(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    shutil.rmtree(final)
    events = []
    original_write = report_module._write_validated_journal
    original_replace = os.replace

    def observe_journal(path, journal):
        original_write(path, journal)
        if Path(path) == validated.journal_path and journal["state"] == "publishing":
            events.append(("journal", json.loads(path.read_text())["state"]))

    def observe_promotion(source, destination):
        if Path(source) == validated.sibling_path and Path(destination) == final:
            events.append(("rename", json.loads(validated.journal_path.read_text())["state"]))
        original_replace(source, destination)

    monkeypatch.setattr(report_module, "_write_validated_journal", observe_journal)
    assert publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0,
        replace=observe_promotion,
    ) == final
    assert events == [("journal", "publishing"), ("rename", "publishing")]


def test_recovery_final_absent_persists_durable_publishing_before_sibling_promotion(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    final.unlink()
    events = []
    original_write = report_module._write_validated_journal
    original_replace = os.replace

    def observe_journal(path, journal):
        original_write(path, journal)
        if Path(path) == validated.journal_path and journal["state"] == "publishing":
            events.append(("journal", json.loads(path.read_text())["state"]))

    def observe_promotion(source, destination):
        if Path(source) == validated.sibling_path and Path(destination) == final:
            events.append(("rename", json.loads(validated.journal_path.read_text())["state"]))
        original_replace(source, destination)

    monkeypatch.setattr(report_module, "_write_validated_journal", observe_journal)
    assert recover_validated_publication(
        final, plan, "reports/concepts/evaluation_manifest.json",
        budget=_measured_budget(tmp_path / "canonical-output", plan),
        absent_window_timeout_seconds=1.0,
        replace=observe_promotion,
    ) == final
    assert events == [("journal", "publishing"), ("rename", "publishing")]


def test_publisher_preserves_foreign_final_when_rollback_would_relocate_it(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    foreign_source = tmp_path / "foreign-final"
    foreign_source.mkdir()
    (foreign_source / "foreign.txt").write_bytes(b"foreign")
    original_replace = os.replace

    def replace_with_foreign_final(source, destination):
        original_replace(source, destination)
        if Path(source) == validated.sibling_path and Path(destination) == final:
            shutil.rmtree(final)
            original_replace(foreign_source, final)

    with pytest.raises(PublicationBlocked, match="rollback|promotion") as error:
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0,
            replace=replace_with_foreign_final,
        )

    assert error.value.status == "BLOCKED"
    assert (final / "foreign.txt").read_bytes() == b"foreign"
    assert validated.names.backup_path.is_dir()
    assert not validated.sibling_path.exists()


def test_publisher_preserves_old_tree_when_promotion_fails_and_rollback_succeeds(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    before = {path.relative_to(final): path.read_bytes() for path in final.rglob("*") if path.is_file()}
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    def fail_promotion(source, destination):
        if Path(source) == validated.sibling_path and Path(destination) == final:
            raise OSError("injected promotion failure")
        os.replace(source, destination)

    with pytest.raises(PublicationBlocked, match="promotion") as error:
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0, replace=fail_promotion
        )

    assert error.value.status == "BLOCKED"
    assert {path.relative_to(final): path.read_bytes() for path in final.rglob("*") if path.is_file()} == before
    assert not validated.names.backup_path.exists()
    assert validated.sibling_path.is_dir()


def test_publisher_preserves_backup_and_candidate_when_rollback_fails(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    calls = []

    def fail_promotion_and_rollback(source, destination):
        calls.append((Path(source), Path(destination)))
        if Path(destination) == final:
            raise OSError("injected promotion or rollback failure")
        os.replace(source, destination)

    with pytest.raises(PublicationBlocked, match="rollback") as error:
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0,
            replace=fail_promotion_and_rollback,
        )

    assert error.value.status == "BLOCKED"
    assert validated.names.backup_path.is_dir()
    assert validated.sibling_path.is_dir()
    assert not final.exists()
    assert len(calls) >= 2


def test_absent_window_includes_durable_journal_transition(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    now = [0.0]
    original = report_module._record_authenticated_backup_after_rename

    def delayed_journal_transition(publication, journal):
        updated = original(publication, journal)
        now[0] = 2.0
        return updated

    monkeypatch.setattr(
        report_module,
        "_record_authenticated_backup_after_rename",
        delayed_journal_transition,
    )
    with pytest.raises(PublicationBlocked, match="absent window"):
        publish_validated_publication(
            validated,
            plan,
            absent_window_timeout_seconds=1.0,
            clock=lambda: now[0],
        )

    assert final.is_dir()
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()


def test_publisher_timeout_rolls_back_old_tree(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    ticks = iter((10.0, 10.5))

    with pytest.raises(PublicationBlocked, match="absent window") as error:
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=0.1,
            clock=lambda: next(ticks),
        )

    assert error.value.status == "BLOCKED"
    assert final.is_dir()
    assert not validated.names.backup_path.exists()
    assert validated.sibling_path.is_dir()


def test_publisher_does_not_mutate_final_before_promotion(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    before = {path.relative_to(final): path.read_bytes() for path in final.rglob("*") if path.is_file()}
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    assert {path.relative_to(final): path.read_bytes() for path in final.rglob("*") if path.is_file()} == before
    assert final.is_dir()
    assert validated.sibling_path.is_dir()


def test_publisher_rejects_an_invalid_existing_final_without_mutation(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    before = final.read_bytes()

    with pytest.raises(PublicationBlocked, match="invalid"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0
        )

    assert final.read_bytes() == before
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()


def test_publisher_requires_an_explicit_absent_window_policy(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    with pytest.raises(PublicationBlocked, match="policy"):
        publish_validated_publication(validated, plan, absent_window_timeout_seconds=None)

    assert final.is_dir()
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()




def test_recovery_blocks_candidate_mode_mismatch_and_preserves_transaction(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    journal = json.loads(validated.journal_path.read_text())
    journal["type_mode"]["candidate_mode"] += 1
    validated.journal_path.write_text(json.dumps(journal), encoding="utf-8")
    final.unlink()
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()
    journal_before = validated.journal_path.read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert not final.exists()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before
    assert validated.journal_path.read_bytes() == journal_before


def test_recovers_an_authenticated_validated_sibling_when_final_is_absent(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    journal = json.loads(validated.journal_path.read_text())
    assert journal["type_mode"]["candidate_mode"] == validated.sibling_path.stat().st_mode
    final.unlink()

    result = recover_validated_publication(
        final, plan, "reports/concepts/evaluation_manifest.json",
        budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
    )

    assert result == final
    assert verify_completed_output(final, expected_identity=plan.evaluation_identity)
    assert not validated.sibling_path.exists()


def test_recovery_blocks_missing_capability_field_without_mutation(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    journal = json.loads(validated.journal_path.read_text())
    del journal["capability_hex"]
    validated.journal_path.write_text(json.dumps(journal), encoding="utf-8")
    final.unlink()
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan),
            absent_window_timeout_seconds=1.0,
        )

    assert not final.exists()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before


def test_recovery_blocks_exact_grammar_foreign_directory_without_journal(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    foreign = prepared.sibling_path
    prepared.journal_path.unlink()
    foreign.mkdir()
    final.unlink()

    with pytest.raises(PublicationBlocked, match="journal|authenticated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan),
            absent_window_timeout_seconds=1.0,
        )

    assert foreign.is_dir()
    assert not (tmp_path / f".{foreign.name}.journal").exists()
    assert not final.exists()


def test_recovery_leaves_a_valid_final_untouched_and_does_not_promote_sibling(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    before = {path.relative_to(final): path.read_bytes() for path in final.rglob("*") if path.is_file()}

    result = recover_validated_publication(
        final, plan, "reports/concepts/evaluation_manifest.json",
        budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
    )

    assert result == final
    assert {path.relative_to(final): path.read_bytes() for path in final.rglob("*") if path.is_file()} == before
    assert validated.sibling_path.is_dir()
    assert json.loads(validated.journal_path.read_text())["state"] == "validated"


@pytest.mark.parametrize("state", ["prepared", "publishing", "published", "aborted"])
def test_recovery_blocks_non_validated_journal_states(
    tmp_path, final, complete_candidate, state
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    journal = json.loads(validated.journal_path.read_text())
    journal["state"] = state
    validated.journal_path.write_text(json.dumps(journal), encoding="utf-8")
    final.unlink()
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()
    journal_before = validated.journal_path.read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated|validated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert not final.exists()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before
    assert validated.journal_path.read_bytes() == journal_before


@pytest.mark.parametrize(
    ("field", "mutator"),
    [
        ("canonical_identity_sha256", lambda journal: "0" * 64),
        ("canonical_relative_path", lambda journal: "reports/foreign/evaluation_manifest.json"),
        ("attempt_token", lambda journal: "2"),
        ("capability_hex", lambda journal: "00" * 31),
        ("expected_manifest_hash", lambda journal: "0" * 64),
        ("same_volume_file_identifiers", lambda journal: {"parent_device": -1, "final_device": -1}),
        ("type_mode", lambda journal: {"expected_type": "file", "final_mode": 0}),
    ],
)
def test_recovery_preserves_sibling_and_journal_on_provenance_mismatch(
    tmp_path, final, complete_candidate, field, mutator
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    journal = json.loads(validated.journal_path.read_text())
    journal[field] = mutator(journal)
    validated.journal_path.write_text(json.dumps(journal), encoding="utf-8")
    final.unlink()
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()
    journal_before = validated.journal_path.read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated") as error:
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert error.value.status == "BLOCKED"
    assert not final.exists()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before
    assert validated.journal_path.read_bytes() == journal_before


def test_recovery_blocks_truncated_journal_and_manifest_mismatch_without_mutation(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    validated.journal_path.write_bytes(validated.journal_path.read_bytes()[:10])
    final.unlink()
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert not final.exists()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before

    second_parent = tmp_path / "second"
    second_parent.mkdir()
    second_final = second_parent / "canonical-output"
    prepared = prepare_complete(second_final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    (validated.sibling_path / "payload.txt").write_bytes(b"foreign")
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            second_final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert not second_final.exists()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before


def test_recovery_rejects_reparse_candidate_when_junction_api_is_unavailable(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    final.unlink()
    original_lstat = os.lstat

    def lstat_with_reparse_attribute(path):
        result = original_lstat(path)
        if Path(path) == validated.sibling_path:
            return SimpleNamespace(st_mode=result.st_mode, st_file_attributes=0x400)
        return result

    monkeypatch.delattr(report_module.Path, "is_junction", raising=False)
    monkeypatch.setattr(report_module.os, "name", "nt")
    monkeypatch.setattr(report_module.os, "lstat", lstat_with_reparse_attribute)
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert not final.exists()
    assert validated.sibling_path.is_dir()
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before


def test_recovery_rejects_copied_candidate_and_journal_pair(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    copied_parent = tmp_path / "copied-parent"
    copied_parent.mkdir()
    copied_final = copied_parent / "canonical-output"
    copied_sibling = copied_parent / validated.sibling_path.name
    copied_journal = copied_parent / validated.journal_path.name
    shutil.copytree(validated.sibling_path, copied_sibling)
    shutil.copy2(validated.journal_path, copied_journal)
    sibling_before = (copied_sibling / "payload.txt").read_bytes()
    journal_before = copied_journal.read_bytes()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            copied_final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert not copied_final.exists()
    assert copied_sibling.is_dir()
    assert (copied_sibling / "payload.txt").read_bytes() == sibling_before
    assert copied_journal.read_bytes() == journal_before
    assert validated.sibling_path.is_dir()
    assert validated.journal_path.is_file()


def test_recovery_preserves_case_variant_lookalike_entries_and_surfaces_block(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    variant = validated.sibling_path.with_name(validated.sibling_path.name.upper())
    try:
        variant.mkdir()
    except FileExistsError:
        pytest.skip("case-variant candidate aliases the exact name on this filesystem")
    final.unlink()

    with pytest.raises(PublicationBlocked, match="look-alike|foreign"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert variant.is_dir()
    assert validated.sibling_path.is_dir()
    assert not final.exists()


def test_recovery_preserves_foreign_lookalike_entries_and_surfaces_block(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    foreign = validated.sibling_path.with_name(validated.sibling_path.name + ".copy")
    foreign.write_bytes(b"foreign")
    final.unlink()
    foreign_before = foreign.read_bytes()

    with pytest.raises(PublicationBlocked, match="look-alike|foreign"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert foreign.read_bytes() == foreign_before
    assert validated.sibling_path.is_dir()
    assert not final.exists()


def test_recovery_preserves_symlink_candidate_and_blocks(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    held = tmp_path / "held-sibling"
    validated.sibling_path.rename(held)
    try:
        validated.sibling_path.symlink_to(held, target_is_directory=True)
    except (OSError, NotImplementedError):
        held.rename(validated.sibling_path)
        pytest.skip("directory symlinks are unavailable")
    final.unlink()

    with pytest.raises(PublicationBlocked, match="authenticated"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert validated.sibling_path.is_symlink()
    assert held.is_dir()
    assert not final.exists()


def test_recovery_rejects_invalid_final_without_touching_validated_sibling(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    final.write_bytes(b"invalid-final")
    sibling_before = (validated.sibling_path / "payload.txt").read_bytes()

    with pytest.raises(PublicationBlocked, match="invalid"):
        recover_validated_publication(
            final, plan, "reports/concepts/evaluation_manifest.json",
            budget=_measured_budget(tmp_path / "canonical-output", plan), absent_window_timeout_seconds=1.0,
        )

    assert final.read_bytes() == b"invalid-final"
    assert (validated.sibling_path / "payload.txt").read_bytes() == sibling_before


def test_publisher_preserves_foreign_backup_entry(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    foreign = validated.names.backup_path
    foreign.write_bytes(b"foreign")

    with pytest.raises(PublicationBlocked, match="backup"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0
        )

    assert foreign.read_bytes() == b"foreign"
    assert final.is_dir()
    assert validated.sibling_path.is_dir()


def test_authenticated_cleanup_never_reaches_legacy_remover(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    monkeypatch.setattr(
        report_module,
        "_remove_controlled_entry",
        lambda *args, **kwargs: pytest.fail("legacy remover reached active publication route"),
    )

    assert publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0
    ) == final
    assert not validated.names.backup_path.exists()


def test_backup_replacement_after_rename_blocks_and_preserves_foreign_tree(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    replacement = tmp_path / "foreign-backup-copy"

    def replace_and_copy(source, destination):
        os.replace(source, destination)
        if Path(destination) == validated.names.backup_path:
            shutil.copytree(destination, replacement)
            shutil.rmtree(destination)
            shutil.copytree(replacement, destination)

    with pytest.raises(PublicationBlocked, match="rollback|promotion"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0,
            replace=replace_and_copy,
        )

    assert replacement.is_dir()
    assert validated.names.backup_path.is_dir()
    assert (replacement / "payload.txt").read_bytes() == b"candidate\n"
    assert validated.sibling_path.is_dir()
    assert not final.exists()


def test_backup_capability_mismatch_blocks_authenticated_cleanup_and_rollback(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    original = report_module._record_authenticated_backup_after_rename

    def tamper_backup_capability(publication, journal):
        updated = original(publication, journal)
        updated["backup_capability_hex"] = "00" * 32
        return updated

    monkeypatch.setattr(
        report_module,
        "_record_authenticated_backup_after_rename",
        tamper_backup_capability,
    )

    with pytest.raises(PublicationBlocked, match="rollback"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0,
        )

    assert final.is_dir()
    assert not validated.sibling_path.exists()
    assert validated.names.backup_path.is_dir()


def test_parent_durability_failure_blocks_prepared_journal(
    tmp_path, final, plan, monkeypatch
):
    monkeypatch.setattr(
        report_module,
        "_durable_parent_directory",
        lambda path: (_ for _ in ()).throw(OSError("injected directory flush failure")),
    )

    with pytest.raises(OSError, match="directory flush"):
        prepare(
            final, plan, "a" * 64,
            capability_provider=lambda size: bytes(range(size)),
        )
    assert final.read_bytes() == b"old-final"


def test_acl_failure_blocks_before_candidate_creation(tmp_path, final, plan, monkeypatch):
    monkeypatch.setattr(
        report_module,
        "_ensure_owner_only_acl",
        lambda path: (_ for _ in ()).throw(OSError("injected ACL failure")),
    )

    with pytest.raises(OSError, match="ACL"):
        prepare(
            final, plan, "b" * 64,
            capability_provider=lambda size: bytes(range(size)),
        )
    assert final.read_bytes() == b"old-final"


def test_final_durability_failure_rolls_back_and_marks_aborted(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    calls = 0
    original = report_module._durable_tree

    def fail_final_tree(path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected final durability failure")
        return original(path)

    monkeypatch.setattr(report_module, "_durable_tree", fail_final_tree)
    with pytest.raises(PublicationBlocked, match="promotion|rollback"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0,
        )

    assert calls >= 2
    assert final.is_dir()
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()
    assert json.loads(validated.journal_path.read_text())["state"] == "aborted"


def test_cooperative_reader_and_publisher_locks_are_cross_thread_exclusive(tmp_path):
    reader_entered = Event()
    release_reader = Event()

    def hold_reader():
        with report_module._reader_lock(tmp_path, "canonical-output"):
            reader_entered.set()
            release_reader.wait(timeout=2)

    reader = Thread(target=hold_reader)
    reader.start()
    assert reader_entered.wait(timeout=2)

    publisher_entered = Event()

    def hold_publisher():
        with report_module._publisher_lock(tmp_path, "canonical-output"):
            publisher_entered.set()

    publisher = Thread(target=hold_publisher)
    publisher.start()
    assert not publisher_entered.wait(timeout=0.1)
    release_reader.set()
    publisher.join(timeout=2)
    reader.join(timeout=2)
    assert publisher_entered.is_set()
    assert not publisher.is_alive()
    assert not reader.is_alive()

    publisher_release = Event()
    publisher_entered.clear()

    def hold_publisher_again():
        with report_module._publisher_lock(tmp_path, "canonical-output"):
            publisher_entered.set()
            publisher_release.wait(timeout=2)

    publisher = Thread(target=hold_publisher_again)
    publisher.start()
    assert publisher_entered.wait(timeout=2)
    reader_entered.clear()

    def acquire_reader_again():
        with report_module._reader_lock(tmp_path, "canonical-output"):
            reader_entered.set()

    reader = Thread(target=acquire_reader_again)
    reader.start()
    assert not reader_entered.wait(timeout=0.1)
    publisher_release.set()
    publisher.join(timeout=2)
    reader.join(timeout=2)
    assert reader_entered.is_set()
    assert not publisher.is_alive()
    assert not reader.is_alive()


def test_cooperative_reader_retries_absence_then_reads_only_final(tmp_path):
    final = tmp_path / "canonical-output"
    policy = CooperativeReaderPolicy(max_attempts=3, delay_seconds=0)
    sleeps = []

    def sleep(delay):
        sleeps.append(delay)
        if len(sleeps) == 1:
            final.write_bytes(b"new")

    result = read_cooperative_publication(
        final, policy=policy, reader=lambda path: path.read_bytes(), sleep=sleep
    )

    assert isinstance(result, CooperativeReadResult)
    assert result.status == "available"
    assert result.value == b"new"
    assert result.attempts == 2
    assert sleeps == [0]


def test_cooperative_reader_returns_unavailable_after_bounded_absence(tmp_path):
    final = tmp_path / "canonical-output"
    sibling = tmp_path / "p3dco.concept-output.foreign.tmp"
    backup = tmp_path / ".canonical-output.backup.foreign"
    sibling.write_bytes(b"must-not-read")
    backup.write_bytes(b"must-not-read")
    result = read_cooperative_publication(
        final,
        policy=CooperativeReaderPolicy(max_attempts=2, delay_seconds=0),
        reader=lambda path: path.read_bytes(),
        sleep=lambda delay: None,
    )

    assert result.status == "unavailable"
    assert result.value is None
    assert result.attempts == 2
    assert result.final_path == final
    assert result.reason == "canonical_final_absent"


def test_cooperative_reader_never_enumerates_siblings_or_backups(tmp_path, monkeypatch):
    final = tmp_path / "canonical-output"
    sibling = tmp_path / "p3dco.concept-output.foreign.tmp"
    backup = tmp_path / ".canonical-output.backup.foreign"
    sibling.write_bytes(b"sibling")
    backup.write_bytes(b"backup")

    def forbidden_enumeration(self):
        raise AssertionError("reader must not inspect sibling or backup entries")

    monkeypatch.setattr(Path, "iterdir", forbidden_enumeration)
    result = read_cooperative_publication(
        final,
        policy=CooperativeReaderPolicy(max_attempts=1, delay_seconds=0),
        reader=lambda path: path.read_bytes(),
        sleep=lambda delay: None,
    )

    assert result.status == "unavailable"


@pytest.mark.parametrize("failure", ["set", "query", "verify"])
def test_windows_journal_acl_failure_blocks_before_contents(
    tmp_path, final, plan, monkeypatch, failure
):
    monkeypatch.setattr(report_module.os, "name", "nt")
    if failure == "set":
        monkeypatch.setattr(
            report_module,
            "_windows_create_owner_only_file",
            lambda path: (_ for _ in ()).throw(OSError("injected ACL set failure")),
        )
    elif failure == "query":
        monkeypatch.setattr(
            report_module,
            "_windows_query_owner_only_acl",
            lambda path: (_ for _ in ()).throw(OSError("injected ACL query failure")),
        )
    else:
        monkeypatch.setattr(
            report_module,
            "_verify_owner_only_acl",
            lambda path: (_ for _ in ()).throw(OSError("injected ACL verification failure")),
        )
    names = derive_publication_names(
        final, plan, "reports/concepts/evaluation_manifest.json", attempt=1,
        existing_names=(), budget=_measured_budget(tmp_path / "canonical-output", plan),
    )

    with pytest.raises(PublicationBlocked, match="ACL"):
        prepare(
            final, plan, "a" * 64,
            capability_provider=lambda size: bytes(range(size)),
        )

    if failure == "set":
        assert not names.journal_path.exists()
    else:
        assert names.journal_path.is_file()
        assert names.journal_path.read_bytes() == b""
    assert final.read_bytes() == b"old-final"


def test_publisher_rejects_acl_alteration_before_candidate_validation(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    original = report_module._verify_owner_only_acl

    def reject_altered_acl(path):
        if Path(path) == validated.sibling_path:
            raise OSError("candidate ACL was altered")
        return original(path)

    monkeypatch.setattr(report_module, "_verify_owner_only_acl", reject_altered_acl)
    with pytest.raises(PublicationBlocked, match="ACL|authenticated"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0
        )

    assert final.is_dir()
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()


@pytest.mark.parametrize("boundary", ["journal", "candidate", "parent"])
def test_durability_boundary_failure_preserves_transaction_evidence(
    tmp_path, final, complete_candidate, monkeypatch, boundary
):
    plan, artifacts = complete_candidate
    prepared = prepare_complete(final, plan, artifacts)
    if boundary == "journal":
        original = report_module._durable_file
        monkeypatch.setattr(
            report_module,
            "_durable_file",
            lambda path: (_ for _ in ()).throw(OSError("injected journal flush failure"))
            if Path(path) == prepared.journal_path else original(path),
        )
        with pytest.raises(PublicationBlocked, match="journal|durability"):
            create_validated_publication_sibling(prepared, plan, artifacts)
        assert prepared.journal_path.is_file()
        assert prepared.journal_path.read_bytes()
        assert prepared.sibling_path.is_dir()
    elif boundary == "candidate":
        original = report_module._durable_tree
        monkeypatch.setattr(
            report_module,
            "_durable_tree",
            lambda path: (_ for _ in ()).throw(OSError("injected candidate flush failure"))
            if Path(path) == prepared.sibling_path else original(path),
        )
        with pytest.raises(PublicationBlocked, match="candidate|durability"):
            create_validated_publication_sibling(prepared, plan, artifacts)
        assert prepared.sibling_path.is_dir()
        assert json.loads(prepared.journal_path.read_text())["state"] == "aborted"
    else:
        original = report_module._durable_parent_directory
        monkeypatch.setattr(
            report_module,
            "_durable_parent_directory",
            lambda path: (_ for _ in ()).throw(OSError("injected parent flush failure"))
            if Path(path) == prepared.final_path.parent else original(path),
        )
        with pytest.raises(PublicationBlocked, match="parent|durability"):
            create_validated_publication_sibling(prepared, plan, artifacts)
        assert prepared.journal_path.is_file()
        assert prepared.journal_path.read_bytes()
        assert prepared.sibling_path.is_dir()


def test_backup_durability_failure_blocks_and_preserves_evidence(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    original = report_module._durable_tree

    monkeypatch.setattr(
        report_module,
        "_durable_tree",
        lambda path: (_ for _ in ()).throw(OSError("injected backup flush failure"))
        if Path(path) == validated.names.backup_path else original(path),
    )

    with pytest.raises(PublicationBlocked, match="promotion|rollback|durability"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0
        )

    assert not final.exists()
    assert validated.sibling_path.is_dir()
    assert validated.names.backup_path.is_dir()
    assert json.loads(validated.journal_path.read_text())["state"] == "aborted"


def test_rename_boundary_flush_failure_preserves_backup_and_candidate(
    tmp_path, final, complete_candidate, monkeypatch
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    monkeypatch.setattr(
        report_module,
        "_durable_parent_directory",
        lambda path: (_ for _ in ()).throw(OSError("injected rename boundary flush failure")),
    )

    with pytest.raises(PublicationBlocked, match="rollback|durability"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0
        )

    assert not final.exists()
    assert validated.names.backup_path.is_dir()
    assert validated.sibling_path.is_dir()


def test_rename_boundary_failure_is_blocked_without_suppressing_evidence(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    def fail_rename(source, destination):
        raise OSError("injected rename boundary failure")

    with pytest.raises(PublicationBlocked, match="rename|promotion|rollback"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0, replace=fail_rename
        )

    assert final.is_dir()
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()
    assert json.loads(validated.journal_path.read_text())["state"] == "aborted"


def test_publisher_lock_keeps_cooperating_reader_out_of_absent_window(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    reader_result = []
    reader_started = Event()
    reader_finished = Event()
    reader_thread = None

    def replace_with_reader_hook(source, destination):
        nonlocal reader_thread
        if Path(source) == final and Path(destination) == validated.names.backup_path:
            def read_after_publish():
                reader_started.set()
                reader_result.append(read_cooperative_publication(
                    final,
                    policy=CooperativeReaderPolicy(max_attempts=1, delay_seconds=0),
                    reader=lambda path: (path / "payload.txt").read_bytes(),
                    sleep=lambda delay: None,
                ))
                reader_finished.set()

            reader_thread = Thread(target=read_after_publish)
            reader_thread.start()
        os.replace(source, destination)

    publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0,
        replace=replace_with_reader_hook,
    )
    assert reader_started.is_set()
    assert reader_thread is not None
    reader_thread.join(timeout=2)
    assert reader_finished.is_set()
    assert reader_result and reader_result[0].status == "available"
    assert reader_result[0].value == b"candidate\n"


def test_noncooperating_reader_observes_only_old_absent_new_during_renames(
    tmp_path, final, complete_candidate
):
    plan, artifacts = complete_candidate
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    observations = []

    def observe_final():
        if not final.exists():
            observations.append("absent")
        elif (final / "payload.txt").read_bytes() == b"candidate\n":
            observations.append("new")
        else:
            observations.append("old")

    def controlled_replace(source, destination):
        source = Path(source)
        destination = Path(destination)
        if source == final and destination == validated.names.backup_path:
            assert final.exists()
            observations.append("old")
        else:
            observe_final()
        os.replace(source, destination)
        if destination == final:
            assert final.is_dir()
            observations.append("new")
        else:
            observe_final()

    publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0, replace=controlled_replace
    )

    assert observations == ["old", "absent", "absent", "new"]


def _require_windows_integration() -> None:
    if os.name != "nt":
        pytest.fail("BLOCKED: windows_integration requires a Windows host")


def _create_windows_junction(link: Path, target: Path) -> None:
    try:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as error:
        pytest.fail(f"BLOCKED: Windows junction creation capability unavailable: {error}")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "no diagnostic").strip()
        pytest.fail(f"BLOCKED: Windows junction creation denied by host policy: {detail}")
    if link.is_symlink() or not link.is_dir() or not report_module._is_reparse_point(link):
        pytest.fail("BLOCKED: mklink did not create a verifiable directory junction")


def _make_windows_long_parent(tmp_path: Path) -> Path:
    parent = tmp_path
    while len(str(parent).encode("utf-16-le")) // 2 <= 270:
        parent = parent / ("phase18f-" + "x" * 30)
        try:
            parent.mkdir()
        except OSError as error:
            pytest.fail(f"BLOCKED: Windows long-path policy prevented directory creation: {error}")
    return parent


@pytest.mark.windows_integration
def test_windows_integration_prepared_journal_is_exclusive_and_durable(tmp_path, plan):
    _require_windows_integration()
    final = tmp_path / "canonical-output"
    prepared = prepare_publication_transaction(
        final,
        plan,
        "reports/concepts/evaluation_manifest.json",
        attempt=1,
        owner_token="windows-owner",
        expected_manifest_hash="a" * 64,
        budget=probe_publication_operations(final, plan, "reports/concepts/evaluation_manifest.json").budget,
    )

    journal = json.loads(prepared.journal_path.read_text(encoding="utf-8"))
    assert journal["state"] == "prepared"
    assert len(bytes.fromhex(journal["capability_hex"])) == 32
    with pytest.raises(FileExistsError):
        os.open(prepared.journal_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    assert json.loads(prepared.journal_path.read_text(encoding="utf-8"))["state"] == "prepared"


@pytest.mark.windows_integration
def test_windows_integration_derived_budget_rejects_long_path_before_mutation(
    tmp_path, plan
):
    _require_windows_integration()
    parent = _make_windows_long_parent(tmp_path)
    final = parent / "canonical-output"
    before = tuple(parent.iterdir())

    with pytest.raises(ValueError, match="budget"):
        prepare_publication_transaction(
            final,
            plan,
            "reports/concepts/evaluation_manifest.json",
            attempt=1,
            owner_token="windows-owner",
            expected_manifest_hash="b" * 64,
            budget=PublicationPathBudget(
                len(str(parent).encode("utf-16-le")) // 2 + 1,
                len("canonical-output"),
            ),
        )

    assert tuple(parent.iterdir()) == before
    assert not final.exists()


@pytest.mark.windows_integration
def test_windows_integration_same_volume_rename_promotion_and_cooperative_read(
    tmp_path, complete_candidate
):
    _require_windows_integration()
    plan, artifacts = complete_candidate
    final = tmp_path / "canonical-output"
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)

    assert validated.sibling_path.stat().st_dev == final.parent.stat().st_dev
    assert publish_validated_publication(
        validated, plan, absent_window_timeout_seconds=1.0
    ) == final
    result = read_cooperative_publication(
        final,
        policy=CooperativeReaderPolicy(max_attempts=1, delay_seconds=0),
        reader=lambda path: (path / "payload.txt").read_bytes(),
    )
    assert result.status == "available"
    assert result.value == b"candidate\n"
    assert not validated.names.backup_path.exists()


@pytest.mark.windows_integration
def test_windows_integration_same_volume_rollback_preserves_old_tree(
    tmp_path, complete_candidate
):
    _require_windows_integration()
    plan, artifacts = complete_candidate
    final = tmp_path / "canonical-output"
    _write_tree(final, artifacts)
    before = (final / "payload.txt").read_bytes()
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    promotion_failed = False

    def fail_once_then_use_real_rename(source, destination):
        nonlocal promotion_failed
        if (
            not promotion_failed
            and Path(source) == validated.sibling_path
            and Path(destination) == final
        ):
            promotion_failed = True
            raise OSError("integration promotion failure")
        os.replace(source, destination)

    with pytest.raises(PublicationBlocked, match="promotion"):
        publish_validated_publication(
            validated,
            plan,
            absent_window_timeout_seconds=1.0,
            replace=fail_once_then_use_real_rename,
        )

    assert promotion_failed
    assert final.is_dir()
    assert (final / "payload.txt").read_bytes() == before
    assert validated.sibling_path.is_dir()
    assert not validated.names.backup_path.exists()


@pytest.mark.windows_integration
def test_windows_integration_cooperative_lock_uses_real_win32_exclusion(tmp_path):
    _require_windows_integration()
    entered = Event()
    released = Event()
    errors = []

    def hold_publisher_lock():
        try:
            with report_module._publisher_lock(tmp_path, "canonical-output"):
                entered.set()
                released.wait(timeout=2)
        except Exception as error:  # pragma: no cover - only host capability evidence
            errors.append(error)
            entered.set()

    publisher = Thread(target=hold_publisher_lock)
    publisher.start()
    assert entered.wait(timeout=2)
    if errors:
        pytest.fail(f"BLOCKED: Win32 publication lock unavailable: {errors[0]}")

    reader_entered = Event()
    reader_errors = []

    def acquire_reader_lock():
        try:
            with report_module._reader_lock(tmp_path, "canonical-output"):
                reader_entered.set()
        except Exception as error:  # pragma: no cover - only host capability evidence
            reader_errors.append(error)
            reader_entered.set()

    reader = Thread(target=acquire_reader_lock)
    reader.start()
    assert not reader_entered.wait(timeout=0.2)
    released.set()
    publisher.join(timeout=2)
    reader.join(timeout=2)
    assert not publisher.is_alive()
    assert not reader.is_alive()
    if reader_errors:
        pytest.fail(f"BLOCKED: Win32 reader lock unavailable: {reader_errors[0]}")
    assert reader_entered.is_set()
    assert (tmp_path / ".canonical-output.publisher.lock").is_file()


@pytest.mark.windows_integration
def test_windows_integration_reparse_candidate_is_detected_and_preserved(
    tmp_path, complete_candidate
):
    _require_windows_integration()
    plan, artifacts = complete_candidate
    final = tmp_path / "canonical-output"
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    target = tmp_path / "reparse-target"
    target.mkdir()
    shutil.rmtree(validated.sibling_path)
    try:
        os.symlink(target, validated.sibling_path, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.fail(f"BLOCKED: Windows reparse-link creation unavailable: {error}")

    assert report_module._is_reparse_point(validated.sibling_path)
    with pytest.raises(PublicationBlocked, match="ambiguous|authenticated"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0
        )
    assert validated.sibling_path.is_symlink()
    assert final.is_dir()
    assert (final / "payload.txt").read_bytes() == b"candidate\n"


@pytest.mark.windows_integration
def test_windows_integration_real_junction_is_rejected_and_all_foreign_entries_preserved(
    tmp_path, complete_candidate
):
    _require_windows_integration()
    plan, artifacts = complete_candidate
    final = tmp_path / "canonical-output"
    _write_tree(final, artifacts)
    prepared = prepare_complete(final, plan, artifacts)
    validated = create_validated_publication_sibling(prepared, plan, artifacts)
    target = tmp_path / "foreign-junction-target"
    target.mkdir()
    foreign_file = target / "foreign.txt"
    foreign_file.write_bytes(b"must-preserve")
    shutil.rmtree(validated.sibling_path)
    _create_windows_junction(validated.sibling_path, target)
    final_before = {
        path.relative_to(final): path.read_bytes()
        for path in final.rglob("*") if path.is_file()
    }
    foreign_before = foreign_file.read_bytes()

    with pytest.raises(PublicationBlocked, match="ambiguous|authenticated"):
        publish_validated_publication(
            validated, plan, absent_window_timeout_seconds=1.0,
        )

    assert report_module._is_reparse_point(validated.sibling_path)
    assert validated.sibling_path.is_dir()
    assert foreign_file.read_bytes() == foreign_before
    assert final.is_dir()
    assert {
        path.relative_to(final): path.read_bytes()
        for path in final.rglob("*") if path.is_file()
    } == final_before
    assert target.is_dir()
    assert (tmp_path / "foreign-junction-target").is_dir()
    validated.sibling_path.unlink()


@pytest.mark.windows_integration
def test_windows_integration_real_acl_and_operation_probe_execute_on_host(
    tmp_path, plan, complete_candidate
):
    _require_windows_integration()
    probe = probe_publication_operations(
        tmp_path / "canonical-output", plan,
        "reports/concepts/evaluation_manifest.json",
    )
    assert probe.operations == ("create", "journal", "validate", "rename", "rollback", "read")
    assert all(probe.path_units[name] > 0 for name in probe.operations)
    assert all(probe.component_units[name] > 0 for name in probe.operations)

    final = tmp_path / "canonical-output"
    prepared = prepare_complete(final, *complete_candidate)
    report_module._verify_owner_only_acl(prepared.journal_path)
    owner_sid = report_module._windows_owner_sid(prepared.journal_path)
    assert re.fullmatch(r"S-[0-9]+(?:-[0-9]+)+", owner_sid)
    assert owner_sid in report_module._windows_query_owner_only_acl(prepared.journal_path)
    validated = create_validated_publication_sibling(
        prepared, complete_candidate[0], complete_candidate[1]
    )
    report_module._verify_candidate_tree_acl(validated.sibling_path)


def _minimal_generate_kwargs(output_root):
    return {
        "output_root": output_root,
        "evaluation_identity": "generated-identity",
        "analysis_mode": "synthetic_test_only",
        "methods": (MethodId.MMD,),
        "directions": (Direction.ADNI_TO_OASIS,),
        "checkpoint_policies": (CheckpointPolicy.PRIMARY_BEST_SOURCE_F1,),
        "included_methods": (),
        "canonical_tables": {},
        "report_statistics": {},
        "root_metadata": {
            "resolved_config": {"analysis_mode": "synthetic_test_only"},
            "provenance_report": {"fixture_only": True},
            "method_status_rows": [{"method": "mmd", "status": "included"}],
            "evaluation_log": "fixture-only\n",
        },
        "policy_metadata": {},
        "identity_inputs": {"configuration_sha256": "a" * 64},
        "library_versions": {"python": "test"},
        "bootstrap_replicates": 1,
        "bootstrap_seed": 7,
        "ci_policy": "percentile_95_linear",
        "gate_states": {},
        "created_utc": "1970-01-01T00:00:00Z",
        "completed_utc": "1970-01-01T00:00:00Z",
    }


def test_windows_budget_uses_measured_host_component_without_magic_fallback(
    tmp_path, plan, monkeypatch
):
    measured_component_units = len("measured-host-component")
    monkeypatch.setattr(report_module.os, "name", "nt")
    monkeypatch.setattr(
        report_module, "_windows_component_limit",
        lambda parent: measured_component_units,
    )

    budget = report_module._probe_budget(tmp_path)

    expected_path_units = (
        len(str(tmp_path).encode("utf-16-le")) // 2
        + 1
        + measured_component_units
    )
    assert budget.verified_component_units == measured_component_units
    assert budget.verified_path_units == expected_path_units


def test_operation_probe_measures_each_bounded_operation(tmp_path, plan):
    result = probe_publication_operations(
        tmp_path / "canonical-output",
        plan,
        "reports/concepts/evaluation_manifest.json",
    )

    assert isinstance(result, PublicationProbeResult)
    assert set(result.operations) == {"create", "journal", "validate", "rename", "rollback", "read"}
    assert set(result.path_units) == set(result.operations)
    assert set(result.component_units) == set(result.operations)
    assert all(result.path_units[name] > 0 for name in result.operations)
    assert all(result.component_units[name] > 0 for name in result.operations)


def test_operation_probe_executes_canonical_promotion_and_rollback_order(
    tmp_path, plan, monkeypatch
):
    calls = []
    replace = os.replace

    def recording_replace(source, destination):
        calls.append((Path(source).name, Path(destination).name))
        return replace(source, destination)

    monkeypatch.setattr(report_module.os, "replace", recording_replace)
    probe_publication_operations(
        tmp_path / "canonical-output",
        plan,
        "reports/concepts/evaluation_manifest.json",
    )

    assert len(calls) == 4
    assert calls[0][0] == "canonical-output"
    assert ".canonical-output.backup." in calls[0][1]
    assert calls[1][0].startswith("p3dco.concept-output.")
    assert calls[1][1] == "canonical-output"
    assert calls[2][0] == "canonical-output"
    assert calls[2][1].startswith("p3dco.concept-output.")
    assert calls[3][0].startswith(".canonical-output.backup.")
    assert calls[3][1] == "canonical-output"


def test_operation_probe_failure_is_fail_closed_and_cleans_only_probe_entries(
    tmp_path, plan, monkeypatch
):
    sentinel = tmp_path / "unrelated-entry"
    sentinel.write_bytes(b"preserve")
    calls = 0
    replace = os.replace

    def fail_promotion(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected probe promotion failure")
        return replace(source, destination)

    monkeypatch.setattr(report_module.os, "replace", fail_promotion)
    with pytest.raises(PublicationBlocked, match="operation"):
        probe_publication_operations(
            tmp_path / "canonical-output",
            plan,
            "reports/concepts/evaluation_manifest.json",
        )

    assert sentinel.read_bytes() == b"preserve"
    assert tuple(tmp_path.iterdir()) == (sentinel,)


def test_identity_token_shortens_only_sibling_representation_and_persists_bound(
    tmp_path, plan
):
    import hashlib

    final = tmp_path / "canonical-output"
    final.write_bytes(b"old-final")
    manifest = b"manifest"
    budget = PublicationPathBudget(320, 50)
    prepared = prepare(
        final,
        plan,
        hashlib.sha256(manifest).hexdigest(),
        budget=budget,
    )
    journal = json.loads(prepared.journal_path.read_text())

    assert len(prepared.names.identity_token) < 52
    assert journal["identity_token_length"] == len(prepared.names.identity_token)
    assert prepared.names.canonical_identity_sha256 == hashlib.sha256(
        serialize_canonical_publication_identity(
            plan, "reports/concepts/evaluation_manifest.json"
        )
    ).hexdigest()
    recovered_names = report_module._recovery_names(
        final,
        plan,
        "reports/concepts/evaluation_manifest.json",
        prepared.sibling_path,
        budget,
    )
    assert recovered_names.identity_token == prepared.names.identity_token

    journal["identity_token_length"] += 1
    prepared.journal_path.write_text(json.dumps(journal), encoding="utf-8")
    with pytest.raises(ValueError, match="journal"):
        report_module._validate_prepared_publication(
            prepared, plan, {"evaluation_manifest.json": manifest}
        )


def test_identity_token_wrong_length_is_rejected_by_recovery_budget(tmp_path, plan):
    budget = PublicationPathBudget(320, 50)
    final = tmp_path / "canonical-output"
    names = derive_publication_names(
        final,
        plan,
        "reports/concepts/evaluation_manifest.json",
        attempt=1,
        budget=budget,
    )
    wrong_sibling = names.sibling_path.with_name(
        names.sibling_path.name.replace(names.identity_token, names.identity_token + "a")
    )

    with pytest.raises(ValueError, match="token length"):
        report_module._recovery_names(
            final,
            plan,
            "reports/concepts/evaluation_manifest.json",
            wrong_sibling,
            budget,
        )


def test_commit_output_and_generate_use_only_bounded_publication_route(
    tmp_path, complete_candidate, monkeypatch
):
    forbidden = (
        "_allocation_lock",
        "_find_non_overwrite_destination",
        "_reserve_destination",
        "_recover_stale_controlled_entries",
        "_publish_output",
    )
    for name in forbidden:
        monkeypatch.setattr(
            report_module,
            name,
            lambda *args, _name=name, **kwargs: pytest.fail(
                f"legacy publication helper invoked: {_name}"
            ),
        )

    plan, artifacts = complete_candidate
    committed = commit_output(tmp_path / "committed", plan, artifacts, overwrite=True)
    assert committed == tmp_path / "committed"
    assert {
        path.relative_to(committed).as_posix(): path.read_bytes()
        for path in committed.rglob("*")
        if path.is_file()
    } == artifacts

    generated = generate_concept_report(**_minimal_generate_kwargs(tmp_path / "generated"))
    assert generated == tmp_path / "generated"
    assert verify_completed_output(generated, expected_identity="generated-identity")
    assert not any(
        ".stage." in entry.name
        or ".reserve." in entry.name
        or ".backup." in entry.name
        or ".allocation.lock" in entry.name
        for entry in tmp_path.iterdir()
    )


def test_commit_output_probe_failure_is_before_final_mutation(tmp_path, complete_candidate):
    plan, artifacts = complete_candidate
    output = tmp_path / "committed"
    before = tuple(tmp_path.iterdir())

    def blocked_probe(final_path, probe_plan, canonical_relative_path):
        raise PublicationBlocked(
            "probe capability unavailable",
            reason="path_capability_unavailable",
            final_path=Path(final_path),
            candidate_path=Path(final_path),
            backup_path=Path(final_path).with_name(".blocked-backup"),
        )

    with pytest.raises(PublicationBlocked, match="probe capability"):
        commit_output(
            output,
            plan,
            artifacts,
            overwrite=True,
            publication_probe=blocked_probe,
        )

    assert tuple(tmp_path.iterdir()) == before
    assert not output.exists()
    assert not any(
        ".stage." in entry.name or ".reserve." in entry.name or ".backup." in entry.name
        for entry in tmp_path.iterdir()
    )


def test_commit_output_budget_failure_is_before_final_mutation(tmp_path, complete_candidate):
    plan, artifacts = complete_candidate
    output = tmp_path / "committed"
    before = tuple(tmp_path.iterdir())
    budget = PublicationPathBudget(
        len(str(output.parent).encode("utf-16-le")) // 2 + 1 + len(output.name),
        len(output.name),
    )

    with pytest.raises(PublicationBlocked, match="verified path capability"):
        commit_output(
            output,
            plan,
            artifacts,
            overwrite=True,
            publication_probe=lambda final_path, probe_plan, canonical_relative_path: budget,
        )

    assert tuple(tmp_path.iterdir()) == before
    assert not output.exists()


def test_generate_concept_report_probe_failure_is_before_final_mutation(tmp_path):
    output = tmp_path / "generated"

    def blocked_probe(final_path, probe_plan, canonical_relative_path):
        raise PublicationBlocked(
            "probe capability unavailable",
            reason="path_capability_unavailable",
            final_path=Path(final_path),
            candidate_path=Path(final_path),
            backup_path=Path(final_path).with_name(".blocked-backup"),
        )

    with pytest.raises(PublicationBlocked, match="probe capability"):
        generate_concept_report(
            **_minimal_generate_kwargs(output), publication_probe=blocked_probe
        )

    assert not output.exists()
    assert not any(
        ".stage." in entry.name or ".reserve." in entry.name or ".backup." in entry.name
        for entry in tmp_path.iterdir()
    )


def _evaluate_cli_args(tmp_path, *, policy=None, overwrite=True):
    args = [
        "--config", str(tmp_path / "config.yaml"),
        "--runs-root", str(tmp_path / "runs"),
        "--artifact-root", str(tmp_path / "artifacts"),
        "--output-root", str(tmp_path / "output"),
        "--direction", "adni_to_oasis",
        "--method", "mmd",
        "--bootstrap-seed", "7",
    ]
    if overwrite:
        args.append("--overwrite")
    if policy is not None:
        args.extend(("--absent-window-timeout-seconds", str(policy)))
    return args


def test_evaluation_overwrite_requires_explicit_absent_window_policy(tmp_path):
    selection = evaluate_concepts.parse_cli(_evaluate_cli_args(tmp_path))

    with pytest.raises(
        evaluate_concepts.ConfigurationError,
        match="--absent-window-timeout-seconds is required with --overwrite",
    ):
        evaluate_concepts._execute(selection)


def test_evaluation_cli_rejects_malformed_absent_window_policy(tmp_path):
    for policy in ("nan", "inf", "-1", "true"):
        with pytest.raises(SystemExit) as error:
            evaluate_concepts.parse_cli(_evaluate_cli_args(tmp_path, policy=policy))
        assert error.value.code == 2


@pytest.mark.parametrize("policy", [float("nan"), float("inf"), -1, True, "1"])
def test_evaluation_rejects_nonfinite_negative_bool_or_malformed_policy(
    tmp_path, policy
):
    selection = evaluate_concepts.parse_cli(_evaluate_cli_args(tmp_path))
    invalid_selection = selection._replace(absent_window_timeout_seconds=policy)

    with pytest.raises(
        evaluate_concepts.ConfigurationError,
        match="--absent-window-timeout-seconds",
    ):
        evaluate_concepts._execute(invalid_selection)


def test_evaluation_cli_wires_absent_window_policy_to_commit_output(tmp_path, monkeypatch):
    selection = evaluate_concepts.parse_cli(
        _evaluate_cli_args(tmp_path, policy=1.25)
    )
    observed = {}

    monkeypatch.setattr(evaluate_concepts, "_load_configuration", lambda selection: {})
    monkeypatch.setattr(
        evaluate_concepts,
        "_evaluation_request",
        lambda selection, config: SimpleNamespace(
            analysis_mode=evaluate_concepts.AnalysisMode.SYNTHETIC_TEST_ONLY,
            run_mode=evaluate_concepts.RunMode.EVALUATE,
        ),
    )
    monkeypatch.setattr(
        evaluate_concepts,
        "_load_verified_fixture_manifest",
        lambda config, config_path: SimpleNamespace(
            manifest_sha256="manifest", fixture_payload_sha256="payload", fixture_files=()
        ),
    )
    monkeypatch.setattr(evaluate_concepts, "_synthetic_fixture_metrics", lambda payload: {})
    monkeypatch.setattr(
        evaluate_concepts,
        "build_synthetic_fixture_bundle",
        lambda **kwargs: (object(), {}),
    )

    def capture_commit(output_root, plan, artifacts, **kwargs):
        observed.update(kwargs)
        return Path(output_root)

    monkeypatch.setattr(evaluate_concepts, "commit_output", capture_commit)

    assert evaluate_concepts._execute(selection) == evaluate_concepts.ExitCode.SUCCESS
    assert observed["overwrite"] is True
    assert observed["absent_window_timeout_seconds"] == 1.25


def _run_git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True,
    )


def _git_tracked_paths(root):
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True,
    ).stdout
    return {path.decode("utf-8") for path in output.split(b"\0") if path}


def _scope_paths(root, roots):
    paths = []
    for relative_root in roots:
        path = root / relative_root
        if path.is_symlink() or path.is_file():
            paths.append(path)
        elif path.is_dir():
            paths.extend(
                candidate for candidate in path.rglob("*")
                if candidate.is_symlink() or candidate.is_file()
            )
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _scope_record(root, path, tracked_paths):
    relative = path.relative_to(root).as_posix()
    metadata = os.lstat(path)
    if stat.S_ISLNK(metadata.st_mode):
        kind = "symlink"
        payload = os.readlink(path).encode("utf-8")
    elif stat.S_ISREG(metadata.st_mode):
        kind = "file"
        payload = path.read_bytes()
    else:
        raise AssertionError(f"unsupported inventory entry: {relative}")
    return {
        "path": relative,
        "tracked_state": "tracked" if relative in tracked_paths else "untracked",
        "kind": kind,
        "mode_or_attributes": {
            "mode": stat.S_IMODE(metadata.st_mode),
            "file_attributes": getattr(metadata, "st_file_attributes", 0),
        },
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def project_candidate_scope(root, *, roots):
    root = Path(root)
    tracked_paths = _git_tracked_paths(root)
    return {
        record["path"]: record
        for record in (
            _scope_record(root, path, tracked_paths)
            for path in _scope_paths(root, roots)
        )
    }


def authorize_candidate_projection(baseline, current, *, allowlist):
    changed = {}
    for path in sorted(set(baseline) | set(current)):
        if baseline.get(path) != current.get(path):
            if path not in allowlist:
                raise ValueError(f"unlisted path changed: {path}")
            changed[path] = {"before": baseline.get(path), "after": current.get(path)}
    return changed


def test_candidate_admission_projection_covers_complete_tracked_and_untracked_scope(tmp_path):
    src = tmp_path / "src"
    config = tmp_path / "config"
    scripts = tmp_path / "scripts"
    src.mkdir()
    config.mkdir()
    scripts.mkdir()
    (src / "tracked.py").write_bytes(b"tracked source\n")
    (config / "tracked.yaml").write_bytes(b"tracked: true\n")
    (scripts / "tracked.py").write_bytes(b"tracked script\n")
    _run_git(tmp_path, "init")
    _run_git(tmp_path, "config", "user.name", "phase18f-test")
    _run_git(tmp_path, "config", "user.email", "phase18f-test@example.invalid")
    _run_git(tmp_path, "add", "-f", "src", "config", "scripts")
    _run_git(tmp_path, "commit", "-m", "baseline")

    baseline = project_candidate_scope(tmp_path, roots=("src", "config", "scripts"))
    (src / "tracked.py").write_bytes(b"admitted source\n")
    (config / "untracked.yaml").write_bytes(b"admitted config\n")
    (scripts / "focused.py").write_bytes(b"admitted script\n")
    current = project_candidate_scope(tmp_path, roots=("src", "config", "scripts"))
    src_only_diff = subprocess.run(
        ["git", "diff", "--", "src"], cwd=tmp_path, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    assert "config/untracked.yaml" not in src_only_diff
    admitted = authorize_candidate_projection(
        baseline, current,
        allowlist={"src/tracked.py", "config/untracked.yaml", "scripts/focused.py"},
    )

    assert set(baseline) == {
        "src/tracked.py", "config/tracked.yaml", "scripts/tracked.py",
    }
    assert set(admitted) == {
        "src/tracked.py", "config/untracked.yaml", "scripts/focused.py",
    }
    assert baseline["src/tracked.py"]["tracked_state"] == "tracked"
    assert current["config/untracked.yaml"]["tracked_state"] == "untracked"
    assert current["scripts/focused.py"]["tracked_state"] == "untracked"
    assert all(
        set(record) == {
            "path", "tracked_state", "kind", "mode_or_attributes", "size", "sha256",
        }
        for record in (*baseline.values(), *current.values())
    )


def test_candidate_admission_projection_rejects_unlisted_path(tmp_path):
    src = tmp_path / "src"
    config = tmp_path / "config"
    src.mkdir()
    config.mkdir()
    (src / "tracked.py").write_bytes(b"tracked source\n")
    _run_git(tmp_path, "init")
    _run_git(tmp_path, "config", "user.name", "phase18f-test")
    _run_git(tmp_path, "config", "user.email", "phase18f-test@example.invalid")
    _run_git(tmp_path, "add", "-f", "src")
    _run_git(tmp_path, "commit", "-m", "baseline")
    baseline = project_candidate_scope(tmp_path, roots=("src", "config"))
    (config / "unlisted.yaml").write_bytes(b"unlisted\n")
    current = project_candidate_scope(tmp_path, roots=("src", "config"))

    with pytest.raises(ValueError, match="unlisted path"):
        authorize_candidate_projection(baseline, current, allowlist=())

    assert "config/unlisted.yaml" in current
