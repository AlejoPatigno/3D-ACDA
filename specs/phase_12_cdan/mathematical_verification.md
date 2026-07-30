# Phase 12 CDAN Mathematical Verification

## Verdict

APPROVED for the mathematical core owned by this verification action.

The inspected implementation satisfies the Phase 12 tensor/loss contracts for exact outer-product conditioning, deterministic flattening, gradient flow through embeddings and latent probabilities, constant GRL sign/scale including coefficient zero, raw discriminator logits, and concatenated mean BCE domain objective with unequal source/target batch sizes.

## Scope and Inputs Read

Specifications:
- `specs/phase_12_cdan/requirements.md`
- `specs/phase_12_cdan/design.md`
- `specs/phase_12_cdan/acceptance.md`
- `specs/phase_12_cdan/agent_plan.yaml`

Implementation:
- `src/pada3dacb/adaptation/gradient_reversal.py`
- `src/pada3dacb/adaptation/cdan.py`
- `src/pada3dacb/adaptation/domain_discriminator.py`

Focused tests:
- `tests/test_gradient_reversal.py`
- `tests/test_cdan_conditional_map.py`
- `tests/test_cdan_domain_loss.py`
- `tests/test_cdan_domain_discriminator.py`
- `tests/test_cdan_gradients.py`
- `tests/test_cdan_resume.py`

## Mathematical Findings

### Exact outer product and deterministic flattening

Approved.

`conditional_outer_product(features, class_probabilities)` computes:

```python
(features.unsqueeze(2) * class_probabilities.unsqueeze(1)).flatten(1)
```

For `z = [[1, 2]]` and `p = [[0.25, 0.5, 0.25]]`, the output is:

```text
[[0.25, 0.5, 0.25, 0.5, 1.0, 0.5]]
```

This is the exact row-major flattening of `H_i = z_i p_i^T`, ordered by feature row then class column: `z_0*p_0, z_0*p_1, z_0*p_2, z_1*p_0, ...`.

The focused tests also verify deterministic repeated construction for multiple samples.

### Gradients through `z` and probabilities

Approved.

The conditional tensor construction uses multiplication and flattening only; neither input is detached. Manual evidence:

```text
z_grad = [[1.0, 1.0]]
p_grad = [[3.0, 3.0, 3.0]]
```

Focused tests additionally verify gradients reach source/target features, source/target probabilities, encoder weights, latent classifier weights, and discriminator parameters.

### GRL sign/scale and coefficient zero

Approved.

`GradientReversalFunction.backward` returns:

```python
gradient.neg().mul(ctx.coefficient), None
```

Therefore the upstream feature gradient is exactly `-coefficient * downstream_gradient`, while discriminator parameter gradients are not reversed.

Evidence from focused and manual checks:

- coefficient `0.25` maps unit upstream gradient to `[-0.25, -0.25]`;
- coefficient `0.0` preserves forward values and produces zero input gradient;
- with CDAN `grl_coefficient=0.0`, encoder/probability adversarial gradients are blocked while discriminator parameters still receive gradients:

```text
gr_l_zero_forward_equal = True
x_grad = [-0.0, -0.0]
cdan_zero_grl_loss_dim = 0
sz_grad_norm = 0.0
sp_grad_norm = 0.0
disc_grad_norm = 0.5618515610694885
```

Coefficient validation rejects non-real, negative, NaN, infinite, and scheduled/function coefficients in the public GRL API.

### Discriminator raw logits

Approved.

`DomainDiscriminator` ends with `nn.Linear(dimensions[-1], 1)` and returns `.squeeze(-1)`. There is no final sigmoid. The focused test sets final bias to `2.0` and confirms output logits are exactly `2.0`, proving raw-logit behavior rather than sigmoid output.

The discriminator validates rank-2 conditional input, exact configured input dimension, floating dtype, and finite values.

### Concatenated BCE domain objective with unequal batch sizes

Approved.

`CDANAdaptationMethod.compute(..., stage="full")` builds separate source and target conditional tensors, obtains one raw logit per sample, then computes:

```python
logits = torch.cat((source_logits, target_logits), dim=0)
targets = torch.cat((torch.zeros_like(source_logits), torch.ones_like(target_logits)), dim=0)
loss = F.binary_cross_entropy_with_logits(logits, targets, reduction="mean")
```

This is the required internal-label contract: source domain = 0, target domain = 1. Because logits and labels are concatenated before the mean reduction, unequal batches are weighted per sample over the total `B_source + B_target`, not averaged per domain first.

Focused test evidence covers source batch size 2 and target batch size 3 with exact manual BCE comparison.

## Validation Commands

Required focused command executed:

```bash
cd /c/Users/LOQ/Desktop/PADA-3DACB && PYTHONPATH=src python -m pytest tests/test_gradient_reversal.py tests/test_cdan_conditional_map.py tests/test_cdan_domain_loss.py tests/test_cdan_domain_discriminator.py tests/test_cdan_gradients.py tests/test_cdan_resume.py -q
```

Result:

```text
47 passed, 1 warning in 54.52s
```

Warning observed:

```text
PytestCacheWarning: could not create cache path C:\Users\LOQ\Desktop\PADA-3DACB\.pytest_cache\v\cache\nodeids: [WinError 5] Acceso denegado
```

This warning affects pytest cache writing only; it does not weaken the mathematical verification result.

Additional manual mathematical probe executed:

```bash
cd /c/Users/LOQ/Desktop/PADA-3DACB && PYTHONPATH=src python - <<'PY'
# checked exact outer product values, gradients through z/p, GRL coefficient zero,
# and CDAN zero-GRL discriminator-gradient behavior
PY
```

Result excerpt:

```text
outer= [[0.25, 0.5, 0.25, 0.5, 1.0, 0.5]]
z_grad= [[1.0, 1.0]] p_grad= [[3.0, 3.0, 3.0]]
gr_l_zero_forward_equal= True x_grad= [-0.0, -0.0]
cdan_zero_grl_loss_dim= 0 sz_grad_norm= 0.0 sp_grad_norm= 0.0 disc_grad_norm= 0.5618515610694885
```

## Blockers

None for this mathematical verification scope.

## Notes

This action did not modify production code or implementation tests. It wrote only the owned report file `specs/phase_12_cdan/mathematical_verification.md`.
## Current Independent Scientific Verification Update

Date: 2026-07-22
Responsible agent: gemini-cli
Action: independent-scientific-verification
Dependencies acknowledged: `audit-existing-phase12`, `complete-phase12-tests`, `remediate-cdan-completed-run-reuse`

### Verdict

APPROVED for this independent scientific verification scope.

No CRITICAL scientific blockers were found. The inspected Phase 12 CDAN implementation continues to satisfy the required mathematical contracts for exact outer-product conditioning, row-major flattening, constant-coefficient GRL behavior including coefficient zero, concatenated-sample BCE weighting for unequal source/target batch sizes, gradient reachability, target-label exclusion from adaptation loss, and completed-run reuse compatibility checks.

### Inputs Re-read

- `AGENTS.md`
- `specs/phase_12_cdan/requirements.md`
- `specs/phase_12_cdan/design.md`
- `specs/phase_12_cdan/acceptance.md`
- `src/pada3dacb/adaptation/gradient_reversal.py`
- `src/pada3dacb/adaptation/cdan.py`
- `src/pada3dacb/adaptation/domain_discriminator.py`
- `src/pada3dacb/training/uda_trainer.py`
- `src/pada3dacb/experiments/cdan.py`
- Relevant CDAN tests: conditional map, GRL, discriminator, domain loss, gradients, no target labels, predictions/completed-run reuse, warmup, trainer, config, checkpoint policy, CLI, fold orchestration, loader cycling, and resume.

### Findings

1. Exact outer-product conditioning and flattening order: PASS.
   - `conditional_outer_product` computes `(features.unsqueeze(2) * class_probabilities.unsqueeze(1)).flatten(1)`.
   - This produces row-major feature-by-class order: for `z=[[1,2]]`, `p=[[0.25,0.5,0.25]]`, output is `[[0.25,0.5,0.25,0.5,1.0,0.5]]`.
   - No detach is present in the conditioning path.

2. GRL sign/scaling, including zero coefficient: PASS.
   - `GradientReversalFunction.backward` returns `gradient.neg().mul(ctx.coefficient)`.
   - Coefficient `0.0` preserves forward values and blocks gradients to conditional inputs while discriminator parameters still receive gradients through the unreversed downstream path.

3. BCE concatenated-sample weighting for unequal source/target batches: PASS.
   - Source and target logits/labels are concatenated before `binary_cross_entropy_with_logits(..., reduction="mean")`.
   - Unequal source/target sizes are therefore weighted per sample over `B_source + B_target`, not by averaging per-domain means.

4. Gradients to `z`, probabilities, shared model, and discriminator: PASS.
   - The domain loss path is differentiable through source/target `z`, latent probabilities, encoder/latent classifier weights, and discriminator parameters.
   - Tests confirm gradients reach `TinyPADA3DACB.encoder.weight`, `TinyPADA3DACB.latent.weight`, and discriminator parameters.

5. Target diagnosis labels cannot enter adaptation loss: PASS.
   - `UDATrainer._validate_target_batch` requires only unlabeled target fields and rejects `y`, `label`, `label_name`, `true_label`, `diagnosis`, `diagnosis_label`, `c_target`, `g_bar`, and `class_probabilities`.
   - The full-stage target forward uses only `target["x"]`; source diagnosis/concept tensors are used only for the approved source objective.

6. Completed-run reuse remediation: PASS.
   - `CDANExperimentRunner._completed_reuse` delegates baseline completed-fold checks to `SourceOnlyExperimentRunner._completed_reuse` and then verifies CDAN-specific manifest identity fields: method, adaptation method/weight, source assignment hash, target-adaptation assignment hash, and target-evaluation assignment hash.
   - This remediation changes reuse safety/identity validation only; it does not alter CDAN tensor construction, GRL behavior, discriminator loss, optimization objective, or target-label policy.

### Commands and Results

Initial focused command:

```bash
cd /c/Users/LOQ/Desktop/PADA-3DACB && PYTHONPATH=src python -m pytest tests/test_cdan_conditional_map.py tests/test_gradient_reversal.py tests/test_cdan_domain_discriminator.py tests/test_cdan_domain_loss.py tests/test_cdan_gradients.py tests/test_cdan_no_target_labels.py tests/test_cdan_predictions.py -q
```

Result: `48 passed, 2 warnings, 2 errors in 4.78s`.

The two errors occurred during pytest `tmp_path` setup due to `PermissionError: [WinError 5] Acceso denegado: 'C:\Users\LOQ\AppData\Local\Temp\pytest-of-LOQ'`; they were environmental, not test assertion failures. Pytest cache warnings also reported denied access under `.pytest_cache`.

Rerun with repository-local pytest base/cache directories:

```bash
cd /c/Users/LOQ/Desktop/PADA-3DACB && mkdir -p .tmp_pytest_verify .tmp_pytest_cache && PYTHONPATH=src python -m pytest tests/test_cdan_conditional_map.py tests/test_gradient_reversal.py tests/test_cdan_domain_discriminator.py tests/test_cdan_domain_loss.py tests/test_cdan_gradients.py tests/test_cdan_no_target_labels.py tests/test_cdan_predictions.py -q --basetemp=.tmp_pytest_verify -o cache_dir=.tmp_pytest_cache
```

Result: `50 passed in 4.76s`.

Additional focused CDAN integration/config/reuse-adjacent command:

```bash
cd /c/Users/LOQ/Desktop/PADA-3DACB && PYTHONPATH=src python -m pytest tests/test_cdan_warmup.py tests/test_cdan_trainer.py tests/test_cdan_config.py tests/test_cdan_checkpoint_policy.py tests/test_cdan_cli.py tests/test_cdan_fold_orchestration.py tests/test_cdan_loader_cycling.py tests/test_cdan_resume.py -q --basetemp=.tmp_pytest_verify -o cache_dir=.tmp_pytest_cache
```

Result: `45 passed in 26.82s`.

Manual mathematical probe:

```bash
cd /c/Users/LOQ/Desktop/PADA-3DACB && PYTHONPATH=src python - <<'PY'
# checked exact outer product values, z/p gradients, GRL coefficient zero,
# zero-GRL CDAN discriminator-gradient behavior, and unequal concatenated BCE value
PY
```

Result excerpt:

```text
outer= [[0.25, 0.5, 0.25, 0.5, 1.0, 0.5]]
z_grad= [[1.0, 1.0]] p_grad= [[3.0, 3.0, 3.0]]
grl_zero_forward_equal= True x_grad= [-0.0, -0.0]
cdan_zero_grl_loss_dim= 0 source_z_grad_norm= 0.0 source_p_grad_norm= 0.0 disc_grad_norm= 0.5223721861839294
unequal_concat_bce= 0.43538904190063477 sample_count= 5
```

### Blockers

None for this independent scientific verification scope.

### Scope Control

This verification did not modify production code, tests, or general documentation. It updated only the owned audit artifact `specs/phase_12_cdan/mathematical_verification.md`.

