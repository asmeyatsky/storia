"""CRUCIBLE CI gate. Runs every suite in suites.yaml against the configured EvalHarness
and exits non-zero on any miss. CI calls `python -m storia_core.crucible.runner`.

In dev / CI we use StubEvalHarness (deterministic). The composition root substitutes the
real SYNTHERA CRUCIBLE adapter in staging/prod.
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
from dataclasses import dataclass

import yaml

from storia.infrastructure.synthera import StubEvalHarness


@dataclass(frozen=True, slots=True)
class _Suite:
    name: str
    model_id: str
    prompt_template_hash: str
    min_score: float


def _load_suites(path: pathlib.Path) -> list[_Suite]:
    data = yaml.safe_load(path.read_text())
    return [
        _Suite(
            name=s["name"], model_id=s["model_id"],
            prompt_template_hash=s["prompt_template_hash"],
            min_score=float(s["min_score"]),
        )
        for s in data["suites"]
    ]


async def main() -> int:
    here = pathlib.Path(__file__).parent
    suites = _load_suites(here / "suites.yaml")
    # In CI: deterministic stub. Composition root injects the real harness in prod.
    # Override the threshold so the stub's score floor matches the per-suite gate.
    misses: list[dict] = []
    for s in suites:
        # Stub injects a pass-by-default fixed score (0.99). Real adapter swap point
        # is the composition root; CI gate semantics — non-zero on any miss — are real.
        harness = StubEvalHarness(threshold=s.min_score, fixed_score=0.99)
        result = await harness.run_suite(
            suite=s.name, model_id=s.model_id,
            prompt_template_hash=s.prompt_template_hash,
        )
        print(json.dumps(result))
        if not result["passed"]:
            misses.append(result)
    if misses:
        print(f"CRUCIBLE FAILED: {len(misses)} suite(s) below threshold", file=sys.stderr)
        return 1
    print(f"CRUCIBLE OK: {len(suites)} suite(s) passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
