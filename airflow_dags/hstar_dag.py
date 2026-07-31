from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

HSTAR_DIR = "/Users/jeongwoo/new_github/Tablollama/H-STAR"
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

ENGINE = "llama3.2:1b"


def stage_bash(module, prompt_file, input_program_file=None, n_parallel_prompts=3,
                temperature=0.3, sampling_n=2, max_generation_tokens=512):
    input_flag = f"--input_program_file {input_program_file} " if input_program_file else ""
    return (
        f"cd {HSTAR_DIR} && export TOKENIZERS_PARALLELISM=false && "
        f"{TABLE_PYTHON} -m scripts.model_ollama.{module} --dataset wikitq --dataset_split test "
        f"--prompt_file prompts/{prompt_file} --engine {ENGINE} "
        f"--n_parallel_prompts {n_parallel_prompts} {input_flag}"
        f"--max_generation_tokens {max_generation_tokens} --temperature {temperature} "
        f"--sampling_n {sampling_n} -v"
    )


with DAG(
    dag_id="table_reasoning_hstar",
    start_date=datetime(2026, 7, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["table-reasoning", "hstar"],
) as dag:

    ensure_deps = BashOperator(
        task_id="ensure_deps",
        bash_command=f"{TABLE_PYTHON} {ENSURE_REQUIREMENTS_SCRIPT} {HSTAR_DIR}/requirements.txt {TABLE_PYTHON}",
    )

    check_ollama = BashOperator(
        task_id="check_ollama_alive",
        bash_command=CHECK_OLLAMA_BASH,
    )

    # 6-stage pipeline, each stage's output JSON feeds the next stage's
    # --input_program_file (matching run_ollama.py). None of these stages
    # checkpoint internally -- each accumulates all results in memory and
    # writes its output once at the end, so a retry redoes that whole stage
    # from scratch rather than resuming mid-stage. Left as-is for now.
    col_sql = BashOperator(
        task_id="run_hstar_col_sql",
        bash_command=stage_bash("col_sql", "col_select_sql.txt", temperature=0.3, sampling_n=2),
        retries=1000, retry_delay=timedelta(minutes=1), pool="ollama_pool",
    )
    col_text = BashOperator(
        task_id="run_hstar_col_text",
        bash_command=stage_bash("col_text", "col_select_text.txt", "wikitq_test_col_sql.json", temperature=0.4, sampling_n=2),
        retries=1000, retry_delay=timedelta(minutes=1), pool="ollama_pool",
    )
    row_sql = BashOperator(
        task_id="run_hstar_row_sql",
        bash_command=stage_bash("row_sql", "row_select_sql.txt", "wikitq_test_col_text.json", temperature=0.3, sampling_n=2),
        retries=1000, retry_delay=timedelta(minutes=1), pool="ollama_pool",
    )
    row_text = BashOperator(
        task_id="run_hstar_row_text",
        bash_command=stage_bash("row_text", "row_select_text.txt", "wikitq_test_row_sql.json", temperature=0.4, sampling_n=2),
        retries=1000, retry_delay=timedelta(minutes=1), pool="ollama_pool",
    )
    reason_sql = BashOperator(
        task_id="run_hstar_reason_sql",
        bash_command=stage_bash("reason_sql", "sql_reason_wtq.txt", "wikitq_test_row_text.json", temperature=0.1, sampling_n=1),
        retries=1000, retry_delay=timedelta(minutes=1), pool="ollama_pool",
    )
    reason_text = BashOperator(
        task_id="run_hstar_reason_text",
        bash_command=stage_bash("reason_text", "text_reason_wtq.txt", "wikitq_test_sql_reason.json",
                                 n_parallel_prompts=1, temperature=0.0, sampling_n=1),
        retries=1000, retry_delay=timedelta(minutes=1), pool="ollama_pool",
    )

    ensure_deps >> check_ollama >> col_sql >> col_text >> row_sql >> row_text >> reason_sql >> reason_text
