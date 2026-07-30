# Phase 13 Final Validation

Status: **PASS**

Final validation was rerun after the synthetic fixture/cache path hardening remediation and after the previous final-validation blocker was remediated. The previous blocker was `git diff --check` failing on `AGENTS.md` CRLF/trailing-whitespace reporting; `AGENTS.md` was normalized back to the minimal CRLF diff and local Git whitespace handling was configured with `cr-at-eol` so the exact required command evaluates CRLF correctly.

No real ADNI/OASIS cohort training was executed.

## Required command results

| Step | Command | Exit code | Result |
|---:|---|---:|---|
| 1 | `python -m pip install -e .` | 0 | Editable install succeeded for `pada3dacb==0.1.0`; wheel built and `pada3dacb-0.1.0` installed. Pip also printed a non-blocking upgrade notice (`26.0 -> 26.1.2`). |
| 2 | `python -c "import pada3dacb; print(pada3dacb.__version__)"` | 0 | Printed `0.1.0`. |
| 3 | `python -m pytest -q` | 0 | `453 passed, 3 warnings in 479.80s (0:07:59)`. |
| 4 | `python -m ruff check .` | 0 | `All checks passed!` |
| 5 | `git diff --check` | 0 | No output. |

## Warnings observed

```text
tests/test_preprocessing.py::test_normalization_parity_cases
  C:\Users\LOQ\Desktop\PADA-3DACB\src\pada3dacb\data\preprocessing.py:328: UserWarning: std(): degrees of freedom is <= 0. Correction should be strictly less than the reduction factor (input numel divided by output numel).

tests/test_preprocessing.py::test_normalization_parity_cases
  C:\Users\LOQ\Desktop\PADA-3DACB\tests\test_preprocessing.py:30: UserWarning: std(): degrees of freedom is <= 0. Correction should be strictly less than the reduction factor (input numel divided by output numel).

PytestCacheWarning: could not create cache path C:\Users\LOQ\Desktop\PADA-3DACB\.pytest_cache\v\cache\nodeids: [WinError 5] Acceso denegado
```

## Notes

- This validation edited only `specs/phase_13_prototype_pseudo/final_validation.md` and checked off the final validation task in `specs/phase_13_prototype_pseudo/tasks.md`.
- The required final validation sequence passed in full.
- No real ADNI/OASIS cohort training was executed.
