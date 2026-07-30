import os
import time

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Table Reasoning Benchmark Runner", layout="wide")
st.title("Table Reasoning Benchmark Runner")


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
    st.error(f"백엔드 연결 실패: {e}")
    st.stop()

left, right = st.columns(2)

# ============================================================
# LEFT: ollama status, model selection, baseline selection, run/stop
# ============================================================
with left:
    st.subheader("Ollama 상태")
    try:
        ollama_running = requests.get(f"{BACKEND_URL}/ollama/status", timeout=3).json()["running"]
    except Exception:
        ollama_running = False

    ollama_toggle = st.toggle(
        "실행 중" if ollama_running else "꺼짐 — 토글을 켜면 시작합니다",
        value=ollama_running,
        key="ollama_toggle",
    )
    if ollama_toggle and not ollama_running:
        requests.post(f"{BACKEND_URL}/ollama/start", timeout=5)
        st.info("Ollama를 시작하는 중입니다. 잠시 후 새로고침하세요.")

    st.subheader("Ollama 모델 선택")
    try:
        models_resp = requests.get(f"{BACKEND_URL}/ollama/models", timeout=5).json()
        model_names = [m["name"] for m in models_resp.get("models", [])]
    except Exception:
        model_names = []

    if model_names:
        st.selectbox("모델", model_names, disabled=is_running)
        st.caption("실행에 사용되는 모델은 아직 각 baseline 기본값으로 고정되어 있습니다.")
    else:
        st.warning("설치된 Ollama 모델이 없습니다.")

    st.subheader("실행할 방식 선택")
    if is_running:
        st.caption("실행 중에는 선택을 바꿀 수 없습니다. 정지 후 다시 선택하세요.")

    label_to_key = {info["label"]: key for key, info in baselines.items()}
    labels = list(label_to_key.keys())

    if running_keys:
        default_label = baselines[running_keys[0]]["label"]
        default_index = labels.index(default_label) if default_label in labels else 0
    else:
        default_index = 0

    selected_label = st.selectbox(
        "방식",
        labels,
        index=default_index,
        disabled=is_running,
        key="baseline_select",
    )
    selected_baselines = [label_to_key[selected_label]]

    col_run, col_stop = st.columns(2)
    with col_run:
        run_clicked = st.button("실행", disabled=is_running, use_container_width=True)
    with col_stop:
        stop_clicked = st.button("정지", disabled=not is_running, use_container_width=True)

    if run_clicked:
        for key in selected_baselines:
            resp = requests.post(f"{BACKEND_URL}/run/{key}", timeout=10)
            if resp.ok:
                st.success(f"{baselines[key]['label']} 트리거됨")
            else:
                st.error(f"{baselines[key]['label']} 트리거 실패: {resp.text}")
        st.rerun()

    if stop_clicked:
        for key in running_keys:
            resp = requests.post(f"{BACKEND_URL}/stop/{key}", timeout=10)
            if resp.ok:
                st.success(f"{baselines[key]['label']} 정지됨")
            else:
                st.error(f"{baselines[key]['label']} 정지 실패: {resp.text}")
        st.rerun()

# ============================================================
# RIGHT: progress + recent results, only for what's actually running
# ============================================================
with right:
    st.subheader("진행 상황")

    if not running_keys:
        st.caption("실행 중인 워크플로우가 없습니다.")
    else:
        st.caption("실행되는 동안 5초마다 자동으로 새로고침됩니다.")

        for key in running_keys:
            info = baselines[key]
            progress = requests.get(f"{BACKEND_URL}/progress/{key}", timeout=5).json()
            st.markdown(f"**{info['label']}** — {progress['done']}/{progress['total']} "
                        f"({progress['percent']}%) — 상태: {progress['task_state']}")
            st.progress(min(progress["percent"] / 100, 1.0))

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
                            _cell(_first_present(r, ["id", "question_id", "idx", "key"])),
                            _cell(_first_present(r, ["question", "utterance"])),
                            _cell(_first_present(r, ["gold_answer", "answer", "target_value"])),
                            _cell(_first_present(r, ["prediction", "text", "predicted_value"])),
                        ]) + " |"
                    )
                st.markdown("\n".join(lines))
            else:
                st.caption("아직 결과 없음")

            st.divider()

if is_running:
    time.sleep(5)
    st.rerun()
