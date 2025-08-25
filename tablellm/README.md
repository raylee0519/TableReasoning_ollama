# Mix-SC

You can see origin code of ReAcTable from here.
https://github.com/Leolty/tablellm/tree/main

---

## 🛠️ Installation

Install the required Python packages using:

```bash
pip install -r requirements.txt
```

---

## 🚀 How to Run
You can run two different scripts to obtain two result variants of Mix-SC.
- [scripts/all_dp.sh](scripts/all_dp.sh): Runs direct prompting on all wtq datasets.
- [scripts/all_pyagent.sh](scripts/all_pyagent.sh): Runs python shell agent on all wtq datasets.

The option ``-model`` can be changed to specify which model you want to use.

The current default value is llama3.3:70b, but you can replace it with any available model.

Detailed explanations of parameters can be found in [run_cot.py](run_cot.py) and [run_agent.py](run_agent.py).

