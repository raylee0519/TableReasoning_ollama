"""
Shared checkpoint helpers for the 6 H-STAR pipeline stages. Each stage's
output is a single JSON dict keyed by example id -- these let a stage
resume from an existing partial file instead of always starting from
scratch, and write progress incrementally instead of only once at the end.
"""
import json
import os


def load_checkpoint(save_path):
    """Load a stage's partially-completed output, if any. Returns {} if
    nothing has been saved yet."""
    if not os.path.isfile(save_path):
        return {}
    try:
        with open(save_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_checkpoint(save_path, new_results):
    """Merge newly-generated results into whatever's already on disk and
    write back the union. Safe to call repeatedly (e.g. after every batch)
    -- never shrinks the file, even if new_results is empty. Writes to a
    temp file first and renames into place so a crash mid-write can't
    corrupt the checkpoint (this file is now written many times per run,
    not just once)."""
    existing = load_checkpoint(save_path)
    existing.update({str(k): v for k, v in new_results.items()})
    tmp_path = save_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(existing, f, indent=4)
    os.replace(tmp_path, save_path)
