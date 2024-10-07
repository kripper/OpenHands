import litellm
import tomllib

with open('config.toml', 'rb') as f:
    config = tomllib.load(f)
    config = config['llm']
    group = 'gemini_pro'
    if group in config:
        config = config[group]

model = config['model']
print('Using model:', model)
api_key = config['api_key']

response = litellm.completion(
    model=model,
    messages=[{'role': 'user', 'content': 'Hello, how are you?'}],
    api_key=api_key,
)

print(response.choices[0].message.content)
