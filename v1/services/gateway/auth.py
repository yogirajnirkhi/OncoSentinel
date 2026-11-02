"""
OncoSentinel v2.0 — Authentication & Role-Based Access Control (RBAC)
Satisfies: NFR-04 (secure auth, RBAC), SRS §1.4 (Intended Users)
Roles: Unified OncoSentinel Core + Hospital Management System (HMS)
Enforces authentic staff user identities, salted PBKDF2 hashing, and strict role scoping.
"""
from __future__ import annotations

import datetime
import hashlib
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.core.settings import get_settings

security_bearer = HTTPBearer(auto_error=False)

ALL_ROLES = [
    "ADMIN",
    "ANALYST",
    "AUDITOR",
    "BILLING_CLERK",
    "CLINICIAN",
    "FINANCE",
    "INVENTORY_MANAGER",
    "LAB_TECH",
    "PATHOLOGIST",
    "PHARMACIST",
    "RADIOLOGIST",
    "RECEPTION",
    "RESEARCHER",
    "SCHEDULER",
]


class UserPrincipal(BaseModel):
    user_id: str
    role: str  # Primary role
    roles: list[str] = []  # All assigned roles
    email: Optional[str] = None
    full_name: Optional[str] = None
    department: Optional[str] = None


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Generate salted PBKDF2-HMAC-SHA256 password hash."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return key.hex(), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """Verify password against stored salted PBKDF2 hash using constant-time comparison."""
    expected_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(expected_hash, hashed_password)


def create_access_token(
    user_id: str,
    role: str = "CLINICIAN",
    roles: Optional[list[str]] = None,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    department: Optional[str] = None,
) -> str:
    settings = get_settings()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.jwt_expire_minutes
    )
    assigned_roles = roles if roles is not None else [role]
    payload = {
        "sub": user_id,
        "role": role,
        "roles": assigned_roles,
        "email": email or f"{user_id}@oncosentinel.hospital.org",
        "full_name": full_name or user_id,
        "department": department or "",
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> UserPrincipal:
    """
    Extracts authenticated user from validated JWT token.
    Enforces strict role scoping and rejects arbitrary bypass tokens.
    """
    settings = get_settings()
    if credentials is None:
        if not settings.is_production:
            # Scoped development fallback: authenticated Dr. Sarah Chen with CLINICIAN role
            return UserPrincipal(
                user_id="dr_chen",
                role="CLINICIAN",
                roles=["CLINICIAN"],
                email="sarah.chen@oncosentinel.hospital.org",
                full_name="Dr. Sarah Chen, MD",
                department="Medical Oncology",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required.",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        role = payload.get("role", "CLINICIAN")
        roles = payload.get("roles") or [role]
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")
        return UserPrincipal(
            user_id=user_id,
            role=role,
            roles=roles,
            email=payload.get("email"),
            full_name=payload.get("full_name"),
            department=payload.get("department"),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )


def require_roles(*allowed_roles: str):
    """Dependency factory checking that user holds at least one of the required roles."""
    def _role_checker(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        user_roles = set(user.roles) if user.roles else {user.role}
        user_roles.add(user.role)
        if "ADMIN" in user_roles or user.role == "ADMIN":
            return user
        if user.role in ("RADIOLOGIST", "PATHOLOGIST") or user_roles.intersection({"RADIOLOGIST", "PATHOLOGIST"}):
            user_roles.update({"RADIOLOGIST", "PATHOLOGIST", "IMAGING_TECH", "LAB_TECH"})
        if user.role == "PHARMACIST" or "PHARMACIST" in user_roles:
            user_roles.add("INVENTORY_MANAGER")
        if user.role == "BILLING_CLERK" or "BILLING_CLERK" in user_roles:
            user_roles.add("FINANCE")
        if not user_roles.intersection(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: This action requires privileges for {', '.join(allowed_roles)}. Your active role is {user.role}.",
            )
        return user
    return _role_checker


def principal_to_hms_identity(principal: UserPrincipal) -> tuple[str, list[str]]:
    """Convert UserPrincipal into immutable subject ID and normalized roles for HMS."""
    roles = set(principal.roles) if principal.roles else {principal.role}
    roles.add(principal.role)
    if principal.role in ("RADIOLOGIST", "PATHOLOGIST") or roles.intersection({"RADIOLOGIST", "PATHOLOGIST"}):
        roles.update({"RADIOLOGIST", "PATHOLOGIST", "IMAGING_TECH", "LAB_TECH"})
    if principal.role == "ADMIN" or "ADMIN" in roles:
        roles.update(ALL_ROLES)
    if principal.role == "PHARMACIST" or "PHARMACIST" in roles:
        roles.add("INVENTORY_MANAGER")
    if principal.role == "BILLING_CLERK" or "BILLING_CLERK" in roles:
        roles.add("FINANCE")
    return principal.user_id, list(roles)
