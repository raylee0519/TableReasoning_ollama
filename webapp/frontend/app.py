import os
import time

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Tablollama", layout="wide")
st.title("Tablollama")
st.caption("Table Reasoning Benchmark Runner")


def _first_present(d: dict, keys: list):
    for k in keys:
        if k in d:
            return d[k]
    return None


# Backend is the single source of truth for "what's running" — never our
# own widget state, which resets on every page reload.
try:
    running_keys = requests.get(f"{BACKEND_URL}/running", timeout=5).json().get("running", [])
except Exception:
    running_keys = []

is_running = len(running_keys) > 0

try:
    baselines = requests.get(f"{BACKEND_URL}/baselines", timeout=5).json()
except Exception as e:
    st.error(f"Backend connection failed: {e}")
    st.stop()

left, right = st.columns(2)

# ============================================================
# LEFT: ollama status, model selection, baseline selection, run/stop
# ============================================================
with left:
    st.subheader("Ollama Status")
    try:
        ollama_running = requests.get(f"{BACKEND_URL}/ollama/status", timeout=3).json()["running"]
    except Exception:
        ollama_running = False

    ollama_toggle = st.toggle(
        "Running" if ollama_running else "Off — toggle to start",
        value=ollama_running,
        key="ollama_toggle",
    )
    if ollama_toggle and not ollama_running:
        requests.post(f"{BACKEND_URL}/ollama/start", timeout=5)
        st.info("Starting Ollama. Refresh in a moment.")

    st.subheader("Ollama Model Selection")
    try:
        models_resp = requests.get(f"{BACKEND_URL}/ollama/models", timeout=5).json()
        model_names = [m["name"] for m in models_resp.get("models", [])]
    except Exception:
        model_names = []

    if model_names:
        selected_model = st.selectbox("Model", model_names, disabled=is_running)
    else:
        st.warning("No Ollama models installed.")
        selected_model = "llama3.2:1b"

    st.subheader("Select Method to Run")
    if is_running:
        st.caption("Selection can't be changed while running. Stop first to change it.")

    label_to_key = {info["label"]: key for key, info in baselines.items()}
    labels = list(label_to_key.keys())

    if running_keys:
        default_label = baselines[running_keys[0]]["label"]
        default_index = labels.index(default_label) if default_label in labels else 0
    else:
        default_index = 0

    selected_label = st.selectbox(
        "Method",
        labels,
        index=default_index,
        disabled=is_running,
        key="baseline_select",
    )
    selected_baselines = [label_to_key[selected_label]]

    col_run, col_stop = st.columns(2)
    with col_run:
        run_clicked = st.button("Run", disabled=is_running, use_container_width=True)
    with col_stop:
        stop_clicked = st.button("Stop", disabled=not is_running, use_container_width=True)

    if run_clicked:
        for key in selected_baselines:
            resp = requests.post(f"{BACKEND_URL}/run/{key}", params={"model": selected_model}, timeout=10)
            if resp.ok:
                st.success(f"{baselines[key]['label']} triggered")
            else:
                st.error(f"{baselines[key]['label']} trigger failed: {resp.text}")
        st.rerun()

    if stop_clicked:
        for key in running_keys:
            resp = requests.post(f"{BACKEND_URL}/stop/{key}", timeout=10)
            if resp.ok:
                st.success(f"{baselines[key]['label']} stopped")
            else:
                st.error(f"{baselines[key]['label']} stop failed: {resp.text}")
        st.rerun()

# ============================================================
# RIGHT: progress + recent results, only for what's actually running
# ============================================================
with right:
    st.subheader("Progress")

    if not running_keys:
        st.caption("No workflow is running.")
    else:
        st.caption("Auto-refreshes every 5 seconds while running.")

        for key in running_keys:
            info = baselines[key]
            progress = requests.get(f"{BACKEND_URL}/progress/{key}", timeout=5).json()
            stages = progress["stages"]
            current_idx = progress["current_stage_index"]

            if len(stages) > 1:
                st.markdown(f"**{info['label']}**")
            for i, stage in enumerate(stages):
                if stage["task_state"] == "success":
                    icon = "✅"
                elif i == current_idx:
                    icon = "▶️"
                else:
                    icon = "⏳"
                st.markdown(f"{icon} **{stage['label']}** — {stage['done']}/{stage['total']} "
                            f"({stage['percent']}%) — status: {stage['task_state']}")
                st.progress(min(stage["percent"] / 100, 1.0))

            results = requests.get(f"{BACKEND_URL}/results/{key}", params={"limit": 10}, timeout=5).json()
            if results:
                # Rendered as a hand-built markdown table (no pandas/pyarrow) — both
                # st.dataframe and st.table route through pyarrow's pandas->Arrow
                # conversion, which segfaults in this container (ARM64 pyarrow bug,
                # see pyarrow.pandas_compat.convert_column). This sidesteps it entirely.
                def _cell(value) -> str:
                    text = str(value if value is not None else "")
                    text = text.replace("|", "\\|").replace("\n", " ")
                    return text[:150] + "…" if len(text) > 150 else text

                header = "| id | question | answer | prediction |"
                separator = "| --- | --- | --- | --- |"
                lines = [header, separator]
                for r in results:
                    lines.append(
                        "| " + " | ".join([
                            _cell(_first_present(r, ["id", "question_id", "idx", "key", "table_ids"])),
                            _cell(_first_present(r, ["question", "utterance"])),
                            _cell(_first_present(r, ["gold_answer", "answer", "target_value"])),
                            _cell(_first_present(r, ["prediction", "text", "predicted_value", "preds"])),
                        ]) + " |"
                    )
                st.markdown("\n".join(lines))
            else:
                st.caption("No results yet.")

            st.divider()

if is_running:
    time.sleep(5)
    st.rerun()
