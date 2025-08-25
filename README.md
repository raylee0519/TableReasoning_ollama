# Table Reasoning Evaluation using LLaMA3.3 70B

This repository enables evaluation of Table Reasoning models on the WikiTableQuestions (WikiTQ) dataset using `llama3.3-70b-instruct` deployed via Ollama.

## ✅ Supported Table QA Systems

The following models have been tested and are currently supported for evaluation:

- **ReAcTable** (✓ WikiTQ compatible)
- **TabSQLify** (✓ WikiTQ compatible)
- **Mix-SC** (✓ WikiTQ compatible)
- **chain-of-Table** (⚠ Only supports **TabFact** dataset)

## ⚙️ Ollama Setup

Before running evaluation, make sure to start the Ollama server with an extended context length to prevent prompt truncation for long tables.

Use the following command to start Ollama:

```bash
OLLAMA_CONTEXT_LENGTH=24576 ollama serve
```
This ensures that up to 24,576 tokens can be processed per prompt, which is crucial for handling large tabular inputs. <br>
If Olama responds to the error, please change the token length to 16,384.
