from __future__ import annotations
import importlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from sqlalchemy import text
from demo.host import make_app
from services.hms.config import load_config
from services.hms.migration import upgrade
from services.hms.tasks import JOB_NAMES, register_tasks, review_job


@pytest.mark.asyncio
async def test_jobs_and_domain_entrypoints():
    app = make_app("sqlite+aiosqlite:///:memory:", "job-unit-test-token-only-12345")
    async with app.router.lifespan_context(app):
        async with app.state.hms_engine.begin() as conn:
            await conn.run_sync(upgrade)
        async with app.state.hms_sessions() as session:
            for name in JOB_NAMES:
                run_key = str(uuid4())
                first = await review_job(name, run_key, session, app.state.hms_bindings)
                again = await review_job(name, run_key, session, app.state.hms_bindings)
                assert first == again
                assert first["status"] == "review_required"
            with pytest.raises(Exception):
                await review_job("untrusted", str(uuid4()), session, app.state.hms_bindings)
        # Entry points delegate to the same validated engine, never a second persistence layer.
        methods = {
            "patient": ["register", "start_encounter", "append_record"],
            "billing": ["issue_invoice", "record_payment", "record_claim", "adjust_invoice"],
            "finance": ["close_period"],
            "pharmacy": ["prescribe", "dispense"],
            "inventory": ["record_movement", "receive", "purchase_order"],
            "scheduling": ["book", "assign_shift", "request_swap"],
            "lab": ["order", "verify"],
            "radiology": ["order", "sign_report"],
        }
        domain = AsyncMock()
        domain.create.return_value = {"id": "synthetic"}
        for module, names in methods.items():
            imported = importlib.import_module("services.hms." + module)
            for name in names:
                assert (await getattr(imported, name)(domain, {}, confirmed=True))[
                    "id"
                ] == "synthetic"
        from services.hms.audit import record

        async with app.state.hms_sessions() as session:
            await record(
                app.state.hms_bindings,
                session,
                request_id=str(uuid4()),
                actor_id="test",
                actor_role="TEST",
                action="test",
                details={},
            )
            await session.commit()


def test_register_jobs():
    registrations = {}

    class CeleryStub:
        def task(self, name):
            def decorate(fn):
                registrations[name] = fn
                return fn

            return decorate

    app = make_app("sqlite+aiosqlite:///:memory:", "job-unit-test-token-only-12345")

    @asynccontextmanager
    async def session_context():
        async with app.router.lifespan_context(app):
            async with app.state.hms_sessions() as session:
                yield session

    register_tasks(CeleryStub(), session_context, app.state.hms_bindings)
    assert len(registrations) == len(JOB_NAMES)
    assert registrations["hms.financial_period_close"]("test")["status"] == "review_required"
