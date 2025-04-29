import pickle
import json
import os

def pkl_to_json_with_index(pkl_path, json_path):
    # pkl 파일 열기
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f)

    # 만약 리스트 형태면 각각에 인덱스를 넣는다
    if isinstance(data, list):
        new_data = []
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                item = item.copy()  # 원본 손상 방지
                item["idx"] = idx
            new_data.append(item)
    else:
        # 리스트가 아닌 경우 (dict 등) 그대로
        new_data = data

    # JSON으로 저장할 때 numpy 타입 변환 처리
    def convert(o):
        if isinstance(o, float):
            return float(o)
        if isinstance(o, int):
            return int(o)
        if isinstance(o, (list, dict, str, type(None))):
            return o
        if hasattr(o, 'tolist'):
            return o.tolist()
        return str(o)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False, default=convert)

    print(f"✅ 변환 완료 (with index): {pkl_path} → {json_path}")

# ✨ 파일 경로 설정
result_dir = "results/tabfact"
os.makedirs(os.path.join(result_dir, "json"), exist_ok=True)

# 변환 실행 (각 항목에 idx 추가)
pkl_to_json_with_index(
    pkl_path=os.path.join(result_dir, "/home/wooo519/ollama_tableReasoning/chain-of-table/results/tabfact_first500/final_result.pkl"),
    json_path=os.path.join(result_dir, "json", "/home/wooo519/ollama_tableReasoning/chain-of-table/results/tabfact_first500/final_result_idx.json")
)

pkl_to_json_with_index(
    pkl_path=os.path.join(result_dir, "/home/wooo519/ollama_tableReasoning/chain-of-table/results/tabfact_first500/dynamic_chain_log_list.pkl"),
    json_path=os.path.join(result_dir, "json", "/home/wooo519/ollama_tableReasoning/chain-of-table/results/tabfact_first500/dynamic_chain_log_list_idx.json")
)
