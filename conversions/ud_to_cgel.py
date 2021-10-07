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

def penman(node, d):
    # print(u, children[u])
    add = False
    res = ''
    upos, form, deprel = node.token["upos"], node.token["form"], node.token['deprel']

    if deprel == 'Clause':
        res = f'({deprel}'
    else:
        if ':' in deprel:
            rel, pos = deprel.split(':')
        else:
            rel, pos = deprel, upos
        res += f'\n{"    " * d}:{rel} ({pos}'
    
    for child in node.children:
        if child.token["id"] > node.token["id"] and not add:
            res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'
            add = True
        res += penman(child, d + 1)
    if not add:
        res += f'\n{"    " * (d + 1)}:Head ({upos} :t "{form}")'

    res += ')'
    return res

with open('cgel.trees.txt', 'w') as fout:
    for sentence in conllu.parse(result):
        sent[1] += 1
        parsed = True
        children = [[] for i in range(len(sentence) + 1)]

        for word in sentence:
            tok[1] += 1
            if word['deprel'].islower():
                parsed = False
            else:
                tok[0] += 1
            pos[word['upos']] += 1
            types[(word['upos'], word['deprel'])] += 1

        for key in sentence.metadata:
            fout.write(f'{key} = {sentence.metadata[key]}\n')

        tree = sentence.to_tree()
        fout.write(penman(tree, 0))
        fout.write('\n\n')

        if parsed:
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