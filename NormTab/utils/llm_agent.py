import os
import tiktoken
from openai import OpenAI
# ---------------------------------------------------------------
# API_KEY = ''

os.environ['OPENAI_API_KEY'] = "ollama"  # Ollama에서는 실제 키가 필요없음

# Ollama OpenAI 호환 API 클라이언트 설정
client = OpenAI(
    base_url=f"http://{os.environ.get('OLLAMA_HOST', 'localhost:11434')}/v1",  # Ollama OpenAI 호환 엔드포인트
    api_key="ollama"  # Ollama에서는 실제로 사용되지 않음
)

# model="gpt-3.5-turbo-0125"
# model="gpt-4-turbo"

def get_completion(prompt, model="llama3.2:1b", temperature=0.7, n=1, max_tokens = 6000):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        n=n,
        stream=False,
        max_tokens=max_tokens,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stop=["\n\n\n"]
    )
    return response.choices[0].message.content


import os

os.environ["GOOGLE_API_KEY"] = ""



def get_completion_gemmini(prompt, temperature=0.7, max_tokens = 8000):
    # Create the model
    # See https://ai.google.dev/api/python/google/generativeai/GenerativeModel

    response = "we do not use google api"
    return  response.text


