import re
import sqlparse

def clean_ddl_for_postgres(sql_script: str) -> str:
    """Sanitizes SQL DDL for PostgreSQL compatibility."""
    if not sql_script:
        return ""

    # 1. Strip MySQL ENUM(...) data types and replace with VARCHAR(255)
    cleaned = re.sub(r'(?i)\bENUM\s*\([^)]*\)', 'VARCHAR(255)', sql_script)

    # 2. Remove MySQL AUTO_INCREMENT keywords
    cleaned = re.sub(r'(?i)\bAUTO_INCREMENT\b', '', cleaned)

    # 3. Remove MySQL Engine, Charset, and Collate specifications
    cleaned = re.sub(r'(?i)ENGINE\s*=\s*\w+', '', cleaned)
    cleaned = re.sub(r'(?i)(DEFAULT\s+)?CHARACTER\s+SET\s*=\s*\w+', '', cleaned)
    cleaned = re.sub(r'(?i)COLLATE\s*=\s*\w+', '', cleaned)

    # 4. Remove MySQL backticks
    cleaned = cleaned.replace("`", "")

    formatted_sql = sqlparse.format(
        cleaned,
        reindent=True,
        keyword_case='upper',
        strip_comments=True
    )
    return formatted_sql.strip()

def extract_table_names(sql_script: str) -> list[str]:
    """Extracts table names from DDL script."""
    tables = []
    pattern = r'(?i)CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"\w]+)'
    matches = re.findall(pattern, sql_script)
    for match in matches:
        table_name = match.strip('`" ')
        if table_name and table_name not in tables:
            tables.append(table_name)
    return tables

def extract_schema_summary(sql_script: str) -> dict:
    """Returns a full schema summary including clean string DDL."""
    cleaned = clean_ddl_for_postgres(sql_script)
    tables = extract_table_names(cleaned)
    return {
        "cleaned_ddl": cleaned,
        "tables": tables,
        "tables_str": ", ".join(tables),
        "table_count": len(tables)
    }

def parse_ddl_file(file_content: str) -> dict:
    return extract_schema_summary(file_content)