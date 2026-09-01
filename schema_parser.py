import re
import sqlparse

def clean_ddl_for_postgres(sql_script: str) -> str:
    if not sql_script:
        return ""

    cleaned = sql_script

    # Convert MySQL DATETIME to PostgreSQL TIMESTAMP and ENUM to VARCHAR
    cleaned = re.sub(r'(?i)\bDATETIME\b', 'TIMESTAMP', cleaned)
    cleaned = re.sub(r'(?i)\bENUM\s*\([^)]+\)', 'VARCHAR(255)', cleaned)

    # Remove MySQL AUTO_INCREMENT, Engine, Charset, and Collate specifications
    cleaned = re.sub(r'(?i)\bAUTO_INCREMENT\b', '', cleaned)
    cleaned = re.sub(r'(?i)ENGINE\s*=\s*\w+', '', cleaned)
    cleaned = re.sub(r'(?i)(DEFAULT\s+)?CHARACTER\s+SET\s*=\s*\w+', '', cleaned)
    cleaned = re.sub(r'(?i)COLLATE\s*=\s*\w+', '', cleaned)
    cleaned = cleaned.replace("`", "")

    # Inject IF NOT EXISTS into CREATE TABLE statements
    cleaned = re.sub(
        r'(?i)CREATE\s+TABLE\s+(?!IF\s+NOT\s+EXISTS\s+)',
        'CREATE TABLE IF NOT EXISTS ',
        cleaned
    )

    formatted_sql = sqlparse.format(
        cleaned,
        reindent=True,
        keyword_case='upper',
        strip_comments=True
    )
    return formatted_sql.strip()

def extract_table_names(sql_script: str) -> list[str]:
    tables = []
    pattern = r'(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\w]+)'
    matches = re.findall(pattern, sql_script)
    for match in matches:
        table_name = match.strip('`" ')
        if table_name and table_name not in tables:
            tables.append(table_name)
    return tables

def parse_ddl_file(file_content: str) -> dict:
    cleaned = clean_ddl_for_postgres(file_content)
    tables = extract_table_names(cleaned)
    return {
        "cleaned_ddl": cleaned,
        "tables": tables,
        "tables_str": ", ".join(tables),
        "table_count": len(tables)
    }