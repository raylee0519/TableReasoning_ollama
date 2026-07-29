from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

TABSQLIFY_DIR = "/Users/jeongwoo/new_github/Tablollama/TabSQLify"
TABLELLM_DIR = "/Users/jeongwoo/new_github/Tablollama/tablellm"
TABLE_PYTHON = "/opt/anaconda3/envs/table/bin/python"

with DAG(
    dag_id="table_reasoning_benchmark",
    start_date=datetime(2026, 7, 29),
    schedule=None,
    catchup=False,
    tags=["table-reasoning"],
) as dag:

    check_ollama = BashOperator(
        task_id="check_ollama_alive",
        bash_command="""
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
        """,
    )

    run_tabsqlify = BashOperator(
        task_id="run_tabsqlify_wtq",
        bash_command=f"cd {TABSQLIFY_DIR} && {TABLE_PYTHON} -u run_wtq_full.py",
        retries=1000,
        retry_delay=timedelta(minutes=1),
    )

    # run_agent_ollama.py has no automatic checkpoint (unlike TabSQLify's done_ids) —
    # it takes a manual `--resume=N` index instead. To make retries safe, we count
    # existing results ourselves before every launch and pass that in as --resume.
    run_tablellm = BashOperator(
        task_id="run_tablellm_wtq",
        bash_command=f"""
        cd {TABLELLM_DIR}
        LOG_DIR=output/wtq_agent_ollama
        mkdir -p "$LOG_DIR"
        RESUME=$(wc -l < "$LOG_DIR/result.jsonl" 2>/dev/null | tr -d ' ')
        RESUME=${{RESUME:-0}}
        echo "Resuming tablellm from index $RESUME"
        {TABLE_PYTHON} -u run_agent_ollama.py --dataset=wtq --log_dir=$LOG_DIR --resume=$RESUME
        """,
        retries=1000,
        retry_delay=timedelta(minutes=1),
    )

    check_ollama >> [run_tabsqlify, run_tablellm]
