"""
OncoSentinel v2.0 — FastAPI Gateway Application
Satisfies: SRS §12, NFR-01, NFR-02, NFR-04, NFR-11
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


class DevRoleSwitchRequest(BaseModel):
    role: Optional[str] = None

from services.core.exceptions import OncoSentinelError
from services.core.logging import configure_logging, get_logger
from services.core.settings import get_settings
from services.db.session import get_async_db, init_db
from services.gateway.auth import UserPrincipal, get_current_user
from services.gateway.hms_adapters import create_hms_bindings
from services.gateway.routes import api_v2_router
from services.hms.routes import mount_hms

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    configure_logging(log_level=settings.log_level)
    logger.info(
        "oncosentinel_v2_starting",
        environment=settings.environment,
        platform_phase=settings.platform_phase,
    )
    # Initialize database tables
    try:
        await init_db()
    except Exception as exc:
        logger.warning("database_init_warning", error=str(exc))
    yield
    # Shutdown
    logger.info("oncosentinel_v2_shutdown")


class LoginPayload(BaseModel):
    username: str
    password: str


class RegisterPayload(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str
    department: Optional[str] = None
    license_number: Optional[str] = None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OncoSentinel v2.0",
        description="Multimodal Cancer AI Clinical Decision-Support & Research Platform",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS Middleware ───────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Audit Middleware for Mutating Actions ─────────────────────────────────
    @app.middleware("http")
    async def audit_mutating_middleware(request: Request, call_next):
        response = await call_next(request)
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            try:
                auth_hdr = request.headers.get("authorization", "")
                actor_id = "anonymous"
                actor_role = "UNAUTHENTICATED"
                if auth_hdr.startswith("Bearer "):
                    token = auth_hdr[7:]
                    try:
                        from jose import jwt as jose_jwt
                        app_settings = get_settings()
                        payload = jose_jwt.decode(
                            token,
                            app_settings.jwt_secret_key.get_secret_value(),
                            algorithms=[app_settings.jwt_algorithm],
                        )
                        actor_id = payload.get("sub", "anonymous")
                        actor_role = payload.get("role", "CLINICIAN")
                    except Exception:
                        pass

                import uuid as py_uuid
                rid = getattr(request.state, "hms_request_id", None) or request.headers.get("x-request-id") or str(py_uuid.uuid4())
                service_name = "hms" if "/hms" in request.url.path else ("auth" if "/auth" in request.url.path else "ai_studio")
                mrn = request.headers.get("x-patient-mrn") or request.query_params.get("patient_id") or request.query_params.get("mrn")

                if not request.url.path.startswith(("/docs", "/openapi", "/static", "/health")):
                    from services.db.models import AuditEvent
                    from services.db.session import async_session_factory
                    async with async_session_factory() as session:
                        ev = AuditEvent(
                            id=str(py_uuid.uuid4()),
                            request_id=str(rid),
                            actor_id=actor_id,
                            actor_role=actor_role,
                            action=f"{request.method} {request.url.path}",
                            service_name=service_name,
                            metadata_json={
                                "status_code": response.status_code,
                                "path": request.url.path,
                                "patient_mrn": mrn,
                            },
                        )
                        session.add(ev)
                        await session.commit()
            except Exception as e:
                logger.debug("audit_middleware_log_warning", error=str(e))
        return response

    # ── Exception Handlers ────────────────────────────────────────────────────
    @app.exception_handler(OncoSentinelError)
    async def oncosentinel_error_handler(request: Request, exc: OncoSentinelError):
        logger.warning("domain_exception_handled", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": exc.__class__.__name__, "message": str(exc)},
        )

    # ── Health Endpoint ───────────────────────────────────────────────────────
    @app.get("/health", tags=["System"])
    @app.get("/api/v2/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "version": "2.0.0",
            "platform_phase": settings.platform_phase,
            "environment": settings.environment,
            "hms_integrated": True,
        }

    # ── Authentication Endpoints ──────────────────────────────────────────────
    @app.post("/api/v2/auth/login", tags=["Auth"])
    async def login_endpoint(payload: LoginPayload, db=Depends(get_async_db)):
        from sqlalchemy import func, or_, select
        from services.db.models import User
        from services.gateway.auth import create_access_token, verify_password

        ident = payload.username.strip().lower()
        result = await db.execute(
            select(User).where(
                or_(func.lower(User.username) == ident, func.lower(User.email) == ident),
                User.is_active == True,
            )
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.hashed_password, user.salt):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )
        token = create_access_token(
            user_id=user.username,
            role=user.role,
            roles=user.roles or [user.role],
            email=user.email,
            full_name=user.full_name,
            department=user.department,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "roles": user.roles or [user.role],
                "department": user.department,
                "email": user.email,
            },
        }

    @app.post("/api/v2/auth/token", tags=["Auth"])
    @app.get("/api/v2/auth/token", tags=["Auth"])
    async def token_endpoint(
        role: Optional[str] = None,
        user_id: Optional[str] = None,
        payload: Optional[LoginPayload] = None,
        db=Depends(get_async_db),
    ):
        from services.gateway.auth import ALL_ROLES, create_access_token

        if payload is not None:
            return await login_endpoint(payload, db=db)

        if settings.is_production:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthenticated query-param token issuance is disabled in production.",
            )

        clean_role = (role or "CLINICIAN").strip().upper()
        if clean_role not in ALL_ROLES:
            clean_role = "CLINICIAN"
        clean_user = user_id or "dr_user"
        token = create_access_token(
            user_id=clean_user,
            role=clean_role,
            roles=[clean_role],
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": clean_role,
            "roles": [clean_role],
            "user_id": clean_user,
            "user": {
                "id": clean_user,
                "username": clean_user,
                "full_name": clean_user,
                "role": clean_role,
                "roles": [clean_role],
                "department": "Medical Oncology",
            },
        }

    @app.post("/api/v2/auth/register", tags=["Auth"])
    async def register_endpoint(payload: RegisterPayload, db=Depends(get_async_db)):
        """Register a new authentic hospital staff account scoped to their clinical/operational role."""
        import uuid
        from datetime import date, timedelta
        from sqlalchemy import or_, select
        from services.db.models import AuditEvent, User
        from services.gateway.auth import ALL_ROLES, create_access_token, hash_password
        from services.hms.models import Staff

        clean_role = payload.role.strip().upper()
        if clean_role not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid hospital role '{payload.role}'. Must be one of: {', '.join(ALL_ROLES)}",
            )

        clean_username = payload.username.strip().lower()
        clean_email = payload.email.strip().lower()
        if len(payload.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters.",
            )

        dept = payload.department or {
            "CLINICIAN": "Medical Oncology",
            "RADIOLOGIST": "Diagnostic Radiology",
            "PATHOLOGIST": "Surgical Pathology",
            "PHARMACIST": "Clinical Oncology Pharmacy",
            "BILLING_CLERK": "Patient Financial Services",
            "SCHEDULER": "Ambulatory Clinic Administration",
            "ADMIN": "Hospital Administration",
            "RESEARCHER": "Translational Cancer Research",
            "AUDITOR": "Clinical Quality & Compliance",
        }.get(clean_role, "General Oncology")

        try:
            existing_res = await db.execute(
                select(User).where(or_(User.username == clean_username, User.email == clean_email))
            )
            if existing_res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A staff account with this username or email already exists.",
                )

            pwd_hash, salt = hash_password(payload.password)
            user_id = str(uuid.uuid4())
            new_user = User(
                id=user_id,
                username=clean_username,
                email=clean_email,
                hashed_password=pwd_hash,
                salt=salt,
                full_name=payload.full_name.strip(),
                role=clean_role,
                roles=[clean_role],
                department=dept,
                is_active=True,
            )
            db.add(new_user)

            new_staff = Staff(
                id=uuid.uuid4(),
                display_name=payload.full_name.strip(),
                role=clean_role,
                department=dept,
                credentials={
                    "license": payload.license_number or "EMP-" + clean_username[:6].upper(),
                    "registered": True,
                },
                license_expiry=date.today() + timedelta(days=730),
                contact={"email": clean_email},
                actor_id=clean_username,
                request_id=str(uuid.uuid4()),
            )
            db.add(new_staff)

            audit_ev = AuditEvent(
                id=str(uuid.uuid4()),
                request_id=str(uuid.uuid4()),
                actor_id=clean_username,
                actor_role=clean_role,
                action="auth:register",
                service_name="auth",
                metadata_json={
                    "full_name": payload.full_name.strip(),
                    "department": dept,
                    "role": clean_role,
                },
            )
            db.add(audit_ev)
            await db.flush()

            token = create_access_token(
                user_id=new_user.username,
                role=new_user.role,
                roles=new_user.roles,
                email=new_user.email,
                full_name=new_user.full_name,
                department=new_user.department,
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": new_user.id,
                    "username": new_user.username,
                    "full_name": new_user.full_name,
                    "role": new_user.role,
                    "roles": new_user.roles,
                    "department": new_user.department,
                    "email": new_user.email,
                },
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("registration_error", error=str(e))
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    @app.post("/api/v2/auth/dev-switch", tags=["Auth"])
    async def dev_role_switch(request: Request, payload: Optional[DevRoleSwitchRequest] = None, role: Optional[str] = Query(None)):
        """Fast role switcher for local development and demonstration."""
        from services.gateway.auth import ALL_ROLES, create_access_token

        target_role = (payload.role if payload and payload.role else role) or "CLINICIAN"
        clean_role = str(target_role).strip().upper()
        role_map = {
            "CLINICIAN": ("dr_chen", "Dr. Sarah Chen, MD", ["CLINICIAN"], "Medical Oncology", "sarah.chen@oncosentinel.hospital.org"),
            "RADIOLOGIST": ("dr_patel", "Dr. Rajesh Patel, MD", ["RADIOLOGIST", "PATHOLOGIST"], "Diagnostic Radiology", "rajesh.patel@oncosentinel.hospital.org"),
            "PHARMACIST": ("pharma_alex", "Alex Rivera, PharmD, BCOP", ["PHARMACIST", "INVENTORY_MANAGER"], "Clinical Oncology Pharmacy", "alex.rivera@oncosentinel.hospital.org"),
            "BILLING_CLERK": ("billing_mark", "Mark Davis, CRCR", ["BILLING_CLERK", "FINANCE"], "Patient Financial Services", "mark.davis@oncosentinel.hospital.org"),
            "ADMIN": ("admin_clara", "Clara Vance, MHA", list(ALL_ROLES), "Hospital Administration", "clara.vance@oncosentinel.hospital.org"),
        }
        user_info = role_map.get(clean_role, role_map["CLINICIAN"])
        uname, fname, roles, dept, email = user_info
        token = create_access_token(
            user_id=uname,
            role=clean_role,
            roles=roles,
            email=email,
            full_name=fname,
            department=dept,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": clean_role,
            "roles": roles,
            "user": {
                "id": uname,
                "username": uname,
                "full_name": fname,
                "role": clean_role,
                "roles": roles,
                "department": dept,
                "email": email,
            },
        }

    @app.get("/api/v2/auth/users", tags=["Auth"])
    async def list_staff_accounts(db=Depends(get_async_db)):
        """Public directory of seeded staff accounts for role-based sign-in and switching."""
        from sqlalchemy import select
        from services.db.models import User

        res = await db.execute(
            select(User)
            .where(User.is_active == True, ~User.username.in_(["s", "s1"]))
            .order_by(User.username)
        )
        users = res.scalars().all()
        return {
            "users": [
                {
                    "username": u.username,
                    "full_name": u.full_name,
                    "role": u.role,
                    "roles": u.roles or [u.role],
                    "department": u.department or "Medical Oncology",
                    "email": u.email,
                }
                for u in users
            ]
        }

    @app.get("/api/v2/auth/me", tags=["Auth"])
    async def get_me(user: UserPrincipal = Depends(get_current_user)):
        return {
            "id": user.user_id,
            "user_id": user.user_id,
            "username": user.user_id,
            "role": user.role,
            "roles": user.roles,
            "email": user.email,
            "full_name": user.full_name,
            "department": user.department,
        }

    # ── Mount HMS (Hospital Management System) Extension ──────────────────────
    hms_bindings = create_hms_bindings()
    mount_hms(app, hms_bindings)
    app.state.hms_bindings = hms_bindings

    # ── Mount API Routes ──────────────────────────────────────────────────────
    app.include_router(api_v2_router)

    # ── Mount Web Static UI ───────────────────────────────────────────────────
    web_dir = Path(__file__).resolve().parent.parent / "web"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    return app


app = create_app()
