import litellm
import toml

number = 7
model = 'gemini'
prompt = f'logs/llm/{model}/{number:03d}_prompt.log'
response = f'logs/llm/{model}/{number:03d}_response.log'

with open(prompt, 'r') as file:
    prompt_content = file.read()

with open(response, 'r') as file:
    response_content = file.read()

config = 'config.toml'

with open(config, 'r') as file:
    config_content = toml.load(file)['llm']
    eval = 1
    if eval:
        key = 'gemini'
        config_content = config_content[key]


model = config_content['model']
api_key = config_content['api_key']

question = 'Why did you use insert content before line 60?'
question = 'Why are you searching for header_rows?'
question = 'Why did you search for header_rows in ui.py?'
question = 'Why are you not responding to the user?'
question = 'Why did you give this response?'
question = 'Why did you missed the file name for insert_content_after_line()? reply in one line.'
new_prompt = f"""
INITIAL PROMPT:

{prompt_content}

INITIAL RESPONSE:
{response_content}

DEBUGGER:
{question}
"""
messages = [
    {
        'role': 'system',
        'content': 'You are the assistant. Your responses are wrong. The debugger will ask you questions and provide you with the initial prompt abd initial response. Answer the questions and provide the corrected response.',
    },
    {'role': 'user', 'content': new_prompt},
]

while True:
    response = litellm.completion(
        model=model,
        messages=messages,
        api_key=api_key,
    )
    resp = response['choices'][0]['message']['content']
    print(resp)
    question = input('> ')
    if question == 'q':
        break
    messages.append({'role': 'assistant', 'content': resp})
    inst = "Don't give codes. Just answer the question."
    messages.append({'role': 'user', 'content': question + '\n\n' + inst})
