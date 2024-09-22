import os

import docker

full_file_name = 'openhands/runtime/plugins/agent_skills/file_ops/file_ops.py'
full_file_name = r'openhands/runtime/client/client.py'
client = docker.from_env()
for c in client.containers.list():
    if 'persisted' in c.name:
        print(c.name)
        # break
        # copy the file to the container
        container_id = c.id
        print(container_id)
        cmd = f'docker cp {full_file_name} {container_id}:/openhands/code/{full_file_name}'
        print(cmd)
        os.system(cmd)

        if 'root' in c.name:
            break
        # restart the container
print('Restarting the container')
c.restart()
