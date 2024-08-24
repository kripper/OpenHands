import json

import requests

data = {
    'action': {
        'action': 'run_ipython',
        'args': {
            'code': '%cd /workspace && %pwd',
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


def run_ipython(code):
    return {
        'action': {
            'action': 'run_ipython',
            'args': {
                'code': code,
            },
        }
    }


def run(command):
    return {
        'action': {
            'action': 'run',
            'args': {
                'command': command,
            },
            'timeout': 1,
        }
    }


def execute_action(data):
    data = json.dumps(data)
    try:
        response = requests.post(
            'http://localhost:63711/execute_action', data=data, timeout=1
        )
        print(response.json()['content'])
    except Exception:
        print(response.json())
        print(response.status_code)


# execute_action(run_ipython('%cd /workspace/astropy__astropy__4.3'))
execute_action(run_ipython('%pwd'))
execute_action(run_ipython('edit_file'))
# execute_action(run('pwd'))
