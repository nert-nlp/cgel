#!/bin/bash
set -eux
cd analysis
python stats.py CGELBank > ../STATS.md
cd ..
python -m scripts.make_index CGELBank > INDEX.md
python -m scripts.make_treesfile > all.trees
