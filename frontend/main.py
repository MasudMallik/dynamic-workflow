
import streamlit as st
import requests
import pandas as pd
import json
from graphviz import Digraph

st.set_page_config(page_title="Dynamic Workflow Generator", page_icon="🔀", layout="wide")

API_URL = "http://127.0.0.1:8000"

COLORS = {
    "Input": "#DBEAFE",
    "Approval": "#FEF3C7",
    "Notification": "#EDE9FE",
    "Decision": "#FFEDD5",
    "Action": "#D1FAE5",
    "End": "#FCE7F3"
}

STEP_TYPES = ["Input", "Approval", "Notification", "Decision", "Action", "End"]

st.title("🔀 Dynamic Workflow Generator")

description = st.text_area(
    "Describe your business process",
    placeholder="Example: HR collects documents, the manager approves them, and IT creates an account."
)

if st.button("✨ Generate Workflow", type="primary"):
    if not description.strip():
        st.warning("Please enter a business process.")
    else:
        try:
            with st.spinner("Generating workflow..."):
                response = requests.post(
                    f"{API_URL}/api/workflows/generate",
                    json={"description": description},
                    timeout=120
                )
                response.raise_for_status()
                workflow = response.json()

            st.session_state.workflow = workflow
            st.session_state.editor_data = pd.DataFrame([
                {
                    "id": s["id"],
                    "name": s["name"],
                    "type": s["type"],
                    "sequence": s["sequence"],
                    "description": s.get("description", ""),
                    "dependencies": ", ".join(s.get("dependencies", [])),
                    "outcomes": json.dumps(s.get("outcomes", {}))
                }
                for s in workflow.get("steps", [])
            ])
            st.rerun()

        except requests.RequestException as e:
            st.error(f"Backend error: {e}")
            if e.response is not None:
                st.code(e.response.text)

if st.session_state.get("workflow"):
    workflow = st.session_state.workflow

    st.divider()
    st.subheader("✏️ Edit Workflow")

    workflow["title"] = st.text_input(
        "Workflow title",
        value=workflow.get("title", "My Workflow")
    )

    workflow["description"] = st.text_area(
        "Workflow description",
        value=workflow.get("description", "")
    )

    edited_df = st.data_editor(
        st.session_state.editor_data,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "type": st.column_config.SelectboxColumn(
                "Type", options=STEP_TYPES
            )
        }
    )

    if st.button("💾 Update Workflow"):
        try:
            steps = []
            ids = edited_df["id"].fillna("").astype(str).str.strip().tolist()

            if not ids or any(not x for x in ids):
                raise ValueError("Every step needs an ID.")

            if len(ids) != len(set(ids)):
                raise ValueError("Step IDs must be unique.")

            id_set = set(ids)

            for _, row in edited_df.iterrows():
                dependencies = [
                    x.strip()
                    for x in str(row["dependencies"]).split(",")
                    if x.strip() and x.strip().lower() != "nan"
                ]

                outcomes_text = str(row["outcomes"]).strip()
                outcomes = json.loads(outcomes_text) if outcomes_text else {}

                if not isinstance(outcomes, dict):
                    raise ValueError("Outcomes must be a JSON object.")

                step = {
                    "id": str(row["id"]).strip(),
                    "name": str(row["name"]).strip(),
                    "type": row["type"],
                    "sequence": int(row["sequence"]),
                    "description": str(row["description"]),
                    "dependencies": dependencies,
                    "outcomes": outcomes
                }

                if not step["name"]:
                    raise ValueError(f"Name required for {step['id']}.")

                if step["type"] not in STEP_TYPES:
                    raise ValueError(f"Invalid type for {step['id']}.")

                for dep in dependencies:
                    if dep not in id_set or dep == step["id"]:
                        raise ValueError(f"Invalid dependency: {dep}")

                for target in outcomes.values():
                    if target not in id_set:
                        raise ValueError(f"Invalid outcome target: {target}")

                steps.append(step)

            if len({s["sequence"] for s in steps}) != len(steps):
                raise ValueError("Sequence numbers must be unique.")

            workflow["steps"] = sorted(steps, key=lambda s: s["sequence"])
            st.session_state.workflow = workflow
            st.session_state.editor_data = pd.DataFrame([
                {
                    **s,
                    "dependencies": ", ".join(s["dependencies"]),
                    "outcomes": json.dumps(s["outcomes"])
                }
                for s in workflow["steps"]
            ])

            st.success("Workflow updated.")
            st.rerun()

        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            st.error(f"Please check your edits: {e}")

    workflow = st.session_state.workflow
    steps = workflow.get("steps", [])

    graph = Digraph("Workflow", format="png")
    graph.attr(
        rankdir="TB",
        bgcolor="white",
        pad="0.25",
        nodesep="0.3",
        ranksep="0.4",
        splines="polyline"
    )
    graph.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Arial",
        fontsize="10",
        margin="0.15,0.10",
        color="#64748B",
        fontcolor="#172033"
    )
    graph.attr("edge", color="#64748B", arrowsize="0.7")

    for step in steps:
        graph.node(
            step["id"],
            f'{step["name"]}\n({step["type"]})',
            fillcolor=COLORS.get(step["type"], "#E2E8F0")
        )

    for step in steps:
        for dep in step.get("dependencies", []):
            graph.edge(dep, step["id"])

        for outcome, target in step.get("outcomes", {}).items():
            graph.edge(step["id"], target, label=outcome)

    st.divider()
    st.subheader("📊 Workflow Diagram")
    st.graphviz_chart(graph, width="stretch")

    try:
        png_data = graph.pipe(format="png")
        st.download_button(
            "🖼️ Download Workflow as PNG",
            data=png_data,
            file_name="workflow.png",
            mime="image/png"
        )
    except Exception as e:
        st.error(f"PNG export failed: {e}")

    st.download_button(
        "⬇️ Download Workflow as JSON",
        data=json.dumps(workflow, indent=2),
        file_name="workflow.json",
        mime="application/json"
    )

    with st.expander("View Workflow JSON"):
        st.json(workflow)

    if st.button("🔄 Start New Workflow"):
        for key in ["workflow", "editor_data"]:
            st.session_state.pop(key, None)
        st.rerun()
