# H-STAR
You can see origin code of NormTab from here : [https://github.com/nikhilsab/H-STAR]


## 📌 Overview

This project runs the **H-STAR Table Reasoning pipeline** using **Ollama’s OpenAI-compatible API**.  
The pipeline sequentially executes multiple reasoning stages (**column extraction → row extraction → reasoning**) with LLMs (LLaMA3, Qwen, etc.), and stores intermediate + final outputs.

Execution is handled by `run_ollama.py`, and model configuration (engine) can be modified directly inside each script under `scripts/model_ollama/`.

---

## 📂 Project Structure

```
.
├── datasets/                        
│   └── wikitq/                      # WikiTableQuestions dataset
│
├── results/
│   └── model_ollama/                # Outputs from each stage (col_sql, col_text, etc.)
│
├── scripts/
│   └── model_ollama/
│       ├── col_sql.py               # SQL-based column extraction
│       ├── col_text.py              # Text-based column extraction
│       ├── row_sql.py               # SQL-based row extraction
│       ├── row_text.py              # Text-based row extraction
│       ├── reason_sql.py            # SQL reasoning
│       └── reason_text.py           # Final reasoning
│
├── generation/                      # Prompt generator + LLM wrappers
│
├── utils/                           # Utility functions (data loader, DB wrapper, etc.)
│
├── run_ollama.py                    # Main entry script
└── requirements.txt                 # Dependencies
```

---

## 🚀 Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run full pipeline

```bash
python run_ollama.py
```

* This will sequentially execute all stages (`col_sql → col_text → row_sql → row_text → reason_sql → reason_text`).
* Intermediate JSON results are saved under `results/model_ollama/`.


### 3. Evaluate final results
```bash
python run_evaluate.py
```

* Loads the final outputs (from reason_text.py) and evaluates them against gold answers.
* Evaluation metrics (e.g., accuracy) are logged and stored for analysis.


### 4. Change model (engine)

Open any script inside `scripts/model_ollama/` (e.g., `col_sql.py`) and modify:

```python
parser.add_argument('--engine', type=str, default="llama3.3:70b")
```

You can switch to another Ollama model, e.g.:

```python
--engine qwen2.5:14b
```

---

## 📝 Output Files

Each stage produces a JSON file in `results/model_ollama/`. For example:

1. **Column SQL (`wikitq_test_col_sql.json`)**
   * LLM-generated column selection in SQL format.

2. **Column Text (`wikitq_test_col_text.json`)**
   * Refined column selection via text reasoning.

3. **Row SQL (`wikitq_test_row_sql.json`)**
   * Row-level selection based on SQL reasoning.

4. **Row Text (`wikitq_test_row_text.json`)**
   * Row refinement with textual reasoning.

5. **Reason SQL (`wikitq_test_sql_reason.json`)**
   * SQL-based intermediate reasoning.

6. **Reason Text (`wikitq_test_text_reason.json`)**
   * Final reasoning output.

---

## ✅ Notes

* Run the entire pipeline with **`run_ollama.py`**.
* All outputs are saved under `results/model_ollama/`.
* For debugging, logs can be printed per stage by adding `-v`.
* Leave key.txt as a blank since we use ollama models.