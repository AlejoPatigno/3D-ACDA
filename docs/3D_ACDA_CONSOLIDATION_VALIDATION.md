# 3D-ACDA Consolidation Validation

Validation date: 2026-08-28

This document records validation of the consolidated repository snapshot. The manifests under `specs/phase_18f_post_seed_validation_remediation/evidence/` are historical Phase 18F evidence and were intentionally preserved without rewriting their embedded hashes.

## Current validation

- Publication and concept reporting: `146 passed, 1 skipped`.
- Focused Phase 18E/F/G validation before the review corrections: `223 passed, 1 skipped, 1 deselected`.
- Broad repository suite before the review corrections, excluding the unavailable private CSV test: `1537 passed, 13 failed, 1 skipped, 1 deselected`.
- Ruff on the files changed by the publication correction: passed.

The 13 broad-suite failures reproduce known inherited prototype drift, one Windows baseline-trainer permission failure, and one historical rename-count expectation. They are not introduced by the consolidation or publication correction.

All staging validation commands set `PYTHONPATH=src` so Python imports the consolidated source tree rather than an older editable installation.