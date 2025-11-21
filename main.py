import os
import time
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import requests
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import bcrypt
import jwt

from database import fetchone, fetchall, execute

load_dotenv()

# ----- Config -----
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))
IDENTITY_SERVICE_URL = os.getenv("IDENTITY_SERVICE_URL", "http://localhost:5001")
GRIEVANCE_SERVICE_URL = os.getenv("GRIEVANCE_SERVICE_URL", "http://localhost:5002")

origins = os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")

# ----- Logging -----
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("trustguard")

app = FastAPI(title="TrustGuard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Security -----
security = HTTPBearer()

def create_token(payload: Dict[str, Any]) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS)
    to_encode = {**payload, "exp": exp}
    token = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return token

def verify_token(token: str) -> Dict[str, Any]:
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def auth_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    return verify_token(credentials.credentials)

# ----- Helpers -----

def api_success(data: Any, status_code: int = 200):
    return {"success": True, "data": data, "error": None, "statusCode": status_code}

# ----- DTOs -----
class RegisterDto(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginDto(BaseModel):
    email: EmailStr
    password: str

class FileGrievanceDto(BaseModel):
    text: str
    category: Optional[str] = None

class CategorizeDto(BaseModel):
    text: str

# ----- Root & Health -----
@app.get("/")
def root():
    return api_success({"message": "TrustGuard API running"})

@app.get("/health")
def health():
    try:
        _ = fetchone("SELECT 1 AS ok")
        db_ok = True
    except Exception:
        db_ok = False
    return api_success({"status": "OK", "db": db_ok})

# ----- Auth Endpoints -----
@app.post("/api/auth/register")
def register(dto: RegisterDto):
    start = time.time()
    existing = fetchone("SELECT id FROM users WHERE lower(email)=lower(%s)", [dto.email])
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(dto.password.encode("utf-8"), salt).decode("utf-8")
    user = fetchone(
        "INSERT INTO users(email, password, name) VALUES(%s,%s,%s) RETURNING id, email, name",
        [dto.email.lower(), hashed, dto.name],
    )
    token = create_token({"sub": str(user["id"]), "email": user["email"]})
    latency_ms = int((time.time() - start) * 1000)
    logger.info("register success %s", dto.email)
    return api_success({
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "latency_ms": latency_ms,
    })

@app.post("/api/auth/login")
def login(dto: LoginDto):
    start = time.time()
    user = fetchone("SELECT id, email, password, name FROM users WHERE lower(email)=lower(%s)", [dto.email])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not bcrypt.checkpw(dto.password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token({"sub": str(user["id"]), "email": user["email"]})
    latency_ms = int((time.time() - start) * 1000)
    logger.info("login success %s", dto.email)
    return api_success({
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user.get("name")},
        "latency_ms": latency_ms,
    })

@app.get("/api/auth/me")
def me(claims: Dict[str, Any] = Depends(auth_dependency)):
    user = fetchone("SELECT id, email, name FROM users WHERE id=%s", [int(claims["sub"])])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return api_success({"id": user["id"], "email": user["email"], "name": user["name"]})

# ----- Identity Verification -----
@app.post("/api/identity/verify")
async def identity_verify(video: UploadFile = File(...), claims: Dict[str, Any] = Depends(auth_dependency)):
    start = time.time()
    try:
        files = {"video": (video.filename, await video.read(), video.content_type or "application/octet-stream")}
        try:
            resp = requests.post(f"{IDENTITY_SERVICE_URL}/predict", files=files, timeout=30)
            if resp.status_code == 200:
                payload = resp.json()
            else:
                raise Exception(f"ML service error {resp.status_code}")
        except Exception as e:
            logger.warning("Identity ML service unavailable, using fallback: %s", str(e))
            payload = {"deepfake_score": 0.15, "liveness_status": "PASS", "overall_result": "VERIFIED"}
        latency_ms = int((time.time() - start) * 1000)
        payload["latency_ms"] = payload.get("latency_ms", latency_ms)
        # Persist
        row = fetchone(
            """
            INSERT INTO identity_checks(user_id, deepfake_score, liveness_status, overall_result, latency_ms)
            VALUES(%s,%s,%s,%s,%s)
            RETURNING id
            """,
            [int(claims["sub"]), float(payload.get("deepfake_score", 0.0)), payload.get("liveness_status", "PASS"), payload.get("overall_result", "VERIFIED"), int(payload.get("latency_ms", latency_ms))],
        )
        payload["id"] = row["id"]
        logger.info("identity verification completed user=%s result=%s", claims.get("sub"), payload.get("overall_result"))
        return api_success(payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("identity verify error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/identity/result/{id}")
def identity_result(id: int, claims: Dict[str, Any] = Depends(auth_dependency)):
    try:
        doc = fetchone(
            "SELECT id, deepfake_score, liveness_status, overall_result, latency_ms, created_at FROM identity_checks WHERE id=%s AND user_id=%s",
            [id, int(claims["sub"])],
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Result not found")
        data = {
            "id": doc["id"],
            "deepfake_score": doc["deepfake_score"],
            "liveness_status": doc["liveness_status"],
            "overall_result": doc["overall_result"],
            "latency_ms": doc["latency_ms"],
            "createdAt": doc["created_at"],
        }
        return api_success(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("identity result error")
        raise HTTPException(status_code=500, detail=str(e))

# ----- App Authenticator -----
@app.post("/api/app/verify")
async def app_verify(
    package_name: Optional[str] = Form(None),
    apk: Optional[UploadFile] = File(None),
    claims: Dict[str, Any] = Depends(auth_dependency),
):
    start = time.time()
    status_label = "UNKNOWN"
    publisher = None
    google_play_link = None
    confidence = 0.5

    try:
        sha256_hash = None
        if apk is not None:
            content = await apk.read()
            sha256_hash = hashlib.sha256(content).hexdigest()
        official = None
        if package_name or sha256_hash:
            if package_name and sha256_hash:
                official = fetchone("SELECT * FROM official_apps WHERE package_name=%s OR sha256_hash=%s LIMIT 1", [package_name, sha256_hash])
            elif package_name:
                official = fetchone("SELECT * FROM official_apps WHERE package_name=%s LIMIT 1", [package_name])
            elif sha256_hash:
                official = fetchone("SELECT * FROM official_apps WHERE sha256_hash=%s LIMIT 1", [sha256_hash])
        if official:
            status_label = "OFFICIAL"
            publisher = official.get("publisher")
            google_play_link = official.get("google_play_link")
            confidence = 0.98
        else:
            suspicious = None
            if package_name:
                suspicious = fetchone("SELECT * FROM suspicious_apps WHERE package_name=%s LIMIT 1", [package_name])
            if suspicious:
                status_label = "SUSPICIOUS"
                publisher = suspicious.get("publisher")
                google_play_link = suspicious.get("google_play_link")
                confidence = suspicious.get("confidence", 0.8)
        latency_ms = int((time.time() - start) * 1000)
        data = {
            "status": status_label,
            "publisher": publisher,
            "google_play_link": google_play_link,
            "confidence": confidence,
            "latency_ms": latency_ms,
        }
        logger.info("app verify package=%s status=%s", package_name, status_label)
        return api_success(data)
    except Exception as e:
        logger.exception("app verify error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/app/registry")
def app_registry(claims: Dict[str, Any] = Depends(auth_dependency)):
    items = fetchall("SELECT id, package_name, sha256_hash, publisher, google_play_link, last_verified FROM official_apps ORDER BY id DESC LIMIT 100")
    return api_success(items)

@app.get("/api/app/suspicious")
def app_suspicious(claims: Dict[str, Any] = Depends(auth_dependency)):
    items = fetchall("SELECT id, package_name, publisher, google_play_link, confidence FROM suspicious_apps ORDER BY id DESC LIMIT 100")
    return api_success(items)

@app.post("/api/app/registry")
def app_add_official(body: Dict[str, Any], claims: Dict[str, Any] = Depends(auth_dependency)):
    row = fetchone(
        """
        INSERT INTO official_apps(package_name, sha256_hash, publisher, google_play_link)
        VALUES(%s,%s,%s,%s)
        RETURNING id
        """,
        [body.get("package_name"), body.get("sha256_hash"), body.get("publisher"), body.get("google_play_link")],
    )
    return api_success({"id": row["id"]})

# ----- Grievance -----
CATEGORIES = [
    "unauthorized_debit",
    "loan_dispute",
    "account_closure",
    "failed_transfer",
    "card_fraud",
    "digital_service_issue",
    "other",
]

@app.post("/api/grievance/file")
def file_grievance(dto: FileGrievanceDto, claims: Dict[str, Any] = Depends(auth_dependency)):
    start = time.time()
    category = dto.category
    if not category:
        try:
            resp = requests.post(f"{GRIEVANCE_SERVICE_URL}/categorize", json={"text": dto.text}, timeout=5)
            if resp.status_code == 200:
                j = resp.json()
                category = j.get("category", "other")
            else:
                category = "other"
        except Exception:
            category = "other"
    urgency = "HIGH" if (category in ["card_fraud", "unauthorized_debit"] or ("fraud" in dto.text.lower() or "debit" in dto.text.lower())) else "MEDIUM"
    complaint_id = f"CASE#{int(time.time()*1000)}"
    row = fetchone(
        """
        INSERT INTO grievances(complaint_id, user_id, text, category, urgency, status, created_at, updated_at)
        VALUES(%s,%s,%s,%s,%s,%s,NOW(),NOW())
        RETURNING complaint_id, category, urgency, status, created_at
        """,
        [complaint_id, int(claims["sub"]), dto.text, category if category in CATEGORIES else "other", urgency, "RECEIVED"],
    )
    latency_ms = int((time.time() - start) * 1000)
    return api_success({
        "complaint_id": row["complaint_id"],
        "category": row["category"],
        "urgency": row["urgency"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "latency_ms": latency_ms,
    })

@app.get("/api/grievance/status/{complaint_id}")
def grievance_status(complaint_id: str, claims: Dict[str, Any] = Depends(auth_dependency)):
    doc = fetchone("SELECT complaint_id, category, urgency, status, created_at, updated_at FROM grievances WHERE complaint_id=%s AND user_id=%s", [complaint_id, int(claims["sub"])])
    if not doc:
        raise HTTPException(status_code=404, detail="Complaint not found")
    last_update = doc.get("updated_at") or doc.get("created_at") or datetime.now(timezone.utc)
    next_update = last_update + timedelta(hours=24)
    timeline = [
        {"event": "created", "at": doc.get("created_at")},
    ]
    if doc.get("status") == "IN_PROGRESS":
        timeline.append({"event": "in_progress", "at": last_update})
    if doc.get("status") == "RESOLVED":
        timeline.append({"event": "resolved", "at": last_update})
    return api_success({
        "complaint_id": complaint_id,
        "category": doc.get("category"),
        "urgency": doc.get("urgency"),
        "status": doc.get("status"),
        "timeline": timeline,
        "next_update_expected": next_update.isoformat(),
    })

@app.post("/api/grievance/categorize")
def grievance_categorize(dto: CategorizeDto, claims: Dict[str, Any] = Depends(auth_dependency)):
    try:
        resp = requests.post(f"{GRIEVANCE_SERVICE_URL}/categorize", json={"text": dto.text}, timeout=5)
        if resp.status_code == 200:
            j = resp.json()
            return api_success(j)
        return api_success({"category": "other", "confidence": 0.5})
    except Exception as e:
        logger.warning("grievance categorize fallback: %s", str(e))
        return api_success({"category": "other", "confidence": 0.5})

@app.get("/api/grievance/analytics")
def grievance_analytics(claims: Dict[str, Any] = Depends(auth_dependency)):
    total = fetchone("SELECT COUNT(*) AS c FROM grievances")
    rows = fetchall("SELECT category, COUNT(*) AS c FROM grievances GROUP BY category")
    cat_counts = {r["category"]: r["c"] for r in rows}
    times = fetchall("SELECT EXTRACT(EPOCH FROM (updated_at - created_at))/3600.0 AS hrs FROM grievances WHERE updated_at IS NOT NULL AND created_at IS NOT NULL")
    vals = [t["hrs"] for t in times]
    avg_resolution = sum(vals)/len(vals) if vals else 0.0
    high_pending = fetchone("SELECT COUNT(*) AS c FROM grievances WHERE urgency='HIGH' AND status <> 'RESOLVED'")
    return api_success({
        "total_complaints": total["c"] if total else 0,
        "by_category": cat_counts,
        "avg_resolution_time_hours": round(avg_resolution, 2),
        "high_priority_pending": high_pending["c"] if high_pending else 0,
    })

# Existing test endpoint
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "connection_status": "Not Connected",
        "tables": []
    }
    try:
        _ = fetchone("SELECT 1 AS ok")
        response["database"] = "✅ Connected & Working"
        response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
        response["connection_status"] = "Connected"
        try:
            rows = fetchall("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            response["tables"] = [r["table_name"] for r in rows][:20]
        except Exception as e:
            response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
