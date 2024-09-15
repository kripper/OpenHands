import litellm
import toml

prompt = r'logs/llm/default/011_prompt.log'
response = r'logs/llm/default/011_response.log'

with open(prompt, 'r') as file:
    prompt_content = file.read()

with open(response, 'r') as file:
    response_content = file.read()

config = 'config.toml'

with open(config, 'r') as file:
    config_content = toml.load(file)['llm']
    eval = 1
    if eval:
        config_content = config_content['eval']


model = config_content['model']
api_key = config_content['api_key']

question = 'In which line super is called? How do you say so?'
new_prompt = f"""
INITIAL PROMPT:
{prompt_content}

INITIAL RESPONSE:
{response_content}

USER:
{question}
"""
while True:
    response = litellm.completion(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': new_prompt},
        ],
        api_key=api_key,
    )
    resp = response['choices'][0]['message']['content']
    print(resp)
    question = input('> ')
    if question == 'q':
        break
    new_prompt = f"""
    {new_prompt}

    ASSISTANT:
    {resp}

    USER:
    {question}
    """
