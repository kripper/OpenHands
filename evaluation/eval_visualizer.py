import json
import webbrowser
from pprint import pprint

import requests

file = r'evaluation\evaluation_outputs\outputs\swe-bench-lite\CodeActAgent\llama3-8b-8192_maxiter_500_N_v1.9-no-hint\output.jsonl'

delete = 0
if delete:
    import os

    os.remove(file)
    print(f'Deleted {file}')
    exit()
with open(file, 'r') as f:
    data = f.readlines()
    data = [json.loads(line) for line in data][0]

# for i in data['history']:
#     pprint(i)
history = data.pop('history')
json_data = {}
json_data.update(
    {
        'version': '1.0',
        'feedback': 'negative',
        'email': 'eval@anon.com',
        'permissions': 'public',
        'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzaWQiOiJiNWIwNjRmYi1mMTFlLTQxMTQtOWYxYy1hOTQ3MmZmYjY1ZGUifQ.MjMpKSWLYI4Cg85Uq8HnjY3MY9iBj8yeNawOwgjX5MU',
    }
)
# flatten the history
history = [i for sublist in history for i in sublist]
json_data['trajectory'] = history
pprint(json_data)
# exit()
FEEDBACK_URL = 'https://share-od-trajectory-3u9bw9tx.uc.gateway.dev/share_od_trajectory'

response = requests.post(
    FEEDBACK_URL,
    json=json_data,
)


rj = response.json()
try:
    f_id = rj['body']['feedback_id']
except Exception:
    print(rj)
    exit()

webbrowser.open(f'https://www.all-hands.dev/share?share_id={f_id}')
