"""In-process metrics used by the dashboard and API health checks.

Metrics intentionally contain no request body or personally identifiable data.
"""
from collections import Counter, deque
from threading import Lock
from time import time

class Metrics:
    def __init__(self):
        self.lock, self.latencies, self.recent, self.counters = Lock(), deque(maxlen=500), deque(maxlen=500), Counter()

    def record(self, route: str, duration_ms: float, status_code: int):
        with self.lock:
            self.latencies.append(duration_ms)
            self.recent.append({"at": time(), "route": route, "duration_ms": round(duration_ms, 2), "status": status_code})
            self.counters["requests"] += 1
            if status_code >= 400: self.counters["failures"] += 1

    def increment(self, name: str, count: int = 1):
        with self.lock: self.counters[name] += count

    def snapshot(self):
        with self.lock:
            samples = list(self.latencies)
            ordered = sorted(samples)
            p95 = ordered[max(0, int(len(ordered) * .95) - 1)] if ordered else 0
            return {"requests": self.counters["requests"], "failures": self.counters["failures"],
                    "avg_latency_ms": round(sum(samples) / len(samples), 2) if samples else 0,
                    "p95_latency_ms": round(p95, 2), "token_usage": self.counters["token_usage"],
                    "retrieval_failures": self.counters["retrieval_failures"], "recent_requests": list(self.recent)[-20:]}

metrics = Metrics()
