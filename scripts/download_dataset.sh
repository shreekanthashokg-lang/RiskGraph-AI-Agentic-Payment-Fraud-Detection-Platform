#!/usr/bin/env bash
# RiskGraph AI - public dataset setup
#
# RiskGraph AI ships with a synthetic generator (scripts/generate_synthetic_data.py)
# so the app runs immediately with zero downloads. This script is only needed if
# you want to additionally train/evaluate against a public fraud dataset.
#
# Datasets (NOT included in this repo - large + license-restricted):
#
#   1. IEEE-CIS Fraud Detection (primary)
#      https://www.kaggle.com/competitions/ieee-fraud-detection/data
#      License: Kaggle competition rules - for research/educational use;
#      requires a free Kaggle account + accepting competition terms.
#
#   2. PaySim (secondary)
#      https://www.kaggle.com/datasets/ealaxi/paysim1
#      License: CC BY-SA 4.0 (synthetic, derived from a real mobile-money log).
#
#   3. BankSim (optional)
#      https://www.kaggle.com/datasets/ealaxi/banksim1
#      License: research/educational use.
#
# Requires the Kaggle CLI (`pip install kaggle --break-system-packages`) and a
# ~/.kaggle/kaggle.json API token (never commit this file).

set -euo pipefail
mkdir -p data/raw

echo "Downloading IEEE-CIS Fraud Detection into data/raw/ieee-cis/ ..."
kaggle competitions download -c ieee-fraud-detection -p data/raw/ieee-cis
unzip -o data/raw/ieee-cis/ieee-fraud-detection.zip -d data/raw/ieee-cis

echo "Downloading PaySim into data/raw/paysim/ ..."
kaggle datasets download -d ealaxi/paysim1 -p data/raw/paysim
unzip -o data/raw/paysim/paysim1.zip -d data/raw/paysim

echo "Done. Raw files are git-ignored (see .gitignore) - do not commit them."
echo "For an immediate local run without any of this, use the synthetic dataset:"
echo "    python scripts/generate_synthetic_data.py"
