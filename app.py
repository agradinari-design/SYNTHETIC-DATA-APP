import streamlit as st
import pandas as pd
from generator import generate_table_data, generate_sql_query
import db
import schema_parser

st.set_page_config(page_title="Data Assistant", layout="wide")

st.sidebar.title("Data Assistant")
page = st.sidebar.radio(
    "Select Module:",
    ["Data Generation", "Talk to Your Data"]
)

# Sidebar Database Management
st.sidebar.divider()
if st.sidebar.button("Clear Database", type="secondary"):
    success, msg = db.clear_database()
    if success:
        st.session_state["generated_data"] = None
        st.session_state["ddl_schema"] = None
        st.session_state["chat_history"] = []
        st.sidebar.success("Database and session reset!")
    else:
        st.sidebar.error(f"Error resetting DB: {msg}")

# Initialize Session States
if "generated_data" not in st.session_state:
    st.session_state["generated_data"] = None
if "ddl_schema" not in st.session_state:
    st.session_state["ddl_schema"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ==========================================
# PHASE 1: DATA GENERATION
# ==========================================
if page == "Data Generation":
    st.title("Data Generation")

    instructions = st.text_area(
        "Prompt",
        placeholder="Enter your prompt here...",
        value="",
        height=100
    )

    uploaded_file = st.file_uploader(
        "Upload DDL Schema",
        type=["sql", "txt", "ddl"],
        help="Supported formats: SQL, DDL, TXT"
    )

    parsed_schema = None
    if uploaded_file:
        ddl_content = uploaded_file.getvalue().decode("utf-8")
        parsed_schema = schema_parser.parse_ddl_file(ddl_content)

    with st.expander("Advanced Parameters", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=0.70, step=0.05)
        with col2:
            num_rows = st.number_input("Rows per Table", min_value=1, max_value=4096, value=10)

    tables_input = st.text_input(
        "Tables to generate (comma separated, optional)",
        placeholder="e.g., books, members, loans",
        value=""
    )

    if st.button("Generate", type="primary"):
        if not uploaded_file or not parsed_schema:
            st.error("Please upload a valid DDL schema file first!")
        else:
            cleaned_ddl = parsed_schema.get("cleaned_ddl", ddl_content)
            extracted_tables = parsed_schema.get("tables", [])

            table_list = [t.strip() for t in tables_input.split(",") if t.strip()] if tables_input.strip() else extracted_tables

            with st.spinner("Generating synthetic data and populating database..."):
                try:
                    # 1. Execute DDL script using cleaned DDL
                    ddl_success, ddl_msg = db.execute_ddl(cleaned_ddl)
                    if not ddl_success:
                        st.error(f"Database Error: {ddl_msg}")
                        st.stop()

                    # 2. Generate synthetic records using Gemini
                    raw_result = generate_table_data(
                        ddl_schema=cleaned_ddl,
                        table_names=table_list,
                        num_rows=num_rows,
                        temperature=temperature,
                        user_instructions=instructions
                    )

                    dataframes = {}
                    if isinstance(raw_result, dict):
                        for table_name, data in raw_result.items():
                            df = pd.DataFrame(data) if isinstance(data, list) else data
                            
                            # Standardize table keys and column names to lowercase
                            clean_table_name = str(table_name).strip().lower()
                            df.columns = [str(col).strip().lower() for col in df.columns]
                            
                            dataframes[clean_table_name] = df

                            save_success, save_msg = db.save_df_to_postgres(df, clean_table_name)
                            if not save_success:
                                st.error(f"Database Save Error: {save_msg}")
                                st.stop()
                    else:
                        df = pd.DataFrame(raw_result)
                        df.columns = [str(col).strip().lower() for col in df.columns]
                        dataframes["output"] = df
                        save_success, save_msg = db.save_df_to_postgres(df, "output")
                        if not save_success:
                            st.error(f"Database Save Error: {save_msg}")
                            st.stop()

                    st.session_state["generated_data"] = dataframes
                    st.session_state["ddl_schema"] = cleaned_ddl
                    st.success("Data successfully generated and saved to database!")
                except Exception as e:
                    st.error(f"Error processing request: {str(e)}")

    if st.session_state["generated_data"]:
        st.divider()
        st.subheader("Data Preview")

        table_options = list(st.session_state["generated_data"].keys())
        selected_table = st.selectbox("Select Table Preview", table_options)

        df = st.session_state["generated_data"][selected_table]
        if isinstance(df, pd.DataFrame):
            st.dataframe(df, use_container_width=True)

        st.write("")
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Save Data",
            data=csv_data,
            file_name=f"{selected_table}_synthetic_data.csv",
            mime="text/csv",
            type="primary"
        )

# ==========================================
# PHASE 2: TALK TO YOUR DATA
# ==========================================
elif page == "Talk to Your Data":
    st.title("Talk to Your Data")

    if not st.session_state.get("generated_data"):
        st.warning("Please generate a dataset in the Data Generation module first.")
    else:
        st.subheader("Query Dataset using Natural Language")

        # Render past chat messages
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "sql" in msg:
                    st.code(msg["sql"], language="sql")
                if "dataframe" in msg:
                    st.dataframe(msg["dataframe"], use_container_width=True)
                    # Render chart if stored
                    if msg.get("has_chart", False):
                        df_chart = msg["dataframe"]
                        st.bar_chart(df_chart.set_index(df_chart.columns[0]))

        # Accept user input
        user_question = st.chat_input("Ask a question about your database...")
        if user_question:
            st.session_state["chat_history"].append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.write(user_question)

            with st.chat_message("assistant"):
                with st.spinner("Generating SQL query..."):
                    try:
                        ddl = st.session_state.get("ddl_schema", "")
                        sql_query = generate_sql_query(ddl, user_question)

                        if not sql_query.upper().startswith("SELECT"):
                            st.error("Only read-only SELECT queries are permitted.")
                        else:
                            st.write("**Generated SQL Query:**")
                            st.code(sql_query, language="sql")

                            query_result = db.run_query(sql_query)
                            st.write("**Query Results:**")
                            st.dataframe(query_result, use_container_width=True)

                            # Auto-render chart for 2-column aggregate results (e.g., category + metric)
                            has_chart = False
                            if len(query_result.columns) == 2 and pd.api.types.is_numeric_dtype(query_result.iloc[:, 1]):
                                st.write("**Visualized Summary:**")
                                st.bar_chart(query_result.set_index(query_result.columns[0]))
                                has_chart = True

                            st.session_state["chat_history"].append({
                                "role": "assistant",
                                "content": "Here are the query results:",
                                "sql": sql_query,
                                "dataframe": query_result,
                                "has_chart": has_chart
                            })
                    except Exception as e:
                        st.error(f"Error executing query: {str(e)}")