# 🛡️ RateGuard — Distributed API Protection Platform

> A production-ready, ultra-high-performance distributed API rate limiting and protection platform built with FastAPI, Redis, and MongoDB.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white)](https://prometheus.io)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

RateGuard is designed to secure backend services with microsecond latency overhead. Powered by a high-performance **FastAPI Gateway**, **Redis atomic Lua sliding-window checks (under 2ms)**, and asynchronous **MongoDB (Beanie ODM)** analytics telemetry, it keeps your APIs secure, observable, and highly reliable.

---

## ⚡ Core Pillars

| 🔐 Secure Identity | ⚡ High-Speed Rate Limiting | 🛡️ Smart Quota Blocks | 📊 Deep Observability |
| :--- | :--- | :--- | :--- |
| • JWT & Refresh Tokens<br>• Google OAuth 2.0 SSO<br>• SHA-256 API Key hashing | • Redis sliding-window check<br>• Sub-**2ms** request validation<br>• Dynamic, plan-tiered limits | • Daily usage quota caps<br>• HMAC-SHA256 signed webhooks<br>• Active blocks & alerts | • Live telemetry history<br>• Prometheus `/metrics` exporter<br>• Glassmorphism admin charts |

---

## 🏗️ Architecture & Request Flow

Below is the conceptual architecture of how an incoming request is validated, logged, and metered:

```text
               [ API Client Request ]
                         │
                         ▼ (with X-API-Key)
               [ FastAPI Gateway App ]
                         │
         ┌───────────────┼───────────────┐
         ▼ (Lua Script)  ▼ (Prometheus)  ▼ (Async Tasks)
     [ Redis Cache ]  [ /metrics ]    [ Beanie ODM ]
    (Limits & Quotas) (Request counts) (Mongo Telemetry)
         │
         ├─► [ Approved ]  ───────► 200 OK (X-RateLimit & X-Quota headers)
         │
         ├─► [ Rate Blocked ] ────► 429 Too Many Requests (Cooldown Alert)
         │
         └─► [ Quota Blocked ] ───► 403 Forbidden (Quota Exceeded Alert)
```

---

## 🛠️ Technology Stack

* **Gateway API**: FastAPI (Python 3.12+)
* **Identity Protocol**: Google OAuth 2.0 + PyJWT Session Security
* **Caching & Key-Value**: Redis 7+ (Memurai for Native Windows support)
* **Primary Database**: MongoDB 8.0+ (Beanie Object-Document Mapper)
* **Metering & Monitoring**: Prometheus Client (`/metrics` scraping endpoint)
* **Visualization**: Interactive Chart.js gauges & real-time telemetry panels
* **Testing & Linting**: Pytest + Ruff

---

## 📂 Project Structure & File Map

The following directory tree maps the exact files present in the RateGuard codebase and their architectural roles:

```text
rateguard/
├── .env.example                       ← Environment templates
├── ruff.toml                          ← Linting guidelines
│
├── backend/
│   ├── requirements.txt               ← Dependencies list (including prometheus-client)
│   ├── app/
│   │   ├── main.py                    ← FastAPI entry point & metrics endpoint scraper
│   │   │
│   │   ├── core/                      ← Security & Metric Configuration
│   │   │   ├── config.py              ← Environment parsing, limits, & quota configs
│   │   │   ├── prometheus.py          ← Custom Prometheus metrics (requests, latency)
│   │   │   └── security.py            ← JWT encoding/decoding & bcrypt password hashing
│   │   │
│   │   ├── db/                        ← Connection Initializations
│   │   │   ├── mongo.py               ← MongoDB async connection & Beanie registration
│   │   │   └── redis_client.py        ← Redis/Memurai client pool setup
│   │   │
│   │   ├── middleware/                ← Authentication Dependencies
│   │   │   └── deps.py                ← JWT verify & current active user checkers
│   │   │
│   │   ├── models/                    ← Beanie ODM Schemas
│   │   │   ├── api_key.py             ← APIKey record model
│   │   │   ├── token.py               ← JWT RefreshToken model
│   │   │   ├── user.py                ← User record model
│   │   │   └── webhook.py             ← WebhookSetting model
│   │   │
│   │   ├── schemas/                   ← Pydantic Data Validations
│   │   │   ├── api_key.py             ← API Key request & response models
│   │   │   ├── user.py                ← User auth request & response models
│   │   │   └── webhook.py             ← Webhook configurations CRUD models
│   │   │
│   │   ├── services/                  ← Core Business Logic
│   │   │   ├── analytics_service.py   ← DB aggregation analytics & request counters
│   │   │   ├── api_key_service.py     ← API Key generation & database lifecycles
│   │   │   ├── auth_service.py        ← User verification & credentials hashing
│   │   │   ├── google_oauth.py        ← Google OAuth code & user info exchange
│   │   │   ├── rate_limiter.py        ← Sliding window Lua executor & daily quota tracker
│   │   │   └── webhook.py             ← HMAC-SHA256 signature generator & dispatcher
│   │   │
│   │   └── api/v1/endpoints/          ← Route Handlers
│   │       ├── analytics.py           ← Telemetry analytics summary endpoints
│   │       ├── auth.py                ← Registration, login, logout, & callback handlers
│   │       ├── health.py              ← System availability endpoints
│   │       ├── keys.py                ← API Key CRUD endpoint router
│   │       ├── limiter.py             ← Rate Limit checker & daily quota gatekeeper
│   │       └── webhooks.py            ← Webhook settings controller endpoints
│   │
│   └── tests/                         ← Pytest Suite & E2E Validation
│       ├── conftest.py                ← Shared database & event loop fixtures
│       ├── test_analytics.py          ← Prometheus /metrics & DB telemetry tests
│       ├── test_auth.py               ← Auth endpoints & callback verification tests
│       ├── test_auth_email.py         ← Credentials registration & login tests
│       ├── test_keys.py               ← API Key lifecycle & permissions tests
│       ├── test_limiter.py            ← Sliding window Lua rate limit flow tests
│       ├── test_quota_webhooks.py     ← Webhook triggers & quota blocks tests
│       └── verify_phase4.py           ← End-to-End manual webhook simulation runner
│
└── frontend/                          ← Vanilla JS Dashboard Client
    ├── index.html                     ← Landings & Marketing page
    │
    ├── assets/css/
    │   └── main.css                   ← Premium Glassmorphism styling sheets
    │
    ├── components/
    │   └── api.js                     ← Modular API endpoint caller library
    │
    └── pages/                         ← Interactive Console Views
        ├── analytics.html             ← Real-time telemetry dashboard (Chart.js charts)
        ├── billing.html               ← Subscriptions billing mock panels
        ├── dashboard.html             ← Core workspace dashboard (Key generators UI)
        ├── login.html                 ← Auth entrance interface
        ├── profile.html               ← Settings, profile fields, & user data
        ├── register.html              ← Sign-up credentials creation
        └── settings.html              ← Webhooks dispatch dashboard configuration
```

---

## 📡 Essential API Reference

### 🔐 Authentication

#### Register Account
`POST /api/v1/auth/register`
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

#### Get JWT Access Token
`POST /api/v1/auth/login` (Content-Type: `application/x-www-form-urlencoded`)
```
username=user%40example.com&password=SecurePassword123
```

---

### 🔑 API Key Management

#### Generate API Key
`POST /api/v1/keys` (Bearer Token required)
```json
{
  "name": "Production Server Key",
  "scopes": ["read", "write"]
}
```
* **Response**:
```json
{
  "id": "6446e1...",
  "name": "Production Server Key",
  "prefix": "rg_live_9ef2...",
  "raw_key": "rg_live_9ef271cb465a3d07e60241cfc8466b0a",
  "plan": "free"
}
```

---

### 🛡️ Rate Limiting Validation

#### Check Key Limit & Quotas
`POST /api/v1/limiter/check`
* **Header**: `X-API-Key: rg_live_9ef271cb465a3d07e60241cfc8466b0a`
* **Response Headers**:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 60
X-Quota-Limit: 1000
X-Quota-Remaining: 999
X-Quota-Reset: 43200
```

---

## 🔒 HMAC Webhook Verification

Webhooks are signed using **HMAC-SHA256** inside the `X-RateGuard-Signature` header to ensure secure delivery. Validate payloads as follows:

```python
import hmac
import hashlib

def verify_rateguard_signature(payload: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 🚀 Local Windows Setup

### 1. Requirements
Ensure **Python 3.12+**, **MongoDB** (`localhost:27017`), and **Memurai/Redis** (`localhost:6379`) are running.

### 2. Environment Configuration
Create a `.env` file in the `backend/` directory:
```bash
cp .env.example .env
```

### 3. Server Startup

* **Start FastAPI Backend**:
  ```bash
  cd backend
  python -m venv .venv
  .venv/Scripts/activate
  pip install -r requirements.txt
  uvicorn app.main:app --reload
  ```
  *(Backend docs live at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) and metrics at [/metrics](http://127.0.0.1:8000/metrics))*

* **Start Static Frontend Dashboard**:
  ```bash
  cd frontend
  python -m http.server 5500
  ```
  *(Dashboard console opens at [http://localhost:5500](http://localhost:5500))*

---

## 🧪 Testing & Verification

* **Execute Pytests**:
  ```bash
  $env:PYTHONPATH="."
  .venv/Scripts/python -m pytest tests -v
  ```
* **Verify Webhooks & Quotas E2E**:
  ```bash
  .venv/Scripts/python tests/verify_phase4.py
  ```

---

## 📅 Roadmap Status

- [x] **Phase 1**: Mono-repo structure & Local Redis/MongoDB setups.
- [x] **Phase 2**: Identity layer (JWT, API Key lifecycles & Google OAuth).
- [x] **Phase 3**: Core Engine (Atomic sliding window rate limiting).
- [x] **Phase 4**: Quota Enforcement & Stripe-compliant HMAC Webhooks.
- [x] **Phase 5**: Observability Dashboard (Prometheus metrics & Telemetry dashboard UI).
- [ ] **Phase 6**: Production Hardening & Load Testing.
