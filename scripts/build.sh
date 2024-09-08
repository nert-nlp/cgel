#!/bin/bash
set -eux
cd analysis
python stats.py > ../STATS.md
cd ..
python -m scripts.make_index > INDEX.md
python -m scripts.make_treesfile > all.trees
