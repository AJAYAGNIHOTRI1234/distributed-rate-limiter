from prometheus_client import Counter, Histogram
from prometheus_client.registry import REGISTRY

# Safely check REGISTRY to avoid duplicate registration exceptions during Uvicorn reloading
if "rateguard_requests_total" not in REGISTRY._names_to_collectors:
    requests_counter = Counter(
        "rateguard_requests_total",
        "Total number of API check requests processed by RateGuard",
        ["status", "plan"]
    )
else:
    requests_counter = REGISTRY._names_to_collectors["rateguard_requests_total"]

if "rateguard_request_latency_seconds" not in REGISTRY._names_to_collectors:
    latency_histogram = Histogram(
        "rateguard_request_latency_seconds",
        "API check request latency in seconds",
        buckets=(0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)
    )
else:
    latency_histogram = REGISTRY._names_to_collectors["rateguard_request_latency_seconds"]
