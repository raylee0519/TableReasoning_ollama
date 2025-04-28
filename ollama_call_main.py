# Chain-of-Table 일반 답변 추출

import openai
import time
import numpy as np


class ChatGPT:
    def __init__(self, model_name, key):
        self.model_name = model_name
        self.key = key

        # Ollama로 쓸 때 설정 추가
        openai.api_base = "http://localhost:11434/v1"
        openai.api_key = ""

    def get_model_options(
        self,
        temperature=0,
        per_example_max_decode_steps=150,
        per_example_top_p=1,
        n_sample=1,
    ):
        return dict(
            temperature=temperature,
            n=n_sample,
            top_p=per_example_top_p,
            max_tokens=per_example_max_decode_steps,
        )

    def generate_plus_with_score(self, prompt, options=None, end_str=None):
        if options is None:
            options = self.get_model_options()
        messages = [
            {
                "role": "system",
                "content": "I will give you some examples, you need to follow the examples and complete the text, and no other content.",
            },
            {"role": "user", "content": prompt},
        ]
        gpt_responses = None
        retry_num = 0
        retry_limit = 2
        error = None
        while gpt_responses is None:
            try:
                gpt_responses = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=messages,
                    stop=end_str,
                    **options
                )
                error = None
            except Exception as e:
                print(str(e), flush=True)
                error = str(e)
                if "This model's maximum context length is" in str(e):
                    print(e, flush=True)
                    gpt_responses = {
                        "choices": [{"message": {"content": "PLACEHOLDER"}}]
                    }
                elif retry_num > retry_limit:
                    error = "too many retry times"
                    gpt_responses = {
                        "choices": [{"message": {"content": "PLACEHOLDER"}}]
                    }
                else:
                    time.sleep(60)
                retry_num += 1
        if error:
            raise Exception(error)
        results = []
        for i, res in enumerate(gpt_responses["choices"]):
            text = res["message"]["content"]
            fake_conf = (len(gpt_responses["choices"]) - i) / len(
                gpt_responses["choices"]
            )
            results.append((text, np.log(fake_conf)))

        return results

    def generate(self, prompt, options=None, end_str=None):
        if options is None:
            options = self.get_model_options()
        options["n"] = 1
        result = self.generate_plus_with_score(prompt, options, end_str)[0][0]
        return result

if __name__ == "__main__":
    # 모델 이름과 key 설정
    model_name = "llama3.3"
    key = ""  # Ollama는 key 필요 없음

    # ChatGPT 클래스 인스턴스 생성
    chatgpt = ChatGPT(model_name=model_name, key=key)

    # 프롬프트를 설정
    prompt = "Explain the concept of overfitting in machine learning."

    # 답변 생성
    try:
        response = chatgpt.generate(prompt)
        print("\n🔵 모델 응답:\n", response)
    except Exception as e:
        print("\n🔴 오류 발생:", str(e))
