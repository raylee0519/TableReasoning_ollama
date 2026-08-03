import json
import os


def load_checkpoint(save_path):
    if not os.path.isfile(save_path):
        return {}
    try:
        with open(save_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_checkpoint(save_path, new_results):
    existing = load_checkpoint(save_path)
    existing.update({str(k): v for k, v in new_results.items()})
    tmp_path = save_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(existing, f, indent=4)
    os.replace(tmp_path, save_path)
