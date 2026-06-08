# 🛡️ RateGuard — Distributed API Protection Platform

> A production-ready distributed API rate limiting and protection platform built with FastAPI, Redis, and MongoDB.

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com)
[![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=flat-square&logo=prometheus&logoColor=white)](https://prometheus.io)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-18%2F18%20passing-brightgreen?style=flat-square)](#-testing--verification)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

RateGuard secures backend services with microsecond latency overhead. It uses a **FastAPI gateway**, **Redis atomic Lua sliding-window checks (sub-2ms)**, and **MongoDB (Beanie ODM)** for analytics telemetry — keeping APIs secure, observable, and highly reliable.

---

## ⚡ Core Features

| 🔐 Identity & Auth | ⚡ Rate Limiting | 🛡️ Quota Enforcement | 📊 Observability |
| :--- | :--- | :--- | :--- |
| JWT access + refresh tokens | Redis sliding-window Lua script | Daily per-plan request caps | Live Chart.js telemetry dashboard |
| Google OAuth 2.0 SSO | Sub-2ms validation overhead | Atomic Redis quota increment | Prometheus `/metrics` exporter |
| Email + password registration | Plan-tiered limits (Free/Pro/Enterprise) | HMAC-SHA256 signed webhooks | Hourly traffic, latency percentiles (p50/p90/p99) |
| Bcrypt password hashing | Automatic key cache eviction on revoke | Quota warning & exceeded alerts | HTTP status breakdown (200/429/403) |

---

## 🏗️ Architecture & Request Flow

```text
              [ API Client Request ]
                        │
                        ▼  (X-API-Key / Authorization Bearer / ?api_key)
              [ FastAPI Gateway — /api/v1/limiter/check ]
                        │
        ┌───────────────┼──────────────────┐
        ▼  (Lua Script) ▼  (Background)    ▼  (Prometheus)
   [ Redis Cache ]  [ Beanie ODM ]     [ /metrics ]
  (Rate + Quota)   (Stats + Telemetry) (Request counters)
        │
        ├─► ✅ Allowed      → 200 OK  (X-RateLimit-* & X-Quota-* headers)
        ├─► 🚫 Rate Blocked → 429 Too Many Requests  (webhook cooldown alert)
        └─► 🚫 Quota Blocked → 403 Forbidden         (webhook dedup alert)
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI (Python 3.13+) with Uvicorn ASGI |
| **Rate Limiting** | Redis 7+ atomic Lua sliding-window script |
| **Database** | MongoDB 8.0+ via Beanie ODM (Motor async driver) |
| **Authentication** | JWT (python-jose) + Bcrypt (passlib) + Google OAuth 2.0 |
| **Webhooks** | HMAC-SHA256 signed payloads via httpx async client |
| **Monitoring** | Prometheus Client — custom request counter + latency histogram |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript + Chart.js |
| **Testing** | Pytest + pytest-asyncio + httpx ASGI client |
| **Linting** | Ruff |

---

## 📂 Project Structure

```text
rateguard/
├── .env.example                       ← Environment variable template
│
├── backend/
│   ├── .env                           ← Local environment config (gitignored)
│   ├── requirements.txt               ← Python dependencies
│   │
│   └── app/
│       ├── main.py                    ← FastAPI app entry point + CORS + security headers
│       │
│       ├── core/
│       │   ├── config.py              ← Settings (rate limits, quotas, JWT, OAuth)
│       │   ├── prometheus.py          ← Prometheus metrics (requests_counter, latency_histogram)
│       │   └── security.py            ← JWT encode/decode, bcrypt hash, SHA-256 key hash
│       │
│       ├── db/
│       │   ├── mongo.py               ← MongoDB async connection + Beanie init
│       │   └── redis_client.py        ← Redis async client (decode_responses=True)
│       │
│       ├── middleware/
│       │   └── deps.py                ← JWT bearer auth dependency (get_current_user)
│       │
│       ├── models/                    ← Beanie ODM document models
│       │   ├── api_key.py             ← APIKey (plan, scopes, daily counter + auto-reset)
│       │   ├── token.py               ← RefreshToken (rotation + revocation)
│       │   ├── user.py                ← User (email, Google ID, plan, role)
│       │   └── webhook.py             ← WebhookSetting (URL, HMAC secret, events)
│       │
│       ├── schemas/                   ← Pydantic request/response models
│       │   ├── api_key.py             ← APIKeyCreate, APIKeyOut, APIKeyCreated
│       │   └── auth.py                ← RegisterRequest (min 8 chars), LoginRequest, TokenPair, UserOut
│       │
│       ├── services/                  ← Business logic
│       │   ├── analytics_service.py   ← Redis telemetry read/write + percentile calculation
│       │   ├── api_key_service.py     ← Key generation, plan-limit enforcement, revoke, rotate
│       │   ├── auth_service.py        ← Register, login, token pair issue, refresh, revoke
│       │   ├── google_oauth.py        ← OAuth code exchange + userinfo fetch
│       │   ├── rate_limiter.py        ← Lua sliding window + quota check + expires_at enforcement
│       │   └── webhook.py             ← HMAC-SHA256 signed webhook dispatcher (httpx)
│       │
│       ├── api/v1/endpoints/          ← Route handlers
│       │   ├── analytics.py           ← GET /analytics/summary, GET /analytics/metrics
│       │   ├── auth.py                ← /auth/register, /login, /logout, /refresh, /me, /google/*
│       │   ├── health.py              ← GET /health
│       │   ├── keys.py                ← CRUD /keys + /keys/{id}/rotate
│       │   ├── limiter.py             ← POST /limiter/check (main rate limit gateway)
│       │   └── webhooks.py            ← GET/PUT /webhooks, POST /webhooks/test
│       │
│       └── tests/
│           ├── conftest.py            ← DB + Redis fixtures (uses rateguard_test DB)
│           ├── test_analytics.py      ← Prometheus + telemetry summary tests
│           ├── test_auth.py           ← OAuth, JWT, refresh, logout tests
│           ├── test_auth_email.py     ← Register + login credential tests
│           ├── test_keys.py           ← Key lifecycle (create, rotate, revoke) tests
│           ├── test_limiter.py        ← Rate limit + quota header tests
│           ├── test_quota_webhooks.py ← Webhook lifecycle + quota block tests
│           └── locustfile.py          ← Load testing scenarios (Locust)
│
└── frontend/
    ├── index.html                     ← Landing / marketing page
    ├── assets/css/main.css            ← Global dark-mode glassmorphism stylesheet
    ├── components/api.js              ← Shared API fetch client (Auth, apiFetch, toast)
    └── pages/
        ├── login.html                 ← Sign in (email/password + Google OAuth)
        ├── register.html              ← Account creation
        ├── dashboard.html             ← API Key management (create, rotate, revoke)
        ├── analytics.html             ← Real-time Chart.js telemetry (auto-refresh)
        ├── settings.html              ← Webhook configuration + test dispatcher
        ├── profile.html               ← User profile settings
        └── billing.html               ← Plan & billing overview
```

---

## 📋 Plan Tiers

| Plan | API Keys | Rate Limit | Daily Quota |
|------|----------|------------|-------------|
| **Free** | 3 keys | 60 req/min | 1,000 req/day |
| **Pro** | 20 keys | 600 req/min | 50,000 req/day |
| **Enterprise** | 100 keys | 6,000 req/min | 500,000 req/day |

---

## 📡 API Reference

**Base URL:** `http://localhost:8000/api/v1`  
**Interactive Docs:** http://localhost:8000/docs

### 🔐 Authentication

#### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "plan": "free"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "tokens": {
    "access_token": "<jwt>",
    "refresh_token": "<jwt>",
    "token_type": "bearer"
  },
  "user": { "id": "...", "email": "...", "name": "...", "plan": "free" },
  "is_new_user": false
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{ "refresh_token": "<jwt>" }
```

#### Logout
```http
POST /auth/logout
Content-Type: application/json

{ "refresh_token": "<jwt>" }
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer <access_token>
```

---

### 🔑 API Key Management

All endpoints require `Authorization: Bearer <access_token>`

#### List Keys
```http
GET /keys
```

#### Create Key
```http
POST /keys
Content-Type: application/json

{
  "name": "Production Server",
  "scopes": ["read", "write"]
}
```

**Response:** includes `raw_key` — copy it immediately, it is **never shown again**.

#### Revoke Key
```http
DELETE /keys/{key_id}
```

#### Rotate Key
```http
POST /keys/{key_id}/rotate
```

---

### 🛡️ Rate Limit Check

```http
POST /limiter/check
X-API-Key: rg_live_xxxxxxxxxxxxxxxx
```

**Response headers:**
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 60
X-Quota-Limit: 1000
X-Quota-Remaining: 998
X-Quota-Reset: 43147
```

API key can also be passed as `Authorization: Bearer <key>` or `?api_key=<key>`.

---

### 📊 Analytics

```http
GET /analytics/summary
Authorization: Bearer <access_token>
```

Returns: `hourly_requests[24]`, `status_breakdown`, `latency_metrics` (p50/p90/p99), `top_keys`.

---

### 🔔 Webhooks

#### Get Config
```http
GET /webhooks
Authorization: Bearer <access_token>
```

#### Update Config
```http
PUT /webhooks
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "is_active": true,
  "events": ["quota.approaching", "quota.exceeded", "rate_limit.exceeded"]
}
```

#### Test Webhook
```http
POST /webhooks/test
Authorization: Bearer <access_token>
Content-Type: application/json

{ "url": "https://your-server.com/webhook", "secret": "whsec_..." }
```

---

## 🔒 HMAC Webhook Verification

Every webhook delivery includes an `X-RateGuard-Signature` header in the format `t=<timestamp>,v1=<signature>`. Verify it on your server:

```python
import hmac, hashlib

def verify_rateguard_signature(payload: str, secret: str, timestamp: str, signature: str) -> bool:
    message = f"{timestamp}.{payload}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## ⚙️ Environment Variables

Create `backend/.env` (copy from `.env.example`):

```env
APP_ENV=development
FRONTEND_URL=http://localhost:5500

# MongoDB
MONGO_URL=mongodb://localhost:27017/rateguard
MONGO_DB=rateguard

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth (optional — leave blank to disable)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:5500/pages/login.html
```

---

## 🚀 Local Setup & Startup

### Prerequisites
- Python 3.13+
- MongoDB running on `localhost:27017`
- Redis (or Memurai on Windows) running on `localhost:6379`

---

### 🔧 Backend — FastAPI (port 8000)

```powershell
# Go to backend directory
cd backend

# First time only — create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# ▶ Start the backend (run this every time)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

| URL | Purpose |
|-----|---------|
| http://localhost:8000 | API root — `{"service": "RateGuard", "status": "running"}` |
| http://localhost:8000/docs | Swagger interactive API explorer |
| http://localhost:8000/redoc | ReDoc API reference |
| http://localhost:8000/metrics | Prometheus scrape endpoint |

---

### 🌐 Frontend — Static Dashboard (port 5500)

Open a **second terminal** (backend must be running first):

```powershell
# Go to frontend directory
cd frontend

# ▶ Start the frontend server (run this every time)
python -m http.server 5500
```

| URL | Page |
|-----|------|
| http://localhost:5500 | Landing page |
| http://localhost:5500/pages/login.html | Sign in |
| http://localhost:5500/pages/register.html | Create account |
| http://localhost:5500/pages/dashboard.html | API Keys dashboard |
| http://localhost:5500/pages/analytics.html | Telemetry & charts |
| http://localhost:5500/pages/settings.html | Webhook configuration |
| http://localhost:5500/pages/billing.html | Plan & billing |

---

## 🧪 Testing & Verification

```powershell
# Run full test suite (18 tests)
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v

# Run with output on failures
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short

# Run a specific test file
.venv\Scripts\python.exe -m pytest tests/test_limiter.py -v

# End-to-end webhook & quota manual runner
.venv\Scripts\python.exe tests/verify_phase4.py

# Load testing (requires backend running)
.venv\Scripts\python.exe -m locust -f tests/locustfile.py --host=http://localhost:8000
```

**Test coverage:** 18/18 passing ✅

| Test File | What it covers |
|-----------|---------------|
| `test_auth.py` | Health, root, OAuth login, JWT refresh, logout |
| `test_auth_email.py` | Register, duplicate email, login, wrong password |
| `test_keys.py` | Create, rotate, revoke key lifecycle |
| `test_limiter.py` | Rate limit check, response headers |
| `test_quota_webhooks.py` | Webhook lifecycle, quota blocking, bad URL |
| `test_analytics.py` | Prometheus metrics, telemetry summary |

---

## 📅 Project Phases

- [x] **Phase 1** — Mono-repo setup, MongoDB + Redis connections, Beanie ODM models
- [x] **Phase 2** — Identity layer: JWT auth, API key lifecycle, Google OAuth 2.0
- [x] **Phase 3** — Core engine: atomic sliding-window rate limiting via Redis Lua
- [x] **Phase 4** — Quota enforcement + HMAC-SHA256 signed webhooks + deduplication
- [x] **Phase 5** — Observability: Prometheus metrics + real-time Chart.js telemetry dashboard
- [x] **Phase 6** — Production hardening: security headers, CORS, plan limits, load testing
