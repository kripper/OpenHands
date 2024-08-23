import shutil

import docker

a = r'openhands\runtime\client\client.py'
b = r'workspace\client.py'

shutil.copy(a, b)

client = docker.from_env()
for c in client.containers.list():
    if 'persisted' in c.name:
        print(c.name)
        break
o = c.exec_run(
    'mv /workspace/client.py /openhands/code/openhands/runtime/client/client.py'
)
print(o.output.decode('utf-8'))

# restart the container
print('Restarting the container')
c.restart()
