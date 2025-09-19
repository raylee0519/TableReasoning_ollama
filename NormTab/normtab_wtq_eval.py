import sqlite3
from utils.preprocess import *
from utils.normalizer import *
from utils.all_prompts import *
from utils.llm_agent import *
import time
import csv
import os
import re

# 로그 폴더 생성
log_dir = "outputs/logs"
os.makedirs(log_dir, exist_ok=True)

# ---------------------------------------------------------------
def clean_response(raw: str) -> str:
    # <think>...</think> 블록 제거
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()


def get_ans_sql(prompt):
    response = None
    while response is None:
        try:
            response = get_completion(prompt, temperature=0.7, max_tokens = 10000)
        except:
            time.sleep(2)
            pass
    return response

def extract_sql(raw: str) -> str:
    # ```sql ... ``` 블록 찾기
    code_block = re.search(r"```sql(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if code_block:
        return code_block.group(1).strip()

    # 전체 텍스트에서 마지막 SELECT ~ LIMIT 까지 추출
    match = re.search(r"(select .*?)(?:;|$)", raw, re.IGNORECASE | re.DOTALL)
    if match:
        sql = match.group(1).strip()
        # 여러 줄인 경우 정리
        sql = " ".join(sql.split())
        return sql

    # 마지막 수단: 줄 단위 탐색
    for line in reversed(raw.splitlines()):
        if line.strip().lower().startswith("select"):
            return line.strip().rstrip(";")

    return ""
# ---------------------------------------------------------------
if __name__ == "__main__":

    norm_table_path = "outputs_GPT4/normTab_targeted_wtq_gpt4.csv" # Table Path

    # -----------------------------------------------------------------------------------------------------------
    tab_group_path = "datasets/table_group_wtq.json"
    with open(tab_group_path, "r") as file:
        table_qa_group = json.load(file)

    # print(table_qa_group)

    df = pd.read_csv(norm_table_path)
    number_of_tables = df.shape[0]

    wikitq_path = 'datasets/wtq_test3.jsonl'
    unique_tabs = [x for x in range(0, number_of_tables)]

    conn = sqlite3.connect('table.db')


    # ----------------------------------------------------------------------------------------------------------
    start = 0
    end = number_of_tables
    # --------------------------------------------------------------

    fw = open(f'outputs/normTab_eval_targeted_wtq.jsonl', 'a')
    # fw.write(json.dumps(tmp) + '\n')
    # ---------------------------------------------------------------
    f = open('outputs/normTab_eval_targeted_wtq.csv', 'a')

    writer = csv.writer(f)
    header = ['id', 'question', 'answer', 'prediction', 'sql', 'response']
    writer.writerow(header)
    # ---------------------------------------------------------------
    counter = start - 1

    # print('Counter: ', counter)

    for index, row in df.iterrows():
        if index in unique_tabs[start:end]:
            id = row['id']
            norm_tab = row['norm_table']
            print(norm_tab)
            norm_tab = eval(str(norm_tab)) if isinstance(norm_tab, str) else norm_tab
            print('ID: ', id)
            if isinstance(norm_tab, list):
                df = pd.DataFrame(norm_tab[1:], columns=norm_tab[0])
            else:
                df = parse_table(norm_tab)
            print("\n Markdown Table (NormTab):\n", df.to_markdown(index=False))

            counter += 1
            print('Counter: ', counter)

            try:
                if isinstance(norm_tab, list):
                    df = pd.DataFrame(norm_tab[1:], columns=norm_tab[0])
                else:
                    df = parse_table(norm_tab)
                print("\n Markdown Table (NormTab):\n", df.to_markdown(index=False))

                df = df.assign(row_number=range(len(df)))
                row_number = df.pop('row_number')
                df.insert(0, 'row_number', row_number)
                df.to_sql('T', conn, if_exists='replace', index=False)

                col = df.columns
                # print('Table Coll: ', col)

                tab_col = ""
                for c in col:
                    tab_col += c + ", "
                tab_col = tab_col.strip().strip(',')
                print('\nTable Column: ', tab_col)


                # Execute select query
                query = "SELECT * FROM T limit 3"
                three_rows = pd.read_sql_query(query, conn)
                three_rows = table_linearization(three_rows, style='pipe')
            except:
                print("error\n")
                continue

            print("\nDataFrame from database (3 rows) :\n", three_rows)

            # -------------------------- Question - Answer Eval --------------------------------------------------------

            table_ids = table_qa_group[id]
            table_ids = [int(item.replace('nu-', '')) for item in table_ids]


            print('\nmain_table:', id, 'table_qa_group: ', table_ids, 'number of questions: ', len(table_ids))
            print("\n-----------------------------------------------\n")
            # table_ids = [0,1]
            correct = 0
            t_samples = 0
            acc = 0.0

            with open(wikitq_path, encoding='utf-8') as f1:
                for i, l in enumerate(f1):
                    if i in table_ids:
                        dic = json.loads(l)
                        ids = dic['ids']
                        title = dic['title']
                        table = dic['table_text']
                        question = dic['statement']
                        answer = dic['answer']
                        answer = ','.join(answer)
                        answer = answer.lower()
                        print('\nid: ', ids, 'Title: ', title,' Q: ', question, ' ans: ', answer)

                        prompt = generate_sql_prompt_wtq(title, tab_col, question, three_rows, mode="normtab")

                        response = ""
                        output_ans = ""

                        try:
                            answer_sql_raw = get_ans_sql(prompt)

                            # 전처리 (Qwen <think> 제거)
                            answer_sql_raw = clean_response(str(answer_sql_raw))

                            # 추론 로그 저장
                            log_file = os.path.join(log_dir, f"{ids}_log.txt")
                            with open(log_file, "w", encoding="utf-8") as lf:
                                lf.write("==== PROMPT ====\n")
                                lf.write(prompt + "\n\n")
                                lf.write("==== RAW RESPONSE ====\n")
                                lf.write(str(answer_sql_raw) + "\n")

                            # SQL만 추출
                            answer_sql = extract_sql(str(answer_sql_raw))
                            if not answer_sql:
                                print(f"⚠️ SQL not found in response for {ids}")
                                continue

                            print("Final SQL:", answer_sql)
                            prediction = pd.read_sql_query(answer_sql, conn)
                            print("\nPrediction: \n\n", prediction.to_markdown(index=False))

                            if prediction.shape == (1, 1):
                                result_list = prediction.values.tolist()

                                output_ans = ""
                                for row in result_list:
                                    for coll in row:
                                        output_ans += str(coll) + " "
                                        # print(coll)
                                output_ans = output_ans.lower()

                            elif not prediction.empty:
                                result_list = prediction.values.tolist()

                                output_ans = ""
                                for row in result_list:
                                    for coll in row:
                                        output_ans += str(coll) +" "
                                    output_ans += ","
                                if output_ans.endswith(','):
                                    output_ans = output_ans.rstrip(',')

                                output_ans = output_ans.lower()

                            output_ans = output_ans.lower()

                            print('Gen output: ', output_ans, 'Gold: ', answer)

                            if output_ans.strip() == answer or output_ans.strip().find(answer) != -1 \
                                    or answer.strip().find(output_ans.strip()) != -1:
                                correct += 1
                                print("correct: ", correct)

                            t_samples += 1
                            acc =  correct / (t_samples + 0.0001)
                            print('Correcet: ', correct, 'total: ', t_samples, "Accuracy: ", acc)
                            print("\n-----------------------------------------------\n")

                        except:
                            print("error: ", ids)
                            continue
                            # ---------------------------------------------------------------------------------------------------------

                        tmp = {'key': ids, 'question': question, 'prediction': output_ans,
                               'answer': answer}
                        fw.write(json.dumps(tmp) + '\n')
                        # #
                        data = [ids, question, answer, output_ans.strip(), answer_sql, prediction.to_markdown(index=False)]
                        writer.writerow(data)
                        # # ---------------------------------------------------------------------------------------------------------

            print("***********************************************************\n")

            print('Main Table ID: ', id, 'Correcet: ', correct, 'total: ', t_samples, "Accuracy: ", acc)
            print("\n-----------------------------------------------\n")
    #         ---------------------------- -------- ------------- ----------- ---------------

    f.close()
    fw.close()

    conn.close()