# Airflow Setup

Orchestrates the table-reasoning baselines in this repo as Airflow tasks instead of running each
one by hand. **TabSQLify** and **tablellm** (its `agent` and `cot` modes as two separate DAGs) are
wired up so far, each as its own DAG; the rest follow the same pattern.

## Airflow Pipeline Affordable
The following models have been tested and are currently supported for evaluation:

- **H-STAR** (X)
- **NormTab** (✓)
- **ReAcTable** (✓)
- **TabSQLify** (✓)
- **Mix-SC** (✓)
- **chain-of-Table** (X)
- **ALTER** (✓)


## Prerequisites

Ollama doesn't need to be running before you trigger a DAG — each one's `check_ollama_alive` polls
it for 30s, and if it's not up, starts it itself (`OLLAMA_CONTEXT_LENGTH=24576 ollama serve`,
detached) and polls for another 60s before giving up. You can still start it manually if you prefer:

```bash
OLLAMA_CONTEXT_LENGTH=24576 ollama serve
```

Each baseline runs in its own conda env with its own `requirements.txt`. TabSQLify and tablellm
currently share one env (`table`) — checked compatible versions of overlapping packages first
(openai, pandas, tiktoken, etc.), only installed the handful of genuinely missing packages, and
never touch already-pinned versions.

Each DAG's first task, `ensure_deps`, automates that same check on every run:
[`airflow_dags/ensure_requirements.py`](airflow_dags/ensure_requirements.py) reads the baseline's
`requirements.txt`, checks which packages are actually missing from the target env, and installs
only those — by name, without the pinned version — so it never downgrades a package the shared env
already has at a newer version. Task order is `ensure_deps → check_ollama_alive → run_<baseline>`.

If a future baseline turns out to have a real conflicting pin
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

# limits how many baseline tasks (across ALL DAGs) can hit Ollama at once
airflow pools set ollama_pool 1 "Limits concurrent Ollama inference requests across baseline DAGs"
```

## Add the DAGs

DAG sources (version-controlled): [`airflow_dags/tabsqlify_dag.py`](airflow_dags/tabsqlify_dag.py),
[`airflow_dags/tablellm_agent_dag.py`](airflow_dags/tablellm_agent_dag.py),
[`airflow_dags/tablellm_cot_dag.py`](airflow_dags/tablellm_cot_dag.py). Symlink all three into
Airflow's dags folder:

```bash
mkdir -p ~/airflow/dags
ln -sf /path/to/Tablollama/airflow_dags/tabsqlify_dag.py ~/airflow/dags/tabsqlify_dag.py
ln -sf /path/to/Tablollama/airflow_dags/tablellm_agent_dag.py ~/airflow/dags/tablellm_agent_dag.py
ln -sf /path/to/Tablollama/airflow_dags/tablellm_cot_dag.py ~/airflow/dags/tablellm_cot_dag.py
```

Update the path constants at the top of each file for your machine (`TABSQLIFY_DIR`,
`TABLELLM_DIR`, `TABLE_PYTHON`).

## Run

```bash
export AIRFLOW_HOME=~/airflow
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES   # works around a macOS gunicorn crash, see below
airflow webserver --port 8080 --workers 1 &
airflow scheduler &
```

Log in at `http://localhost:8080` (`admin` / `admin`) and trigger `table_reasoning_tabsqlify`,
`table_reasoning_tablellm_agent`, and/or `table_reasoning_tablellm_cot` — independently, since
they're all separate DAGs now.

## Why separate DAGs instead of one shared DAG

Originally tablellm's `agent` and `cot` modes lived in one DAG (one healthcheck fanning out to two
parallel baseline tasks) — and before that, TabSQLify and tablellm also shared a DAG. Both were
split for the same reason: a shared DAG couples lifecycle. Triggering the DAG runs every task in
it, so the webapp's "run just this one baseline" couldn't actually run just one; pausing the DAG to
permanently stop one baseline's auto-retry also stopped the other's; `max_active_runs=1` throttled
across baselines that have nothing to do with each other. Splitting gives independent trigger/
pause/resume/retry control per baseline. The one thing a shared DAG bought — not hammering Ollama
with multiple baselines at once — is instead handled by `ollama_pool` (1 slot), which is a global
Airflow resource, not scoped to a single DAG. Every baseline task declares `pool="ollama_pool"`, so
Airflow won't run more than one of them against Ollama at the same time even though they live in
different DAGs. The healthcheck bash snippet is duplicated across the DAG files as a result — a
small, worthwhile trade for independent control.

## Automatic recovery

Every baseline task has `retries=1000` / `retry_delay=1 min`. If a task dies mid-run (Ollama
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
for good (not just this attempt), pause that specific DAG too, otherwise the retry policy revives
it — pausing only affects that one baseline now, not both.

## Known issue: webserver log viewer crashes (macOS)

The webserver's gunicorn workers can die with `SIGSEGV` repeatedly on macOS, which shows up as
"No task logs found" in the UI even though the task is running fine and writing real output.
`--workers 1` plus `OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES` reduces but doesn't fully eliminate
it. If the UI log viewer is unreliable, tail the log file directly instead — it's always accurate:

```bash
tail -f ~/airflow/logs/dag_id=<dag_id>/run_id=<run_id>/task_id=<task_id>/attempt=1.log
```

## CI

[`.github/workflows/requirements-check.yml`](.github/workflows/requirements-check.yml) installs
each wired-up baseline's `requirements.txt` in a fresh venv on every push/PR that touches it —
currently scoped to TabSQLify and tablellm, the only two that have been reviewed/cleaned up so far.

## TODO

- Add the other 5 baselines (ALTER, H-STAR, NormTab, ReAcTable, chain-of-table) — own conda env
  (or shared, if versions actually check out) + own DAG, same pattern. Check each one's own
  checkpoint situation individually — don't assume it has one. Add each to the CI matrix once
  reviewed.
- Both tablellm DAGs pass `--sub_sample=False` explicitly, so they run the full 4344 WTQ questions,
  matching TabSQLify's scale (the scripts' own default is `sub_sample=True`, a fixed 837-question
  subset baked into `data/wtq.json`'s `sampled_indices` field — useful for a quick smoke test via
  `--sub_sample=True` on the command line, but no longer what's wired into Airflow). TabSQLify at
  ~3 min/sample locally → full-set runs are multi-day unattended jobs; the `--resume=$(wc -l ...)`
  checkpoint assumes the run order (and thus `--sub_sample` value) never changes mid-stream — if
  `result.jsonl` already has lines from a `sub_sample=True` run, don't resume it under
  `sub_sample=False` (or vice versa), since `global_i` enumerates a different, non-overlapping
  order in each mode. Delete/rename the old output first.
- TabSQLify has no TabFact entrypoint in this repo (only WTQ) despite leftover TabFact utility
  files (`utils/prompt_tabfact.py`, `utils/tabfact_data.py`) — would need a new runner script to
  actually use them.
