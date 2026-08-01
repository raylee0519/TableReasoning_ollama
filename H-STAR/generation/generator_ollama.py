"""
Ollama 기반 Generator (OpenAI 호환 API 사용)
"""

import os
import time
from typing import Dict, List, Union, Tuple
from openai import OpenAI
from generation.prompt import PromptBuilder


class Generator(object):
    """
    Ollama generation wrapper.
    """

    def __init__(self, args, keys=None):
        self.args = args
        self.keys = keys if keys else ["ollama"]   # 더미 키
        self.current_key_id = 0

        # Ollama OpenAI 호환 API 클라이언트 설정
        self.client = OpenAI(
            base_url=f"http://{os.environ.get('OLLAMA_HOST', 'localhost:11434')}/v1",  # Ollama API 엔드포인트
            api_key="ollama"                       # Ollama는 실제 키 불필요
        )

        # 기존 PromptBuilder 유지
        self.prompt_builder = PromptBuilder(args) if args else None

    def build_few_shot_prompt_from_file(
            self,
            file_path: str,
            n_shots: int
    ):
        """
        파일에서 Few-shot prompt 로드
        """
        with open(file_path, 'r') as f:
            lines = f.readlines()
        few_shot_prompt_list = []
        one_shot_prompt = ''
        last_line = None
        for line in lines:
            if line == '\n' and last_line == '\n':
                few_shot_prompt_list.append(one_shot_prompt)
                one_shot_prompt = ''
            else:
                one_shot_prompt += line
            last_line = line
        few_shot_prompt_list.append(one_shot_prompt)
        few_shot_prompt_list = few_shot_prompt_list[:n_shots]
        few_shot_prompt_list[-1] = few_shot_prompt_list[-1].strip()
        few_shot_prompt = '\n'.join(few_shot_prompt_list)
        return few_shot_prompt

    def build_generate_prompt(
            self,
            data_item: Dict,
            generate_type: Tuple,
            **kwargs
    ):
        """
        최종 프롬프트 생성
        """
        return self.prompt_builder.build_generate_prompt(
            **data_item,
            generate_type=generate_type,
            **kwargs
        )

    def generate_one_pass(
            self,
            prompts: List[Tuple],
            verbose: bool = False
    ):
        """
        Ollama 모델 호출 (한 번의 inference pass)
        """
        result_idx_to_eid = []
        for p in prompts:
            result_idx_to_eid.extend([p[0]] * self.args.sampling_n)
        prompts = [p[1] for p in prompts]
        start_time = time.time()

        result = self._call_ollama_api(
            engine=self.args.engine,
            prompts=prompts,
            max_tokens=self.args.max_generation_tokens,
            temperature=self.args.temperature,
            top_p=self.args.top_p,
            n=self.args.sampling_n,
            stop=self.args.stop_tokens,
        )
        print(f'Ollama api one inference time: {time.time() - start_time}')

        if verbose:
            print('\n', '*' * 20, 'Ollama API Call', '*' * 20)
            for prompt in prompts:
                print(prompt)
                print('\n')
            print('- - - - - - - - - - ->>')

        # 결과 파싱
        response_dict = dict()
        for idx, g in enumerate(result["choices"]):
            text = g["message"]["content"]
            eid = result_idx_to_eid[idx]
            eid_pairs = response_dict.get(eid, None)
            if eid_pairs is None:
                eid_pairs = []
                response_dict[eid] = eid_pairs
            eid_pairs.append((text))

            if verbose:
                print(text)

        return response_dict

    def _call_ollama_api(
            self,
            engine: str,
            prompts: Union[str, List],
            max_tokens,
            temperature: float,
            top_p: float,
            n: int,
            stop: List[str],
    ):
        """
        Ollama API 호출 (OpenAI Chat API 호환)
        """
        if isinstance(prompts, str):
            prompts = [prompts]

        choices = []
        for prompt_item in prompts:
            response = self.client.chat.completions.create(
                model=engine,
                messages=[
                    {"role": "system",
                     "content": "You are a helpful assistant for table reasoning."},
                    {"role": "user", "content": prompt_item},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                n=n,
                stop=stop,
            )
            choices += response.choices

        return {"choices": [{"message": {"content": c.message.content}} for c in choices]}
