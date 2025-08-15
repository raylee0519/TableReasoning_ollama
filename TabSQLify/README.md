# TabSQLify

You can see origin code of TabSQLify from here: [https://github.com/mahadi-nahid/TabSQLify](https://github.com/mahadi-nahid/TabSQLify)

---

## 🛠️ Installation

Install the required Python packages using:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run

### 1. Inference for a Single Sample

Run inference on a specific sample from the WTQ dataset:

```bash
python run_wtq_A.py
```

This prints SQL, model output, and prediction for one sample.

---

### 2. Batch Inference for All Samples

Evaluate the entire WikiTableQuestions dataset:

```bash
python run_wtq_full.py
```

Correct and incorrect results are saved to JSONL files.

---

## 📌 Sample Output

```json
{
  "id": "nu-1503",
  "question": "were more games played at the ksv roeselare or the excelsior mouscron?",
  "gold_answer": "ksv roeselare",
  "prediction": "ksv roeselare.",
  "sql": "select * from T",
  "response": "To determine where more games were played, we need to sum up the number of games played for each club mentioned in the comparison: KSV Roeselare and Excelsior Mouscron.\n\nFor KSV Roeselare:\n- Season 2004/05: 29 games\n- Season 2005/06: 26 games\n- Season 2006/07: 29 games\n- Season 2007/08: 25 games\n\nTotal games played for KSV Roeselare = 29 + 26 + 29 + 25 = 109 games\n\nFor Excelsior Mouscron:\n- Season 2008/09: 31 games\n- Season 2009/10: 14 games\n\nTotal games played for Excelsior Mouscron = 31 + 14 = 45 games\n\nTherefore, more games were played at KSV Roeselare (109 games) than at Excelsior Mouscron (45 games).\n\nAnswer: KSV Roeselare.",
  "r_num_cell": 66,
  "t_num_cell": 66,
  "correct": true,
  "three_row_table": "row_number | season | club | competition | games | goals\n0 | 2002/03 | raec mons | jupiler league | 19 | 0\n1 | 2003/04 | raec mons | jupiler league | 23 | 0\n2 | 2004/05 | ksv roeselare | belgian second division | 29 | 1",
  "linearized_table": "row_number | season | club | competition | games | goals\n0 | 2002/03 | raec mons | jupiler league | 19 | 0\n1 | 2003/04 | raec mons | jupiler league | 23 | 0\n2 | 2004/05 | ksv roeselare | belgian second division | 29 | 1\n3 | 2005/06 | ksv roeselare | jupiler league | 26 | 0\n4 | 2006/07 | ksv roeselare | jupiler league | 29 | 1\n5 | 2007/08 | ksv roeselare | jupiler league | 25 | 0\n6 | 2008/09 | excelsior mouscron | jupiler league | 31 | 1\n7 | 2009/10 | excelsior mouscron | jupiler league | 14 | 1\n8 | 2009/10 | győri eto fc | soproni liga | 1 | 0\n9 | 2010/11 | kortrijk | jupiler league | 0 | 0\n10 | none | none | totaal | 278 | 4"
}
```
