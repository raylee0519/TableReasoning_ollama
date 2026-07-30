from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

ALTER_DIR = "/Users/jeongwoo/new_github/Tablollama/ALTER"
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
    dag_id="table_reasoning_alter",
    start_date=datetime(2026, 7, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["table-reasoning", "alter"],
) as dag:

    ensure_deps = BashOperator(
        task_id="ensure_deps",
        bash_command=f"{TABLE_PYTHON} {ENSURE_REQUIREMENTS_SCRIPT} {ALTER_DIR}/requirements.txt {TABLE_PYTHON}",
    )

    check_ollama = BashOperator(
        task_id="check_ollama_alive",
        bash_command=CHECK_OLLAMA_BASH,
    )

    # Stage 1: table augmentation (summary/schema/composition side info),
    # required before Pipeline mode can run at all -- batch_pipe.py reads all
    # three result/augmentation/*.csv files unconditionally. Already self-
    # resuming (fixed filename per aug type, skips table ids already in that
    # file) without any changes needed.
    run_augmentation = BashOperator(
        task_id="run_alter_augmentation",
        bash_command=(
            f"cd {ALTER_DIR} && {TABLE_PYTHON} -u run.py "
            "--task_name wikitable --split test --mode Augmentation "
            "--aug_type summary schema composition --model llama3.2:1b"
        ),
        retries=1000,
        retry_delay=timedelta(minutes=1),
        pool="ollama_pool",
    )

    # Stage 2: the actual QA pipeline. --save_file is required -- without it
    # nothing is written and the self-resume check has nothing to read.
    run_pipeline = BashOperator(
        task_id="run_alter_pipeline",
        bash_command=(
            f"cd {ALTER_DIR} && {TABLE_PYTHON} -u run.py "
            "--task_name wikitable --split test --mode Pipeline "
            "--save_file --model llama3.2:1b"
        ),
        retries=1000,
        retry_delay=timedelta(minutes=1),
        pool="ollama_pool",
    )

    ensure_deps >> check_ollama >> run_augmentation >> run_pipeline
