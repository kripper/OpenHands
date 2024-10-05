import litellm
import tomllib

with open('config.toml', 'rb') as f:
    config = tomllib.load(f)

model = config['llm']['model']
api_key = config['llm']['api_key']

response = litellm.completion(
    model=model,
    messages=[{'role': 'user', 'content': 'Hello, how are you?'}],
    api_key=api_key,
)

print(response.choices[0].message.content)
