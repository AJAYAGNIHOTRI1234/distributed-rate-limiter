# RateGuard — Distributed API Protection Platform

RateGuard is a high-performance distributed rate limiting and API protection platform built with FastAPI, Redis (Memurai), and MongoDB.

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Vanilla JS + Premium Glassmorphism UI |
| Theme | Day/Night (Light/Dark) Mode Support |
| Backend | FastAPI + Python 3.12 |
| Auth | Google OAuth 2.0 + JWT (python-jose) |
| Database | MongoDB 8.2 (Native Windows) |
| Cache | Redis 7+ (Memurai) |
| Code Quality | Ruff + Pytest |

---

## Project Structure

```
rateguard/
├── .env.example             ← Environment template
├── ruff.toml                ← Linting configuration
├── .github/workflows/ci.yml ← CI/CD Pipeline
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py          ← FastAPI Entry Point
│   │   ├── core/            ← Config & Security
│   │   ├── db/              ← Mongo & Redis initialization
│   │   ├── models/          ← Beanie Documents
│   │   ├── schemas/         ← Pydantic Models
│   │   ├── services/        ← Business Logic
│   │   ├── middleware/      ← Auth Dependencies
│   │   └── api/v1/          ← API Endpoints
│   └── tests/               ← Unit & Integration Tests
│
└── frontend/                ← Vanilla JS Dashboard
    ├── index.html           ← Landing Page
    ├── pages/               ← Dashboard, Profile, Billing, Settings, Analytics
    ├── assets/              ← CSS & Images
    └── components/          ← API Client (api.js)
```

---

## Local Setup (Native Windows)

### 1. Prerequisites
- **Python 3.12+**
- **MongoDB**: Ensure MongoDB service is running on `localhost:27017`.
- **Memurai (Redis)**: Ensure Memurai service is running on `localhost:6379`.

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env
cp ../.env.example .env
```

### 3. Verification of Identity Layer

Run the comprehensive test suite to verify Auth and API Key logic:

```powershell
# Set PYTHONPATH to include the app
$env:PYTHONPATH="backend"

# Run tests
.venv/Scripts/python -m pytest backend/tests -v
```

All 12 tests should pass, confirming that JWT and API Key lifecycles are secure.

### 4. Running the App
```bash
# Start backend
uvicorn app.main:app --reload

# Start frontend (using python server as example)
cd ../frontend && python -m http.server 5500
```
Open [http://localhost:5500](http://localhost:5500) to access the platform.

---

## Roadmap

- [x] **Phase 1**: Mono-repo, Native environment setup (Redis + Mongo), CI Pipeline.
- [x] **Phase 2**: Identity & Lifecycle (JWT Auth, API Key CRUD).
- [x] **Frontend Polish**: Fully navigable dashboard with Profile, Billing, Settings, and Day/Night mode.
- [x] **Phase 3**: Core Engine (Redis Lua Sliding Window Rate Limiting).
- [x] **Phase 4**: Quota Enforcement & Webhooks (Daily blocks & Stripe-compliant HMAC signed Webhooks).
- [/] **Phase 5**: Observability & Real-Time Dashboard (Prometheus /metrics & in-console telemetry UI) — *In Progress*.
- [ ] **Phase 6**: Production Hardening & Load Testing.

