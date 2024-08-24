import json

import requests

data = {
    'action': {
        'action': 'run_ipython',
        'args': {
            'code': 'open_file',
        },
    }
}
data1 = {
    'action': {
        'action': 'run',
        'args': {
            'command': 'pwd',
        },
        'timeout': 1,
    }
}

json_data = json.dumps(data)
response = requests.post('http://localhost:63711/execute_action', json=data, timeout=1)
try:
    print(response.json()['content'])
except Exception:
    print(response.json())
    print(response.status_code)
