#color 프롬프트

system_prompt = """ 
You are an AI assistant that analyzes chart images and constructs the reasoning process to derive answers when given question-answer pairs.  

You must follow a structured approach by decomposing the question into sub-questions and solving them systematically.

### Response Format:
---
**Let's break down this problem.**

**Question Phase:**  
1. (Ask about element 1)  
2. (Ask about element 2)
3. ...  


**Solution Phase:**  
1) (Answer sub-question 1 with reasoning and answer)  
2) (Answer sub-question 2 with reasoning and answer)
3) ... 
---

### **Guidelines:**

- **Question Phase:**  
  - Identify the necessary elements from the question to solve the problem.  
  - Generate sub-questions **strictly following the format**:  
    ```
    1. (Ask about element 1)  
    2. (Ask about element 2)  
    3. ... 
    ```
  - The number of sub-questions must be **exactly reflected in the Solution Phase**.  

- **Solution Phase:**  
  - Ensure that every sub-question **has a corresponding answer** in the exact order.  
  - Provide answers **strictly following the format**:  
    ```
    1) (Answer sub-question 1 with reasoning and answer)  
    2) (Answer sub-question 2 with reasoning and answer)  
    3) ...  
    ```
  - Responses must be **clear, precise, and follow the structured format without skipping or merging answers**.  
  - **Do not include the word "table" in any response.**  
"""

few_shot_examples = [
{
    'role': 'user',
    'content': 'query:"What is the combined percentage of respondents who view dark wedge in green and olive wedge in green as the greatest threat?", table:"Entity | Value & Don\'t know (black) | 5 & Lashkare Taiba (dark green) | 20 & China (light green) | 6 & Naxalites (olive green) | 19 & AII of these (VOL) (gray) | 2 & Pakistan (green) | 47"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/12814.png']
},
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What value corresponds to the dark wedge in green?\n"
        "2. What value corresponds to the olive wedge in green?\n"
        "3. What is the combined value of the two?\n\n"
        "**Solution Phase:**\n"
        "1) The dark green wedge refers to **Lashkare Taiba**, which has a value of **20**.\n"
        "2) The olive green wedge refers to **Naxalites**, which has a value of **19**.\n"
        "3) The combined value is **20 + 19 = 39**.\n\n"
        "**Final Answer:** 39"
    )
},
    #예시 2
{
    'role': 'user',
    'content': 'query:"What is the difference in percentages between the highest orange series and the lowest green series from 2005 to 2015?", table:"Year | Favorable (green) | Unfavorable (orange) & 2005 | 43 | 35 & 2006 | 52 | 29 & 2007 | 42 | 39 & 2008 | 39 | 42 & 2009 | 50 | 38 & 2010 | 49 | 36 & 2011 | 51 | 36 & 2012 | 40 | 40 & 2013 | 37 | 52 & 2014 | 35 | 55 & 2015 | 38 | 54"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/10095.png']
},
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What is the highest value in the orange series between 2005 and 2015?\n"
        "2. What is the lowest value in the green series between 2005 and 2015?\n"
        "3. What is the difference between the highest orange and the lowest green values?\n\n"
        "**Solution Phase:**\n"
        "1) The orange series (Unfavorable) values are: [35, 29, 39, 42, 38, 36, 36, 40, 52, 55, 54]. The highest value is **55** in **2014**.\n"
        "2) The green series (Favorable) values are: [43, 52, 42, 39, 50, 49, 51, 40, 37, 35, 38]. The lowest value is **35** in **2014**.\n"
        "3) The difference is **55 - 35 = 20**.\n\n"
        "**Final Answer:** 20"
    )
},
    # 예제 3 (복잡한 질문 - 평균 계산)
{
    'role': 'user',
    'content': 'query:"Calculate the average change in gray-colored bar category\'s share between consecutive years from 2010 to 2020.", table:"Characteristic | Agriculture (blue) | Industry (dark blue) | Services (gray) & 2020 | 27.73% | 22.65% | 49.62% & 2019 | 28.64% | 22.45% | 48.91% & 2018 | 29.63% | 22.29% | 48.08% & 2017 | 30.79% | 22.02% | 47.19% & 2016 | 31.82% | 21.72% | 46.46% & 2015 | 33.04% | 22.04% | 44.92% & 2014 | 34.28% | 21.4% | 44.32% & 2013 | 34.98% | 20.95% | 44.07% & 2012 | 35.93% | 21.07% | 43% & 2011 | 37.19% | 19.99% | 42.82% & 2010 | 39.15% | 18.66% | 42.19%"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/multi_col_393.png']
},
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What are the values of the gray-colored bar from 2010 to 2020?\n"
        "2. What are the year-to-year changes in these values?\n"
        "3. What is the average of these absolute changes?\n\n"
        "**Solution Phase:**\n"
        "1) Values for Services (gray) from 2010 to 2020:\n"
        "   [42.19, 42.82, 43.00, 44.07, 44.32, 44.92, 46.46, 47.19, 48.08, 48.91, 49.62]\n"
        "2) Year-to-year absolute changes:\n"
        "   - 2011-2010: |42.82 - 42.19| = 0.63\n"
        "   - 2012-2011: |43.00 - 42.82| = 0.18\n"
        "   - 2013-2012: |44.07 - 43.00| = 1.07\n"
        "   - 2014-2013: |44.32 - 44.07| = 0.25\n"
        "   - 2015-2014: |44.92 - 44.32| = 0.60\n"
        "   - 2016-2015: |46.46 - 44.92| = 1.54\n"
        "   - 2017-2016: |47.19 - 46.46| = 0.73\n"
        "   - 2018-2017: |48.08 - 47.19| = 0.89\n"
        "   - 2019-2018: |48.91 - 48.08| = 0.83\n"
        "   - 2020-2019: |49.62 - 48.91| = 0.71\n"
        "   → Total change: 6.73 across 10 intervals\n"
        "3) Average change = 6.73 / 10 = **0.673**\n\n"
        "**Final Answer:** 0.673"
    )
},
    # 예제 4 (복잡한 질문 - 합 비교)
{
    'role': 'user',
    'content': 'query:"Calculate the difference in the sum of the blue bar category and dark blue bar category \\"No\\" responses compared to their \\"Yes\\" responses.", table:"Characteristic | Total (grey) | Male (blue) | Female (dark blue) & Yes | 53% | 45% | 60% & No | 47% | 54% | 40%"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/multi_col_614.png']
},
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What are the values of the blue and dark blue bars for the 'No' response?\n"
        "2. What are the values of the blue and dark blue bars for the 'Yes' response?\n"
        "3. What is the sum of the 'No' values and the sum of the 'Yes' values?\n"
        "4. What is the difference between the sums?\n\n"
        "**Solution Phase:**\n"
        "1) The 'No' response values are:\n"
        "   - Blue (Male): 54%\n"
        "   - Dark Blue (Female): 40%\n"
        "2) The 'Yes' response values are:\n"
        "   - Blue (Male): 45%\n"
        "   - Dark Blue (Female): 60%\n"
        "3) Sum of 'No' = 54 + 40 = **94**\n"
        "   Sum of 'Yes' = 45 + 60 = **105**\n"
        "4) Difference = |94 - 105| = **11**\n\n"
        "**Final Answer:** 11"
    )
},
    # 예제 4
{
    'role': 'user',
    'content': 'query:"How many age groups have more than 5% of patients in the highlighted in blue category?", table:"Characteristic | Patients with an underlying health condition (blue) | Patients without an underlying health condition (black) & 9 years and younger | 0.6% | 0.1% & 10 to 19 years | 0.8% | 0.1% & 20 to 29 years | 1.4% | 0.1% & 30 to 39 years | 2.8% | 0.1% & 40 to 49 years | 4.5% | 0.4% & 50 to 59 years | 7.8% | 0.9% & 60 to 69 years | 16.7% | 2.4% & 70 to 79 years | 31.7% | 10.2% & 80 years and older | 49.7% | 29.8% & Total | 19.5% | 1.6%"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/multi_col_1364.png']
},
#예제4
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What are the percentages of patients in the blue bar category for each age group?\n"
        "2. Which of these values are greater than 5%?\n"
        "3. How many age groups satisfy this condition?\n\n"
        "**Solution Phase:**\n"
        "1) Blue bar (Patients with an underlying health condition) percentages by age group:\n"
        "   - 9 years and younger: 0.6%\n"
        "   - 10 to 19 years: 0.8%\n"
        "   - 20 to 29 years: 1.4%\n"
        "   - 30 to 39 years: 2.8%\n"
        "   - 40 to 49 years: 4.5%\n"
        "   - 50 to 59 years: 7.8%\n"
        "   - 60 to 69 years: 16.7%\n"
        "   - 70 to 79 years: 31.7%\n"
        "   - 80 years and older: 49.7%\n"
        "2) Values greater than 5%:\n"
        "   - 50 to 59 years: 7.8%\n"
        "   - 60 to 69 years: 16.7%\n"
        "   - 70 to 79 years: 31.7%\n"
        "   - 80 years and older: 49.7%\n"
        "3) Total number of age groups with more than 5%: 4\n\n"
        "**Final Answer:** 4"
    )
},
    # 예시 5 (비율 계산)
{
    'role': 'user',
    'content': 'query:"What is the ratio of malaria incidence in highlighted in pink country compared to blue-highlighted in gray country?", table:"Country | Incidence of malaria, 1990 & Togo (pink) | 493 & Yemen (purple) | 370 & Tajikistan (blue-gray) | 196 & Middle SDI (teal) | 12 & Costa Rica (orange) | 1"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/93612508003287.png']
},
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What is the incidence of malaria in the pink-highlighted country?\n"
        "2. What is the incidence of malaria in the blue-gray-highlighted country?\n"
        "3. What is the ratio of the first value to the second?\n\n"
        "**Solution Phase:**\n"
        "1) The pink-highlighted country is **Togo**, with a malaria incidence of **493** per 1,000 people at risk.\n"
        "2) The blue-gray-highlighted country is **Tajikistan**, with a malaria incidence of **196**.\n"
        "3) Ratio = 493 / 196 ≈ **2.51** (rounded to two decimal places)\n\n"
        "**Final Answer:** 2.51"
    )
},
    # 예시 6 (조지아 빈곤율 차이 계산)
{
    'role': 'user',
    'content': 'query:"In which countries is the percentage of beige-colored bar greater than the percentage of blue-colored bar?", table:"|        | More important (green) | As important (beige) | Less important (blue) | & |--------|------------------------|----------------------|-----------------------| & | Greece | 24                     | 40                   | 30                    | & | UK     | 23                     | 36                   | 39                    | & | Spain  | 22                     | 48                   | 28                    | & | Italy  | 21                     | 31                   | 34                    | & | Poland | 21                     | 33                   | 31                    | & | Hungary| 20                     | 41                   | 33                    | & | Sweden | 16                     | 30                   | 53                    | & | Netherlands | 15                | 32                   | 52                    | & | Germany| 10                     | 34                   | 50                    | & | France | 9                      | 39                   | 51                    | & | MEDIAN | 21                     | 37                   | 38                    |"',
    'images': ['/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png/3787.png']
},
{
    'role': 'assistant',
    'content': (
        "Let's break down this problem.\n\n"
        "**Question Phase:**\n"
        "1. What are the values of the beige-colored bar (As important) for each country?\n"
        "2. What are the values of the blue-colored bar (Less important) for each country?\n"
        "3. In which countries is the beige value greater than the blue value?\n\n"
        "**Solution Phase:**\n"
        "1) Beige vs Blue comparison:\n"
        "- Greece: 40 vs 30 → beige > blue\n"
        "- UK: 36 vs 39 → beige < blue\n"
        "- Spain: 48 vs 28 → beige > blue\n"
        "- Italy: 31 vs 34 → beige < blue\n"
        "- Poland: 33 vs 31 → beige > blue\n"
        "- Hungary: 41 vs 33 → beige > blue\n"
        "- Sweden: 30 vs 53 → beige < blue\n"
        "- Netherlands: 32 vs 52 → beige < blue\n"
        "- Germany: 34 vs 50 → beige < blue\n"
        "- France: 39 vs 51 → beige < blue\n"
        "- MEDIAN: 37 vs 38 → beige < blue\n"
        "2) Countries where beige > blue: Greece, Spain, Poland, Hungary\n\n"
        "**Final Answer:** Greece, Spain, Poland, Hungary"
    )
}
]

import ollama
import json
import time
import os

input_file = "/home/wooo519/decs_jupyter_lab/multimodals/ollama_getAnswer/position/question_color_6.json"
IMAGE_BASE_PATH = "/home/wooo519/decs_jupyter_lab/llava/ChartQA/ChartQA_Dataset/train/png"
output_file = "/home/wooo519/decs_jupyter_lab/multimodals/ollama_getAnswer/position/answers/color_6_reversed.json"
# ✅ 기존 데이터 불러오기 (파일이 존재하면 로드, 없으면 빈 리스트)
if os.path.exists(output_file):
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)  # 기존 데이터를 리스트로 로드
            if not isinstance(existing_data, list):  # 파일이 {} 빈 객체로 저장되었을 경우 복구
                existing_data = []
    except json.JSONDecodeError:
        print("⚠️ 기존 JSON 파일이 손상됨. 새로 생성합니다.")
        existing_data = []
else:
    existing_data = []

# ✅ 이미 처리된 데이터 확인 (중복 방지)
processed_entries = {(entry["imgname"], entry["question"]) for entry in existing_data}
print(f"🔄 기존에 처리된 데이터: {len(processed_entries)}개 (건너뛸 예정)")

# ✅ Ollama API 요청 함수
def generate_response(input_data):
    """LLM을 호출하여 이미지 + 질문 + 표 데이터를 활용한 응답 생성"""

    global system_prompt, few_shot_examples

    image_path = os.path.join(IMAGE_BASE_PATH, input_data["imgname"].strip())

    user_input = {
        "role": "user",
        "content": f'question:"{input_data["question"]}", table:"{input_data["table"]}"',
        "images": [image_path]
    }

    try:
        response = ollama.chat(
            model='llama3.2-vision:90b',
            messages=[{"role": "system", "content": system_prompt}] + few_shot_examples + [user_input]
        )

        return {
            "imgname": input_data["imgname"],
            "question": input_data["question"],
            "table": input_data["table"],
            "response": response.get("message", {}).get("content", "")
        }

    except Exception as e:
        print(f"❌ 오류 발생 (imgname: {input_data['imgname']}): {e}")
        return None  # 오류 발생 시 None 반환

# ✅ 입력 데이터 불러오기
with open(input_file, "r", encoding="utf-8") as f:
    dataset = json.load(f)

# ✅ 한 개씩 저장되도록 수정
for i, data in enumerate(reversed(dataset)):
    entry_key = (data["imgname"], data["question"])  # ✅ imgname + query 기준으로 중복 방지

    if entry_key in processed_entries:
        print(f"⏩ {i+1} / {len(dataset)} 데이터 이미 처리됨: {data['imgname']} | {data['question']} (건너뜀)")
        continue  # 이미 처리된 데이터는 건너뛴다.

    result = generate_response(data)
    if result:
        existing_data.append(result)  # 새로운 데이터 추가
        processed_entries.add(entry_key)  # ✅ 새롭게 추가된 항목을 중복 체크 리스트에 추가
        
        # ✅ 한 개씩 즉시 저장 (파일이 중간에 깨지는 문제 방지)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)

        print(f"✅ {i+1} / {len(dataset)} 데이터 생성 및 저장 완료")

    time.sleep(2)  # API 부하 방지

print(f"✅ 모든 데이터 저장 완료! 파일 위치: {output_file}")