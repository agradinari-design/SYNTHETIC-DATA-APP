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
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            
            for statement in ddl_script.split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))
        return (True, "DDL executed successfully.")
    except Exception as e:
        return (False, f"DDL Execution Error: {str(e)}")

def save_df_to_postgres(df: pd.DataFrame, table_name: str):
    try:
        engine = get_db_engine()
        df_clean = df.copy()
        df_clean.columns = [str(col).strip().lower() for col in df_clean.columns]
        
        df_clean.to_sql(table_name.lower(), engine, if_exists="append", index=False)
        return (True, f"Table '{table_name}' saved successfully.")
    except Exception as e:
        return (False, f"Data insertion error for table '{table_name}': {str(e)}")

def run_query(sql_query: str) -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql_query), conn)