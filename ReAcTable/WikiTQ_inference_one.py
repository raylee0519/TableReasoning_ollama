# 하나의 데이터만 불러오기
import json
import pandas as pd
from tabqa.GptCOTPrompter_BeamSeach import CodexAnswerCOTExecutor_HighTemperaturMajorityVote

# 환경 세팅
NNDemo = False
max_demo = 5
gpt_model = 'llama3.3'
program = 'sql-py'
template = 'original-sql-py-no-intermediate'

# 데이터셋 로드
dataset = pd.read_csv('./dataset/WikiTableQuestions/data/pristine-unseen-tables.tsv', sep='\t')

# 인덱스 0번 데이터 하나만 사용
i = 5

# CodexAnswerCOTExecutor 실행
codex_prompter = CodexAnswerCOTExecutor_HighTemperaturMajorityVote(
    f'prompt_template/{template}.json',
    dataset.iloc[i]['id'],
    dataset.iloc[i]['utterance'],
    dataset.iloc[i]['context'],
    dataset.iloc[i]['targetValue'],
    base_path='./dataset/WikiTableQuestions/',
    demo_file=f'few-shot-demo/WikiTQ-{program}.json',
)

codex_prompter.max_demo = max_demo
codex_prompter.model = gpt_model
codex_prompter._gen_gpt_prompt(NNDemo)
codex_prompter._get_gpt_prediction_majority_vote(repeat_times=5)
log = codex_prompter._log_dict()

# 출력 확인
print(json.dumps(log, indent=2))

# 필요 시 파일로 저장
with open('single_test_output_5.json', 'w') as f:
    json.dump(log, f, indent=4)
