import os
import shutil

# 설정
# maxLimit = 5
local_result_file = f'./result/result_4344.json'
eval_result_dir = './dataset/WikiTableQuestions/results/'
eval_result_file = os.path.join(eval_result_dir, f'result_4344.json')
evaluator_path = './dataset/WikiTableQuestions/evaluator.py'

# 평가용 디렉토리가 없으면 생성
if not os.path.exists(eval_result_dir):
    os.makedirs(eval_result_dir)

# 결과 파일 복사 (존재하지 않아도 생성됨)
shutil.copy(local_result_file, eval_result_file)

# 평가 실행
os.system(f'cd ./dataset/WikiTableQuestions/ && python2 evaluator.py ./results/result_4344.json')
