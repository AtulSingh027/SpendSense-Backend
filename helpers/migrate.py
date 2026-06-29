"""
Migration runner — executes helpers/migrations.sql against the configured MySQL database.

Usage:
    python -m helpers.migrate
"""

import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()


def run_migrations() -> None:

    #-------------------------------------------------------------------------------------------------
    #change the file name here and apply using the python -m helpers.migrate
    sql_path = os.path.join(os.path.dirname(__file__), "migrations/")

    #-------------------------------------------------------------------------------------------------

    if not os.path.exists(sql_path):
        print(f"ERROR: migration file not found at {sql_path}")
        sys.exit(1)

    with open(sql_path, "r") as f:
        sql_content = f.read()

    # Split on semicolons, filter empty statements
    statements = [s.strip() for s in sql_content.split(";") if s.strip()]

    conn = pymysql.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "3306")),
        user=os.getenv("DATABASE_USER", "root"),
        password=os.getenv("DATABASE_PASSWORD", "12345"),
        database=os.getenv("DATABASE_NAME", "spend_sense"),
        charset="utf8mb4",
    )

    try:
        with conn.cursor() as cursor:
            for i, stmt in enumerate(statements, 1):
                try:
                    cursor.execute(stmt)
                    print(f"  [{i}/{len(statements)}] OK")
                except pymysql.err.OperationalError as exc:
                    # Table/index already exists — skip gracefully
                    if exc.args[0] in (1050, 1061):
                        print(f"  [{i}/{len(statements)}] SKIPPED (already exists)")
                    else:
                        raise
            conn.commit()
        print("\nMigrations completed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()
