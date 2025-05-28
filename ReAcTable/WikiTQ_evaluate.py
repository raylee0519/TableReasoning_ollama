import subprocess

# Relative path to evaluator directory
evaluator_dir = './dataset/WikiTableQuestions'
evaluator_script = 'evaluator.py'
# Match the prediction path relative to the evaluator's working directory
relative_prediction_path = '../../result/result_4344.json'

# Run evaluation
subprocess.run(
    ['python2', evaluator_script, relative_prediction_path],
    cwd=evaluator_dir
)