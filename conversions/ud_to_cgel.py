from depedit import DepEdit
import conllu
from collections import defaultdict

test = False

filename = "en_ewt-ud-train.conllu.txt"
if test:
    filename = "test.conllu.txt"

infile = open(filename)
config_file  = open("../convertor/ud-to-cgel.ini")
d = DepEdit(config_file)
result = d.run_depedit(infile)

types = defaultdict(int)
pos = defaultdict(int)

sent = [0, 0]
tok = [0, 0]


for sentence in conllu.parse(result):
    sent[1] += 1
    full = True
    for word in sentence:
        tok[1] += 1
        if word['deprel'].islower():
            full = False
        else:
            tok[0] += 1
        pos[word['upos']] += 1
        types[(word['upos'], word['deprel'])] += 1
    if full:
        sent[0] += 1

with open('results.txt', 'w') as fout:
    fout.write(f'{sent[0]} / {sent[1]} sentences fully parsed ({sent[0] / sent[1]}).\n')
    fout.write(f'{tok[0]} / {tok[1]} words fully parsed ({tok[0] / tok[1]}).\n')
    fout.write('POS\n')
    for i in pos:
        fout.write(f'{i}, {pos[i]}\n')
    fout.write('\n')
    fout.write('DEP\n')
    for i in types:
        fout.write(f'{i}, {types[i]}\n')

with open('cgel.conllu', 'w') as fout:
    fout.write(result)