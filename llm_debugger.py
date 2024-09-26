import litellm
import toml

number = 2
model = 'gemini_pro'
model = 'gemini'
with open('evaluation/swe_bench/config.toml', 'r') as f:
    environ = f.read()
    config = toml.loads(environ)
    selection_id = config['selected_ids'][0].split('-')[-1]
prompt = f'logs/llm/{model}_{selection_id}/{number:03d}_prompt.log'
response = f'logs/llm/{model}_{selection_id}/{number:03d}_response.log'

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
question = """
========
KNOWLEDGE LINES:
When editing a subclass, ensure that all parameters and attributes of the superclass's `__init__` method are thoroughly examined and understood. Always pass necessary attributes or arguments to the superclass to maintain proper initialization, while handling subclass-specific attributes within the subclass itself.
Don't overlook the need to pass arguments to `super().__init__`
========

The `RST` class's `__init__` method doesn't accept `header_rows`.
> But it does accept `header_rows` in `FixedWidth` class. Why wrong?
"""
question = 'What made you to use browse to search for astropy code on github?'

inst = '\n\nJust tell the reason for the wrong action.'
question += inst
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
        with open(prompt, 'r') as file:
            prompt_content = file.read()
        response = litellm.completion(
            model=model,
            messages=[{'role': 'user', 'content': prompt_content}],
            api_key=api_key,
        )
        resp = response['choices'][0]['message']['content']
        print(resp)
        break
    messages.append({'role': 'assistant', 'content': 'Assistant: ' + resp})
    messages.append({'role': 'user', 'content': 'User: ' + question})
    inst = 'Reply in one line.'
    messages.append({'role': 'system', 'content': 'System: ' + inst})
