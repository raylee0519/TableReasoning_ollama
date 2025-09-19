import json
from utils.evaluator import Evaluator

# Enter the model - llama / gpt / gemini 
model = "ollama" 
# Enter the dataset - tab_fact / wikitq
dataset = "wikitq"
with open(f'results/model_{model}/{dataset}_test_exec_results.json', 'r') as f:
    outputs = json.load(f)

# Define accuracy to 0
acc =0
# Iterate through each output and calculate the accuracy
for i in outputs:
    try:
        output = outputs[str(i)]
        if dataset == 'wikitq':
            pred_answer = output['generations'][0].split('the answer is: ')[1]
            pred_answer = pred_answer.split('"')[1:2]

        elif dataset == 'tab_fact':
            pred_answer = output['generations'][0].lower().split('statement is: ')[1].replace(" ", "")
            if pred_answer == 'true.' or pred_answer == 'true':
                pred_answer = [1]
            elif pred_answer == 'false' or pred_answer == 'false.':
                pred_answer = [0]

        gold_answer = output['ori_data_item']['answer_text']
        # Score is either 1 or 0
        score = Evaluator().evaluate(
        pred_answer,
        gold_answer,
        dataset=dataset,
        question=output['ori_data_item']['question']
        )
        acc += score
    except:
        pass
print(f"Correct Samples: {acc}; Total Samples: {len(outputs)}")
print(f"Accuracy: {100*acc/len(outputs):.2f}")