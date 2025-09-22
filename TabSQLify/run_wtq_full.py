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

def clean_log_text(log_text: str) -> str:
    """
    불필요한 few-shot 블록 제거
    """
    blocks = [
        (
            "Table: Marek Plawgo",
            "SQL: select date, attendance from T order by attendance desc"
        ),
        (
            "Table_title: Piotr Kędzia",
            "Answer: 12,467"
        )
    ]

    cleaned = log_text
    for start_marker, end_marker in blocks:
        while True:
            start_idx = cleaned.find(start_marker)
            end_idx = cleaned.find(end_marker)
            if start_idx != -1 and end_idx != -1:
                cleaned = cleaned[:start_idx] + cleaned[end_idx + len(end_marker):]
            else:
                break

    return cleaned.strip()

def get_done_ids(log_dir):
    """
    이미 처리된 log 파일들의 id 목록 반환
    """
    done_ids = set()
    if os.path.exists(log_dir):
        for fname in os.listdir(log_dir):
            if fname.endswith(".txt"):
                done_ids.add(fname.replace(".txt", ""))
    return done_ids

def tabsqlify_wtq(T, title, tab_col, question, three_row, selection='rc', log_file=None):
    logs = []  # 로그 수집용

    prompt = gen_table_decom_prompt(title, tab_col, question, three_row, selection=selection)
    logs.append("Prompt:\n" + prompt)
    sql = get_sql_3(prompt)
    sql = sql.strip()
    sql = re.sub(r"^```[a-zA-Z]*", "", sql)  # ```sql, ``` 제거
    sql = re.sub(r"```$", "", sql)           # 마지막 ``` 제거
    sql = sql.strip()
    logs.append(f"\nM1 SQL:\n{sql}\n")

    response = ""
    output_ans = ""
    linear_table = ""
    result = pd.DataFrame()

    try:
        result = sqldf(sql, locals())
    except Exception as e:
        output_ans = "error"
        logs.append(f"SQL Error: {e}")

    if result.shape == (1, 1):
        result_list = result.values.tolist()
        output_ans = " ".join(str(coll) for row in result_list for coll in row)
        response = "direct ans"
        output_ans = output_ans.lower()
        logs.append(f"Direct ans result: {output_ans}")
    elif not result.empty:
        linear_table = table_linearization(result, style='pipe')
        prompt_ans = generate_sql_answer_prompt(title, sql, linear_table, question)
        logs.append("Answer Prompt:\n" + prompt_ans)
        response = get_answer(prompt_ans)
        logs.append("Model Response:\n" + response)
        try:
            output_ans = response.split("Answer:")[1]
        except:
            logs.append("Error: Answer generation.")
            output_ans = response
        match = re.search(r'(The|the) answer is ([^\.]+)\.', output_ans)
        if match:
            output_ans = match.group(2).strip('"')
    else:
        logs.append("Empty SQL result. Switching to col-selection...")
        prompt = gen_table_decom_prompt(title, tab_col, question, three_row, selection='col')
        sql = get_sql_3(prompt)
        logs.append("Col SQL:\n" + sql)
        try:
            result = sqldf(sql, locals())
        except Exception as e:
            logs.append(f"Col SQL Error: {e}")
        if not result.empty:
            linear_table = table_linearization(result, style='pipe')
        else:
            sql = "select * from T"
            result = sqldf(sql, locals())
            linear_table = table_linearization(result, style='pipe')

        prompt_ans = generate_sql_answer_prompt(title, sql, linear_table, question)
        logs.append("Answer Prompt:\n" + prompt_ans)
        response = get_answer(prompt_ans)
        logs.append("Model Response:\n" + response)
        try:
            output_ans = response.split("Answer:")[1]
        except:
            logs.append("Error: Answer generation.")
            output_ans = response
        match = re.search(r'(The|the) answer is ([^\.]+)\.', output_ans)
        if match:
            output_ans = match.group(2).strip('"')

    # 로그 파일 저장
    if log_file is not None:
        cleaned_logs = clean_log_text("\n".join(logs))
        with open(log_file, 'w', encoding='utf-8') as lf:
            lf.write(cleaned_logs)

    return sql, result, response, output_ans, linear_table

if __name__ == "__main__":
    log_dir = "outputs/logs"
    os.makedirs(log_dir, exist_ok=True)

    path = 'datasets/wtq_test3.jsonl'
    output_path = 'outputs/wtq_sql_results.jsonl'
    wrong_output_path = 'outputs/wtq_sql_wrong_results.jsonl'

    # 이미 처리된 ID 목록 가져오기
    done_ids = get_done_ids(log_dir)
    print("✅ Already processed:", len(done_ids))

    correct = 0
    t_samples = 0
    empty_error_ids = []

    tabsqlify = True

    with open(path, encoding='utf-8') as f1:
        for i, l in enumerate(f1):
            dic = json.loads(l)
            ids = dic['ids']

            # 이미 로그가 있으면 skip
            if ids in done_ids:
                print(f"⏭️ Skip id={ids} (already processed)")
                continue

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
                    T, title, tab_col, question, three_row, selection='rc',
                    log_file=os.path.join(log_dir, f"{ids}.txt")
                )
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
                fout.write(json.dumps(result_item, ensure_ascii=False, default=str) + '\n')
            if not is_correct:
                with open(wrong_output_path, 'a', encoding='utf-8') as fwout:
                    fwout.write(json.dumps(result_item, ensure_ascii=False, default=str) + '\n')

            if is_correct:
                correct += 1
                print("correct: ", correct)
            t_samples += 1
            print('Correcet: ', correct, 'total: ', t_samples, "Accuracy: ", correct / (t_samples + 0.0001))

    print('✅ Final: Correcet: ', correct, 'total: ', t_samples, "Accuracy: ", correct / (t_samples + 0.0001))
    print('empty_error_ids: ', empty_error_ids)
