"""Read-only Phase 18 real-run authorization checker."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml  # noqa: E402

from pada3dacb.publication.authorization import check_authorization, format_blockers  # noqa: E402

DEFAULT_CONFIG = Path("configs/publication/real_run_authorization.yaml")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        manifest = _load(args.config)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"REAL RUN NOT AUTHORIZED\n- configuration_error: {exc}")
        print("PASS — FAIL-CLOSED AUTHORIZATION VERIFIED")
        return 2

    result = check_authorization(manifest)
    if not result.authorized:
        print("REAL RUN NOT AUTHORIZED")
        print("BLOCKERS:")
        print(format_blockers(result))
        print("PASS — FAIL-CLOSED AUTHORIZATION VERIFIED")
        return 1
    print("REAL RUN AUTHORIZED RECORD IS COMPLETE; this read-only checker opened no data path.")
    return 0


def _load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("configuration root must be a mapping")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
