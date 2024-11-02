import os
import pickle
from pprint import pprint

import toml
from datasets import load_dataset

from evaluation.swe_bench.swe_bench2 import update_issue_description
from sandbox_checker import execute_action, run, run_ipython

with open(r'evaluation\swe_bench\config.toml', 'r') as f:
    config = toml.load(f)

import re


def count_hunks_from_patch(patch):
    hunk_pattern = re.compile(r'^@@.*@@', re.MULTILINE)
    hunk_count = len(hunk_pattern.findall(patch))
    return hunk_count


# print(config)
# instance_id = 'astropy__astropy-14539'
instance_id = config['selected_ids'][0]
repo, issue_id = instance_id.rsplit('-', 1)
repo = repo.replace('__', '/')
url = f'https://github.com/{repo}/issues/{issue_id}'
print(url)


def get_instance(instance_id):
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
            print(ins['instance_id'], 'new ->', instance_id)
            force = 1
    return ins


if 0:
    instance_ids = [
        'django__django-13033',
        'django__django-13158',
        'django__django-13590',
        'django__django-14017',
        'django__django-14580',
        'django__django-14608',
        'django__django-14787',
        'matplotlib__matplotlib-24149',
        'sympy__sympy-12419',
        'sympy__sympy-16792',
        'sympy__sympy-17655',
    ]
    for instance_id in instance_ids:
        ins = get_instance(instance_id)
        print(instance_id, count_hunks_from_patch(ins['patch'][0]))
    exit()
else:
    ins = get_instance(instance_id)
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
    test_patch = ins['test_patch'][0]
    print(test_patch)
    if 1:
        code = rf"""
code = r'''{test_patch}'''
with open(f'/testbed/test_patch.diff', 'w') as f:
    f.write(code)
"""
        execute_action(run_ipython(code))
        cmd = 'git apply /testbed/test_patch.diff'
        execute_action(run(cmd))


if 0:
    print('-' * 100)
    print(['TEST PASS_TO_PASS'])
    pprint(ins['PASS_TO_PASS'][0])
    print(['TEST FAIL_TO_PASS'])
    pprint(ins['FAIL_TO_PASS'][0])
