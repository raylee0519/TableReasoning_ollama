import os

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

REPO_ROOT = os.environ.get("REPO_ROOT", "/Users/jeongwoo/new_github/Tablollama")
TABLE_PYTHON = os.environ.get("TABLE_PYTHON", "/opt/anaconda3/envs/table/bin/python")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "localhost:11434")
MODEL = "{{ dag_run.conf.get('model', 'llama3.2:1b') }}"

TABSQLIFY_DIR = os.path.join(REPO_ROOT, "TabSQLify")
ENSURE_REQUIREMENTS_SCRIPT = os.path.join(REPO_ROOT, "airflow_dags", "ensure_requirements.py")
MLFLOW_LOG_SCRIPT = os.path.join(REPO_ROOT, "mlflow_tracking", "log_run.py")

CHECK_OLLAMA_BASH = f"""
for i in $(seq 1 6); do
  curl -sf -m 5 http://{OLLAMA_HOST}/api/tags > /dev/null && exit 0
  sleep 5
done

echo "Ollama not responding, starting it..."
OLLAMA_CONTEXT_LENGTH=24576 nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
disown

for i in $(seq 1 12); do
  curl -sf -m 5 http://{OLLAMA_HOST}/api/tags > /dev/null && exit 0
  sleep 5
done

echo "Ollama failed to start" >&2
exit 1
"""

with DAG(
    dag_id="table_reasoning_tabsqlify",
    start_date=datetime(2026, 7, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["table-reasoning", "tabsqlify"],
) as dag:

    ensure_deps = BashOperator(
        task_id="ensure_deps",
        bash_command=f"{TABLE_PYTHON} {ENSURE_REQUIREMENTS_SCRIPT} {TABSQLIFY_DIR}/requirements.txt {TABLE_PYTHON}",
    )

    check_ollama = BashOperator(
        task_id="check_ollama_alive",
        bash_command=CHECK_OLLAMA_BASH,
    )

    run_tabsqlify = BashOperator(
        task_id="run_tabsqlify_wtq",
        bash_command=f"cd {TABSQLIFY_DIR} && {TABLE_PYTHON} -u run_wtq_full.py",
        env={"MODEL_NAME": MODEL},
        append_env=True,
        retries=1000,
        retry_delay=timedelta(minutes=1),
        pool="ollama_pool",
    )

    log_to_mlflow = BashOperator(
        task_id="log_to_mlflow",
        bash_command=f"{TABLE_PYTHON} {MLFLOW_LOG_SCRIPT} --baseline tabsqlify --model {MODEL}",
        retries=3,
        retry_delay=timedelta(seconds=30),
    )

    ensure_deps >> check_ollama >> run_tabsqlify >> log_to_mlflow
