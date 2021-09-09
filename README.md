Parsing CGEL trees created in LaTeX by Brett Reynolds (@brettrey3 on Twitter, who also runs @DailySyntaxTree).

# Running the UD to CGEL conversion

First make a new Python environment in whatever environment manager you use.

```bash
pip install depedit
cd conversions
python -m depedit -c ud-to-cgel.ini en_ewt-ud-train.conllu.txt > cgel.conllu
```