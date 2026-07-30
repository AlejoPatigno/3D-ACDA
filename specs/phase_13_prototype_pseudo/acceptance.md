# Phase 13 Acceptance

Status: READY FOR REVIEW. Implementation acceptance is blocked until `spec_review.md` approves this extraction.

## Specification acceptance

- [ ] `specs/phase_13_prototype_pseudo/notebook_extraction.md` traces active and obsolete notebook definitions.
- [ ] `requirements.md` uses executable requirements and scenarios.
- [ ] `design.md` states tensor contracts, equations, integration boundaries, target-label firewall, and checkpoint/resume implications.
- [ ] `tasks.md` matches `agent_plan.yaml` dependencies and file ownership.
- [ ] No production code, tests, config, `AGENTS.md`, `pyproject.toml`, `.gitignore`, or `agent_plan.yaml` were modified by canonical extraction.
- [ ] Independent review confirms no scientific value was invented.

## Scientific acceptance criteria

### Prototype alignment

- [ ] Current-batch source prototypes are per-class means over `z_src` using source labels.
- [ ] Target prototypes are per-class means over `z_tgt` for target rows whose concept-head confidence is `>= tau_p`.
- [ ] Alignment uses mean squared Euclidean distance over classes valid in both source and accepted target batches.
- [ ] Source separation uses mean `relu(proto_margin - L2 distance)^2` over unordered valid source prototype pairs.
- [ ] Absent classes, no accepted target rows, or no mutually valid class produce zero alignment.
- [ ] Fewer than two source-valid classes produce zero separation.
- [ ] No prototype normalization, cache, EMA, memory bank, momentum, or schedule exists.

### Pseudo-label adaptation

- [ ] Pseudo-label probabilities come from `softmax(logits_c_tgt, dim=-1)`.
- [ ] Confidence is max softmax probability; pseudo label is argmax class.
- [ ] Acceptance threshold is fixed `conf >= tau_p`.
- [ ] Loss is `F.cross_entropy(logits_c_tgt[mask], pseudo[mask])` with mean reduction.
- [ ] Empty accepted set returns zero scalar loss and count zero.
- [ ] No temperature scaling, entropy threshold, class balancing, or target concept/anatomy input is added.

### Combined objective

- [ ] Warm stage computes only source core losses with warm multipliers and reports adaptation losses as zero.
- [ ] Full stage computes source core losses plus `lambda_proto * L_proto` and `lambda_pl * L_pl`.
- [ ] Canonical executed coefficients are explicit: `lambda_proto=1.0`, `lambda_pl=0.1`, `tau_p=0.95`, `proto_margin=1.0`, `lambda_sep=0.1`, plus source/warm coefficients in `design.md`.
- [ ] Test-only coefficient overrides are clearly labeled and cannot become implicit real-run defaults.

### Target-label firewall

- [ ] Target adaptation loader can provide only `x`.
- [ ] Adaptation loss does not read target `y`, `c_target`, or `g_bar`.
- [ ] Target evaluation metrics are monitoring-only and do not affect loss, gradients, optimizer, scheduler, checkpoint selection, epoch count, or hyperparameters.

### Checkpoint/resume

- [ ] No adaptation-specific state is serialized because the canonical method is stateless across batches/epochs.
- [ ] Existing trainer checkpoint/resume policy remains responsible for model/optimizer/scaler/history state.

## Required commands and evidence

Focused commands after each implementation action:

```bash
python -m pytest -q tests/test_prototype_loss.py tests/test_prototype_construction.py tests/test_prototype_gradients.py
python -m pytest -q tests/test_pseudo_label_selection.py tests/test_pseudo_label_loss.py tests/test_pseudo_label_gradients.py
python -m pytest -q tests/test_prototype_pseudo_total.py tests/test_proposed_method_reference.py tests/test_proposed_method_edge_cases.py
python -m pytest -q tests/test_proposed_method_no_target_labels.py tests/test_proposed_method_warmup.py tests/test_proposed_method_resume.py
```

Full phase validation commands:

```bash
python -m pip install -e .
python -c "import pada3dacb; print(pada3dacb.__version__)"
python -m pytest -q
python -m ruff check .
git diff --check
```

Current baseline evidence before Phase 13 implementation:

```text
python -m pytest -q
exit 0; 312 passed, 3 warnings in 206.89s
```

## Block condition

If independent specification review cannot verify any equation, coefficient, tensor contract, or target-label firewall rule against the authoritative notebook, implementation MUST remain blocked and the unresolved item MUST be added to `decisions.md` by the owning action-plan owner.
