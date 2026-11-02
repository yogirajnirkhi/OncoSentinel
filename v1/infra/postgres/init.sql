-- OncoSentinel v2.0 — PostgreSQL Initialization & Immutability Triggers
-- Satisfies: FR-16, FR-29, NFR-06, NFR-09

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ── Trigger Function: Prevent UPDATE or DELETE on Append-Only / Insert-Only tables
CREATE OR REPLACE FUNCTION enforce_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'OncoSentinel Security Violation: Table % is append-only/insert-only. UPDATE and DELETE operations are forbidden.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- ── Create patient_timeline_events immutability trigger
-- (Applied if table exists or deferred until table creation)
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'patient_timeline_events') THEN
        DROP TRIGGER IF EXISTS trg_patient_timeline_append_only ON patient_timeline_events;
        CREATE TRIGGER trg_patient_timeline_append_only
        BEFORE UPDATE OR DELETE ON patient_timeline_events
        FOR EACH ROW EXECUTE FUNCTION enforce_append_only();
    END IF;
END $$;

-- ── Create audit_events immutability trigger
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'audit_events') THEN
        DROP TRIGGER IF EXISTS trg_audit_events_insert_only ON audit_events;
        CREATE TRIGGER trg_audit_events_insert_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION enforce_append_only();
    END IF;
END $$;
