"""
OncoSentinel v2.0 — Pytest Fixtures and Test Setup
"""
from __future__ import annotations

import io
import os
import pytest
import numpy as np
from PIL import Image

# Ensure test session defaults to SQLite
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from services.core.settings import get_settings

# Import HMS models so their tables are registered with Base.metadata for tests.
import services.hms.models  # noqa: F401


@pytest.fixture(scope="session")
def sample_image_bytes() -> bytes:
    """Creates a valid 224x224 synthetic ultrasound/medical test image."""
    img = Image.new("RGB", (224, 224), color=(30, 40, 55))
    # Draw simple gradient/features
    arr = np.array(img, dtype=np.uint8)
    arr[80:140, 80:140] = 120
    test_img = Image.fromarray(arr)
    buf = io.BytesIO()
    test_img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(scope="session")
def degraded_image_bytes() -> bytes:
    """Creates a low-resolution, zero-contrast image to trigger quality rejection."""
    img = Image.new("L", (32, 32), color=0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()



@pytest.fixture(autouse=True)
async def setup_test_db():
    """Provides an isolated SQLite in-memory database for tests."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from services.db.models import Base
    from services.db.session import get_async_db
    from services.gateway.app import app

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_async_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_async_db] = override_get_async_db
    yield
    app.dependency_overrides.clear()

