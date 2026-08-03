import os

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s
from datetime import datetime, timedelta

REPO_ROOT = os.environ.get("REPO_ROOT", "/Users/jeongwoo/new_github/Tablollama")
TABLE_PYTHON = os.environ.get("TABLE_PYTHON", "/opt/anaconda3/envs/table/bin/python")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "localhost:11434")
MODEL = "{{ dag_run.conf.get('model', 'llama3.2:1b') }}"

TABSQLIFY_DIR = os.path.join(REPO_ROOT, "TabSQLify")
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

REPO_VOLUME = k8s.V1Volume(
    name="repo",
    host_path=k8s.V1HostPathVolumeSource(path="/repo"),
)
REPO_VOLUME_MOUNT = k8s.V1VolumeMount(name="repo", mount_path="/repo")

with DAG(
    dag_id="table_reasoning_tabsqlify_k8s",
    start_date=datetime(2026, 7, 29),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["table-reasoning", "tabsqlify", "k8s-poc"],
) as dag:

    check_ollama = BashOperator(
        task_id="check_ollama_alive",
        bash_command=CHECK_OLLAMA_BASH,
    )

    run_tabsqlify = KubernetesPodOperator(
        task_id="run_tabsqlify_wtq_k8s",
        name="tabsqlify-wtq",
        namespace="default",
        image="tablollama-airflow-scheduler:latest",
        image_pull_policy="IfNotPresent",
        cmds=["bash", "-c"],
        arguments=[f"cd {TABSQLIFY_DIR} && python -u run_wtq_full.py"],
        env_vars={
            "MODEL_NAME": MODEL,
            "OLLAMA_HOST": "host.docker.internal:11434",
        },
        volumes=[REPO_VOLUME],
        volume_mounts=[REPO_VOLUME_MOUNT],
        get_logs=True,
        is_delete_operator_pod=True,
        startup_timeout_seconds=120,
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

    check_ollama >> run_tabsqlify >> log_to_mlflow
