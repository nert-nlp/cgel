#!/bin/bash
set -eux

python add_page_numbers.py > pagified
python add_html_formatting.py cge01-2Ex.docx cge03Ex.docx cge04Ex.docx cge05Ex.docx cge06Ex.docx cge07Ex.docx cge08Ex.docx cge09Ex.docx cge10Ex.docx cge11Ex.docx cge12Ex.docx cge13Ex.docx cge14Ex.docx cge15Ex.docx cge16Ex.docx cge17Ex.docx
mv pagified.html cge01-17Ex.html
git checkout -- pagified.html
python pagified_html_to_yaml.py
YAML=cge01-17Ex.yaml
python strip_global_ex_ids.py $YAML > build/$YAML
python stats.py $YAML > STATS.md
