import os
from datetime import datetime

import docker

full_file_names = [
    'openhands/runtime/plugins/agent_skills/file_ops/file_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/cst_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/ast_ops.py',
    'openhands/runtime/plugins/agent_skills/file_ops/file_utils.py',
    r'openhands/runtime/utils/bash.py',
    r'openhands/runtime/action_execution_server.py',
]
client = docker.from_env()
for c in client.containers.list():
    if 'persisted' in c.name:
        print(c.name)
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
