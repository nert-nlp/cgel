from depedit import DepEdit
import conllu
from collections import defaultdict

infile = open("en_ewt-ud-train.conllu.txt")
config_file  = open("ud-to-cgel.ini")
d = DepEdit(config_file)
result = d.run_depedit(infile)

types = defaultdict(int)

for sentence in conllu.parse(result):
    for word in sentence:
        types[(word['upos'], word['deprel'])] += 1

for i in types:
    print(i, types[i])