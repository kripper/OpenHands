#!python
import json
import re
import sys
import webbrowser
from pprint import pprint

import requests

if sys.argv[1:]:
    file = sys.argv[1]
else:
    from pyperclip import paste

    file = paste()

# output.json or trajectory.json
if 1:
    with open(file, 'r') as f:
        data = f.readlines()
        ansi_color_escape = re.compile(r'\\u001b\[[0-9;]*m')
        data = [ansi_color_escape.sub('', line) for line in data]
        null_observation = ', {"message": "No observation", "observation": "null", "content": "", "extras": {}}'
        data = [line.replace(null_observation, '') for line in data]
        data = [json.loads(line) for line in data]
        history = []
        for d in data:
            history.extend(d['history'])
        history = [i for sublist in history for i in sublist]
        # history = history[3:]

else:
    fp = r'evaluation\evaluation_outputs\astropy__astropy-12907.json'
    with open(fp, 'r') as f:
        data = json.load(f)
        history = data['traj']
if not sys.argv[1:] or 0:
    pprint(history)
    # exit()
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

json_data['trajectory'] = history

# pprint(json_data);exit()
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
