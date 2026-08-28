import json
import os
import re
from google import genai
from langfuse import observe

def get_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip("'\" ")
    if api_key:
        return genai.Client(api_key=api_key)
    
    return genai.Client(
        vertexai=True,
        project=os.getenv("GCP_PROJECT", "gd-gcp-gridu-genai"),
        location="global"
    )

def _clean_and_parse_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return json.loads(text.strip())

def _call_gemini(prompt: str, temperature: float = 0.2, response_mime_type: str = "application/json"):
    client = get_client()
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]

    config = {'temperature': temperature}
    if response_mime_type:
        config['response_mime_type'] = response_mime_type

    last_error = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"Gemini generation failed: {str(last_error)}")

@observe()
def generate_table_data(*args, **kwargs):
    ddl_schema = kwargs.get("ddl_schema") or kwargs.get("schema") or (args[0] if args else "")
    if isinstance(ddl_schema, dict):
        ddl_schema = ddl_schema.get("cleaned_ddl", str(ddl_schema))

    tables = kwargs.get("table_names") or kwargs.get("table_name") or (args[1] if len(args) > 1 else "")
    num_rows = kwargs.get("num_rows") or (args[2] if len(args) > 2 else 15)
    temperature = kwargs.get("temperature", 0.2)
    instructions = kwargs.get("user_instructions") or kwargs.get("instructions", "")

    prompt = f"""
    You are an expert database synthetic data generator.

    SQL DDL Schema:
    {ddl_schema}

    Generate synthetic rows for these tables: {tables}
    Number of rows per table: {num_rows}
    Additional User Instructions: {instructions if instructions else 'None'}

    Requirements:
    1. Preserve primary key and foreign key relational integrity across tables.
    2. Output MUST be valid JSON only without surrounding explanation.
    3. The root JSON object must contain keys corresponding to each requested table name.
    4. Each table key must hold an array of row objects mapping column names to generated values.
    """

    raw_text = _call_gemini(prompt, temperature, response_mime_type="application/json")
    return _clean_and_parse_json(raw_text)

@observe()
def generate_sql_query(ddl_schema: str, user_question: str) -> str:
    prompt = f"""
    You are an expert SQL assistant.

    Given the following database schema:
    {ddl_schema}

    Translate the following user question into a valid, read-only SQL SELECT query:
    "{user_question}"

    Requirements:
    1. Return ONLY an executable SQL query starting with SELECT.
    2. Do NOT include markdown code blocks or explanatory text.
    """

    response_text = _call_gemini(prompt, temperature=0.1, response_mime_type=None)
    return response_text.strip().replace("```sql", "").replace("```", "").strip()