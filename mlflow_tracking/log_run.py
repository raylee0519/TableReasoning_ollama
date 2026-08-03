import argparse
import csv
import json
import os
import subprocess

import mlflow

REPO_ROOT = os.environ.get("REPO_ROOT", "/Users/jeongwoo/new_github/Tablollama")

BASELINE_CONFIGS = {
    "tabsqlify": {
        "results_path": os.path.join(REPO_ROOT, "TabSQLify", "outputs", "wtq_sql_results.jsonl"),
        "format": "jsonl",
        "correct_field": "correct",
    },
    "tablellm_agent": {
        "results_path": os.path.join(REPO_ROOT, "tablellm", "output", "wtq_agent_ollama", "result.jsonl"),
        "format": "jsonl",
        "gold_field": "answer",
        "pred_field": "text",
    },
    "tablellm_cot": {
        "results_path": os.path.join(REPO_ROOT, "tablellm", "output", "wtq_cot_ollama", "result.jsonl"),
        "format": "jsonl",
        "gold_field": "answer",
        "pred_field": "text",
    },
    "reactable": {
        # ReAcTable bakes the model name into its own output filename, so
        # this has to be resolved per-run against whichever model actually
        # produced it (see main()).
        "results_path": lambda model: os.path.join(
            REPO_ROOT, "ReAcTable", "result",
            f"CodexAnswerCOTExecutor_HighTemperaturMajorityVote_original-sql-py-no-intermediate_sql-py_NNDemo=False_model{model}.jsonl",
        ),
        "format": "jsonl",
        "correct_field": "execution_match",
    },
    "normtab": {
        "results_path": os.path.join(REPO_ROOT, "NormTab", "outputs", "normTab_eval_targeted_wtq.jsonl"),
        "format": "jsonl",
        "gold_field": "answer",
        "pred_field": "prediction",
    },
}


def _match(gold, pred) -> bool:
    if gold is None or pred is None:
        return False
    gold = str(gold).strip().lower()
    pred = str(pred).strip().lower()
    if not gold or not pred:
        return False
    return pred == gold or pred in gold or gold in pred


def _load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _resolve_path(config, model):
    path = config["results_path"]
    return path(model) if callable(path) else path


def compute_metrics(config, model):
    path = _resolve_path(config, model)
    if not os.path.isfile(path):
        return {"done": 0}

    rows = _load_jsonl(path)
    metrics = {"done": len(rows)}
    if not rows:
        return metrics

    if "correct_field" in config:
        vals = [bool(r.get(config["correct_field"])) for r in rows]
        metrics["accuracy"] = sum(vals) / len(vals)
    elif "gold_field" in config and "pred_field" in config:
        matches = [_match(r.get(config["gold_field"]), r.get(config["pred_field"])) for r in rows]
        metrics["accuracy"] = sum(matches) / len(matches)

    return metrics


def git_commit_hash():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT
        ).decode().strip()
    except Exception:
        return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, choices=list(BASELINE_CONFIGS.keys()))
    parser.add_argument("--model", default="llama3.2:1b")
    parser.add_argument("--dataset", default="wtq")
    parser.add_argument(
        "--tracking-uri",
        default=os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"),
    )
    args = parser.parse_args()

    config = BASELINE_CONFIGS[args.baseline]
    metrics = compute_metrics(config, args.model)

    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment("table-reasoning-wtq")

    with mlflow.start_run(run_name=args.baseline):
        mlflow.log_param("baseline", args.baseline)
        mlflow.log_param("dataset", args.dataset)
        mlflow.log_param("model", args.model)
        mlflow.log_param("git_commit", git_commit_hash())
        for name, value in metrics.items():
            mlflow.log_metric(name, value)
        results_path = _resolve_path(config, args.model)
        if os.path.isfile(results_path):
            mlflow.log_artifact(results_path)

    print(f"Logged {args.baseline}: {metrics}")


if __name__ == "__main__":
    main()
