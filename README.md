# TrustGuard Monorepo (MVP)

This repository contains a production-aligned scaffold for the TrustGuard platform:

- Node.js API Gateway (Express + TypeScript + Mongoose)
- Next.js Frontend (Redux Toolkit + MUI + Tailwind)
- Python Flask ML microservices (Identity + Grievance)
- MongoDB via Docker
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
- API: http://localhost:8080/api/health
- Frontend: http://localhost:3000
- Identity ML: http://localhost:5001/health
- Grievance ML: http://localhost:5002/health

## Services

- api-gateway: Express TypeScript server exposing REST endpoints under /api
- next-frontend: Next.js app consuming the API
- identity-ml: Flask service with /predict
- grievance-ml: Flask service with /categorize

## API Conventions

All responses follow { success, data, error, statusCode }.

Routes:
- /api/auth/register, /api/auth/login, /api/auth/profile
- /api/identity/verify, /api/identity/checks
- /api/app/official (GET, POST), /api/app/suspicious (GET, POST)
- /api/grievance (GET, POST), /api/grievance/analytics

Auth: Bearer JWT (24h expiry). Passwords hashed with bcrypt.

## Dev without Docker

API
```
cd api-gateway
npm install
npm run dev
```
Ensure MongoDB is running and .env has MONGODB_URI, DATABASE_NAME, JWT_SECRET.

Frontend
```
cd next-frontend
npm install
npm run dev
```
Set NEXT_PUBLIC_API_URL to your API (e.g., http://localhost:8080/api).

## Notes

- The existing FastAPI + Vite prototype remains for live preview here. The Node/Next stack is fully scaffolded for local/docker use.
- ML calls include safe fallbacks when services are unavailable.
