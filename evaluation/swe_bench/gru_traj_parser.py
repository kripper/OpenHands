import json

from pyperclip import paste

traj = json.loads(paste())
# // script to print chat human friendly
for i in traj['trajectory']['details'][0]['exportedConversation']['plans'][0]:
    for j in i:
        print(j['thought'])
        print('' * 100)
