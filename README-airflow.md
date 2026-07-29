# Airflow Setup

Orchestrates the table-reasoning baselines in this repo as Airflow tasks instead of running each
one by hand. **TabSQLify** and **tablellm** are wired up so far; the rest follow the same pattern.

## Prerequisites

Ollama doesn't need to be running before you start the DAG — `check_ollama_alive` polls it for 30s,
and if it's not up, starts it itself (`OLLAMA_CONTEXT_LENGTH=24576 ollama serve`, detached) and
polls for another 60s before giving up. You can still start it manually if you prefer:

```bash
OLLAMA_CONTEXT_LENGTH=24576 ollama serve
```

Each baseline runs in its own conda env with its own `requirements.txt`. TabSQLify and tablellm
currently share one env (`table`) — checked compatible versions of overlapping packages first
(openai, pandas, tiktoken, etc.), only installed the handful of genuinely missing packages, and
never touch already-pinned versions. If a future baseline turns out to have a real conflicting pin
(e.g. H-STAR's `openai==0.28.0` vs tablellm's `1.12.0`), give it its own env instead.

Airflow itself always gets its own separate env — it only needs to shell out to each baseline's
interpreter, not share a runtime with any of them.

## Install

```bash
conda create -n airflow python=3.11 -y
conda activate airflow
export AIRFLOW_HOME=~/airflow

pip install "apache-airflow==2.10.4" apache-airflow-providers-http \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.11.txt"
```

## Initialize

```bash
export AIRFLOW_HOME=~/airflow
airflow db migrate

# disable Airflow's ~70 bundled example DAGs: set load_examples = False
# in $AIRFLOW_HOME/airflow.cfg under [core], then:
airflow db reset -y

airflow users create --username admin --password admin \
  --firstname <first> --lastname <last> --role Admin --email <email>

airflow connections add ollama_default --conn-type http --conn-host localhost --conn-port 11434
```

## Add the DAG

DAG source: [`airflow_dags/table_reasoning_dag.py`](airflow_dags/table_reasoning_dag.py)
(version-controlled), symlinked into Airflow's dags folder:

```bash
mkdir -p ~/airflow/dags
ln -sf /path/to/Tablollama/airflow_dags/table_reasoning_dag.py ~/airflow/dags/table_reasoning_dag.py
```

Update the path constants at the top of that file for your machine:

```python
TABSQLIFY_DIR = "/path/to/Tablollama/TabSQLify"
TABLELLM_DIR = "/path/to/Tablollama/tablellm"
TABLE_PYTHON = "/path/to/conda/envs/table/bin/python"
```

## Run

```bash
export AIRFLOW_HOME=~/airflow
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES   # works around a macOS gunicorn crash, see below
airflow webserver --port 8080 --workers 1 &
airflow scheduler &
```

Log in at `http://localhost:8080` (`admin` / `admin`) and trigger `table_reasoning_benchmark`.

## DAG structure

```
check_ollama_alive → [run_tabsqlify_wtq, run_tablellm_wtq]   (parallel, both gated by one healthcheck)
```

## Automatic recovery

Both baseline tasks have `retries=1000` / `retry_delay=1 min`. If a task dies mid-run (Ollama
hiccup, crash, etc.), Airflow relaunches it automatically — no manual retrigger needed.

- `run_wtq_full.py` (TabSQLify) skips already-completed samples via its own `done_ids` checkpoint
  (`outputs/logs/`).
- `run_agent_ollama.py` (tablellm) has **no built-in checkpoint** — it takes a manual `--resume=N`
  index instead of auto-detecting progress. The task's `bash_command` counts existing lines in
  `output/wtq_agent_ollama/result.jsonl` and passes that count as `--resume` on every launch, so
  automatic retries resume correctly instead of re-appending duplicate results from index 0. Any
  future baseline without its own checkpoint needs the same treatment — don't assume `retries=`
  alone is safe.

To stop a task on purpose, mark it "Failed" in the UI (or via the API) — Airflow's own heartbeat
detects the state change and kills the underlying process within one heartbeat cycle. To stop it
for good (not just this attempt), pause the DAG too, otherwise the retry policy revives it.

## Known issue: webserver log viewer crashes (macOS)

The webserver's gunicorn workers can die with `SIGSEGV` repeatedly on macOS, which shows up as
"No task logs found" in the UI even though the task is running fine and writing real output.
`--workers 1` plus `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` reduces but doesn't fully eliminate
it. If the UI log viewer is unreliable, tail the log file directly instead — it's always accurate:

```bash
tail -f ~/airflow/logs/dag_id=table_reasoning_benchmark/run_id=<run_id>/task_id=<task_id>/attempt=1.log
```

## TODO

- Add the other 5 baselines (ALTER, H-STAR, NormTab, ReAcTable, chain-of-table) — own conda env
  (or shared, if versions actually check out) + task each, same pattern. Check each one's own
  checkpoint situation individually — don't assume it has one.
- tablellm's default `sub_sample=True` only runs 837 of the WTQ questions (vs. TabSQLify's full
  4344). TabSQLify at ~3 min/sample locally → ~9 days unattended for the full set; test on a small
  subset first if timing tablellm against the same scale matters.
