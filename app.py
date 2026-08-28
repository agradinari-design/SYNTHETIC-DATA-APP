import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import re
import sqlparse
import io

from generator import (
    generate_table_data,
    modify_table_data,
    stream_sql_response,
    validate_prompt
)
import db
import schema_parser

st.set_page_config(page_title="Synthetic Data & AI Chat", layout="wide")

# Session State Initialization
if "generated_data" not in st.session_state:
    st.session_state["generated_data"] = {}
if "ddl_schema" not in st.session_state:
    st.session_state["ddl_schema"] = ""
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

st.sidebar.title("Navigation")
page = st.sidebar.radio("Select Page", ["Phase 1 — Data Generation", "Phase 2 — Talk to Your Data"])

def is_safe_read_only_sql(sql: str) -> bool:
    """Strict AST validation for single-statement SELECT queries."""
    parsed = sqlparse.parse(sql)
    if len(parsed) != 1:
        return False
    stmt = parsed[0]
    if stmt.get_type() != 'SELECT':
        return False
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "GRANT", "TRUNCATE", "--", "/*"]
    return not any(kw in sql.upper() for kw in forbidden)

# ==========================================
# PHASE 1: SYNTHETIC DATA GENERATION & EDITING
# ==========================================
if page == "Phase 1 — Data Generation":
    st.header("Phase 1 — Synthetic Data Generation")
    
    uploaded_file = st.file_uploader("Upload DDL File (.sql, .ddl, .txt)", type=["sql", "ddl", "txt"])
    user_instructions = st.text_area("Custom Generation Instructions", "Ensure realistic dates and names.")
    
    col1, col2 = st.columns(2)
    with col1:
        row_count = st.number_input("Rows per table", min_value=1, max_value=500, value=10)
    with col2:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7)

    if st.button("Generate Synthetic Data") and uploaded_file:
        raw_ddl = uploaded_file.read().decode("utf-8")
        parsed = schema_parser.parse_ddl_file(raw_ddl)
        cleaned_ddl = parsed["cleaned_ddl"]
        tables = parsed["tables"]

        # Guardrail Check
        guardrail = validate_prompt(user_instructions)
        if not guardrail["is_safe"] or not guardrail["is_on_topic"]:
            st.error(f"Guardrail Blocked Request: {guardrail.get('reason', 'Unsafe or off-topic input.')}")
        else:
            with st.spinner("Executing DDL & Generating Data..."):
                ddl_ok, msg = db.execute_ddl(cleaned_ddl)
                if not ddl_ok:
                    st.error(f"DDL Execution Failed: {msg}")
                else:
                    data_dict = generate_table_data(cleaned_ddl, user_instructions, row_count, tables, temperature)
                    all_saved = True
                    for table_name, rows in data_dict.items():
                        df = pd.DataFrame(rows)
                        saved, save_msg = db.save_df_to_postgres(table_name, df)
                        if not saved:
                            all_saved = False
                            st.error(f"Failed to save {table_name}: {save_msg}")

                    if all_saved:
                        st.session_state["generated_data"] = {k: pd.DataFrame(v) for k, v in data_dict.items()}
                        st.session_state["ddl_schema"] = cleaned_ddl
                        st.success("Dataset successfully generated and saved to PostgreSQL!")

    # Per-Table Preview & Edit-by-Prompt Control (Q1 & Q3 fix)
    if st.session_state["generated_data"]:
        st.divider()
        st.subheader("Generated Tables Preview & Direct Editing")
        selected_table = st.selectbox("Select Table to Preview / Edit", list(st.session_state["generated_data"].keys()))
        
        current_df = st.session_state["generated_data"][selected_table]
        st.dataframe(current_df)

        st.markdown(f"**Edit Table: `{selected_table}`**")
        edit_prompt = st.text_input(f"Modification instructions for {selected_table}", key=f"edit_{selected_table}")
        if st.button("Submit Edit", key=f"sub_{selected_table}") and edit_prompt:
            guard = validate_prompt(edit_prompt)
            if not guard["is_safe"]:
                st.error("Edit blocked by safety guardrails.")
            else:
                with st.spinner("Applying modifications..."):
                    updated_rows = modify_table_data(selected_table, current_df.to_dict(orient="records"), edit_prompt)
                    new_df = pd.DataFrame(updated_rows)
                    saved, save_msg = db.save_df_to_postgres(selected_table, new_df)
                    if saved:
                        st.session_state["generated_data"][selected_table] = new_df
                        st.success(f"Updated `{selected_table}` successfully!")
                        st.rerun()
                    else:
                        st.error(f"Failed to persist edits: {save_msg}")

# ==========================================
# PHASE 2: TALK TO YOUR DATA (CHAT & SQL)
# ==========================================
elif page == "Phase 2 — Talk to Your Data":
    st.header("Phase 2 — Talk to Your Data")

    if not st.session_state["generated_data"] or not st.session_state["ddl_schema"]:
        st.warning("Please generate and persist data in Phase 1 before accessing Chat.")
    else:
        # Display Conversation History
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "sql" in msg:
                    st.code(msg["sql"], language="sql")
                if "df" in msg:
                    st.dataframe(msg["df"])
                if "chart" in msg:
                    st.image(msg["chart"])

        user_query = st.chat_input("Ask a question about your dataset...")
        if user_query:
            st.session_state["chat_history"].append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.write(user_query)

            # Guardrails Check
            guard = validate_prompt(user_query)
            if not guard["is_safe"] or not guard["is_on_topic"]:
                bot_msg = f"Request Denied: {guard.get('reason', 'Off-topic or harmful prompt.')}"
                st.session_state["chat_history"].append({"role": "assistant", "content": bot_msg})
                with st.chat_message("assistant"):
                    st.error(bot_msg)
            else:
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    full_text = ""

                    # Stream Assistant Response (Token by Token)
                    stream = stream_sql_response(
                        user_query, 
                        st.session_state["ddl_schema"], 
                        st.session_state["chat_history"]
                    )
                    for chunk in stream:
                        full_text += chunk
                        response_placeholder.markdown(full_text)

                    # Extract SQL Code Block
                    sql_match = re.search(r"```sql\s*(.*?)\s*```", full_text, re.DOTALL)
                    sql_query = sql_match.group(1).strip() if sql_match else ""

                    chart_buffer = None
                    result_df = None

                    if sql_query:
                        if not is_safe_read_only_sql(sql_query):
                            st.error("Generated SQL failed read-only safety validation.")
                        else:
                            st.code(sql_query, language="sql")
                            result_df = db.run_query(sql_query)
                            if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                                st.dataframe(result_df)

                                # Seaborn Visualization (Q3 fix)
                                num_cols = result_df.select_dtypes(include=['number']).columns
                                cat_cols = result_df.select_dtypes(include=['object', 'category']).columns

                                if len(num_cols) > 0 and len(cat_cols) > 0:
                                    fig, ax = plt.subplots(figsize=(8, 4))
                                    sns.barplot(data=result_df, x=cat_cols[0], y=num_cols[0], ax=ax)
                                    plt.xticks(rotation=45)
                                    st.pyplot(fig)

                                    buf = io.BytesIO()
                                    fig.savefig(buf, format="png", bbox_inches="tight")
                                    chart_buffer = buf.getvalue()

                    # Save Turn to Chat History
                    assistant_entry = {"role": "assistant", "content": full_text}
                    if sql_query:
                        assistant_entry["sql"] = sql_query
                    if result_df is not None:
                        assistant_entry["df"] = result_df
                    if chart_buffer:
                        assistant_entry["chart"] = chart_buffer
                    st.session_state["chat_history"].append(assistant_entry)