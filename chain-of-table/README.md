# Chain-of-Table with Ollama

# Command Usages

## Arguments

| Argument | Description | Default |
|:---|:---|:---|
| `--dataset_path` | Path to the dataset | `./data/tabfact/test.jsonl` |
| `--raw2clean_path` | Path to the preprocessed raw2clean file (cleaned by Dater) | `./data/tabfact/raw2clean.json` |
| `--model_name` | Name of the OpenAI API model | `gpt-3.5-turbo-16k-0613` |
| `--result_dir` | Path to the result directory | `./results/tabfact` |
| `--openai_key` | Key of the OpenAI API | `""` |
| `--first_n` | Number of the first N samples to evaluate (-1 means full dataset) | `-1` |
| `--n_proc` | Number of processes for multiprocessing | `1` |
| `--chunk_size` | Chunk size used in multiprocessing | `1` |

---

## Example Usages

### Run tests on the first 10 cases

```bash
python run_tabfact.py \
  --dataset_path 'data/tabfact/test.jsonl' \
  --raw2clean_path 'data/tabfact/raw2clean.jsonl' \
  --result_dir 'results/tabfact_first10' \
  --first_n 10 \
  --n_proc 10 \
  --chunk_size 1 \
  --openai_api_key <YOUR_KEY>
```

---

### Run the experiment on the whole dataset

```bash
python run_tabfact.py \
  --dataset_path 'data/tabfact/test.jsonl' \
  --raw2clean_path 'data/tabfact/raw2clean.jsonl' \
  --result_dir 'results/tabfact' \
  --n_proc 20 \
  --chunk_size 10 \
  --openai_api_key <YOUR_KEY>
```

---

# Notes

- `<YOUR_KEY>`: Your OpenAI API key (if needed). Leave empty if using local Ollama.
- When using Ollama models (like llama3.3), `--openai_key ""` can be safely left empty.

