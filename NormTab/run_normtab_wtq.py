import csv
import os
from pandasql import sqldf
from sqlalchemy import create_engine
from utils.preprocess import *
from utils.normalizer import *
from utils.all_prompts import *
from utils.llm_agent import *
import json
import time
from ast import literal_eval

# ---------------------------------------------------------------

def get_normtab_response(title, table, mode="targeted", max_retries=3):
    if mode == "basic":
        prompt = generate_normtab_prompt_basic(title, table)
    elif mode == "targeted":
        prompt = generate_normtab_prompt_targeted(title, table)

    print(f"[DEBUG] Calling LLM with mode: {mode}")
    
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Attempt {attempt + 1}/{max_retries}")
            response = get_completion(prompt, temperature=0.7, max_tokens=4000)
            print(f"[DEBUG] Response received: {response[:100]}...")  # 처음 100자만 출력
            return response
        except Exception as e:
            print(f"[ERROR] Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                print(f"[ERROR] All attempts failed for LLM call")
                return None

def select_columns(title, three_rows, tab_col, max_retries=3):
    prompt = generate_col_prompt(title, three_rows, tab_col)
    
    for attempt in range(max_retries):
        try:
            print(f"[DEBUG] Column selection attempt {attempt + 1}/{max_retries}")
            response = get_completion(prompt, temperature=0.5, max_tokens=100)
            print(f"[DEBUG] Column selection response: {response}")
            return response
        except Exception as e:
            print(f"[ERROR] Column selection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                print(f"[ERROR] All column selection attempts failed")
                return None

def run_normtab_basic(table, title):
    original_table_markdown = table.to_markdown(index=False)
    print('Table Markdown:\n', original_table_markdown)
    
    try:
        norm_table = get_normtab_response(title, original_table_markdown, mode="basic")
        if norm_table is None:
            raise ValueError("Failed to get response from LLM")
            
        print('response: \n', norm_table)
        
        # 응답 파싱 시도
        if '=' in norm_table:
            norm_table = str(norm_table).strip().split('=')[1]
        else:
            print(f"[WARNING] No '=' found in response, using full response")
        
        norm_table_df = parse_table(norm_table)
        return norm_table_df
        
    except Exception as e:
        print(f"[ERROR] NormTab Basic Error: {str(e)}")
        return pd.DataFrame()  # 빈 DataFrame 반환

def run_normtab_targeted(table, title):
    T = table
    col = T.columns

    tab_col = ", ".join(col)
    print('Table Columns: ', tab_col)

    # Three Sample Rows
    try:
        engine = create_engine('sqlite:///normtab_wtq.db')
        query = "SELECT * FROM T limit 3"
        three_rows = sqldf(query, locals())
        three_rows = table_linearization(three_rows, style='pipe')
        print("[DEBUG] Three rows extracted successfully")
    except Exception as e:
        print(f"[ERROR] Failed to extract three rows: {str(e)}")
        # 대안: 직접 상위 3개 행 선택
        three_rows = table.head(3).to_string()

    # Column Selection
    norm_tab_col = select_columns(title, three_rows, tab_col)
    if norm_tab_col is None:
        print("[ERROR] Column selection failed, using all columns")
        norm_tab_col = str(list(col))
    else:
        try:
            if '=' in norm_tab_col:
                norm_tab_col = str(norm_tab_col).strip().split('=')[1]
        except:
            pass
    
    print('\nColumn Selection (Step 1): ', norm_tab_col, type(norm_tab_col))

    # Extract Subtable
    try:
        extracted_subtable, remaining_subtable = split_table(T, norm_tab_col)
        print("[DEBUG] Table split successfully")
    except Exception as e:
        print(f"[ERROR] Col Extraction Error: {str(e)}")
        # 대안: 원본 테이블 사용
        extracted_subtable = T
        remaining_subtable = pd.DataFrame()

    print('-------------------------\n')

    # NormTab Step 2
    extracted_subtable_markdown = extracted_subtable.to_markdown(index=False)
    print('\nExtracted Table Markdown:\n', extracted_subtable_markdown)
    
    if not remaining_subtable.empty:
        print("\nRemaining subtable: \n", remaining_subtable.to_markdown(index=False))

    norm_subtable = pd.DataFrame()
    if not extracted_subtable.empty:
        print("[DEBUG] Processing extracted subtable with NormTab")
        try:
            norm_subtable_response = get_normtab_response(title, extracted_subtable_markdown, mode="targeted")
            
            if norm_subtable_response is None:
                raise ValueError("Failed to get NormTab response")
            
            # 응답 파싱
            if '=' in norm_subtable_response:
                norm_subtable_str = str(norm_subtable_response).strip('```')
            else:
                norm_subtable_str = str(norm_subtable_response).strip('```')
                
            norm_subtable = parse_table(norm_subtable_str)
            print("\nNormalized Subtable (NormTab) Step 2:\n", norm_subtable.to_markdown(index=False))
            
        except Exception as e:
            print(f"[ERROR] NormTab Step 2 Error: {str(e)}")
            norm_subtable = extracted_subtable  # 대안: 원본 사용

    # Merge
    try:
        merged_norm_table_df = pd.concat([remaining_subtable, norm_subtable], axis=1)
        merged_norm_table_markdown = merged_norm_table_df.to_markdown(index=False)
        print("\nMerged Table (Normalized) Step 2:\n", merged_norm_table_markdown)
    except Exception as e:
        print(f"[ERROR] Merge error: {str(e)}")
        merged_norm_table_df = norm_subtable if not norm_subtable.empty else extracted_subtable

    print('\n*****************************************\n')

    # Postprocessing
    try:
        last_row = merged_norm_table_df.iloc[-1].tolist()
        ignore_last_row = detect_ignore_last_row(str(last_row))
        
        if ignore_last_row:
            merged_norm_table_df = merged_norm_table_df.iloc[:-1]
            print('Ignored last row: ', merged_norm_table_df.to_markdown(index=False))
    except Exception as e:
        print(f"[ERROR] Last row processing error: {str(e)}")
        ignore_last_row = False

    print('\n*****************************************\n')

    # Transposition
    try:
        need_transposition = transpose_table_detector(merged_norm_table_df, title)
        print("Need transposition: ", need_transposition)
        
        if need_transposition:
            transposed_table = transpose_table_df(merged_norm_table_df)
            modified_merged_norm_table_df = transposed_table
        else:
            modified_merged_norm_table_df = merged_norm_table_df
    except Exception as e:
        print(f"[ERROR] Transposition error: {str(e)}")
        need_transposition = False
        modified_merged_norm_table_df = merged_norm_table_df

    return norm_tab_col, merged_norm_table_df, modified_merged_norm_table_df, ignore_last_row, need_transposition

# ---------------------------------------------------------------

def split_table(table, column_string):
    try:
        column_list = literal_eval(column_string)
    except:
        # 파싱 실패 시 문자열 그대로 사용
        column_list = [col.strip() for col in column_string.replace('[', '').replace(']', '').replace("'", "").split(',')]
    
    # 존재하는 컬럼만 필터링
    valid_columns = [col for col in column_list if col in table.columns]
    
    if not valid_columns:
        print(f"[WARNING] No valid columns found, using all columns")
        valid_columns = table.columns.tolist()
    
    extracted_subtable = table[valid_columns]
    remaining_columns = [col for col in table.columns if col not in valid_columns]
    remaining_subtable = table[remaining_columns] if remaining_columns else pd.DataFrame()
    
    return extracted_subtable, remaining_subtable

def df_to_list_of_lists(df):
    header = df.columns.tolist()
    data = df.values.tolist()
    return [header] + data

# ---------------------------------------------------------------

OUTPUT_DIR = 'outputs'
NORMALIZE_OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'normTab_targeted_wtq_llama3.2:1b.csv')
NORMALIZE_HEADER = ['id', 'table title', 'original_tab', 'norm_table_markdown', 'norm_table', 'norm_table_modified','norm_table_t', 'columns', 'transpose', 'last_row']


def get_done_table_ids(path):
    """Table ids already normalized in a prior run -- read via csv.DictReader
    (not line-count) since fields like norm_table_markdown contain embedded
    newlines that a plain line-count would miscount."""
    done = set()
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                done.add(row['id'])
    return done


if __name__ == "__main__":
    path = 'datasets/wtq_test3.jsonl'

    table_ids = UNIQUE_TAB_IDS_WTQ  # full range, not a debug slice
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    done_ids = get_done_table_ids(NORMALIZE_OUTPUT_PATH)
    print(f"Already normalized: {len(done_ids)} tables")

    write_header = not (os.path.exists(NORMALIZE_OUTPUT_PATH) and os.path.getsize(NORMALIZE_OUTPUT_PATH) > 0)
    f = open(NORMALIZE_OUTPUT_PATH, 'a', newline='', encoding='utf-8')
    writer = csv.writer(f)
    if write_header:
        writer.writerow(NORMALIZE_HEADER)
        f.flush()

    normtab_mode = "targeted"  # 명확하게 설정
    error_ids = []

    with open(path, encoding='utf-8') as f1:
        for i, l in enumerate(f1):
            if i in table_ids:
                try:
                    dic = json.loads(l)
                    ids = dic['ids']
                    if ids in done_ids:
                        continue

                    title = dic['title']
                    table = dic['table_text']

                    print(f'\n\n[INFO] Processing id: {ids}, title: {title}')

                    T = dict2df(table)
                    original_table_markdown = T.to_markdown(index=False)

                    if normtab_mode == "basic":
                        try:
                            norm_table_df = run_normtab_basic(T, title)
                            if norm_table_df.empty:
                                raise ValueError("Empty normalized table")
                                
                            norm_table_markdown = norm_table_df.to_markdown(index=False)
                            norm_table = df_to_list_of_lists(norm_table_df)
                            data = [ids, title, original_table_markdown, norm_table_markdown, norm_table]
                            
                        except Exception as e:
                            print(f"[ERROR] NormTab Basic Error for {ids}: {str(e)}")
                            error_ids.append(ids)
                            continue
                    
                    elif normtab_mode == "targeted":
                        try:
                            results = run_normtab_targeted(T, title)
                            if results is None:
                                raise ValueError("No results from targeted normtab")
                                
                            norm_tab_col, merged_norm_table_df, modified_merged_norm_table_df, is_last_row, is_transposed = results
                            
                            merged_norm_table = df_to_list_of_lists(merged_norm_table_df)
                            merged_norm_table_markdown = merged_norm_table_df.to_markdown(index=False)
                            
                            modified_merged_norm_table = df_to_list_of_lists(modified_merged_norm_table_df)
                            modified_merged_norm_table_markdown = modified_merged_norm_table_df.to_markdown(index=False)
                            
                            norm_table_t = df_to_list_of_lists(modified_merged_norm_table_df)
                            
                            data = [ids, title, original_table_markdown, merged_norm_table_markdown, merged_norm_table, 
                                   modified_merged_norm_table_markdown, norm_table_t, norm_tab_col, is_last_row, is_transposed]
                            
                            print(f"[INFO] Successfully processed {ids}")
                            
                        except Exception as e:
                            print(f"[ERROR] NormTab Targeted Error for {ids}: {str(e)}")
                            error_ids.append(ids)
                            continue
                    
                    # Write results
                    writer.writerow(data)
                    f.flush()
                    print(f"[INFO] Written results for {ids}")
                    
                except Exception as e:
                    print(f"[ERROR] General error processing {ids}: {str(e)}")
                    error_ids.append(ids)
                    continue
    
    print(f"\n[FINAL] Error Ids: {error_ids}")
    f.close()
