# TrustGuard Monorepo (MVP)

This repository contains a production-aligned scaffold for the TrustGuard platform:

- FastAPI backend (Python) with PostgreSQL via SQLAlchemy
- Next.js Frontend (Redux Toolkit + MUI + Tailwind)
- Python Flask ML microservices (Identity + Grievance)
- PostgreSQL via Docker
- End-to-end orchestration with docker-compose

## Getting Started (Docker)

1. Copy environment template

```
cp .env.example .env
```

2. Build & run all services

```
docker compose up --build
```

3. Open apps
- API: http://localhost:8080/health
- Frontend: http://localhost:3000
- Identity ML: http://localhost:5001/health
- Grievance ML: http://localhost:5002/health

After containers are healthy, run DB migrations (in another terminal):

```
docker compose exec api alembic upgrade head
```

## Services

- api: FastAPI server exposing REST endpoints under /api
- next-frontend: Next.js app consuming the API
- identity-ml: Flask service with /predict
- grievance-ml: Flask service with /categorize
- postgres: PostgreSQL database

## API Conventions

All responses follow { success, data, error, statusCode }.

Routes:
- /api/auth/register, /api/auth/login, /api/auth/me
- /api/identity/verify, /api/identity/result/:id
- /api/app/registry (GET, POST), /api/app/suspicious (GET)
- /api/grievance/file (POST), /api/grievance/status/:id (GET), /api/grievance/analytics (GET)

Auth: Bearer JWT (24h expiry). Passwords hashed with bcrypt.

## Dev without Docker

Backend
```
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/trustguard
uvicorn main:app --reload --port 8080
```
Run migrations:
```
alembic upgrade head
```

Frontend
```
cd next-frontend
npm install
npm run dev
```
Set NEXT_PUBLIC_API_URL to your API (e.g., http://localhost:8080/api).

## Notes

- The backend now uses PostgreSQL with SQLAlchemy and Alembic for migrations.
- ML calls include safe fallbacks when services are unavailable.
