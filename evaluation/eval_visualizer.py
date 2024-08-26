#!/usr/bin/env python
import json
import sys
import webbrowser

import requests

if sys.argv[1:]:
    file = sys.argv[1]
else:
    file = r'evaluation\evaluation_outputs\outputs\swe-bench-lite\CodeActSWEAgent\llama3-8b-8192_maxiter_6_N_v1.6-no-hint\output.jsonl'

# output.json or trajectory.json
if 1:
    with open(file, 'r') as f:
        data = f.readlines()
        data = [json.loads(line) for line in data][0]
        history = data.pop('history')
else:
    fp = r'evaluation\evaluation_outputs\astropy__astropy-12907.json'
    with open(fp, 'r') as f:
        data = json.load(f)
        history = data['traj']
# for i in data['history']:
#     pprint(i)
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
# pprint(json_data)
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
