import random
import string
from locust import HttpUser, task, between

class LocustRateLimiterUser(HttpUser):
    # Simulate a realistic user pacing (between 0.5 to 2.0 seconds between tasks)
    wait_time = between(0.5, 2.0)
    
    def on_start(self):
        """
        Setup procedure: Create a dynamic user, authenticate, and generate a valid API key.
        """
        self.email = f"locust-{self._random_string(8)}@example.com"
        self.password = "LocustPassword123!"
        self.auth_token = None
        self.api_key = None
        
        # 1. Register a new user
        register_payload = {
            "email": self.email,
            "password": self.password,
            "first_name": "Locust",
            "last_name": "Tester"
        }
        with self.client.post("/api/v1/auth/register", json=register_payload, catch_response=True) as resp:
            if resp.status_code in [200, 201]:
                resp.success()
            else:
                resp.failure(f"Registration failed with code {resp.status_code}: {resp.text}")
                return

        # 2. Authenticate to receive JWT
        login_payload = {
            "email": self.email,
            "password": self.password
        }
        with self.client.post("/api/v1/auth/login", json=login_payload, catch_response=True) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.auth_token = data.get("tokens", {}).get("access_token")
                resp.success()
            else:
                resp.failure(f"Login failed with code {resp.status_code}: {resp.text}")
                return

        # 3. Create a dynamic API key
        if self.auth_token:
            key_headers = {"Authorization": f"Bearer {self.auth_token}"}
            key_payload = {
                "name": f"Locust-Key-{self._random_string(4)}",
                "scopes": ["read", "write"]
            }
            with self.client.post("/api/v1/keys", json=key_payload, headers=key_headers, catch_response=True) as resp:
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    self.api_key = data.get("raw_key")
                    resp.success()
                else:
                    resp.failure(f"API Key creation failed with code {resp.status_code}: {resp.text}")

    @task(90)
    def check_limiter_allowed(self):
        """
        Simulate standard client traffic hitting the limiter checker.
        """
        if not self.api_key:
            return  # Skip task if setup failed
            
        headers = {"X-API-Key": self.api_key}
        with self.client.post("/api/v1/limiter/check", headers=headers, catch_response=True) as resp:
            if resp.status_code in [200, 429, 403]:
                # Status 429 and 403 are expected behavioral codes under high load blocks
                resp.success()
            else:
                resp.failure(f"Limiter check returned unexpected status {resp.status_code}: {resp.text}")

    @task(5)
    def get_analytics_summary(self):
        """
        Simulate admin console user fetching real-time telemetry metrics.
        """
        if not self.auth_token:
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        with self.client.get("/api/v1/analytics/summary", headers=headers, catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Analytics summary fetch failed with code {resp.status_code}")

    @task(5)
    def check_gateway_health(self):
        """
        Simulate heartbeat checks from monitoring systems.
        """
        with self.client.get("/api/v1/health", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Gateway health check failed with status {resp.status_code}")

    def _random_string(self, length):
        letters = string.ascii_lowercase + string.digits
        return ''.join(random.choice(letters) for _ in range(length))
