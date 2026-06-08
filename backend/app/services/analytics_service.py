import math
from datetime import UTC, datetime
from app.db.redis_client import get_redis

class TelemetryService:
    @staticmethod
    async def track_request(user_id: str, key_prefix: str, status_code: int, latency_ms: float) -> None:
        """
        Atomically records a request event in Redis under user-specific metrics keys.
        Data is stored with a 7-day TTL to remain self-pruning and lightweight.
        """
        redis = get_redis()
        if not redis:
            return

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        current_hour = datetime.now(UTC).strftime("%H")

        # Define Redis keys
        requests_key = f"rateguard:analytics:{user_id}:requests:{today}"
        status_key = f"rateguard:analytics:{user_id}:status:{today}"
        keys_key = f"rateguard:analytics:{user_id}:keys:{today}"
        latency_key = f"rateguard:analytics:{user_id}:latency:{today}"

        try:
            # 1. Increment hourly traffic count (Redis Hash)
            await redis.hincrby(requests_key, current_hour, 1)
            await redis.expire(requests_key, 7 * 24 * 3600)  # 7 days TTL

            # 2. Increment status code count (Redis Hash)
            await redis.hincrby(status_key, str(status_code), 1)
            await redis.expire(status_key, 7 * 24 * 3600)

            # 3. Increment key-specific traffic count (Redis Hash)
            await redis.hincrby(keys_key, key_prefix, 1)
            await redis.expire(keys_key, 7 * 24 * 3600)

            # 4. Record latency (Redis Bounded List - keeps last 1000 items)
            await redis.rpush(latency_key, f"{latency_ms:.2f}")
            await redis.ltrim(latency_key, -1000, -1)
            await redis.expire(latency_key, 7 * 24 * 3600)

        except Exception as e:
            print(f"[Telemetry] Failed to record telemetry: {e}")

    @staticmethod
    async def get_analytics_summary(user_id: str) -> dict:
        """
        Compiles the last 24 hours of analytics metrics for Chart.js dashboard ingestion.
        Calculates percentiles (p50, p90, p99) and active client ratios.
        """
        redis = get_redis()
        if not redis:
            return {
                "hourly_requests": [0] * 24,
                "status_breakdown": {"2xx": 0, "4xx": 0, "5xx": 0},
                "latency_metrics": {"p50": 0.0, "p90": 0.0, "p99": 0.0},
                "top_keys": []
            }

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        
        requests_key = f"rateguard:analytics:{user_id}:requests:{today}"
        status_key = f"rateguard:analytics:{user_id}:status:{today}"
        keys_key = f"rateguard:analytics:{user_id}:keys:{today}"
        latency_key = f"rateguard:analytics:{user_id}:latency:{today}"

        try:
            # 1. Fetch hourly request metrics
            hourly_data = await redis.hgetall(requests_key) or {}
            hourly_requests = []
            for h in range(24):
                hour_str = f"{h:02d}"
                val = hourly_data.get(hour_str) or 0
                hourly_requests.append(int(val))

            # 2. Fetch status codes and categorize them
            status_data = await redis.hgetall(status_key) or {}
            status_breakdown = {"200": 0, "429": 0, "403": 0}
            for code, count_str in status_data.items():
                count = int(count_str)
                if code in status_breakdown:
                    status_breakdown[code] += count
                else:
                    # Categorize other codes if any
                    category = f"{code[0]}xx"
                    status_breakdown[category] = status_breakdown.get(category, 0) + count

            # 3. Calculate latency percentiles (p50, p90, p99)
            latency_strings = await redis.lrange(latency_key, 0, -1) or []
            latencies = sorted([float(x) for x in latency_strings])
            
            latency_metrics = {"p50": 0.0, "p90": 0.0, "p99": 0.0}
            if latencies:
                n = len(latencies)
                latency_metrics["p50"] = latencies[int(math.ceil(n * 0.5)) - 1]
                latency_metrics["p90"] = latencies[int(math.ceil(n * 0.9)) - 1]
                latency_metrics["p99"] = latencies[int(math.ceil(n * 0.99)) - 1]

            # 4. Compile active keys list
            keys_data = await redis.hgetall(keys_key) or {}
            top_keys = []
            for key_prefix, count_str in keys_data.items():
                top_keys.append({"prefix": key_prefix, "requests": int(count_str)})
            
            # Sort top keys descending by request volume
            top_keys = sorted(top_keys, key=lambda x: x["requests"], reverse=True)[:5]

            return {
                "hourly_requests": hourly_requests,
                "status_breakdown": status_breakdown,
                "latency_metrics": latency_metrics,
                "top_keys": top_keys
            }

        except Exception as e:
            print(f"[Telemetry] Summary error: {e}")
            return {
                "hourly_requests": [0] * 24,
                "status_breakdown": {"200": 0, "429": 0, "403": 0},
                "latency_metrics": {"p50": 0.0, "p90": 0.0, "p99": 0.0},
                "top_keys": []
            }
