from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

REACTABLE_DIR = "/Users/jeongwoo/new_github/Tablollama/ReAcTable"
TABLE_PYTHON = "/opt/anaconda3/envs/table/bin/python"
ENSURE_REQUIREMENTS_SCRIPT = "/Users/jeongwoo/new_github/Tablollama/airflow_dags/ensure_requirements.py"
MLFLOW_LOG_SCRIPT = "/Users/jeongwoo/new_github/Tablollama/mlflow_tracking/log_run.py"

CHECK_OLLAMA_BASH = """
for i in $(seq 1 6); do
  curl -sf -m 5 http://localhost:11434/api/tags > /dev/null && exit 0
  sleep 5
done

echo "Ollama not responding, starting it..."
OLLAMA_CONTEXT_LENGTH=24576 nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
disown

for i in $(seq 1 12); do
  curl -sf -m 5 http://localhost:11434/api/tags > /dev/null && exit 0
  sleep 5
done

echo "Ollama failed to start" >&2
exit 1
"""

with DAG(
    dag_id="table_reasoning_reactable",
    start_date=datetime(2026, 7, 30),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["table-reasoning", "reactable"],
) as dag:

    ensure_deps = BashOperator(
        task_id="ensure_deps",
        bash_command=f"{TABLE_PYTHON} {ENSURE_REQUIREMENTS_SCRIPT} {REACTABLE_DIR}/requirements.txt {TABLE_PYTHON}",
    )

    check_ollama = BashOperator(
        task_id="check_ollama_alive",
        bash_command=CHECK_OLLAMA_BASH,
    )

    # WikiTQ_inference.py checkpoints itself by scanning its own output
    # .jsonl for already-done ids (same self-resuming style as TabSQLify's
    # done_ids, no --resume flag needed), so a bare rerun after any retry is
    # safe.
    run_reactable = BashOperator(
        task_id="run_reactable_wtq",
        bash_command=f"cd {REACTABLE_DIR} && {TABLE_PYTHON} -u WikiTQ_inference.py",
        retries=1000,
        retry_delay=timedelta(minutes=1),
        pool="ollama_pool",
    )

    log_to_mlflow = BashOperator(
        task_id="log_to_mlflow",
        bash_command=f"{TABLE_PYTHON} {MLFLOW_LOG_SCRIPT} --baseline reactable",
        retries=3,
        retry_delay=timedelta(seconds=30),
    )

    ensure_deps >> check_ollama >> run_reactable >> log_to_mlflow
