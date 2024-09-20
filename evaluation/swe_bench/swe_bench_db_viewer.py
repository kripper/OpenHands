import os
import pickle

from datasets import load_dataset

instance_id = 'astropy__astropy-14182'

if not os.path.exists('./cache/filtered_data.pkl'):
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
else:
    with open('./cache/filtered_data.pkl', 'rb') as f:
        ins = pickle.load(f)

print(ins['base_commit'])
print(ins['hints_text'])


print(['problem_statement'])
print(ins['problem_statement'][0])
print('-' * 100)
print(['test_patch'])
print(ins['test_patch'][0])
