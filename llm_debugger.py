import litellm
import toml

number = 16
prompt = f'logs/llm/default/{number:03d}_prompt.log'
response = f'logs/llm/default/{number:03d}_response.log'

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

question = 'Why did you generate this response?'
question = 'Where insert_content_at_line will insert the content?'
new_prompt = f"""
INITIAL PROMPT:
{prompt_content}

INITIAL RESPONSE:
{response_content}

DEBUGGER:
{question}
"""
while True:
    response = litellm.completion(
        model=model,
        messages=[
            {
                'role': 'system',
                'content': "Don't give codes. Just answer the question.",
            },
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

DEBUGGER:
{question}
Don\'t give codes. Just answer the question.
    """
