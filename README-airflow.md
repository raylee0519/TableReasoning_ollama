# Airflow Setup

Orchestrates 6 of this repo's table-reasoning baselines as Airflow DAGs instead of running each
one by hand: **TabSQLify**, **Mix-SC** (tablellm's `agent` and `cot` modes, as two DAGs),
**ReAcTable**, **NormTab**, **ALTER**, **H-STAR**. `chain-of-table` is not wired up (its code needs
a real rewrite, not just bug fixes).

## Architecture

Everything runs via Docker Compose (`docker-compose.yml` at the repo root): Airflow
(webserver + scheduler), MLflow, and the webapp (FastAPI backend + Streamlit frontend). Ollama is
the one exception — it stays host-native, reached from containers via `host.docker.internal`,
since the models a user has pulled are their own actively-curated state, not something to duplicate
into a container.

```bash
ollama serve                # on the host, once
docker compose up --build   # everything else
```

Webapp: `http://localhost:8501` · Airflow UI: `http://localhost:8080` (`admin`/`admin`) · MLflow
UI: `http://localhost:5001`.

## DAG pattern

Each baseline is its own DAG in [`airflow_dags/`](airflow_dags/), following the same task chain:

```
ensure_deps → check_ollama_alive → run_<baseline> [→ run_<stage2> → ...] → log_to_mlflow
```

- `ensure_deps`: installs only whatever's missing from that baseline's `requirements.txt`, never
  touches already-installed versions.
- `check_ollama_alive`: polls the host Ollama for up to 90s before failing.
- The run task(s): every task shares `pool="ollama_pool"` (1 slot), so only one baseline ever hits
  Ollama at a time even though they're all separate DAGs. `retries=1000` — a crashed task just
  relaunches. Every baseline's own script self-resumes from its own output file, so a retry never
  redoes finished work.
- `log_to_mlflow` (5 of 6 baselines — see below): reads the baseline's result file after it
  finishes and logs it to MLflow.

NormTab, ALTER, and H-STAR are multi-stage (2, 2, and 6 tasks respectively); the rest are single-task.

## Model selection

The model picked in the webapp actually drives the run now — it used to be cosmetic. The flow:
webapp trigger → Airflow `dag_run.conf["model"]` → each DAG reads it back via Jinja
(`{{ dag_run.conf.get('model', 'llama3.2:1b') }}`) → passed into the baseline as either a CLI flag
(ALTER, H-STAR, Mix-SC) or a `MODEL_NAME` env var (TabSQLify, ReAcTable, NormTab, whose own code
has no CLI support for it). ReAcTable, NormTab, and ALTER also bake the model name into their
output filenames, so the webapp and MLflow logging resolve those paths dynamically per-run instead
of assuming a fixed name.

## MLflow tracking

[`mlflow_tracking/log_run.py`](mlflow_tracking/log_run.py) reads a baseline's result file post-hoc
and logs params (baseline/model/dataset/git commit) + metrics (done count, accuracy where
computable) + the result file as an artifact. Accuracy is computed for TabSQLify, Mix-SC
(agent/cot), ReAcTable, and NormTab — not ALTER or H-STAR, whose saved output doesn't currently
include enough to score without new parsing work.

## Known gaps

- `chain-of-table` isn't wired up.
- ALTER/H-STAR aren't scored in MLflow yet.
- `nltk`'s `punkt_tab` data isn't pre-downloaded — will crash a sample that exercises
  `word_tokenize`.
