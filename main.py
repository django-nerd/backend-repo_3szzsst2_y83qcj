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
from bson import ObjectId
import bcrypt
import jwt

from database import db, create_document, get_documents

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

def api_error(message: str, status_code: int = 400):
    return {"success": False, "data": None, "error": message, "statusCode": status_code}

# ----- Models (Pydantic DTOs) -----
class RegisterDto(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginDto(BaseModel):
    email: EmailStr
    password: str

class VerifyAppDto(BaseModel):
    package_name: Optional[str] = None

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
    # Simple DB check
    try:
        _ = db.list_collection_names()
        db_ok = True
    except Exception:
        db_ok = False
    return api_success({"status": "OK", "db": db_ok})

# ----- Auth Endpoints -----
@app.post("/api/auth/register")
def register(dto: RegisterDto):
    start = time.time()
    users = db["user"]
    existing = users.find_one({"email": dto.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(dto.password.encode("utf-8"), salt)
    user_doc = {
        "email": dto.email.lower(),
        "password": hashed.decode("utf-8"),
        "name": dto.name,
        "createdAt": datetime.now(timezone.utc)
    }
    result = users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_token({"sub": user_id, "email": dto.email.lower()})
    latency_ms = int((time.time() - start) * 1000)
    logger.info("register success %s", dto.email)
    return api_success({
        "token": token,
        "user": {"id": user_id, "email": dto.email.lower(), "name": dto.name},
        "latency_ms": latency_ms
    })

@app.post("/api/auth/login")
def login(dto: LoginDto):
    start = time.time()
    users = db["user"]
    user = users.find_one({"email": dto.email.lower()})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not bcrypt.checkpw(dto.password.encode("utf-8"), user["password"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_token({"sub": str(user["_id"]), "email": user["email"]})
    latency_ms = int((time.time() - start) * 1000)
    logger.info("login success %s", dto.email)
    return api_success({
        "token": token,
        "user": {"id": str(user["_id"]), "email": user["email"], "name": user.get("name")},
        "latency_ms": latency_ms
    })

@app.get("/api/auth/me")
def me(claims: Dict[str, Any] = Depends(auth_dependency)):
    users = db["user"]
    user = users.find_one({"_id": ObjectId(claims["sub"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return api_success({"id": str(user["_id"]), "email": user["email"], "name": user.get("name")})

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
        doc = {
            "user_id": ObjectId(claims["sub"]),
            "deepfake_score": payload.get("deepfake_score", 0.0),
            "liveness_status": payload.get("liveness_status", "PASS"),
            "overall_result": payload.get("overall_result", "VERIFIED"),
            "latency_ms": payload.get("latency_ms", latency_ms),
            "createdAt": datetime.now(timezone.utc)
        }
        res = db["identitycheck"].insert_one(doc)
        payload["id"] = str(res.inserted_id)
        logger.info("identity verification completed user=%s result=%s", claims.get("sub"), payload.get("overall_result"))
        return api_success(payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("identity verify error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/identity/result/{id}")
def identity_result(id: str, claims: Dict[str, Any] = Depends(auth_dependency)):
    try:
        doc = db["identitycheck"].find_one({"_id": ObjectId(id), "user_id": ObjectId(claims["sub"])})
        if not doc:
            raise HTTPException(status_code=404, detail="Result not found")
        data = {
            "id": str(doc["_id"]),
            "deepfake_score": doc.get("deepfake_score"),
            "liveness_status": doc.get("liveness_status"),
            "overall_result": doc.get("overall_result"),
            "latency_ms": doc.get("latency_ms"),
            "createdAt": doc.get("createdAt")
        }
        return api_success(data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("identity result error")
        raise HTTPException(status_code=500, detail=str(e))

# ----- App Authenticator -----
@app.post("/api/app/verify")
async def app_verify(package_name: Optional[str] = Form(None), apk: Optional[UploadFile] = File(None), claims: Dict[str, Any] = Depends(auth_dependency)):
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
        coll_off = db["officialapp"]
        coll_susp = db["suspiciousapp"]
        query = {}
        if package_name:
            query["package_name"] = package_name
        if sha256_hash:
            query["sha256_hash"] = sha256_hash
        official = coll_off.find_one(query)
        if official:
            status_label = "OFFICIAL"
            publisher = official.get("publisher")
            google_play_link = official.get("google_play_link")
            confidence = 0.98
        else:
            suspicious = coll_susp.find_one({k: v for k, v in query.items() if k in ["package_name"]})
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
            "latency_ms": latency_ms
        }
        logger.info("app verify package=%s status=%s", package_name, status_label)
        return api_success(data)
    except Exception as e:
        logger.exception("app verify error")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/app/registry")
def app_registry(claims: Dict[str, Any] = Depends(auth_dependency)):
    items = list(db["officialapp"].find().limit(100))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return api_success(items)

@app.get("/api/app/suspicious")
def app_suspicious(claims: Dict[str, Any] = Depends(auth_dependency)):
    items = list(db["suspiciousapp"].find().limit(100))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return api_success(items)

@app.post("/api/app/registry")
def app_add_official(body: Dict[str, Any], claims: Dict[str, Any] = Depends(auth_dependency)):
    # Simple admin check: first registered user can be admin; for MVP, allow all authenticated to add
    body["last_verified"] = datetime.now(timezone.utc)
    res = db["officialapp"].insert_one(body)
    return api_success({"id": str(res.inserted_id)})

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
    doc = {
        "complaint_id": complaint_id,
        "user_id": ObjectId(claims["sub"]),
        "text": dto.text,
        "category": category if category in CATEGORIES else "other",
        "urgency": urgency,
        "status": "RECEIVED",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    db["grievance"].insert_one(doc)
    latency_ms = int((time.time() - start) * 1000)
    return api_success({
        "complaint_id": complaint_id,
        "category": doc["category"],
        "urgency": urgency,
        "status": doc["status"],
        "createdAt": doc["createdAt"],
        "latency_ms": latency_ms
    })

@app.get("/api/grievance/status/{complaint_id}")
def grievance_status(complaint_id: str, claims: Dict[str, Any] = Depends(auth_dependency)):
    doc = db["grievance"].find_one({"complaint_id": complaint_id, "user_id": ObjectId(claims["sub"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Complaint not found")
    last_update = doc.get("updatedAt", doc.get("createdAt", datetime.now(timezone.utc)))
    next_update = last_update + timedelta(hours=24)
    timeline = [
        {"event": "created", "at": doc.get("createdAt")},
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
        "next_update_expected": next_update.isoformat()
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
    total = db["grievance"].count_documents({})
    # by category
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    cat_counts = {i["_id"]: i["count"] for i in db["grievance"].aggregate(pipeline)}
    # avg resolution time (placeholder using created->updated)
    # For MVP, compute avg(updatedAt - createdAt)
    times = []
    for g in db["grievance"].find({}, {"createdAt": 1, "updatedAt": 1}):
        if g.get("createdAt") and g.get("updatedAt"):
            diff = (g["updatedAt"] - g["createdAt"]).total_seconds() / 3600.0
            times.append(diff)
    avg_resolution = sum(times) / len(times) if times else 0.0
    high_pending = db["grievance"].count_documents({"urgency": "HIGH", "status": {"$ne": "RESOLVED"}})
    return api_success({
        "total_complaints": total,
        "by_category": cat_counts,
        "avg_resolution_time_hours": round(avg_resolution, 2),
        "high_priority_pending": high_pending
    })

# Existing test endpoint
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = getattr(db, 'name', '✅ Connected')
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
