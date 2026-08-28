import json
import os
import re
from google import genai
from langfuse import observe

MODEL_NAME = "gemini-2.5-flash"

def get_client():
    """Enforces Vertex AI authentication per specs."""
    return genai.Client(
        vertexai=True,
        project=os.getenv("GCP_PROJECT", "gd-gcp-gridu-genai"),
        location=os.getenv("GCP_LOCATION", "global")
    )

def validate_prompt(prompt: str) -> bool:
    """Guardrail for prompt injection and off-topic checks."""
    forbidden = ["ignore previous", "system prompt", "drop table", "delete from", "alter table"]
    return not any(phrase in prompt.lower() for phrase in forbidden)

def stream_sql_response(prompt: str):
    """Streams response tokens incrementally."""
    client = get_client()
    response = client.models.generate_content_stream(
        model=MODEL_NAME,
        contents=prompt
    )
    for chunk in response:
        yield chunk.text

@observe()
def generate_table_data(ddl_schema: str, prompt: str, row_count: int = 10):
    client = get_client()
    full_prompt = f"Given schema:\n{ddl_schema}\nGenerate {row_count} rows of synthetic JSON data. Context: {prompt}"
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=full_prompt,
        config={'response_mime_type': 'application/json'}
    )
    return json.loads(response.text)

@observe()
def generate_sql_query(user_question: str, schema: str):
    client = get_client()
    prompt = f"Schema:\n{schema}\nQuestion: {user_question}\nGenerate a single valid read-only SQL query."
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text.replace("```sql", "").replace("```", "").strip()
    