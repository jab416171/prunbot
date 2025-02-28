#!/usr/bin/env bash

source ~/.venv/prun_bot_prod/bin/activate
source .env
PYTHONPATH=".:${PYTHONPATH}"
export PYTHONPATH
python prunbot/run.py
