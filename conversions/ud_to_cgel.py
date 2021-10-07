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

def penman(sentence, children, u, d):
    # print(u, children[u])
    add = False
    res = ''
    upos = sentence[u - 1]["upos"]
    form = sentence[u - 1]["form"]

    if u != 0:
        deprel = sentence[u - 1]['deprel']
        if deprel == 'Clause':
            res = f'({deprel}'
        else:
            if ':' in deprel:
                rel, pos = deprel.split(':')
            else:
                rel, pos = deprel, upos
            res += f'\n{"    " * d}:{rel} ({pos}'
    else:
        add = True
    
    for v in children[u]:
        if v > u and not add:
            res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'
            add = True
        res += penman(sentence, children, v, d + 1)
    if not add:
        res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'

    if u != 0: res += ')'
    return res

with open('cgel.trees.txt', 'w') as fout:
    for sentence in conllu.parse(result):
        sent[1] += 1
        full = True
        children = [[] for i in range(len(sentence) + 1)]

        for i, word in sentence:
            if isinstance(word['id'], tuple): continue
            children[int(word['head'])].append(int(word['id']))
            tok[1] += 1
            if word['deprel'].islower():
                full = False
            else:
                tok[0] += 1
            pos[word['upos']] += 1
            types[(word['upos'], word['deprel'])] += 1

        for key in sentence.metadata:
            fout.write(f'{key} = {sentence.metadata[key]}\n')
        fout.write(penman(sentence, children, 0, -1))
        fout.write('\n\n')

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