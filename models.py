from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # relationships
    identity_checks = relationship("IdentityCheck", back_populates="user")
    grievances = relationship("Grievance", back_populates="user")

class IdentityCheck(Base):
    __tablename__ = "identity_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    deepfake_score: Mapped[float] = mapped_column(Float, default=0.0)
    liveness_status: Mapped[str] = mapped_column(String(32), default="PASS")
    overall_result: Mapped[str] = mapped_column(String(32), default="VERIFIED")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="identity_checks")

class OfficialApp(Base):
    __tablename__ = "official_apps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255))
    google_play_link: Mapped[Optional[str]] = mapped_column(Text)
    last_verified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    __table_args__ = (
        UniqueConstraint('package_name', name='uq_official_apps_package_name'),
    )

class SuspiciousApp(Base):
    __tablename__ = "suspicious_apps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    publisher: Mapped[Optional[str]] = mapped_column(String(255))
    google_play_link: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)

class Grievance(Base):
    __tablename__ = "grievances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="other")
    urgency: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="grievances")
