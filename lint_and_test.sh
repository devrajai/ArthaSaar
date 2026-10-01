#!/bin/bash
pip install flake8 pytest
flake8 scripts/history_collect.py --ignore=E501,E702,E402
