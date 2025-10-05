# ALTER: Augmentation for Large-Table-Based Reasoning
You can see origin code of NormTab from here : [https://github.com/Hanzhang-lang/ALTER/]

## 🚀 Installation
```
conda create -n alter python=3.10
conda activate alter
pip install -r requirements.txt
```

## 📍 Redis Store 
You can run the experiments with *LocalFile Store* or *Redis Store*.

To run the experiments with Redis store, you can use the following command to start a Redis store in Docker:
```
docker run -d -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

## 🚀 Installation

```bash
git clone https://github.com/yourname/ALTER
cd ALTER
conda create -n alter python=3.10
conda activate alter
pip install -r requirements.txt
```

## 🎯 Run

```bash
# 1. Augmentation
sh scripts/aug.sh

# 2. Reasoning pipeline
sh scripts/pipelines.sh
```

## 🧪 Evaluation

```bash
python run_evaluate.py
```


### Optional: Redis Store (for caching)

```bash
docker run -d -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

## 📂 Project Structure
```
.
├── augmentation.py                  # Table augmentation script (pre-stage)
├── batch_pipe.py                    # Main ALTER pipeline logic
├── run_ollama.py                    # Entry point for Ollama execution
│
├── scripts/
│   ├── aug.sh                       # Run augmentation phase
│   ├── pipelines.sh                 # Run reasoning pipeline
│   └── model_ollama/                # Model-specific configs (Ollama)
│
├── data_loader/
│   ├── TableLoader.py               # Table loading and preprocessing
│   ├── table_augmentation.py        # Table augmentation utilities
│   ├── table_format.py              # Table normalization and formatting
│   └── datasets/                    # Dataset loaders (WikiTQ, TabFact, etc.)
│
├── prompt_manager/                  # Prompt templates for augmentation + reasoning
├── utils/                           # Normalization, parsing, helper utilities
├── notebooks/                       # Experimental notebooks
├── config.yaml                      # Configuration file (set model & dataset)
├── results/                         # Saved intermediate + final results
└── requirements.txt                 # Dependencies
```
