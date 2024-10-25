import litellm
import tomllib

with open('config.toml', 'rb') as f:
    config = tomllib.load(f)
    config = config['llm']
    group = 'gemini_pro'
    group = 'nemo'
    if group in config:
        config = config[group]

model = config['model']
print('Using model:', model)
api_key = config['api_key']
base_url = config.get('base_url')
args = (
    {
        'base_url': base_url,
    }
    if base_url
    else {}
)

response = litellm.completion(
    model=model,
    messages=[{'role': 'user', 'content': 'Hello, how are you?'}],
    api_key=api_key,
    **args,
)

print(response.choices[0].message.content)
