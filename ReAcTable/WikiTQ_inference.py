import json
import os

import pandas as pd
from tqdm import tqdm

from tabqa.GptCOTPrompter_BeamSeach import CodexAnswerCOTExecutor_HighTemperaturMajorityVote

dataset = pd.read_csv('./dataset/WikiTableQuestions/data/pristine-unseen-tables.tsv', sep='\t')

NNDemo = False
max_demo = 5
gpt_model = os.environ.get('MODEL_NAME', 'llama3.2:1b')
program = 'sql-py'
template = 'original-sql-py-no-intermediate'

output_dir = './result'
os.makedirs(output_dir, exist_ok=True)
output_result_file = os.path.join(
    output_dir,
    f'CodexAnswerCOTExecutor_HighTemperaturMajorityVote_{template}_{program}_NNDemo={NNDemo}_model{gpt_model}.jsonl',
)


def get_done_ids(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line)['id'])
                except json.JSONDecodeError:
                    continue
    return done


def run_one(i):
    max_retry = 3
    while max_retry > 0:
        try:
            codex_prompter = CodexAnswerCOTExecutor_HighTemperaturMajorityVote(
                f'prompt_template/{template}.json',
                dataset.iloc[i]['id'],
                dataset.iloc[i]['utterance'],
                dataset.iloc[i]['context'],
                dataset.iloc[i]['targetValue'],
                # NOTE: must match the dataset load path above (both relative
                # to the ReAcTable/ working directory) -- the original script
                # had this as '../dataset/WikiTableQuestions/', which pointed
                # one level too high and crashed on the very first sample.
                base_path='./dataset/WikiTableQuestions/',
                demo_file=f'few-shot-demo/WikiTQ-{program}.json',
            )
            codex_prompter.max_demo = max_demo
            codex_prompter.model = gpt_model
            codex_prompter._gen_gpt_prompt(NNDemo)
            codex_prompter._get_gpt_prediction_majority_vote(repeat_times=5)
            return codex_prompter._log_dict()
        except Exception as e:
            log = {
                'id': dataset.iloc[i]['id'],
                'uncaught_err': str(e),
            }
            if "model's maximum context length" in str(e):
                return log
            max_retry -= 1
    return log


if __name__ == '__main__':
    done_ids = get_done_ids(output_result_file)
    print(f"Already processed: {len(done_ids)}")
    
    with open(output_result_file, 'a', encoding='utf-8') as f:
        for i in tqdm(range(dataset.shape[0])):
            row_id = dataset.iloc[i]['id']
            if row_id in done_ids:
                continue
            log = run_one(i)
            f.write(json.dumps(log) + '\n')
            f.flush()
