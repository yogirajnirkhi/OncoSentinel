from __future__ import annotations
import os
from uuid import uuid4
from datetime import datetime, timezone
import pytest
from sqlalchemy import text
from demo.host import Base, make_app
from services.hms.migration import upgrade


@pytest.mark.asyncio
async def test_postgresql_guards_and_unbalanced_posting():
    url = os.environ.get("HMS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set HMS_TEST_DATABASE_URL to an isolated PostgreSQL hms_test* database")
    if "hms_test" not in url.rsplit("/", 1)[-1]:
        raise RuntimeError("Refusing destructive tests outside hms_test* database")
    app = make_app(url, "postgres-unit-test-token-only-12345")
    engine = app.state.hms_engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(upgrade)
    async with engine.begin() as conn:
        count = await conn.scalar(
            text("SELECT count(*) FROM pg_trigger WHERE tgname LIKE '%_immutable'")
        )
        assert count >= 10
    # Database enforcement applies even to direct SQL bypassing the ORM.
    async with app.state.hms_sessions() as session:
        with pytest.raises(Exception):
            await session.execute(text("TRUNCATE hms_finance_ledger"))
        await session.rollback()
        row = {"id": uuid4(), "transaction": uuid4(), "source": uuid4(), "request": str(uuid4())}
        await session.execute(
            text("""INSERT INTO hms_finance_ledger
          (id,transaction_id,account,debit,credit,source_id,period,actor_id,request_id,version,extra)
          VALUES (:id,:transaction,'TEST',10,0,:source,'2026-01','test',:request,1,'{}')"""),
            row,
        )
        with pytest.raises(Exception):
            await session.commit()
        await session.rollback()
    await engine.dispose()
