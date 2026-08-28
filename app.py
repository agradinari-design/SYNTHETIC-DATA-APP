import sys
from pathlib import Path

# Fix ModuleNotFoundError when Docker runs app.py from the root directory
current_dir = Path(__file__).parent
subfolder = current_dir / "SYNTHETIC-DATA-APP"

if subfolder.exists() and str(subfolder) not in sys.path:
    sys.path.append(str(subfolder))
elif str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from generator import (
    generate_table_data,
    generate_sql_query,
    stream_sql_response,
    validate_prompt,
    is_safe_sql
)
import db
import schema_parser


# Data Validation Helper
def validate_synthetic_rows(data: dict) -> dict:
    """Validates generated data dictionary before database persistence."""
    cleaned_data = {}
    if not isinstance(data, dict):
        return cleaned_data

    for table_name, rows in data.items():
        if not isinstance(rows, list):
            continue
        valid_rows = []
        for row in rows:
            if isinstance(row, dict) and not any(v is None for v in row.values()):
                valid_rows.append(row)
        if valid_rows:
            cleaned_data[table_name] = valid_rows
    return cleaned_data


# In-Chat Visualization Helper
def render_chat_chart(df: pd.DataFrame, x_col: str, y_col: str, chart_type: str = "bar"):
    """Renders Seaborn charts directly in Streamlit chat flow."""
    fig, ax = plt.subplots(figsize=(8, 4))
    if chart_type == "bar":
        sns.barplot(data=df, x=x_col, y=y_col, ax=ax)
    elif chart_type == "line":
        sns.lineplot(data=df, x=x_col, y=y_col, ax=ax)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)


# Page Setup
st.set_page_config(page_title="Data Assistant", layout="wide")
st.sidebar.title("Data Assistant")
page = st.sidebar.radio("Select Module:", ["1. Synthetic Data Generator", "2. Talk to Your Data"])

if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_data" not in st.session_state:
    st.session_state.generated_data = {}
if "ddl_schema" not in st.session_state:
    st.session_state.ddl_schema = ""


# MODULE 1: SYNTHETIC DATA GENERATOR
if page == "1. Synthetic Data Generator":
    st.header("Synthetic Data Generator")

    uploaded_file = st.file_uploader("Upload DDL Schema (.sql, .txt, .ddl)", type=["sql", "txt", "ddl"])
    user_instructions = st.text_area("Prompt / Generation Instructions:", "Generate realistic synthetic data")

    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
    with col2:
        num_rows = st.number_input("Rows per table", min_value=1, max_value=1000, value=10)

    if uploaded_file is not None:
        ddl_text = uploaded_file.read().decode("utf-8")
        st.session_state.ddl_schema = ddl_text
        table_names = schema_parser.parse_ddl_file(ddl_text)

        st.success(f"Parsed Tables: {', '.join(table_names)}")

        if st.button("Generate Data"):
            # Guardrail Check
            if not validate_prompt(user_instructions):
                st.error("Generation blocked by prompt safety guardrail.")
                st.stop()

            with st.spinner("Generating synthetic data..."):
                # Execute DDL in Postgres
                db.execute_ddl(ddl_text)

                # Corrected Signature Call
                raw_data = generate_table_data(
                    ddl_schema=ddl_text,
                    user_instructions=user_instructions,
                    num_rows=num_rows,
                    table_names=table_names,
                    temperature=temperature
                )

                # Validate non-null rows before insertion
                cleaned_data = validate_synthetic_rows(raw_data)

                # Save DataFrames to Postgres & Session State
                for t_name, rows in cleaned_data.items():
                    df = pd.DataFrame(rows)
                    st.session_state.generated_data[t_name] = df
                    db.save_df_to_postgres(df, t_name)

                st.success("Synthetic data successfully generated and persisted!")

    # Previews & Downloads + Per-Table Edit Flow
    if st.session_state.generated_data:
        st.subheader("Data Preview & Edits")
        selected_table = st.selectbox("Select Table to Preview/Edit:", list(st.session_state.generated_data.keys()))

        if selected_table:
            curr_df = st.session_state.generated_data[selected_table]
            st.dataframe(curr_df)

            # Per-table edit-by-prompt
            edit_prompt = st.text_input(f"Edit {selected_table} via Prompt:")
            if st.button(f"Submit Edit for {selected_table}"):
                if validate_prompt(edit_prompt):
                    with st.spinner("Updating table data..."):
                        updated_raw = generate_table_data(
                            ddl_schema=st.session_state.ddl_schema,
                            user_instructions=f"Update table {selected_table} based on: {edit_prompt}",
                            num_rows=len(curr_df),
                            table_names=[selected_table],
                            temperature=temperature
                        )
                        valid_updated = validate_synthetic_rows(updated_raw)
                        if selected_table in valid_updated:
                            new_df = pd.DataFrame(valid_updated[selected_table])
                            st.session_state.generated_data[selected_table] = new_df
                            db.save_df_to_postgres(new_df, selected_table)
                            st.rerun()
                else:
                    st.error("Edit request blocked by prompt safety guardrail.")

            csv_data = curr_df.to_csv(index=False)
            st.download_button(
                label=f"Download {selected_table} CSV",
                data=csv_data,
                file_name=f"{selected_table}.csv",
                mime="text/csv"
            )


# MODULE 2: TALK TO YOUR DATA
elif page == "2. Talk to Your Data":
    st.header("Talk to Your Data")

    if not st.session_state.ddl_schema:
        st.warning("Please generate or upload a schema in Module 1 first.")
        st.stop()

    # Display History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "df" in msg:
                st.dataframe(msg["df"])

    user_question = st.chat_input("Ask a question about your data...")

    if user_question:
        # 1. Guardrail Check
        if not validate_prompt(user_question):
            st.error("Query blocked by safety guardrail.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):
            # Stream Main Answer Tokens
            response_placeholder = st.empty()
            full_response = ""
            for chunk in stream_sql_response(user_question, history=st.session_state.messages[:-1]):
                full_response += chunk
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

            # Generate Raw SQL Query with CORRECT Argument Order (user_question, schema)
            generated_sql = generate_sql_query(
                user_question=user_question,
                schema=st.session_state.ddl_schema,
                history=st.session_state.messages[:-1]
            )

            # Strict Single-Statement Read-Only SQL Safety Check
            if not is_safe_sql(generated_sql):
                st.error("Generated query failed strict read-only SQL validation.")
                st.code(generated_sql, language="sql")
            else:
                st.code(generated_sql, language="sql")
                try:
                    result_df = db.run_query(generated_sql)
                    st.dataframe(result_df)

                    # Automatic chart rendering if numeric columns exist
                    num_cols = result_df.select_dtypes(include=['number']).columns
                    cat_cols = result_df.select_dtypes(include=['object', 'string']).columns
                    if len(num_cols) >= 1 and len(cat_cols) >= 1:
                        render_chat_chart(result_df, x_col=cat_cols[0], y_col=num_cols[0], chart_type="bar")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "df": result_df
                    })
                except Exception as e:
                    st.error(f"Error executing SQL: {e}")