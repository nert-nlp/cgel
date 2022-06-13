import conllu
import sys
sys.path.append('../')
import cgel
from collections import Counter
from math import log

with open('../datasets/cgel_from_ud/ud_train.conllu') as f:
    ud_data = conllu.parse(f.read())

with open('../datasets/cgel_from_ud/cgel.trees.conllu') as f:
    cgel_data = conllu.parse(f.read())

cgel, ud, penn = Counter(), Counter(), Counter()
cgel_ud, ud_penn, penn_cgel = Counter(), Counter(), Counter()

tot = 0
for ud_tree, cgel_tree in zip(ud_data, cgel_data):
    for ud_tok, cgel_tok in zip(ud_tree, cgel_tree):
        ud_pos = ud_tok['upos']
        penn_pos = ud_tok['xpos']
        cgel_pos = cgel_tok['upos']
        
        ud[ud_pos] += 1
        penn[penn_pos] += 1
        cgel[cgel_pos] += 1
        cgel_ud[(cgel_pos, ud_pos)] += 1
        ud_penn[(ud_pos, penn_pos)] += 1
        penn_cgel[(penn_pos, cgel_pos)] += 1
        tot += 1

def H(c):
    res = 0
    for _, freq in c.items():
        res -= freq / tot * log(freq / tot, 2)
    return res

mi_cgel_ud = 0
for (cgel_pos, ud_pos), count in cgel_ud.items():
    mi_cgel_ud += (count / tot) * log((count * tot) / (cgel[cgel_pos] * ud[ud_pos]), 2)
mi_ud_penn = 0
for (ud_pos, penn_pos), count in ud_penn.items():
    mi_ud_penn += (count / tot) * log((count * tot) / (ud[ud_pos] * penn[penn_pos]), 2)
mi_penn_cgel = 0
for (penn_pos, cgel_pos), count in penn_cgel.items():
    mi_penn_cgel += (count / tot) * log((count * tot) / (penn[penn_pos] * cgel[cgel_pos]), 2) 
print(mi_cgel_ud, mi_ud_penn, mi_penn_cgel)
print(H(cgel), H(ud), H(penn))