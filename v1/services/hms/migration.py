from __future__ import annotations

from typing import Any

from sqlalchemy import Connection, text

from services.hms.models import IMMUTABLE, MODELS, OperationReceipt


def hms_tables() -> list[Any]:
    return [model.__table__ for model in MODELS.values()] + [OperationReceipt.__table__]


def install_guards(connection: Connection) -> None:
    tables = [model.__tablename__ for model in IMMUTABLE]
    if connection.dialect.name == "postgresql":
        connection.execute(
            text("""CREATE OR REPLACE FUNCTION hms_deny_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN
        RAISE EXCEPTION 'HMS append-only table: amendment/reversal required';
        END; $$;""")
        )
        for name in tables:
            # Identifiers are static SQLAlchemy declarations, not user input.
            connection.execute(text(f"DROP TRIGGER IF EXISTS {name}_immutable ON {name}"))
            connection.execute(
                text(
                    f"CREATE TRIGGER {name}_immutable BEFORE UPDATE OR DELETE ON {name} FOR "
                    f"EACH ROW EXECUTE FUNCTION hms_deny_mutation()"
                )
            )
            connection.execute(text(f"DROP TRIGGER IF EXISTS {name}_no_truncate ON {name}"))
            connection.execute(
                text(
                    f"CREATE TRIGGER {name}_no_truncate BEFORE TRUNCATE ON {name} FOR EACH "
                    f"STATEMENT EXECUTE FUNCTION hms_deny_mutation()"
                )
            )
        connection.execute(
            text("""CREATE OR REPLACE FUNCTION hms_balanced_posting()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF (SELECT count(*) < 2 OR sum(debit) <> sum(credit)
                  FROM hms_finance_ledger WHERE transaction_id=NEW.transaction_id) THEN
                RAISE EXCEPTION 'Unbalanced HMS accounting transaction';
              END IF;
              RETURN NEW;
            END; $$;""")
        )
        connection.execute(
            text("DROP TRIGGER IF EXISTS hms_balanced_posting ON hms_finance_ledger")
        )
        connection.execute(
            text("""CREATE CONSTRAINT TRIGGER hms_balanced_posting
            AFTER INSERT ON hms_finance_ledger DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION hms_balanced_posting()""")
        )
        # btree_gist must be approved/installed by DB administration once.
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        for table in ["hms_scheduling_appointments", "hms_scheduling_shifts"]:
            name = table + "_no_overlap"
            exists = connection.scalar(
                text("SELECT 1 FROM pg_constraint WHERE conname=:name"), {"name": name}
            )
            if not exists:
                connection.execute(
                    text(f"""ALTER TABLE {table} ADD CONSTRAINT {name}
                  EXCLUDE USING gist (provider_id WITH =, tstzrange(start,"end",'[)') WITH &&)
                  WHERE (status <> 'cancelled')""")
                )
    elif connection.dialect.name == "sqlite":
        # Portable guards for testing only. Production must use PostgreSQL.
        for table in tables:
            for operation in ["UPDATE", "DELETE"]:
                connection.execute(
                    text(f"""CREATE TRIGGER IF NOT EXISTS {table}_{operation.lower()}_deny
                  BEFORE {operation} ON {table} BEGIN
                  SELECT RAISE(ABORT, 'HMS append-only record'); END""")
                )


def upgrade(connection: Connection) -> None:
    MODELS["patients"].metadata.create_all(connection, tables=hms_tables(), checkfirst=True)
    install_guards(connection)
