#!/usr/bin/env bash
sudo apt update
sudo apt install -y netcat
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.12
curl -sSL https://install.python-poetry.org | python3.12 -
cat << EOF > config.toml
[core]
workspace_base = "./workspace"
debug = 1

[sandbox]
use_host_network = 1
persist_sandbox = 1
fast_boot = 1
user_id = 1001
EOF
