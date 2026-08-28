# PADA-3DACB Project Context

## Initialization scope

- SDD initialization validated for the prospective, documentation-only Phase 18 migration work.
- Frozen live commit: `aafe817365cb4068f167b398c776aff4c3b1f021`.
- Active repository phase: Phase 18.
- Immediate next work: author a new prospective Phase 18e migration specification in a new spec directory, followed by separate review.
- Runtime, scientific behavior, source, configuration, tests, runs, results, generated artifacts, historical specifications, and historical documentation are out of scope and must remain unchanged.

## Stack and conventions

- Python package/research codebase (`pyproject.toml`, `requirements.txt`, `environment.yml`).
- Python requirement: >=3.10.
- Packaging uses setuptools with source packages under `src`.
- Optional development dependencies include `pytest` and `ruff`.
- OpenSpec configuration is present at `openspec/config.yaml`; its proposal/spec/design/tasks rules require a problem statement, acceptance criteria, tradeoffs, and review-workload protection.
- Existing OpenSpec artifacts are organized under `openspec/changes/`; historical artifacts must not be edited for this work.
- `.atl/skill-registry.md` is present and available for skill resolution.

## Testing and strict-TDD state

- The parent phase explicitly declares strict TDD enabled. This initialization performs no implementation or test execution.
- The checked-in `openspec/config.yaml` currently declares `strict_tdd: false` and no configured test runner. It was intentionally not modified because the delegated scope forbids configuration changes and the existing config is user-maintained.
- `pyproject.toml` declares pytest configuration and an optional pytest development dependency, but no test command is configured in OpenSpec. Any later implementation/verification phase must follow the parent-provided strict-TDD contract and separately resolve the executable runner.

## Artifact persistence

- Artifact store mode: `both`.
- File-backed project context: this file.
- Engram persistence was attempted for topic `sdd-init/PADA-3DACB-3d-acda-mmd` but the local Engram service was unavailable (`127.0.0.1:7437`). No Engram artifact is claimed.

## Guardrails for Phase 18e

- Prospective documentation/specification only.
- No runtime or scientific behavior changes.
- No modification of source/config/test files.
- Do not touch runs, results, or generated artifacts.
- Do not alter historical specs or docs.
- Create the Phase 18e specification only in a new spec directory, subject to separate review.
