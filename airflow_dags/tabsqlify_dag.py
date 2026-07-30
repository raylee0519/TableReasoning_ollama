from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

TABSQLIFY_DIR = "/Users/jeongwoo/new_github/Tablollama/TabSQLify"
TABLE_PYTHON = "/opt/anaconda3/envs/table/bin/python"
ENSURE_REQUIREMENTS_SCRIPT = "/Users/jeongwoo/new_github/Tablollama/airflow_dags/ensure_requirements.py"

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
    dag_id="table_reasoning_tabsqlify",
    start_date=datetime(2026, 7, 29),
    schedule=None,
    catchup=False,
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
        retries=1000,
        retry_delay=timedelta(minutes=1),
        pool="ollama_pool",
    )

    ensure_deps >> check_ollama >> run_tabsqlify
