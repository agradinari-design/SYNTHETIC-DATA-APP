import os
import pandas as pd
from sqlalchemy import create_engine, text

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "synthetic_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_db_engine():
    return create_engine(DATABASE_URL)

def execute_ddl(ddl_script: str):
    if not ddl_script:
        return (False, "No DDL script provided.")
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
            conn.execute(text(ddl_script))
            conn.commit()
        return (True, "DDL executed successfully.")
    except Exception as e:
        return (False, f"DDL Execution Error: {str(e)}")

def clear_database():
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
            conn.commit()
        return (True, "Database reset successfully.")
    except Exception as e:
        return (False, f"Error dropping schema: {str(e)}")

def save_df_to_postgres(df: pd.DataFrame, table_name: str):
    try:
        engine = get_db_engine()
        df.to_sql(table_name, engine, if_exists="append", index=False)
        return (True, f"Table '{table_name}' saved successfully.")
    except Exception as e:
        return (False, f"Data insertion error for table '{table_name}': {str(e)}")

def run_query(sql_query: str) -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql_query), conn)