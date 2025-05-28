import csv
import json
import re
import time
import pandas as pd
from pandasql import sqldf
from sqlalchemy import create_engine
from utils.preprocess import *
from utils.normalizer import *
from utils.prompt_wtq import *

def tabsqlify_wtq(T, title, tab_col, question, three_row, selection='rc'):
    prompt = gen_table_decom_prompt(title, tab_col, question, three_row, selection=selection)
    print(prompt)
    sql = get_sql_3(prompt)
    print('\nM1: ', sql, '\n')

    response = ""
    output_ans = ""
    linear_table = ""
    result = pd.DataFrame()

    try:
        result = sqldf(sql, locals())
    except:
        output_ans = "error"

    if result.shape == (1, 1):
        result_list = result.values.tolist()
        output_ans = " ".join(str(coll) for row in result_list for coll in row)
        response = "direct ans"
        output_ans = output_ans.lower()
    elif not result.empty:
        linear_table = table_linearization(result, style='pipe')
        prompt_ans = generate_sql_answer_prompt(title, sql, linear_table, question)
        print('promt_ans:\n', prompt_ans)
        response = get_answer(prompt_ans)
        print('response: ', response)
        try:
            output_ans = response.split("Answer:")[1]
        except:
            print("Error: Answer generation.")
            output_ans = "" + response
        match = re.search(r'(The|the) answer is ([^\.]+)\.', output_ans)
        if match:
            output_ans = match.group(2).strip('"')
    else:
        print('empty.')
        prompt = gen_table_decom_prompt(title, tab_col, question, three_row, selection='col')
        sql = get_sql_3(prompt)
        print('col sql: ', sql)
        try:
            result = sqldf(sql, locals())
        except:
            print('col selection - empty/error')
        if not result.empty:
            linear_table = table_linearization(result, style='pipe')
        else:
            sql = "select * from T"
            result = sqldf(sql, locals())
            linear_table = table_linearization(result, style='pipe')

        prompt_ans = generate_sql_answer_prompt(title, sql, linear_table, question)
        print('promt_ans:\n', prompt_ans)
        response = get_answer(prompt_ans)
        print('response: ', response)
        try:
            output_ans = response.split("Answer:")[1]
        except:
            print("Error: Answer generation.")
            output_ans = "" + response
        match = re.search(r'(The|the) answer is ([^\.]+)\.', output_ans)
        if match:
            output_ans = match.group(2).strip('"')

    return sql, result, response, output_ans, linear_table

if __name__ == "__main__":
    path = 'datasets/wtq_test3.jsonl'
    output_path = 'outputs/wtq_sql_results.jsonl'
    wrong_output_path = 'outputs/wtq_sql_wrong_results.jsonl'

    correct = 0
    t_samples = 0
    empty_error_ids = []

    tabsqlify = True

    with open(path, encoding='utf-8') as f1:
        for i, l in enumerate(f1):
            dic = json.loads(l)
            ids = dic['ids']
            title = dic['title']
            table = dic['table_text']
            question = dic['statement']
            answer = ','.join(dic['answer']).lower()

            print('\n\nid: ', ids, ' Q: ', question, ' ans: ', answer)

            T = dict2df(table)
            T = T.assign(row_number=range(len(T)))
            row_number = T.pop('row_number')
            T.insert(0, 'row_number', row_number)
            tab_col = ", ".join(T.columns)

            engine = create_engine('sqlite:///database.db')
            T = convert_df_type(T)

            if tabsqlify:
                sql_3 = "select * from T limit 3"
                three_row_df = sqldf(sql_3, locals())
                three_row = table_linearization(three_row_df, style='pipe')
                sql, result, response, output_ans, linear_table = tabsqlify_wtq(
                    T, title, tab_col, question, three_row, selection='rc')
                t_num_cell = T.size
                r_num_cell = result.size
            else:
                linear_table = table_linearization(T, style='pipe')
                prompt_ans = gen_full_table_prompt(title, tab_col, linear_table, question)
                response = get_answer(prompt_ans)
                try:
                    output_ans = response.split("Answer:")[1]
                except:
                    print("Error: Answer generation.")
                    output_ans = "" + response
                match = re.search(r'(The|the) answer is ([^\.]+)\.', output_ans)
                if match:
                    output_ans = match.group(2).strip('"')
                t_num_cell = T.size
                r_num_cell = T.size
                sql = 'select * from T;'

            output_ans = output_ans.lower()
            is_correct = (
                output_ans.strip() == answer or
                output_ans.strip() in answer or
                answer.strip() in output_ans.strip()
            )

            result_item = {
                "id": ids,
                "question": question,
                "gold_answer": answer,
                "prediction": output_ans.strip(),
                "sql": sql,
                "response": response,
                "r_num_cell": r_num_cell,
                "t_num_cell": t_num_cell,
                "correct": is_correct,
                "three_row_table": three_row,
                "linearized_table": linear_table
            }

            with open(output_path, 'a', encoding='utf-8') as fout:
                fout.write(json.dumps(result_item, ensure_ascii=False) + '\n')
            if not is_correct:
                with open(wrong_output_path, 'a', encoding='utf-8') as fwout:
                    fwout.write(json.dumps(result_item, ensure_ascii=False) + '\n')

            if is_correct:
                correct += 1
                print("correct: ", correct)
            t_samples += 1
            print('Correcet: ', correct, 'total: ', t_samples, "Accuracy: ", correct / (t_samples + 0.0001))

    print('✅ Final: Correcet: ', correct, 'total: ', t_samples, "Accuracy: ", correct / (t_samples + 0.0001))
    print('empty_error_ids: ', empty_error_ids)
