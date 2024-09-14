import os
import subprocess

import docker

cmd = 'docker cp openhands/runtime/plugins/agent_skills/file_ops/file_ops.py 880cdf72bd6cc256c17797ad1baab2c121e0d1423cff13c114d97fbf9435af3f:/openhands/code/openhands/runtime/plugins/agent_skills/file_ops/file_ops.py'
print(subprocess.run(cmd, shell=0, capture_output=True).stdout)
# find why empty output

full_file_name = 'openhands/runtime/plugins/agent_skills/file_ops/file_ops.py'
full_file_name = r'openhands/runtime/client/client.py'
print(os.getcwd())
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
        out = subprocess.run(cmd.split(' '), shell=0, capture_output=True)
        print(out.stdout, out.stderr)

# restart the container
# print('Restarting the container')
# c.restart()
