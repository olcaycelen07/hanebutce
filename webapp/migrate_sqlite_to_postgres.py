from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app import DATABASE_PATH, init_db, normalize_database_url


TABLES = [
    ("users", ["id", "full_name", "email", "password_hash", "created_at"]),
    ("households", ["id", "name", "slug", "owner_user_id", "plan_type", "currency_code", "created_at"]),
    ("household_members", ["id", "household_id", "user_id", "role", "joined_at"]),
    ("household_categories", ["id", "household_id", "type", "name", "created_at"]),
    (
        "transactions",
        [
            "id",
            "household_id",
            "created_by_user_id",
            "member_user_id",
            "type",
            "title",
            "amount",
            "category",
            "transaction_date",
            "note",
            "created_at",
        ],
    ),
    (
        "bills",
        [
            "id",
            "household_id",
            "created_by_user_id",
            "member_user_id",
            "title",
            "amount",
            "category",
            "due_date",
            "status",
            "frequency",
            "last_generated_date",
            "note",
            "created_at",
        ],
    ),
    (
        "invitations",
        [
            "id",
            "household_id",
            "email",
            "role",
            "token",
            "status",
            "invited_by_user_id",
            "accepted_by_user_id",
            "created_at",
            "accepted_at",
        ],
    ),
]


def quoted_columns(columns: list[str]) -> str:
    return ", ".join(columns)


def placeholders(count: int) -> str:
    return ", ".join(["%s"] * count)


def reset_sequence(cursor, table_name: str) -> None:
    cursor.execute(
        f"""
        SELECT setval(
            pg_get_serial_sequence(%s, 'id'),
            COALESCE((SELECT MAX(id) FROM {table_name}), 1),
            (SELECT COUNT(*) > 0 FROM {table_name})
        )
        """,
        (table_name,),
    )


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL tanimli degil. Once PostgreSQL baglantisini ayarla.")

    init_db()

    sqlite_conn = sqlite3.connect(DATABASE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    postgres_conn = psycopg.connect(normalize_database_url(database_url), row_factory=dict_row)

    with sqlite_conn, postgres_conn:
        with postgres_conn.cursor() as pg_cursor:
            for table_name, columns in TABLES:
                rows = sqlite_conn.execute(f"SELECT {quoted_columns(columns)} FROM {table_name} ORDER BY id").fetchall()
                if not rows:
                    continue

                insert_sql = f"""
                INSERT INTO {table_name} ({quoted_columns(columns)})
                VALUES ({placeholders(len(columns))})
                ON CONFLICT (id) DO NOTHING
                """
                for row in rows:
                    pg_cursor.execute(insert_sql, tuple(row[column] for column in columns))
                reset_sequence(pg_cursor, table_name)

    sqlite_conn.close()
    postgres_conn.close()
    print("SQLite verileri PostgreSQL hedefine aktarildi.")


if __name__ == "__main__":
    main()
