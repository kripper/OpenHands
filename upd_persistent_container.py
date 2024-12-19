import os
from datetime import datetime

import docker

full_file_names = [
    'openhands/runtime/plugins/agent_skills/agentskills.py',
    'openhands/runtime/plugins/agent_skills/file_ops/file_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/cst_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/ast_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/file_utils.py',
    'openhands/runtime/plugins/agent_skills/file_ops/so.py',
    'openhands/runtime/plugins/jupyter/execute_server.py',
    'openhands/runtime/plugins/vscode/__init__.py',
    'openhands/runtime/utils/bash.py',
    'openhands/runtime/action_execution_server.py',
    'openhands/linter/__init__.py',
    'sel/selenium_session_details.py',
    'sel/selenium_tester.py',
]
client = docker.from_env()
for c in client.containers.list():
    name = c.name
    if not name.startswith('kevin-'):
        continue
    if 'persisted' in name:
        print(name)
        # break
        # copy the file to the container
        container_id = c.id
        print(container_id)
        for full_file_name in full_file_names:
            cmd = f'docker cp {full_file_name} {container_id}:/openhands/code/{full_file_name}'
            # print(cmd)
            os.system(cmd)

        if 'root' in c.name:
            break
        # restart the container
print('Restarting the container')
c.restart()
print(datetime.now())
