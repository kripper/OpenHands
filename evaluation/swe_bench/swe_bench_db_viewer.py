import os
import pickle

import toml
from datasets import load_dataset

from evaluation.swe_bench.swe_bench2 import update_issue_description

with open(r'evaluation\swe_bench\config.toml', 'r') as f:
    config = toml.load(f)

# print(config)
# instance_id = 'astropy__astropy-14539'
instance_id = config['selected_ids'][0]
repo, issue_id = instance_id.rsplit('-', 1)
repo = repo.replace('__', '/')
url = f'https://github.com/{repo}/issues/{issue_id}'
print(url)
force = 0
for _ in range(2):
    if not os.path.exists('./cache/filtered_data.pkl') or force:
        dataset = load_dataset(
            'princeton-nlp/SWE-bench_Verified',
            cache_dir='./cache',
            verification_mode='no_checks',
            num_proc=4,
            split='test',
        )
        # Serialize filtered dataset
        ins = dataset.filter(lambda x: x['instance_id'] == instance_id)
        with open('./cache/filtered_data.pkl', 'wb') as f:
            pickle.dump(ins, f)
        break
    else:
        with open('./cache/filtered_data.pkl', 'rb') as f:
            ins = pickle.load(f)
    if instance_id != ins['instance_id'][0]:
        print(ins['instance_id'], instance_id)
        force = 1

#
print('base_commit', ins['base_commit'])
print('environment_setup_commit', ins['environment_setup_commit'])
# print(ins['hints_text'])

print(['problem_statement'])
# print(ins['problem_statement'][0])
a = update_issue_description(ins['problem_statement'][0], instance_id)
print(a)
if 1:
    print('-' * 100)
    print(['test_patch'])
    print(ins['FAIL_TO_PASS'][0])
    print('pass to pass')
    print(ins['PASS_TO_PASS'][0])
