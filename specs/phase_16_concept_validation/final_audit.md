# Phase 16 final technical audit

## Current verdict

**Pending final rerun after remediation.** The implementation is eligible for a second independent verification only after every command in the evidence matrix below passes on the remediated bytes.

## Scope

- Phase 16 only.
- Synthetic fixtures and deterministic evaluation only.
- No real ADNI/OASIS evaluation.
- No archive, commit, push, PR, release, or publication.
- No Phase 17 work.

## Scientific audit

| Control | Expected disposition |
|---|---|
| Fixed class order | CN=0, MCI=1, AD=2 |
| Concept fidelity | `c_hat` versus immutable `c_target` |
| Anatomy consistency | `c_hat` versus immutable `g_bar` |
| Consistency direction | Explicitly derived from configured `L_cons` |
| ROI stability | Separate fidelity/anatomy/concept/alpha profiles |
| Bootstrap unit | Diagnosis-stratified subjects after aggregation |
| Method family | prototype_pseudo versus source_only/CORAL/MMD/CDAN |
| AAGN/FasterSNN | Not applicable to concept evaluation |
| Target-label firewall | Posthoc evaluation only |
| CFS/ACS/PCS/QIS | BLOCKED; no equation invented |

## Provenance audit

- Precomputed concept and anatomical targets are required.
- Candidate validation issues block inference.
- Checkpoint, normalizer, ROI-order, atlas, and target artifacts fail closed.
- Subject outputs require valid lowercase SHA-256 metadata.
- Output publication uses an exact file allowlist, artifact index, manifest-last commit, and hash-verified read-only reuse.

## Verification matrix

| Evidence | Required result | Final result |
|---|---|---|
| Independent metric/statistics references | PASS | Pending rerun |
| Complete `tests/test_concept_*.py` | PASS | Pending rerun |
| Previous-method regressions | PASS | Pending rerun |
| Full `python -m pytest -q` | PASS | Pending rerun |
| `python -m ruff check .` | PASS | Pending rerun |
| `git diff --check` | PASS | Pending rerun |
| Synthetic dry-run and validate-only | Exit 0, no output | Pending rerun |
| Synthetic evaluate repeated | Exit 0, byte-identical | Pending rerun |
| Synthetic reuse | Exit 0, no mtime change | Pending rerun |
| Real gate | Blocked before output | Pending rerun |
| Graph update | Exit 0 | Pending rerun |

## Administrative boundary

Native incident #1793 remains a hard blocker for archive and every delivery/publication operation. It does not authorize lock deletion, authority repair, or changes to earlier scientific phases.

## Phase boundary

Phase 17 has not started and remains prohibited until Phase 16 receives independent PASS and explicit human approval.
