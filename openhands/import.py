import json
import os

import requests

# ==============================INPUTS==============================
feedback_id = 'd9467879dfb19113adf4bd7ae67a5b83194a00b7d8c03eb7729706ebd3676a5e'
step_count = -1
# ==================================================================


data = {'feedback_id': feedback_id}
file_name = f'_{feedback_id}.json'
disable_import = False
if disable_import:
    with open('event_history.json', 'w') as f:
        json.dump([], f)
if os.path.exists(file_name):
    with open(file_name, 'r') as f:
        event_history = json.load(f)
else:
    response = requests.post(
        'https://show-od-event_history-3u9bw9tx.uc.gateway.dev/show-od-event_history',
        json=data,
    )
    event_history = response.json()['trajectory']

if step_count != -1:
    new_event_history = []
    for i in event_history:
        if i.get('log'):
            step_count -= 1
            print(i)
        if step_count == 0:
            break
        new_event_history.append(i)

with open('event_history.json', 'w') as f:
    json.dump(event_history, f, indent=4)
