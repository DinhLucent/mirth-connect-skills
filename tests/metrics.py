from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ScenarioMeasurement:
    name: str
    category: str
    iterations: int
    ok: bool
    durations_ms: list[float] = field(default_factory=list)
    request_count_delta: int = 0
    errors: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def mean_ms(self) -> float:
        return statistics.fmean(self.durations_ms) if self.durations_ms else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.durations_ms:
            return 0.0
        values = sorted(self.durations_ms)
        index = min(len(values) - 1, int(round((len(values) - 1) * 0.95)))
        return values[index]

    @property
    def max_ms(self) -> float:
        return max(self.durations_ms) if self.durations_ms else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "iterations": self.iterations,
            "ok": self.ok,
            "mean_ms": round(self.mean_ms, 3),
            "p95_ms": round(self.p95_ms, 3),
            "max_ms": round(self.max_ms, 3),
            "request_count_delta": self.request_count_delta,
            "errors": self.errors,
            "details": self.details,
        }


def timed_call(fn: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter()
    result = fn()
    duration_ms = (time.perf_counter() - start) * 1000
    return result, duration_ms


def score_measurements(measurements: list[ScenarioMeasurement]) -> dict[str, Any]:
    total = len(measurements)
    passed = sum(1 for item in measurements if item.ok)
    failed = total - passed
    mean_ms = statistics.fmean([item.mean_ms for item in measurements]) if measurements else 0.0
    p95_ms = max((item.p95_ms for item in measurements), default=0.0)
    total_requests = sum(item.request_count_delta for item in measurements)
    score = round((passed / total) * 100, 2) if total else 0.0
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "score": score,
        "mean_ms": round(mean_ms, 3),
        "worst_p95_ms": round(p95_ms, 3),
        "total_mock_requests": total_requests,
    }
