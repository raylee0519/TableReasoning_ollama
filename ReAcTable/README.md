# ReAcTable

You can see origin code of ReAcTable from here.
https://github.com/yunjiazhang/ReAcTable

---

## 🛠️ Installation

Install the required Python packages using:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run

### 1. Inference for a Single Sample

Use this script to run inference on one specific index from the WikiTQ dataset:

```bash
python WikiTQ_inference_one.py
```

You can manually specify the `i` index of the sample to test in the script.

---

### 2. Batch Inference for All Samples

Use this script to run inference over the entire WikiTQ dataset:

```bash
python WikiTQ_inference.py
```

Results will be saved in `.json` format.

---

## 📌 Sample Output

```json
{
  "id": "nu-5",
  "utterance": "in which competition did hopley finish first?",
  "source_csv": "csv/204-csv/483.csv",
  "target_value": "World Junior Championships",
  "predicted_value": "World Junior Championships"
}
```
