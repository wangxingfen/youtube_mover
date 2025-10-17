from openai import OpenAI
import json
from retrying import retry
@retry(stop_max_attempt_number=200, wait_exponential_multiplier=200, wait_exponential_max=400)
def chanslater(text):
    '''生成运镜提示词'''
    with open("settings.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    client = OpenAI(
    # 请用知识引擎原子能力API Key将下行替换为：api_key="sk-xxx",
    api_key=config["api_key"], # 如何获取API Key：https://cloud.tencent.com/document/product/1772/115970
    base_url=config["base_url"],
)
    completion = client.chat.completions.create(
        model=config['model'],  # 此处以 deepseek-r1 为例，可按需更换模型名称。
        temperature=0,
        messages=[
            {'role': 'system', 'content':"你是一台翻译机，把下面的文本翻译成中文，不要额外解释,即使原文不完整，也是逐字翻译即可。"},
            {'role': 'user', 'content': text}
            ]
)
    chanslated_prompt=completion.choices[0].message.content
    return chanslated_prompt
def chanslater_z2e(text):
    '''生成运镜提示词'''
    with open("settings.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    client = OpenAI(
    # 请用知识引擎原子能力API Key将下行替换为：api_key="sk-xxx",
    api_key=config["api_key"], # 如何获取API Key：https://cloud.tencent.com/document/product/1772/115970
    base_url=config["base_url"],
)
    completion = client.chat.completions.create(
        model=config['model'],  # 此处以 deepseek-r1 为例，可按需更换模型名称。
        temperature=0.7,
        max_tokens=8192,
        top_p=0.6,
        messages=[
            {'role': 'system', 'content':"把下面的文本翻译成英文，不要额外解释"},
            {'role': 'user', 'content': text}
            ]
)
    chanslated_prompt=completion.choices[0].message.content
    return chanslated_prompt
if __name__ == "__main__":
    print(chanslater("A close-up shot of a person holding a smartphone, with the screen displaying a vibrant app interface. The background is softly blurred, emphasizing the device and the user's hand. The image is in focus, with a soft gradient overlay."))