import json

import toml


def check_if_resolved():
    status_path = 'evaluation/swe_bench/status.json'

    with open(status_path, 'r') as f:
        data = json.load(f)

    resolved_instances = [i[0] for i in data['resolved']][:-1]

    toml_path = 'evaluation/swe_bench/config.toml'

    with open(toml_path, 'r') as f:
        toml_data = toml.load(f)

    if toml_data['selected_ids'][0] in resolved_instances:
        print('already resolved')
        exit(0)
    else:
        print('not resolved')


if __name__ == '__main__':
    check_if_resolved()
