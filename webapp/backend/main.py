"""
Thin FastAPI backend that sits in front of Ollama's API and Airflow's REST API,
so the Streamlit frontend (or anyone else) doesn't need to know either exists.
"""
import csv
import json
import os
import shutil
import subprocess

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

REPO_ROOT = os.environ.get("REPO_ROOT", "/Users/jeongwoo/new_github/Tablollama")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
AIRFLOW_BASE_URL = os.environ.get("AIRFLOW_BASE_URL", "http://localhost:8080/api/v1")
AIRFLOW_AUTH = ("admin", "admin")

BASELINES = {
    "tabsqlify": {
        "label": "TabSQLify",
        "dag_id": "table_reasoning_tabsqlify",
        "task_id": "run_tabsqlify_wtq",
        "progress_kind": "dir_count",
        "progress_path": os.path.join(REPO_ROOT, "TabSQLify", "outputs", "logs"),
        "results_path": os.path.join(REPO_ROOT, "TabSQLify", "outputs", "wtq_sql_results.jsonl"),
        "total": 4344,
    },
    "tablellm_agent": {
        "label": "tablellm (Agent)",
        "dag_id": "table_reasoning_tablellm_agent",
        "task_id": "run_tablellm_agent_wtq",
        "progress_kind": "line_count",
        "progress_path": os.path.join(REPO_ROOT, "tablellm", "output", "wtq_agent_ollama", "result.jsonl"),
        "results_path": os.path.join(REPO_ROOT, "tablellm", "output", "wtq_agent_ollama", "result.jsonl"),
        "total": 4344,
    },
    "tablellm_cot": {
        "label": "tablellm (CoT)",
        "dag_id": "table_reasoning_tablellm_cot",
        "task_id": "run_tablellm_cot_wtq",
        "progress_kind": "line_count",
        "progress_path": os.path.join(REPO_ROOT, "tablellm", "output", "wtq_cot_ollama", "result.jsonl"),
        "results_path": os.path.join(REPO_ROOT, "tablellm", "output", "wtq_cot_ollama", "result.jsonl"),
        "total": 4344,
    },
    "reactable": {
        "label": "ReAcTable",
        "dag_id": "table_reasoning_reactable",
        "task_id": "run_reactable_wtq",
        "progress_kind": "line_count",
        "progress_path": os.path.join(
            REPO_ROOT, "ReAcTable", "result",
            "CodexAnswerCOTExecutor_HighTemperaturMajorityVote_original-sql-py-no-intermediate_sql-py_NNDemo=False_modelllama3.2:1b.jsonl",
        ),
        "results_path": os.path.join(
            REPO_ROOT, "ReAcTable", "result",
            "CodexAnswerCOTExecutor_HighTemperaturMajorityVote_original-sql-py-no-intermediate_sql-py_NNDemo=False_modelllama3.2:1b.jsonl",
        ),
        "total": 4344,
    },
    "normtab": {
        "label": "NormTab",
        "dag_id": "table_reasoning_normtab",
        "task_id": "run_normtab_eval",
        "progress_kind": "line_count",
        "progress_path": os.path.join(REPO_ROOT, "NormTab", "outputs", "normTab_eval_targeted_wtq.jsonl"),
        "results_path": os.path.join(REPO_ROOT, "NormTab", "outputs", "normTab_eval_targeted_wtq.jsonl"),
        "total": 4339,
    },
    "alter": {
        "label": "ALTER",
        "dag_id": "table_reasoning_alter",
        "task_id": "run_alter_pipeline",
        "progress_kind": "csv_row_count",
        "results_kind": "csv",
        "progress_path": os.path.join(REPO_ROOT, "ALTER", "result", "answer", "wikitable_test_llama3.2:1b.csv"),
        "results_path": os.path.join(REPO_ROOT, "ALTER", "result", "answer", "wikitable_test_llama3.2:1b.csv"),
        "total": 4344,
    },
}

app = FastAPI(title="Table Reasoning Benchmark Runner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_baseline_or_404(key: str) -> dict:
    baseline = BASELINES.get(key)
    if baseline is None:
        raise HTTPException(status_code=404, detail=f"Unknown baseline '{key}'")
    return baseline


@app.get("/ollama/models")
def list_ollama_models():
    """Which models Ollama already has pulled — informational only for now,
    doesn't change which model a triggered run actually uses."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama not reachable: {e}")
    return resp.json()


@app.get("/ollama/status")
def ollama_status():
    try:
        requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return {"running": True}
    except requests.RequestException:
        return {"running": False}


@app.post("/ollama/start")
def start_ollama():
    """Starts Ollama in the background if it's not already running. Same
    approach as each DAG's check_ollama_alive task. Only works when this
    backend runs directly on the host — inside a container there's no
    `ollama` binary to launch, and it wouldn't be starting it on the host
    anyway, so Ollama must be started manually in that case."""
    try:
        requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return {"running": True, "started": False}
    except requests.RequestException:
        pass

    if shutil.which("ollama") is None:
        raise HTTPException(
            status_code=501,
            detail="No 'ollama' binary here (likely running inside a container). "
                   "Start Ollama on the host manually: OLLAMA_CONTEXT_LENGTH=24576 ollama serve",
        )

    env = dict(os.environ)
    env["OLLAMA_CONTEXT_LENGTH"] = "24576"
    subprocess.Popen(
        ["ollama", "serve"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"running": False, "started": True}


@app.get("/baselines")
def list_baselines():
    return {
        key: {"label": b["label"], "dag_id": b["dag_id"], "total": b["total"]}
        for key, b in BASELINES.items()
    }


@app.post("/run/{baseline_key}")
def trigger_run(baseline_key: str):
    baseline = _get_baseline_or_404(baseline_key)
    dag_id = baseline["dag_id"]

    # DAGs are paused by default when first created — unpause before triggering.
    requests.patch(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}",
        auth=AIRFLOW_AUTH,
        json={"is_paused": False},
        timeout=10,
    )

    resp = requests.post(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns",
        auth=AIRFLOW_AUTH,
        json={},
        timeout=10,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Airflow trigger failed: {resp.text}")
    return resp.json()


def _count_progress(baseline: dict) -> int:
    path = baseline["progress_path"]
    if baseline["progress_kind"] == "dir_count":
        if not os.path.isdir(path):
            return 0
        return len([f for f in os.listdir(path) if f.endswith(".txt")])
    if baseline["progress_kind"] == "line_count":
        if not os.path.isfile(path):
            return 0
        with open(path) as f:
            return sum(1 for _ in f)
    if baseline["progress_kind"] == "csv_row_count":
        # Raw line count is wrong here -- cells (model responses, etc.) can
        # contain embedded newlines, so a plain line count over-counts rows.
        if not os.path.isfile(path):
            return 0
        with open(path, newline="", encoding="utf-8") as f:
            return max(sum(1 for _ in csv.reader(f)) - 1, 0)  # -1 for header
    return 0


ACTIVE_DAG_RUN_STATES = {"queued", "running"}


def _latest_task_state(dag_id: str, task_id: str) -> str:
    """Fast path for the frequently-polled progress display: just the
    single newest run's state. Only 2 Airflow API calls, so this stays
    quick even if Airflow's webserver is a bit slow to respond."""
    runs_resp = requests.get(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns",
        auth=AIRFLOW_AUTH,
        params={"order_by": "-execution_date", "limit": 1},
        timeout=10,
    )
    if runs_resp.status_code != 200:
        return "unknown"
    runs = runs_resp.json().get("dag_runs", [])
    if not runs:
        return "no_runs_yet"

    run = runs[0]
    ti_resp = requests.get(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns/{run['dag_run_id']}/taskInstances/{task_id}",
        auth=AIRFLOW_AUTH,
        timeout=10,
    )
    ti_state = ti_resp.json().get("state") if ti_resp.status_code == 200 else None
    # Right after a trigger, the DagRun row exists before its TaskInstance
    # does (or the TI's state is still null) until the scheduler's next
    # loop picks it up. Fall back to the DagRun's own state — set the
    # instant the trigger call returns — so the UI shows something
    # immediately instead of "unknown" for those first few seconds.
    return ti_state or run.get("state") or "unknown"


def _active_run_id(dag_id: str, limit: int = 3) -> str | None:
    """The most recent run of this DAG that's genuinely still active
    (queued or running) — the one actually worth stopping, and the signal
    the frontend uses to know a baseline just got triggered. Checked at the
    DagRun level rather than the task-instance level: a DagRun's own state
    is set the instant a trigger succeeds, while its TaskInstance may not
    exist (or may report state=None) until the scheduler's next loop —
    checking task-instance state alone made a just-triggered baseline look
    "not running" for several seconds. Each DAG now maps to exactly one
    baseline (post agent/cot split), so the DAG's own state is enough —
    no need to also inspect a specific task_id here."""
    runs_resp = requests.get(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns",
        auth=AIRFLOW_AUTH,
        params={"order_by": "-execution_date", "limit": limit},
        timeout=10,
    )
    if runs_resp.status_code != 200:
        return None

    for run in runs_resp.json().get("dag_runs", []):
        if run.get("state") in ACTIVE_DAG_RUN_STATES:
            return run["dag_run_id"]
    return None


@app.get("/running")
def get_running_baselines():
    """Which baseline keys are genuinely active right now — the frontend
    uses this (not its own widget state, which resets on page reload) to
    decide what to show/lock/auto-refresh."""
    running = [
        key for key, b in BASELINES.items()
        if _active_run_id(b["dag_id"]) is not None
    ]
    return {"running": running}


@app.post("/stop/{baseline_key}")
def stop_run(baseline_key: str):
    """Actually stops a running baseline: force-fails the active DagRun
    itself (not one hardcoded task instance). A DAG has 3 sequential tasks
    (ensure_deps -> check_ollama_alive -> the actual run) and the live one
    at stop-time could be any of them — patching only the last task_id did
    nothing if e.g. ensure_deps was still installing packages. Force-
    failing the run's own state also finalizes it out of queued/running
    immediately, which matters because `_active_run_id`/`/running` check
    the DagRun's state: without this, a run that never got past `queued`
    (e.g. because the DAG was already paused when it was triggered) would
    sit "active" forever with no live process and nothing left to stop.
    Airflow cascades this into failing whichever task instances are still
    non-terminal, and its heartbeat kills the actual live process the same
    way a direct task-instance fail does. Then pauses the DAG so nothing
    new starts before the user explicitly runs it again."""
    baseline = _get_baseline_or_404(baseline_key)
    dag_id = baseline["dag_id"]

    run_id = _active_run_id(dag_id)
    if run_id is None:
        raise HTTPException(status_code=404, detail="No active run to stop")

    run_resp = requests.patch(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}/dagRuns/{run_id}",
        auth=AIRFLOW_AUTH,
        json={"state": "failed"},
        timeout=10,
    )
    if run_resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Failed to stop run: {run_resp.text}")

    requests.patch(
        f"{AIRFLOW_BASE_URL}/dags/{dag_id}",
        auth=AIRFLOW_AUTH,
        json={"is_paused": True},
        timeout=10,
    )
    return {"stopped": True, "dag_id": dag_id, "run_id": run_id}


@app.get("/progress/{baseline_key}")
def get_progress(baseline_key: str):
    baseline = _get_baseline_or_404(baseline_key)
    done = _count_progress(baseline)
    total = baseline["total"]
    return {
        "done": done,
        "total": total,
        "percent": round(100 * done / total, 2) if total else 0,
        "task_state": _latest_task_state(baseline["dag_id"], baseline["task_id"]),
    }


@app.get("/results/{baseline_key}")
def get_recent_results(baseline_key: str, limit: int = 10):
    """Most recently completed samples, newest first — for showing a live list
    of what the benchmark has actually produced, not just a percentage."""
    baseline = _get_baseline_or_404(baseline_key)
    path = baseline["results_path"]
    if not os.path.isfile(path):
        return []

    if baseline.get("results_kind") == "csv":
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return list(reversed(rows[-limit:]))

    with open(path) as f:
        lines = f.readlines()

    results = []
    for line in reversed(lines[-limit:]):
        line = line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results
